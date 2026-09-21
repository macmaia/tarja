# tarja-bench v0.2

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
python -m bench.generate --seed 42 --out bench/data/v0.2
sha256sum bench/data/v0.2/*.jsonl   # EN: compare with manifest.json / PT: compare c/ o manifest.json
```

## licence / licença

EN: data CC BY 4.0, code Apache 2.0. Law texts in the semi-real subset are public domain in Brazil (Lei 9.610/1998, art. 8, IV).
PT: dados CC BY 4.0, código Apache 2.0. Texto de lei no semi-real é domínio público no Brasil (Lei 9.610/1998, art. 8, IV).
