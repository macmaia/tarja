<!-- .github/PULL_REQUEST_TEMPLATE.md
[PR-TEMPLATE] EN: the two things that break most often here are a spec change without regenerating, and a real
identifier reaching a public repository. Both are checkboxes rather than prose for that reason.
PT: os 2 erros mais comuns aqui são mudar a spec sem regerar, e dado real chegar a um repositório público. -->

## What changed / O que mudou

<!-- EN: one paragraph, and the issue it closes. PT: um parágrafo, e a issue que fecha. -->

Closes #

## Why / Por quê

<!-- EN: the behaviour before and after. For a detection change, say what it stops catching or starts catching.
     PT: o comportamento antes e depois. Se muda detecção, diga o que deixa de pegar ou passa a pegar. -->

## Checklist

- [ ] EN: no real personal data anywhere in the diff, including tests, fixtures and commit messages / PT: nenhum dado pessoal real no diff, incluindo testes, fixtures e mensagens de commit
- [ ] EN: tests pass: `pytest` / PT: testes passam
- [ ] EN: if I touched `spec/`, I ran `python tools/gen_entities.py` and committed the regenerated `src/tarja/entities.py` / PT: se mexi em `spec/`, rodei o `gen_entities.py` e commitei o `entities.py` regerado
- [ ] EN: a new or changed rule cites its normative source in the YAML, with the date it was accessed / PT: regra nova ou alterada cita a fonte normativa no YAML, com a data de acesso
- [ ] EN: new behaviour has a test that fails without the change / PT: comportamento novo tem teste que falha sem a mudança
- [ ] EN: public docstrings are bilingual, EN then PT / PT: docstring pública é bilíngue, EN depois PT

## Detection changes only / Só para mudança de detecção

<!-- EN: delete this section if the PR does not change what is detected.
     PT: apague esta seção se o PR não muda o que é detectado. -->

- [ ] EN: I ran the benchmark and pasted the before and after numbers below / PT: rodei o benchmark e colei os números antes e depois
- [ ] EN: I considered whether this changes the published results, and said so / PT: considerei se isso muda os resultados publicados, e disse

```
EN: paste the output of python -m bench.evaluate here / PT: cole a saída do bench.evaluate aqui
```
