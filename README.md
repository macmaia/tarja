# tarja

**EN** · Finds Brazilian personal identifiers (CPF, CNPJ etc) in free text, so you can mask them before data goes to an LLM, logs, BI, wherever.

Built for anyone shipping software in Brazil, incl. foreign companies adapting to the LGPD (Brazil's GDPR). Plenty of CPF/CNPJ validators exist already (brutils, validate-docbr). What's missing is finding the ID *inside* text, scoring it with Portuguese context, and covering what paid DLPs skip: alphanumeric CNPJ (Jul/2026), CNS (health card), CNJ case numbers.

Status: pre-alpha (`0.4.0.dev0`). API will change.

**PT** · Detecta docs brasileiros (CPF, CNPJ etc) em texto livre, p/ mascarar antes de mandar dado p/ LLM, log, BI, onde for.

Serve p/ qq um q desenvolve p/ o Brasil, inclusive empresa gringa se adaptando à LGPD. Validador de CPF/CNPJ já tem de monte (brutils, validate-docbr). O q falta é achar o doc *dentro* do texto, dar score c/ contexto em pt-BR e cobrir o q os DLPs pagos ignoram: CNPJ alfanumérico (jul/2026), CNS, nº de processo CNJ.

Status: pré-alfa (`0.4.0.dev0`). A API ainda muda.

## install / instalar

```bash
pip install -e ".[dev]"
```

## usage / uso

```python
import tarja

text = "Paciente CPF 529.982.247-25, cartao SUS 729 1417 7763 1701, processo 0000001-83.2017.8.26.0100"

for m in tarja.find(text):
    print(m.entity, m.start, m.end, m.score)  # BR_CPF 13 27 0.95 ...

tarja.mask(text)  # "Paciente CPF <BR_CPF>, cartao SUS <BR_CNS>, processo <BR_CNJ>"
tarja.mask(text, strategy="pseudonym")  # <BR_CPF_1>, same value -> same label / mesmo valor -> mesmo rotulo
tarja.mask(text, strategy="hash", salt="your-secret")  # <BR_CPF:3f9a1c0b2e7d>

tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35")  # True (alphanumeric CNPJ / CNPJ alfanum)
```

EN: `hash` is pseudonymisation, not anonymisation under the LGPD: whoever has the salt can link it back.
PT: `hash` é pseudonimização, não anonimização na LGPD: quem tem o salt consegue religar.

### command line / linha de comando

```bash
tarja scan contrato.txt                  # JSON lines, values hidden / valores escondidos
tarja scan contrato.txt --format table
tarja scan contrato.txt --show-values    # EN: raw values, careful / PT: valor cru, cuidado
tarja mask contrato.txt > limpo.txt
cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ --min-score 0.9
```

EN: exit code 1 when something is found, 0 when clean, 2 on error. Handy in CI.
PT: exit code 1 qdo acha algo, 0 qdo limpo, 2 em erro. Útil em CI.

## entities / entidades

| code | what it is / o q é | tier | status |
|---|---|---|---|
| `BR_CPF` | individual taxpayer ID / CPF | N1 | beta |
| `BR_CNPJ` | company ID, numeric + alphanumeric / CNPJ numérico + alfanum | N1 | beta |
| `BR_CNS` | national health card / cartão SUS | N1 | beta |
| `BR_NIS` | NIS / PIS / PASEP / NIT | N1 | experimental |
| `BR_CNJ` | court case number / nº de processo CNJ | N1 | beta |
| `BR_TITULO_ELEITOR` | voter ID / título de eleitor | N1 | beta |
| `BR_CNH` | driving licence / CNH (needs context / exige contexto) | N1 | experimental |
| `BR_RENAVAM` | vehicle registry / RENAVAM (needs context / exige contexto) | N1 | beta |
| `BR_PLACA` | number plate, old + Mercosur / placa antiga + Mercosul | N2 | beta |
| `BR_PIX_EVP` | PIX random key / chave PIX aleatória (needs context / exige contexto) | N2 | beta |
| `BR_TELEFONE` | phone / telefone | N2 | beta |
| `BR_CEP` | postcode / CEP (needs context / exige contexto) | N3 | beta |
| `BR_CNM` | national property registry number / Código Nacional de Matrícula | N1 | beta |
| `BR_CIB` | national property cadastre / Cadastro Imobiliário Brasileiro (needs context / exige contexto) | N1 | beta |
| `BR_IPTU` | municipal property tax ID / inscrição do IPTU (needs context / exige contexto) | N3 | experimental |
| `BR_MATRICULA_IMOVEL` | property registry number / matrícula do imóvel (needs context / exige contexto) | N3 | experimental |

EN: N1 = strong check digit, N2 = format only, N3 = needs context, N4 = NER. Scores: N1 0.95 with a context word nearby, 0.8 to 0.9 without. N2 0.7 / 0.5. N3 only with context, 0.5. Wrong check digit = dropped. Speed: ~1 ms per 100 tokens, 16 entities.
PT: N1 = DV forte, N2 = só formato, N3 = depende de contexto, N4 = NER. Score: N1 0.95 c/ palavra de contexto perto, 0.8 a 0.9 sem. N2 0.7 / 0.5. N3 só c/ contexto, 0.5. DV errado = descartado. Velocidade: ~1 ms por 100 tokens, 16 entidades.

## layout / organização

EN:
- `spec/entities/*.yaml`: one file per entity (regex, check digit, context, score, official source). Single source of truth, everything else is generated/tested from here.
- `spec/schema.json`: schema for those yaml files.
- `src/tarja/validators/`: check digits per document, stdlib only.
- `tests/`: `python -m unittest discover -s tests` or `pytest`.
- Tip: code comments carry tags like `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, so ctrl+f finds anything. Every comment is EN first, PT right after.

PT:
- `spec/entities/*.yaml`: 1 arquivo por entidade (regex, DV, contexto, score, fonte oficial). Fonte única, o resto é gerado/testado daqui.
- `spec/schema.json`: schema desses yaml.
- `src/tarja/validators/`: DV de cada doc, só stdlib.
- `tests/`: `python -m unittest discover -s tests` ou `pytest`.
- Dica: os comentários têm tags tipo `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, dá p/ achar tudo c/ ctrl+f. Todo comentário é EN primeiro, PT logo dps.

EN: official source for each rule, and whether it was checked: `docs/SOURCES.md`. Presidio plugin and upstream PR: `docs/presidio.md`.
PT: fonte oficial de cada regra, e se foi conferida: `docs/SOURCES.md`. Plugin do Presidio e PR: `docs/presidio.md`.

## licence / licença

Apache 2.0. EN: why, in `docs/decisions.md`. PT: motivo em `docs/decisions.md`.

Maintained by / mantido por [@macmaia](https://github.com/macmaia) · tarja@micah6ai.com
