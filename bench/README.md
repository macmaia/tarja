# tarja-bench

**EN** · Benchmark for detecting Brazilian personal identifiers in Portuguese text. Built for the resource paper (ARR, see the planning doc) and to compare tarja, Presidio, cloud DLPs, NER models and LLMs on equal terms.

**PT** · Benchmark de detecção de identificadores brasileiros em texto em português. Feito p/ o artigo de recurso (ARR) e p/ comparar tarja, Presidio, DLPs de nuvem, NER e LLMs nas mesmas condições.

## subsets / subconjuntos

| subset | docs | levels / níveis | source / origem |
|---|---|---|---|
| `synthetic_controlled` | 5,000 | D0, D1 | `bench/generate.py`, seed 42 |
| `synthetic_adversarial` | 3,000 | D2 to D5 | `bench/generate.py`, seed 42 |
| `semireal` | EN: you choose / PT: vc escolhe | D0 | `bench/semireal.py` + EN: public texts / PT: textos públicos |
| `real` (restricted / restrito) | 1,000 | - | EN: annotated by hand, never published / PT: anotado à mão, nunca publicado |

Split: 30% dev / 70% test.

| level | EN | PT |
|---|---|---|
| D0 | canonical layout | layout canônico |
| D1 | no punctuation, or spaces instead of separators | sem pontuação, ou espaço no lugar do separador |
| D2 | line break inside, glued to the previous word, table cell | quebra de linha no meio, colado na palavra anterior, célula de tabela |
| D3 | invalid look-alikes as distractors (not annotated) | parecidos inválidos como distratores (não anotados) |
| D4 | OCR noise: O for 0, l for 1 (annotated) | ruído de OCR: O no lugar de 0, l no lugar de 1 (anotado) |
| D5 | misleading context: word says CPF, number is a NIS | contexto enganoso: palavra diz CPF, número é NIS |

## data / dados

EN: the JSONL files are NOT committed (they'd trip the 500 KB pre-commit limit and they're 100% reproducible). `bench/data/v0.1/manifest.json` is committed with each file's sha256, and a test regenerates everything and checks the hashes. To get the files:
PT: os JSONL NÃO são commitados (passariam do limite de 500 KB do pre-commit e são 100% reprodutíveis). O `manifest.json` vai p/ o git c/ o sha256 de cada arquivo, e um teste regera tudo e confere. P/ ter os arquivos:

```bash
python -m bench.generate --seed 42 --out bench/data/v0.1
```

EN: format, one JSON per line / PT: formato, 1 JSON por linha:
`{"id", "domain", "difficulty", "text", "spans": [{"start", "end", "entity"}]}`

## run a system / rodar um sistema

```bash
python -m bench.run --system tarja --data bench/data/v0.1/synthetic_adversarial.test.jsonl
python -m bench.evaluate --gold bench/data/v0.1/synthetic_adversarial.test.jsonl --pred bench/results/tarja__synthetic_adversarial.test.json
```

