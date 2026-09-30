# Changelog

EN: notable changes per release. Format: Keep a Changelog. Versioning: SemVer, with the 0.x caveat that a
minor bump may change behaviour.
PT: mudanças relevantes por versão. Formato: Keep a Changelog. Versionamento: SemVer, c/ a ressalva de 0.x,
onde um minor pode mudar comportamento.

## [Unreleased]

## [0.9.0] - 2026-09-29

EN: this release closes five fail-open defects found by the fourth review board on 29/09/2026, while it was
reviewing two feature proposals that were both rejected. Four of the five were in a published artefact.
PT: esta versão fecha cinco defeitos de falha aberta achados pelo 4o board de revisão em 29/09/2026, enquanto
ele revisava duas propostas de funcionalidade, as duas recusadas. Quatro dos cinco estavam em artefato
publicado.

### Security / Segurança

- **`Vault(key=...)` now goes through the same guard as `mask(salt=...)`.** EN: `Vault(key=b"senha")` was
  accepted and emitted deterministic tokens, so the reversible path, the one with the higher consequence,
  was the only one without the weak-key check. `key=None` still generates a random key and is not validated.
  `key=b""` now raises instead of silently generating one, because a caller who lost their key used to get
  working tokens that joined with nothing. PT: o `Vault` aceitava chave fraca, e era o único caminho sem a
  guarda. `key=b""` agora levanta em vez de gerar chave em silêncio.
- **`tarja scan` exit code no longer follows the report filter.** EN: the exit code is decided over every
  candidate `find()` returns, before the threshold is applied. Until 0.8.0 the same filtered list fed the
  report and the exit code, so `--min-score 0.9` hid a `BR_CEP` scoring 0.50 AND turned exit 1 into exit 0,
  which flips `tarja scan f.txt && send.sh` from fail-closed to fail-open. A display option can no longer
  decide whether data leaves the machine. PT: o exit code passa a ser decidido sobre todo candidato, antes
  do filtro. Opção de exibição não decide mais se o dado sai da máquina.
- **`tarja mask` refuses a score threshold.** EN: `mask --min-score 0.9` used to leave a 0.50 `BR_CEP`
  unmasked in the output file, with exit 0. It now exits 2, because a flag that is accepted and does
  something else is the defect itself. PT: agora sai com 2 em vez de deixar valor em claro no arquivo.
- **`tarja mask` reports ID-shaped values with a wrong check digit.** EN: they were left in cleartext with
  no signal on any channel, and `residual()` reported the file clean, which is a green light over personal
  data. `mask` now writes a counted warning to stderr, and `--suspect` masks them. Masking them by default
  is deliberately not the answer: an invoice or protocol number in CPF shape is a suspect too, and `mask`
  output replaces the document. PT: agora avisa no stderr com a contagem, e `--suspect` mascara.
- **Score flags refuse NaN, inf and values outside [0.0, 1.0].** EN: `--min-score nan` made every comparison
  False, dropped every finding and returned exit 0. A check a typo can disable is not a check. PT: agora
  exit 2.

### Added / Novo

- EN: `residual(text, report_invalid=True)` returns ID-shaped values with a wrong check digit. Without it, a
  masked file whose only leftover is a mistyped CPF came back as an empty list, which reads as clean.
  PT: `residual(..., report_invalid=True)` enxerga suspeito.
- EN: `--suspect` moved from `scan` to the shared options, so `mask --suspect` exists.
  PT: `--suspect` virou opção comum, então `mask --suspect` existe.

### Fixed / Corrigido

- EN: `residual()` dropped `valid_dv` when it rebuilt each `Match` to restore the original offsets, so any
  suspect that reached it came back labelled valid. PT: o `residual()` descartava o `valid_dv`.
- EN: `README.md` and the `cli.py` header both recommended `tarja scan - --min-score 0.9` as a CI idiom,
  which is the vulnerable one. A valid CPF with no context word scores 0.85, so that command ignored real
  CPFs and the pipeline passed. PT: o README e o cabeçalho da CLI recomendavam justamente o idioma
  vulnerável.
- EN: `examples/rag_pipeline.py` defaulted the corpus key to `"00" * 32`, valid hex, 32 bytes long and
  worthless, in the file people copy into a real ingestion job. It now asks for `TARJA_CORPUS_KEY` and stops
  with an explanation. There is deliberately no fallback to a random key: that would change the tokens on
  every run and silently stop today's index joining with yesterday's. PT: o exemplo de RAG tinha chave nula
  por omissão, e agora exige a variável. Sem chave aleatória de propósito.
- EN: the same example called `residual(..., min_score=0.5)` a fail-closed gate. That threshold let
  `BR_MATRICULA_IMOVEL` (0.40) and an out-of-context `BR_CEP` or `BR_IPTU` (0.30) straight into the index.
  PT: o portão do exemplo usava limiar, e deixava passar três entidades para dentro do índice.

### Removed / Removido

- **`mask(strategy="hash")`.** EN: renamed to `pseudonym_stable` in 0.5, with a deprecation warning that said
  the old name went away in 0.6. It was still accepted in 0.8.0, three releases past the announced date.
  Removed here, because a deprecation notice from a project that does not keep its removal dates buys
  nothing, and 0.9.0 announces one for `--min-score`. The error now names the replacement instead of only
  listing the valid options. PT: renomeado na 0.5 com aviso prometendo remocao na 0.6, e seguia aceito na
  0.8.0. Removido aqui, pq aviso de depreciacao de projeto que nao cumpre prazo nao vale nada, e esta versao
  anuncia um prazo p/ o `--min-score`. O erro nomeia o substituto.

### Deprecated / Depreciado

- EN: `--min-score` is renamed to `--report-min-score`. The old name read as "the minimum score I care
  about", which is why raising it was expected to be conservative and did the opposite. Renamed rather than
  just re-documented, because the name was the defect. The old spelling still works and warns on stderr, not
  as a `DeprecationWarning`, which Python hides by default on a command line. Removal target 1.0.0.
  PT: `--min-score` virou `--report-min-score`. O nome era o defeito, então foi renomeado e não só
  redocumentado. O antigo segue funcionando e avisa no stderr. Sai na 1.0.0.

### Notes / Notas

- EN: the report is now filtered AFTER overlap resolution instead of before. `tests/test_board4.py` checks
  over the 17 built-in entities that raising the threshold only ever removes rows and never adds them, and
  it was verified over 3.5 MB of federal law as well. It is NOT a guarantee: an entity registered through
  `register_entity()` with an N1 score below an overlapping N2 score breaks the property, and no test
  catches that today. It is open as B4-g in PENDING.md, and the real fix is a check inside
  `register_entity()`. The command line itself is unaffected either way, because it filters the report
  after overlap resolution, which is monotone by construction.
  PT: o filtro passou a rodar depois da resolução de sobreposição. O teste confere a propriedade para as 17
  entidades embutidas, e não para entidade registrada por terceiro, o que segue aberto como B4-g.
- EN: expect more pipelines to fail after upgrading. That is the fix working, not a new false positive. On
  3.5 MB of federal law, `find()` at no threshold produces 4 false positives, all `BR_MATRICULA_IMOVEL` at
  score 0.40, all in the public-registry act. That figure is a cost measurement on legal prose and says
  nothing about administrative text, where N1 and N2 entities are common.
  PT: espere mais pipelines falhando depois de atualizar. É a correção funcionando, não falso positivo novo.

## [0.8.0] and earlier / e anteriores

EN: no changelog was kept before 0.9.0. See the git history and the release notes.
PT: não havia changelog antes da 0.9.0. Veja o histórico e as notas de release.
