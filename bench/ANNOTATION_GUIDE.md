# annotation guide / guia de anotação (v0.2)

EN: for the semi-real check and the restricted real subset (1,000 passages from official gazettes). Two annotators work independently on the same docs, then `bench/iaa.py` measures agreement, then disagreements are adjudicated.
PT: p/ conferência do semi-real e o subconjunto real restrito (1.000 trechos de diários oficiais). 2 anotadores trabalham de forma independente nos mesmos docs, dps o `bench/iaa.py` mede a concordância, dps as divergências são arbitradas.

## what to mark / o q marcar

EN: every occurrence of the 16 entity types in `docs/SOURCES.md`, using the codes (`BR_CPF`...). Mark the identifier only, not the label ("CPF") nor surrounding punctuation.
PT: toda ocorrência dos 16 tipos em `docs/SOURCES.md`, c/ os códigos (`BR_CPF`...). Marque só o identificador, não o rótulo ("CPF") nem pontuação em volta.

| case / caso | rule / regra |
|---|---|
| `CPF: 529.982.247-25.` | EN: mark `529.982.247-25`, not the final dot / PT: marca `529.982.247-25`, sem o ponto final |
| EN: wrong check digit / PT: DV errado | EN: do NOT mark, add a note "invalid DV" / PT: NÃO marca, anota "DV inválido" |
| EN: OCR noise (`529.982.247-2S`) | EN: mark it if a human would read it as that ID / PT: marca se uma pessoa leria como aquele ID |
| EN: split by a line break / PT: quebrado por linha | EN: one span covering both lines / PT: 1 span cobrindo as 2 linhas |
| EN: partially masked (`***.982.247-**`) | EN: do NOT mark, note "masked" (it's already protected) / PT: NÃO marca, anota "mascarado" (já está protegido) |
| EN: context says CPF, number is a NIS / PT: contexto diz CPF, número é NIS | EN: label by what the number IS (check with `tarja.validate`) / PT: rotula pelo q o número É (confere c/ `tarja.validate`) |
| EN: valid for 2 entities (CPF and NIS) / PT: válido p/ 2 entidades | EN: follow the context word; no context -> BR_CPF, note "ambiguous" / PT: segue a palavra de contexto; sem contexto -> BR_CPF, anota "ambíguo" |
| EN: CNPJ of a company / PT: CNPJ de empresa | EN: mark it anyway (the benchmark measures detection, LGPD category is a separate field) / PT: marca mesmo assim |
| `matrícula` | EN: only property registry numbers, not student/employee ones / PT: só de imóvel, não de aluno/funcionário |

## format / formato

EN: same JSONL as the benchmark, plus an optional `"notes"` list per doc.
PT: mesmo JSONL do benchmark, mais uma lista `"notes"` opcional por doc.

## agreement target / meta de concordância

EN: report span F1 (exact and partial) and character-level Cohen's kappa. Below 0.8 kappa, revise this guide and re-annotate a sample before continuing.
PT: reportar F1 de span (exato e parcial) e kappa de Cohen por caractere. Abaixo de 0,8 de kappa, revisar este guia e reanotar uma amostra antes de seguir.

## real data rules / regras p/ dado real

EN: real passages stay encrypted, outside git (`data/real/` is gitignored), never in issues, prompts to external LLMs or screenshots. Only aggregate numbers leave the machine. Needs the ethics approval first (E7.1).
PT: trecho real fica criptografado, fora do git (`data/real/` está no .gitignore), nunca em issue, prompt de LLM externo ou print. Só número agregado sai da máquina. Precisa da aprovação de ética antes (E7.1).