| system | EN: needs / PT: precisa |
|---|---|
| `tarja` | - |
| `presidio-default`, `presidio-br` | `pip install presidio-analyzer` (+ `packages/presidio-br`) |
| `azure` | `pip install azure-ai-textanalytics`, `AZURE_LANGUAGE_ENDPOINT`, `AZURE_LANGUAGE_KEY` |
| `google-sdp` | `pip install google-cloud-dlp`, `GOOGLE_CLOUD_PROJECT`, `gcloud auth application-default login` |
| `macie` | EN: upload each doc as `s3://bucket/bench/<id>.txt`, run a Macie classification job, export findings JSON, `MACIE_FINDINGS_JSON=...` / PT: sobe cada doc como `<id>.txt`, roda job de classificação, exporta os findings, `MACIE_FINDINGS_JSON=...` |
| `purview` | EN: run the docs through a DLP policy test, export CSV `doc_id,sit_name,start,end`, `PURVIEW_EXPORT_CSV=...` / PT: idem |
| `spacy` | `pip install spacy && python -m spacy download pt_core_news_lg` |
| `llm` | `--provider anthropic|openai --model <id>`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` |

EN: LLM protocol: prompt versioned in `bench/prompts/llm_v1.txt`, temperature 0, every answer cached in `bench/cache/` (re-runs are free and identical). Cloud runs: the date is stored in the result; write down the cost.
PT: protocolo LLM: prompt versionado em `bench/prompts/llm_v1.txt`, temperatura 0, toda resposta em cache em `bench/cache/` (rodar de novo é grátis e idêntico). Nuvem: a data fica no resultado; anote o custo.

## metrics / métricas

EN: span-level P/R/F1, three modes (`exact`, `partial`, `untyped`), per entity and per difficulty, 95% CI by bootstrap over documents (1,000 resamples).
PT: P/R/F1 por span, 3 modos (`exact`, `partial`, `untyped`), por entidade e por dificuldade, IC 95% por bootstrap de documentos (1.000 reamostras).

## first numbers (tarja 0.5.0.dev0, test split) / primeiros números

| subset | exact F1 | partial F1 | EN: weakest level / PT: nível mais fraco |
|---|---|---|---|
| controlled | 0.980 | 0.984 | D1 0.958 (D0 1.000) |
| adversarial | 0.822 | 0.839 | D4 0.255 (OCR noise / ruído de OCR) |

EN: history. Before 19/09/2026: controlled 0.950 / adversarial 0.797 exact F1 (D1 0.874, D2 0.890). The fixes for spaced separators (CNPJ, CNJ, NIS, CNM, CIB) and tighter matricula context were tuned on the dev split only, and the test split was run once afterwards. OCR noise (D4) is left as a stated limitation on purpose: fixing the level where tarja is weakest, on a benchmark its author built, would not be credible.
PT: histórico. Antes de 19/09/2026: controlado 0,950 / adversarial 0,797 de F1 exato (D1 0,874, D2 0,890). As correções de separador c/ espaço (CNPJ, CNJ, NIS, CNM, CIB) e do contexto da matrícula foram ajustadas só no dev, e o teste rodou 1 vez no fim. O ruído de OCR (D4) fica como limitação declarada de propósito: corrigir o nível mais fraco do tarja num benchmark feito pela mesma autora não seria crível.

## independence of the gold / independência do gold

EN: labels come from the generator, and the generator uses check-digit code. To keep tarja from grading itself, every generated value must also pass `bench/reference.py`, a separate implementation written from the official rules with no imports from tarja (CPF, CNPJ, CNS, NIS, CNJ, voter ID, RENAVAM, card). CNH, CNM and CIB have no reference yet and rely on tarja alone. Where `validate-docbr` is installed, a test also checks CPF, CNS, NIS and RENAVAM against it. D0 scores near 1.0 are expected by construction and are NOT evidence of real-world accuracy. That comes from the semi-real subset and the hand-annotated sample (E4.4).
PT: os rótulos vêm do gerador, e o gerador usa código de DV. P/ o tarja não se autoavaliar, todo valor gerado também tem q passar no `bench/reference.py`, implementação separada, escrita a partir das regras oficiais, sem importar nada do tarja (CPF, CNPJ, CNS, NIS, CNJ, título, RENAVAM, cartão). CNH, CNM e CIB ainda não têm referência e dependem só do tarja. Onde o `validate-docbr` estiver instalado, um teste compara CPF, CNS, NIS e RENAVAM c/ ele. Score perto de 1,0 no D0 é esperado por construção e NÃO prova acerto no mundo real. Isso vem do semi-real e da amostra anotada à mão (E4.4).

## annotation / anotação

EN: `ANNOTATION_GUIDE.md` + `python -m bench.iaa --a a.jsonl --b b.jsonl` for inter-annotator agreement.
PT: `ANNOTATION_GUIDE.md` + `python -m bench.iaa --a a.jsonl --b b.jsonl` p/ concordância entre anotadores.
