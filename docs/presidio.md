# tarja + Presidio

EN: two ways to get Brazilian identifiers into Presidio.
PT: 2 jeitos de ter identificadores brasileiros no Presidio.

| | `tarja-presidio` (plugin, E3.1) | upstream PR (E3.4) |
|---|---|---|
| EN: entities / PT: entidades | all 16 tarja entities / todas as 16 | CPF + CNPJ |
| EN: install / PT: instalação | EN: not on PyPI yet, install from the repo / PT: ainda não está no PyPI, instale do repo:<br>`pip install "tarja-presidio @ git+https://github.com/macmaia/tarja.git#subdirectory=packages/tarja-presidio"` | EN: built into Presidio once merged / PT: nativo qdo aceitarem |
| EN: updates / PT: atualização | EN: follows tarja releases / PT: segue o tarja | EN: Presidio's release cycle / PT: ciclo do Presidio |

## example / exemplo (E3.2)

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
import tarja_presidio

# EN: Portuguese NLP engine (spaCy). One-off: python -m spacy download pt_core_news_md
# PT: motor NLP em portugues (spaCy). Uma vez: python -m spacy download pt_core_news_md
nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pt", "model_name": "pt_core_news_md"}],
    }
).create_engine()

registry = RecognizerRegistry(supported_languages=["pt"])
registry.load_predefined_recognizers(languages=["pt"], nlp_engine=nlp_engine)  # EN: e-mail, names... / PT: e-mail, nomes...
tarja_presidio.register(registry)  # EN: 16 Brazilian entities / PT: 16 entidades brasileiras

analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=["pt"])

text = "Paciente Maria, CPF 529.982.247-25, cartao SUS 898 0000 0004 3208, CEP 22290-140."
for r in analyzer.analyze(text=text, language="pt", score_threshold=0.4):
    print(r.entity_type, text[r.start : r.end], round(r.score, 2))
```

EN: expected: `BR_CPF` and `BR_CNS` at 1.0 (valid check digit), `BR_CEP` only when the context enhancer lifts it above the threshold (the word "CEP" is right before it), plus `PERSON` from spaCy.
PT: esperado: `BR_CPF` e `BR_CNS` c/ 1.0 (DV válido), `BR_CEP` só se o enhancer de contexto subir acima do limite (a palavra "CEP" tá logo antes), mais `PERSON` do spaCy.

## scores

| tarja | Presidio (`tarja-presidio`) |
|---|---|
| EN: wrong check digit / PT: DV errado | `validate_result -> False`, EN: dropped / PT: descartado |
| EN: valid check digit / PT: DV válido | `validate_result -> True`, score 1.0 |
| EN: context required (CEP, CNH, RENAVAM, PIX, CIB, IPTU, matrícula) / PT: exige contexto | EN: base 0.1, raised by Presidio's context enhancer; use `score_threshold` / PT: base 0.1, sobe c/ o enhancer de contexto; use `score_threshold` |
| EN: no check digit (plate, phone) / PT: sem DV (placa, telefone) | EN: tarja's "without context" score / PT: score "sem contexto" do tarja |

EN: tarja's own `find()` is stricter (context-required entities never appear without context). Use tarja directly when you don't need the rest of Presidio.
PT: o `find()` do próprio tarja é mais rígido (entidade q exige contexto nunca aparece sem ele). Use o tarja direto qdo não precisar do resto do Presidio.
