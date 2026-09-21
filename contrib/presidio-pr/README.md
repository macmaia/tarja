# presidio-pr

**EN** · Everything for the upstream PR to [Presidio](https://github.com/data-privacy-stack/presidio) (E3.3 to E3.7): native `BrCpfRecognizer` and `BrCnpjRecognizer`, tests, config and docs snippets, PR text. The folder mirrors Presidio's paths, so files can be copied as they are.

**PT** · Tudo p/ o PR no Presidio (E3.3 a E3.7): `BrCpfRecognizer` e `BrCnpjRecognizer` nativos, testes, trechos de config e docs, texto do PR. A pasta espelha os caminhos do Presidio, então os arquivos são copiados como estão.

EN: the code here follows **Presidio's** conventions, not tarja's: English-only comments, `typing.Optional/List`, check digits inline with zero dependencies (their CONTRIBUTING asks to avoid new deps). That's why this folder is excluded from tarja's ruff config.
PT: o código aqui segue as convenções **do Presidio**, não as do tarja: comentários só em inglês, `typing.Optional/List`, DV inline sem dependência (o CONTRIBUTING deles pede p/ evitar deps novas). Por isso a pasta fica fora do ruff do tarja.

## files / arquivos

| file / arquivo | goes to / vai p/ | step |
|---|---|---|
| `presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/brazil/*.py` | same path / mesmo caminho | E3.4 |
| `presidio-analyzer/tests/test_br_*_recognizer.py` | same path / mesmo caminho | E3.6 |
| `default_recognizers.yaml.snippet` | `presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml` | E3.5 |
| `predefined_recognizers__init__.snippet` | `presidio-analyzer/presidio_analyzer/predefined_recognizers/__init__.py` | E3.5 |
| `supported_entities.snippet.md` | `docs/supported_entities.md` | E3.7 |
| `PR_DESCRIPTION.md` | EN: PR body / PT: texto do PR | E3.8 |

## steps (on your Mac) / passos (no seu Mac)

```bash
# E3.3 EN: fork + clone + dev env / PT: fork + clone + ambiente
gh repo fork data-privacy-stack/presidio --clone
cd presidio
git checkout -b feature/brazil-cpf-cnpj
# EN: follow docs/development.md in the fork for the exact env setup (it changes over time)
# PT: seguir o docs/development.md do fork p/ o setup exato (muda c/ o tempo)
cd presidio-analyzer
pip install -e ".[dev]"   # or / ou: the command in docs/development.md

# E3.4 + E3.6 EN: copy the files / PT: copia os arquivos
T=~/Desktop/EBAPE/doxxing-vaccine/tarja/contrib/presidio-pr/presidio-analyzer
cp -R $T/presidio_analyzer/predefined_recognizers/country_specific/brazil presidio_analyzer/predefined_recognizers/country_specific/
cp $T/tests/test_br_*_recognizer.py tests/

# E3.5 EN: paste the two snippets by hand / PT: colar os 2 trechos a mao
#   default_recognizers.yaml.snippet -> presidio_analyzer/conf/default_recognizers.yaml
#   predefined_recognizers__init__.snippet -> presidio_analyzer/predefined_recognizers/__init__.py

# E3.6 EN: run the tests + coverage / PT: roda testes + cobertura
pytest tests/test_br_cpf_recognizer.py tests/test_br_cnpj_recognizer.py --cov=presidio_analyzer/predefined_recognizers/country_specific/brazil --cov-report=term-missing
pytest   # EN: the whole suite must still pass / PT: a suite toda tem q continuar passando
ruff check . && ruff format --check .

# E3.7 EN: paste supported_entities.snippet.md into docs/supported_entities.md / PT: colar no docs/supported_entities.md
```

EN: things to double-check against the fork before opening the PR, because Presidio's internals may have moved since this was written: the `tests` helper `assert_result_within_score_range` and the `max_score` fixture, whether `PatternRecognizer.analyze` still de-duplicates overlapping matches of the same entity (the CPF tests expect 1 result per number), and the exact yaml keys.
PT: conferir no fork antes de abrir o PR, pq o Presidio pode ter mudado: o helper `assert_result_within_score_range` e a fixture `max_score` em `tests`, se o `PatternRecognizer.analyze` ainda remove match duplicado da mesma entidade (os testes de CPF esperam 1 resultado por número), e as chaves exatas do yaml.
