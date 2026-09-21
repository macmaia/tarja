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

EN: the JSONL files are NOT committed (they'd trip the 500 KB pre-commit limit and they're 100% reproducible). `bench/data/v0.2/manifest.json` is committed with each file's sha256, and a test regenerates everything and checks the hashes. To get the files:
PT: os JSONL NÃO são commitados (passariam do limite de 500 KB do pre-commit e são 100% reprodutíveis). O `manifest.json` vai p/ o git c/ o sha256 de cada arquivo, e um teste regera tudo e confere. P/ ter os arquivos:

```bash
python -m bench.generate --seed 42 --out bench/data/v0.2
```

EN: format, one JSON per line / PT: formato, 1 JSON por linha:
`{"id", "domain", "difficulty", "text", "spans": [{"start", "end", "entity"}]}`

## run a system / rodar um sistema

```bash
python -m bench.run --system tarja --data bench/data/v0.2/synthetic_adversarial.test.jsonl
python -m bench.evaluate --gold bench/data/v0.2/synthetic_adversarial.test.jsonl --pred bench/results/tarja__synthetic_adversarial.test.json
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

## test-split log / registro de uso do teste

EN: every time tarja was scored on the TEST split, and why. Tuning happens on dev only. Report this table in the paper.
PT: toda vez q o tarja rodou no TESTE, e por quê. Ajuste só no dev. Reportar esta tabela no artigo.

| date / data | tarja | bench data | why / motivo | controlled F1 (exact) | adversarial F1 (exact) |
|---|---|---|---|---|---|
| 2026-09-18 | 0.4.0.dev0 | v0.1 initial | first numbers / primeiros números | 0.946 | 0.786 |
| 2026-09-19 | 0.5.0.dev0 | v0.1 + BR_CARTAO | new entity changed the data / entidade nova mudou os dados | 0.950 | 0.791 |
| 2026-09-19 | 0.5.0.dev0 | v0.1 + reference validators | gold regenerated (look-alikes stricter) / gold regerado | 0.950 | 0.797 |
| 2026-09-19 | 0.5.0.dev0 | same / igual | after fixes tuned on dev (spaced separators, matricula adjacency) / dps das correções ajustadas no dev | 0.980 | 0.822 |
| 2026-09-21 | 0.6.0.dev0 | **v0.2** | BR_CARTAO now needs a registered issuer prefix, not Luhn alone, which changed the D3 look-alikes. Generation also moved to one random stream per document, so a future validator change moves only the documents that use that entity / BR_CARTAO passou a exigir prefixo de emissor, e a geração passou a ter um fluxo aleatório por documento | 0.978 | 0.825 |

EN: the bench data changed twice before any release, so `BENCH_VERSION` stayed 0.1.0 up to 20/09. The card
validator change on 21/09 altered the generated corpus, so the version moved to **0.2.0**. Nothing had been
published to Zenodo yet, which is why this was cheap. From the Zenodo freeze on, any change bumps the version
and gets a row here before the numbers are quoted anywhere.
PT: os dados mudaram 2x antes de qq publicação, entao o `BENCH_VERSION` ficou em 0.1.0 até 20/09. A mudança no
validador de cartão em 21/09 alterou o corpus gerado, entao a versão foi p/ **0.2.0**. Nada tinha subido no
Zenodo ainda, e por isso saiu barato. A partir do congelamento no Zenodo, qq mudança sobe a versão e ganha uma
linha aqui antes de o número ser citado em qq lugar.

EN: the v0.1 to v0.2 move is within resampling noise, which is the reassuring answer: controlled 0.980 to
0.978, adversarial 0.822 to 0.825, semi-real 0.990 unchanged. Per difficulty, partial F1 went D0 1.000,
D1 0.958 to 0.957, D2 0.972 to 0.963, D3 0.997 unchanged, D4 0.255 to 0.266, D5 0.884 to 0.895. Requiring an
issuer prefix on BR_CARTAO cost nothing measurable here, because the benchmark's cards were always generated
with a Visa prefix. What it buys is on real text, where Luhn alone fires on roughly one in ten long numeric
strings.
PT: a passagem da v0.1 p/ a v0.2 fica dentro do ruido de reamostragem, q e a resposta tranquilizadora:
controlado 0.980 p/ 0.978, adversarial 0.822 p/ 0.825, semi-real 0.990 igual. Exigir prefixo de emissor no
BR_CARTAO nao custou nada aqui, pq o cartao do benchmark sempre foi gerado c/ prefixo Visa. O ganho esta em
texto real.

EN: **why one random stream per document.** With a single shared stream, the generator asks the validator
whether a candidate look-alike is invalid, and a stricter validator changes that answer, which shifts every
draw after the first difference and rewrites the whole corpus. Deriving the stream from (seed, subset, index)
keeps the damage local: only documents that use the changed entity move.
PT: **por que um fluxo aleatório por documento.** C/ um fluxo só, mudar o validador deslocava todos os sorteios
seguintes e reescrevia o corpus inteiro. Derivando de (semente, subconjunto, índice), só os documentos da
entidade alterada mudam.

## related benchmarks / benchmarks relacionados

EN: two 2026 preprints are close and should be cited as concurrent work. REDACT (Vats et al., arXiv 2606.19881) is a controlled multilingual benchmark with Brazilian Portuguese as a locale and checksum specifications in its generator, but its identification types stop at generic classes (national ID, tax reference), it has no examples that fail a checksum and no surface-format axis. Brazilian-PHI (Eduardo, Research Square 10.21203/rs.3.rs-10757966/v1) has 500 synthetic Portuguese clinical notes with check-digit validation for CPF and CNPJ, scored against distractors from other code families (ICD-10, dates, facility codes, dosages), with every identifier valid by construction, CNS by regex only, no alphanumeric CNPJ, no court case numbers and no surface noise. What tarja-bench adds: same-class look-alikes that fail the check digit as labelled negatives (D3), document noise as controlled levels (D1, D2, D4), misleading context (D5), and 17 Brazilian types including CNJ, CNM, CIB and the alphanumeric CNPJ.
PT: 2 preprints de 2026 chegam perto e devem ser citados como trabalho concorrente. O REDACT (Vats et al.) é multilíngue e controlado, c/ pt-BR como locale e checksum no gerador, mas os tipos de identificação param em classes genéricas, não tem exemplo q falha no checksum nem eixo de formato de superfície. O Brazilian-PHI (Eduardo) tem 500 notas clínicas sintéticas c/ DV em CPF e CNPJ, contra distratores de outras famílias, c/ todo identificador válido por construção, CNS só por regex, sem CNPJ alfanumérico, sem processo CNJ e sem ruído. O q o tarja-bench acrescenta: parecido inválido da MESMA classe como negativo rotulado (D3), ruído de documento como nível controlado (D1, D2, D4), contexto enganoso (D5) e 17 tipos brasileiros, incluindo CNJ, CNM, CIB e CNPJ alfanumérico.

## independence of the gold / independência do gold

EN: labels come from the generator, and the generator uses check-digit code. To keep tarja from grading itself, every generated value must also pass `bench/reference.py`, a separate implementation written from the official rules with no imports from tarja (CPF, CNPJ, CNS, NIS, CNJ, voter ID, RENAVAM, card). CNH, CNM and CIB have no reference yet and rely on tarja alone. Where `validate-docbr` is installed, a test also checks CPF, CNS, NIS and RENAVAM against it. D0 scores near 1.0 are expected by construction and are NOT evidence of real-world accuracy. That comes from the semi-real subset and the hand-annotated sample (E4.4).
PT: os rótulos vêm do gerador, e o gerador usa código de DV. P/ o tarja não se autoavaliar, todo valor gerado também tem q passar no `bench/reference.py`, implementação separada, escrita a partir das regras oficiais, sem importar nada do tarja (CPF, CNPJ, CNS, NIS, CNJ, título, RENAVAM, cartão). CNH, CNM e CIB ainda não têm referência e dependem só do tarja. Onde o `validate-docbr` estiver instalado, um teste compara CPF, CNS, NIS e RENAVAM c/ ele. Score perto de 1,0 no D0 é esperado por construção e NÃO prova acerto no mundo real. Isso vem do semi-real e da amostra anotada à mão (E4.4).

## annotation / anotação

EN: `ANNOTATION_GUIDE.md` + `python -m bench.iaa --a a.jsonl --b b.jsonl` for inter-annotator agreement.
PT: `ANNOTATION_GUIDE.md` + `python -m bench.iaa --a a.jsonl --b b.jsonl` p/ concordância entre anotadores.
