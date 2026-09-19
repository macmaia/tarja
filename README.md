# tarja

**EN** · Finds Brazilian personal identifiers (CPF, CNPJ etc) in free text, so you can mask them before data goes to an LLM, logs, BI, wherever.

Built for anyone shipping software in Brazil, incl. foreign companies adapting to the LGPD (Brazil's GDPR). Plenty of CPF/CNPJ validators exist already (brutils, validate-docbr). What's missing is finding the ID *inside* text, scoring it with Portuguese context, and covering what paid DLPs skip: alphanumeric CNPJ (Jul/2026), CNS (health card), CNJ case numbers.

Status: pre-alpha (`0.1.0.dev0`). API will change.

**PT** · Detecta docs brasileiros (CPF, CNPJ etc) em texto livre, p/ mascarar antes de mandar dado p/ LLM, log, BI, onde for.

Serve p/ qq um q desenvolve p/ o Brasil, inclusive empresa gringa se adaptando à LGPD. Validador de CPF/CNPJ já tem de monte (brutils, validate-docbr). O q falta é achar o doc *dentro* do texto, dar score c/ contexto em pt-BR e cobrir o q os DLPs pagos ignoram: CNPJ alfanumérico (jul/2026), CNS, nº de processo CNJ.

Status: pré-alfa (`0.1.0.dev0`). A API ainda muda.

## install / instalar

```bash
pip install -e ".[dev]"
```

## usage / uso

```python
import tarja

tarja.validate("BR_CPF", "529.982.247-25")        # True
tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35")   # True (alphanumeric CNPJ / CNPJ alfanum)

from tarja.validators import cnpj
cnpj.compute_check_digits("12ABC34501DE")         # "35"
cnpj.format("12abc34501de35")                     # "12.ABC.345/01DE-35"
```

EN: `tarja.find()` (search in text) lands in 0.2.
PT: `tarja.find()` (achar no texto) vem na 0.2.

## entities / entidades

| code | what it is / o q é | tier | status |
|---|---|---|---|
| `BR_CPF` | individual taxpayer ID / CPF | N1 | beta |
| `BR_CNPJ` | company ID, numeric + alphanumeric / CNPJ numérico + alfanum | N1 | beta |

EN: N1 = strong check digit, N2 = format only, N3 = needs context, N4 = NER.
PT: N1 = DV forte, N2 = só formato, N3 = depende de contexto, N4 = NER.

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

## licence / licença

Apache 2.0. EN: why, in `docs/decisions.md`. PT: motivo em `docs/decisions.md`.

Maintained by / mantido por [@macmaia](https://github.com/macmaia) · tarja@micah6ai.com
