# Presidio em português: por que o padrão não pega CPF, e como resolver

PT: esta página está em português primeiro, ao contrário do resto da documentação, porque o problema que ela
resolve é procurado em português.
EN: this page is Portuguese first, unlike the rest of the docs, because the problem it solves is searched for
in Portuguese. Short English summary at the end.

O [Presidio](https://microsoft.github.io/presidio/) é a biblioteca aberta da Microsoft para achar e anonimizar
dado pessoal em texto. Ele funciona bem em inglês. Em português, a primeira coisa que quase todo mundo tenta é
achar um CPF, e não acha nada. Esta página explica por quê, mostra três caminhos e diz quando cada um vale.

## O que acontece

```python
from presidio_analyzer import AnalyzerEngine

analyzer = AnalyzerEngine()
texto = "Paciente Maria, CPF 529.982.247-25, cartao SUS 729 1417 7763 1701."
print(analyzer.analyze(text=texto, language="en"))
```

O CPF não aparece. Dependendo da configuração, ou não sai nada, ou sai um `PERSON` errado, ou o número é
classificado como algo genérico. Não é defeito de instalação.

## Por que

Três razões somadas, e todas as três precisam ser entendidas para a solução fazer sentido.

**O Presidio não procura "dado pessoal", ele procura entidades que alguém registrou.** A arquitetura é um
registro de reconhecedores, um por tipo de entidade. Existem reconhecedores prontos para `US_SSN`,
`UK_NHS`, `IN_AADHAAR` e outros. Nenhum para CPF, CNPJ, título de eleitor ou cartão do SUS. Onde não há
reconhecedor, não há detecção, e o Presidio não avisa que não sabe procurar.

**Reconhecedor é preso a um idioma.** Cada reconhecedor declara `supported_language`. Carregar os
reconhecedores padrão com `language="pt"` traz muito pouco, porque quase todos declaram `en`. Hoje a chave
`pt` não aparece no `default_recognizers.yaml` do projeto.

**Regex sozinho produz falso positivo em volume.** Um CPF é onze dígitos, e onze dígitos em texto
administrativo brasileiro também é protocolo, matrícula, número de processo e código interno. Detectar por
formato apenas transforma o relatório em ruído. É aqui que entra a parte que mais muda o resultado, adiante.

## Caminho 1: escrever o seu reconhecedor

É o caminho que ensina como o Presidio funciona, e que serve para qualquer identificador, inclusive os
internos da sua empresa.

Um CPF tem dois dígitos verificadores calculados por módulo 11 sobre os nove primeiros. Isso é o que separa um
CPF de onze dígitos quaisquer, e é a diferença entre um relatório útil e uma lista de números.

```python
from presidio_analyzer import Pattern, PatternRecognizer


def cpf_valido(valor: str) -> bool:
    d = [int(c) for c in valor if c.isdigit()]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for n in (9, 10):
        soma = sum(d[i] * ((n + 1) - i) for i in range(n))
        dv = (soma * 10) % 11
        if (0 if dv == 10 else dv) != d[n]:
            return False
    return True


class CpfRecognizer(PatternRecognizer):
    PATTERNS = [Pattern("cpf", r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", 0.3)]
    CONTEXT = ["cpf", "cadastro de pessoa fisica"]

    def __init__(self, supported_language: str = "pt"):
        super().__init__(
            supported_entity="BR_CPF",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str):
        # True sobe o score p/ 1.0, False descarta o achado, None deixa como está
        return cpf_valido(pattern_text)
```

E registrar:

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

registry = RecognizerRegistry(supported_languages=["pt"])
registry.add_recognizer(CpfRecognizer())
analyzer = AnalyzerEngine(registry=registry, supported_languages=["pt"])

for r in analyzer.analyze(text=texto, language="pt"):
    print(r.entity_type, texto[r.start:r.end], round(r.score, 2))
```

O `validate_result` é a peça central e é frequentemente ignorada. Devolver `False` faz o Presidio **descartar**
o achado, não apenas rebaixá-lo. É isso que tira do relatório o número de protocolo que por acaso tinha onze
dígitos.

Repetir esse trabalho para CNPJ, CNS, CNJ, título de eleitor, NIS, RENAVAM, CNH, CEP, placa e telefone dá
bastante trabalho, e cada um tem uma regra diferente. O CNS tem rotina oficial do Ministério da Saúde. O
processo judicial usa ISO 7064 módulo 97-10. O CNPJ passou a aceitar letras. É por isso que existe o caminho 2.

## Caminho 2: usar o tarja pelo Presidio

O [tarja](https://github.com/macmaia/tarja) implementa as 16 entidades brasileiras com a validação de cada uma,
e o `tarja-presidio` registra todas elas no Presidio de uma vez.

O `tarja-presidio` ainda não está no PyPI. Hoje se instala direto do repositório:

```bash
pip install tarja
pip install "tarja-presidio @ git+https://github.com/macmaia/tarja.git#subdirectory=packages/tarja-presidio"
python -m spacy download pt_core_news_md
```

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
import tarja_presidio

nlp_engine = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "pt", "model_name": "pt_core_news_md"}],
}).create_engine()

registry = RecognizerRegistry(supported_languages=["pt"])
registry.load_predefined_recognizers(languages=["pt"], nlp_engine=nlp_engine)
tarja_presidio.register(registry)

analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=["pt"])
for r in analyzer.analyze(text=texto, language="pt", score_threshold=0.4):
    print(r.entity_type, texto[r.start:r.end], round(r.score, 2))
```

O motor do spaCy continua valendo a pena mesmo com os identificadores resolvidos, porque é ele que traz
`PERSON` e as entidades que dependem de linguagem, que os identificadores estruturados não cobrem.

## Caminho 3: usar o tarja direto, sem Presidio

Se o que você precisa é só achar e mascarar identificador brasileiro, o Presidio é uma camada a mais para
instalar, configurar e manter.

```bash
pip install tarja
```

```python
import tarja

tarja.mask(texto)   # "Paciente Maria, CPF <BR_CPF>, cartao SUS <BR_CNS>."
```

O tarja não tem dependência em tempo de execução e o `find()` é mais rígido que a versão pelo Presidio: uma
entidade que exige contexto nunca aparece sem contexto.

## Qual escolher

| Situação | Caminho |
|---|---|
| Já usa Presidio, quer nome e endereço junto | 2 |
| Já usa Presidio e tem identificador interno próprio | 1, e 2 para os brasileiros |
| Só precisa de identificador brasileiro, em lote | 3 |
| Quer entender como o Presidio funciona por dentro | 1 |
| Texto em inglês, sem identificador brasileiro | Presidio padrão, sem nada disto |

A última linha é séria. Se o seu texto é em inglês e você não precisa de identificador brasileiro, o Presidio
padrão resolve e nada nesta página se aplica.

## Estado do upstream

Há uma proposta aberta no repositório do Presidio adicionando reconhecedores de CPF e CNPJ ao projeto, com uma
questão em aberto sobre declarar o idioma como `pt` ou `en`, já que a chave `pt` ainda não existe na
configuração padrão deles. Se for aceita, os dois passam a vir nativos, e o `tarja-presidio` continua útil para as
outras catorze entidades.

## Limites

Nada aqui detecta nome, endereço ou dado clínico em prosa: isso depende de reconhecimento de entidade nomeada e
é o que o motor do spaCy faz, com a qualidade que ele tem em português. Ausência de achado não é prova de
ausência de dado pessoal. E dígito verificador válido não significa que o número pertence a alguém real, apenas
que ele é bem formado.

---

**EN, short version.** Presidio ships no recognizer for Brazilian identifiers, and its recognizers are
per-language while almost all defaults declare `en`, so CPF is simply not looked for. Format-only regex is not
enough either, because eleven digits is also a protocol or case number in Brazilian administrative text. Three
ways out: write a `PatternRecognizer` whose `validate_result` checks the mod-11 digits (the code above is
complete), register all sixteen Brazilian entities through `tarja-presidio`, which is powered by tarja, or skip
Presidio and use tarja directly when identifiers are all you need.
