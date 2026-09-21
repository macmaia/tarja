# contributing / contribuindo

## setup

```bash
git clone https://github.com/macmaia/tarja && cd tarja
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" pre-commit
pre-commit install                   # EN: lint on every commit / PT: lint em todo commit
pytest                               # EN: min. 90% coverage / PT: cobertura min. 90%
ruff check . && ruff format --check .
```

## new entity / entidade nova

EN:
1. Open an issue first with the entity, the official standard and a few examples.
2. Create `spec/entities/<id>.yaml` following `spec/schema.json` (id with `BR_` prefix). Fill in `description` (EN-UK) and `description_pt`.
3. `sources` must point to the official standard for the algorithm (Receita, TSE, Ministry of Health, CNJ...). No official source = goes in as `experimental`.
4. Validator in `src/tarja/validators/<name>.py`: pure function, stdlib only, source repeated at the top, every block commented in short English with a `[NAME-THING]` tag. Public docstrings are bilingual, EN first then PT.
5. Tests: official case, wrong check digit, bad format, repeated digits (where it makes sense) and one property test (generate, validate, mutate).
6. Add the id to `spec/registry.yaml` and run `python tools/gen_entities.py`. Never edit `src/tarja/entities.py` by hand: it is generated and CI checks it.

EN: an identifier that only matters to you (a company ID, one state's IE) does not need a PR: use `tarja.register_entity()` at start-up.

PT:
1. Abre uma issue antes, c/ a entidade, a norma oficial e uns exemplos.
2. Cria `spec/entities/<id>.yaml` seguindo `spec/schema.json` (id c/ prefixo `BR_`). Preenche `description` (EN-UK) e `description_pt`.
3. `sources` c/ a norma oficial do algoritmo (Receita, TSE, MS, CNJ...). Sem fonte oficial entra como `experimental`.
4. Validador em `src/tarja/validators/<nome>.py`: função pura, só stdlib, fonte repetida no topo, todo bloco comentado em inglês curto c/ tag `[NOME-ALGO]`. Docstring pública bilíngue, EN primeiro e PT dps.
5. Testes: caso oficial, DV errado, formato ruim, repetidos (qdo fizer sentido) e 1 teste de propriedade (gera, valida, muta).
6. Põe o id no `spec/registry.yaml` e roda `python tools/gen_entities.py`. Nunca edite o `src/tarja/entities.py` à mão: ele é gerado e o CI confere.

PT: identificador q só importa p/ vc (matrícula de empresa, IE de 1 estado) não precisa de PR: use `tarja.register_entity()` na inicialização.

## real data: no / dado real: não

EN: never, anywhere (code, tests, issues, PRs, logs). Only generated numbers with valid check digits or examples published by a public body. Found real data here? See `SECURITY.md`.
PT: nunca, em lugar nenhum (código, teste, issue, PR, log). Só número gerado c/ DV válido ou exemplo publicado por órgão oficial. Achou dado real aqui? Ver `SECURITY.md`.

## commits / PRs

EN:
- `git commit -s` (DCO, https://developercertificate.org)
- one PR per entity or per change
- in the PR, say how you tested accuracy
- code identifiers in UK English (`normalise`, not `normalize`)

PT:
- `git commit -s` (DCO, https://developercertificate.org)
- 1 PR por entidade ou por mudança
- no PR, conta como vc testou a acurácia
- nomes no código em inglês UK (`normalise`, não `normalize`)

## conduct / conduta

EN: see `CODE_OF_CONDUCT.md`. PT: ver `CODE_OF_CONDUCT.md`.
