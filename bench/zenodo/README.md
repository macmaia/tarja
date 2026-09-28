# tarja-bench v0.3

**EN** · Portuguese documents annotated for 17 Brazilian personal identifier types. All identifiers are synthetic. Full description, intended uses and limits in `DATASHEET.md`.

**PT** · Documentos em português anotados p/ 17 tipos de identificador pessoal brasileiro. Todo identificador é sintético. Descrição, usos previstos e limites no `DATASHEET.md`.

## files / arquivos

| file | content |
|---|---|
| `synthetic_controlled.{dev,test}.jsonl` | D0, D1 |
| `synthetic_adversarial.{dev,test}.jsonl` | D2 to D5 |
| `semireal.{dev,test}.jsonl` | law text + synthetic IDs / texto de lei + IDs sintéticos |
| `manifest.json` | sha256, counts, versions / sha256, contagens, versões |
| `DATASHEET.md`, `CITATION.cff`, `LICENSE-DATA.txt` | docs |

EN: one JSON per line / PT: 1 JSON por linha: `{"id", "domain", "difficulty", "text", "spans": [{"start", "end", "entity"}]}`

## reproduce / reproduzir

```bash
pip install tarja  # or/ou: git clone https://github.com/macmaia/tarja && pip install -e .

# EN: the four synthetic files, from the seed alone / PT: os 4 sintéticos, só pela seed
python -m bench.generate --seed 42 --out bench/data/v0.3

# EN: the two semi-real files also need the law texts, which are NOT in this package
# PT: os 2 semi-reais precisam tb dos textos de lei, q NÃO vão neste pacote
python -m bench.fetch_public_texts --out ../corpus_publico
python -m bench.semireal --src ../corpus_publico --n 2000 --out bench/data/v0.3

sha256sum bench/data/v0.3/*.jsonl   # EN: compare with manifest.json / PT: compare c/ o manifest.json
```

EN: the four synthetic files reproduce from the seed alone and their sha256 is stable. The two semi-real files
depend on what planalto.gov.br serves: if a law is amended, its paragraphs change and the sha256 will differ.
Each semi-real document therefore carries its source URL and retrieval date, which is what makes that subset
auditable even when it is not bit-reproducible.
PT: os 4 sintéticos reproduzem só pela seed e o sha256 é estável. Os 2 semi-reais dependem do q o
planalto.gov.br serve: se uma lei for alterada, os parágrafos mudam e o sha256 difere. Por isso cada documento
semi-real carrega a URL de origem e a data de coleta, o q torna o subconjunto auditável mesmo sem ser
reproduzível bit a bit.

## licence / licença

EN: data CC BY 4.0, code Apache 2.0. Law texts in the semi-real subset are public domain in Brazil (Lei 9.610/1998, art. 8, IV).
PT: dados CC BY 4.0, código Apache 2.0. Texto de lei no semi-real é domínio público no Brasil (Lei 9.610/1998, art. 8, IV).
