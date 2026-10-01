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

EN: an identifier that only matters to you (a company ID, one state's IE) does not need a PR: use `tarja.register_entity()` at start-up, then `tarja.freeze()` before serving requests. The registry is module-level state that `find()` reads on every call, so registration belongs in start-up and nowhere else. `freeze()` makes a late registration raise `RegistryFrozenError` instead of racing a reader.

PT:
1. Abre uma issue antes, c/ a entidade, a norma oficial e uns exemplos.
2. Cria `spec/entities/<id>.yaml` seguindo `spec/schema.json` (id c/ prefixo `BR_`). Preenche `description` (EN-UK) e `description_pt`.
3. `sources` c/ a norma oficial do algoritmo (Receita, TSE, MS, CNJ...). Sem fonte oficial entra como `experimental`.
4. Validador em `src/tarja/validators/<nome>.py`: função pura, só stdlib, fonte repetida no topo, todo bloco comentado em inglês curto c/ tag `[NOME-ALGO]`. Docstring pública bilíngue, EN primeiro e PT dps.
5. Testes: caso oficial, DV errado, formato ruim, repetidos (qdo fizer sentido) e 1 teste de propriedade (gera, valida, muta).
6. Põe o id no `spec/registry.yaml` e roda `python tools/gen_entities.py`. Nunca edite o `src/tarja/entities.py` à mão: ele é gerado e o CI confere.

PT: identificador q só importa p/ vc (matrícula de empresa, IE de 1 estado) não precisa de PR: use `tarja.register_entity()` na inicialização e `tarja.freeze()` antes de servir requisição. O registro é estado de módulo q o `find()` lê a cada chamada, então registrar é coisa de start-up. O `freeze()` faz registro tardio levantar `RegistryFrozenError` em vez de correr contra um leitor.

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

## release / publicação

EN: releasing is not `git tag` on its own.

1. bump `__version__` in `src/tarja/__init__.py` (and in `packages/tarja-presidio/src/tarja_presidio/__init__.py` for the plugin)
2. write the `CHANGELOG.md` entry. A release that changes what `find()` detects carries the benchmark numbers before and after. One that only changes the command line says so and gives the figures it re-measured
3. `python -m pytest -q && python -m ruff check . && python -m ruff format --check . && python -m mypy src`
4. `python tools/mutation_check.py`. A surviving mutant blocks the release
5. commit, push, and **open the resulting CI and audit runs**. Both have to be green on the commit you are about to tag
6. `git tag v0.9.0 && git push origin v0.9.0`. The release workflow re-checks the audit run itself and refuses to build if it is not green on `main`
7. `gh release create <tag>` with the changelog entry as the notes

EN: **step 5 is the one that gets skipped, and it is the one that matters.** The audit job ran red for five
days across eight consecutive runs, with three stacked flag fixes, and nothing was wrong with the fixes: the
runs were never opened. A fix recorded without the run id that proves it is not a fix, it is a hypothesis.
When you write down a root cause, write the run id next to it.

PT: publicar não é só `git tag`. O passo 5 é o que se esquece e é o que importa: o job de audit ficou
vermelho cinco dias em oito rodadas seguidas, com três correções empilhadas, e o problema não era nenhuma
delas. Ninguém abriu as rodadas. Correção registrada sem o id da rodada que prova não é correção, é hipótese.

## conduct / conduta

EN: see `CODE_OF_CONDUCT.md`. PT: ver `CODE_OF_CONDUCT.md`.
