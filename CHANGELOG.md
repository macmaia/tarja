# Changelog

EN: notable changes per release. Format: Keep a Changelog. Versioning: SemVer, with the 0.x caveat that a
minor bump may change behaviour.
PT: mudanças relevantes por versão. Formato: Keep a Changelog. Versionamento: SemVer, c/ a ressalva de 0.x,
onde um minor pode mudar comportamento.

## [Unreleased]

## [0.10.0] - 2026-10-01

EN: a character you cannot see used to hide an identifier completely. Upgrade if you scan text that came
from a PDF, from Word, or from anyone else.
PT: um caractere q você não vê escondia um identificador por inteiro. Atualize se você lê texto vindo de PDF,
de Word, ou de terceiro.

### Security / Segurança

- **One invisible character inside an identifier no longer hides it.** A zero-width space between two digits
  of a valid CPF made `find()` return nothing at all, not even a suspect. The reader does not see the
  character, a language model reads the identifier normally, and `tarja scan` reported the file clean.

  Ten characters across five classes did it: zero-width space, zero-width non-joiner, word joiner, soft
  hyphen, bidi controls, variation selectors, combining marks, tag characters, Hangul fillers, and circled
  digits. They are not only an attack. Soft hyphens and zero-width characters come out of ordinary PDF and
  Word extraction on their own, so this was a silent false negative in normal use too.

  Circled digits are fixed in the normaliser. The rest get a second detection pass over the text with those
  characters removed, mapped back to the original offsets. A match that only appears after the removal is
  reported as **valid**, not as a suspect, because an identifier that resolves only once the invisible
  characters are gone is not a doubtful candidate.
  PT: um caractere invisível dentro de um identificador não o esconde mais. Dez caracteres em cinco classes
  faziam o `find()` não devolver nada, nem suspeito. Não é só ataque: hífen opcional e espaço de largura zero
  saem sozinhos de extração de PDF e de Word.

- **`mask()` refuses overlapping spans instead of damaging the document.** It substitutes from the end
  backwards, which is only correct while the spans are disjoint. `find()` guarantees that; a list built by
  hand and passed as `matches=` did not, and an overlapping pair silently produced a corrupted document.

### Changed / Mudou

- **`Match.value` may now contain invisible characters.** `text[start:end] == value` still holds, which is
  what the type has always promised, but the value of a match found through the new pass is the original
  slice, invisibles included. If you revalidate `value` yourself, normalise it first.
  PT: o `Match.value` pode conter caractere invisível agora. O `text[start:end] == value` continua valendo.

- `dataclasses.asdict(match)` and `vars(match)` now raise instead of returning the identifier. `repr()` and
  `to_dict()` already hid it, and those two walked around it, which is what a structured logging library
  calls. Use `to_dict(include_value=False)`.

### Benchmark

EN: unchanged, and this one was proved rather than assumed. Over all 10,000 published benchmark documents,
the new pass never triggers and `find()` returns identical results with it on and off. The published
figures stand: synthetic_controlled exact F1 0.978, synthetic_adversarial 0.825, semireal 0.9768, bench data
v0.3. Cost on clean text is about 7% more time.
PT: inalterado, e desta vez provado e não suposto: nos 10.000 documentos publicados a passada nova nunca
dispara e o resultado é idêntico com ela ligada e desligada.


## [0.9.0] - 2026-09-29

EN: five fail-open defects, found in the 4th code review on 29/09/2026. Four of them were in something
already published. If you are on 0.8.0 or earlier, upgrade.
PT: cinco defeitos de falha aberta, achados na 4a revisao de codigo em 29/09/2026. Quatro estavam em coisa
já publicada. Se você está na 0.8.0 ou antes, atualize.

### Security / Segurança

- **`tarja scan` exit code no longer follows the report filter.** Until 0.8.0 the same filtered list fed
  both the report and the exit code, so `--min-score 0.9` hid a `BR_CEP` scoring 0.50 and turned exit 1 into
  exit 0. That flips `tarja scan f.txt && send.sh` from fail-closed to fail-open. The exit code is now
  decided over every candidate, before any threshold.
  PT: o exit code passa a ser decidido sobre todo candidato, antes do filtro. Opção de exibição não decide
  mais se o dado sai da máquina.

- **`tarja mask` refuses a score threshold.** `mask --min-score 0.9` used to leave a 0.50 `BR_CEP` in
  cleartext in the output file, exit 0. It now exits 2. PT: agora sai com 2.

- **`tarja mask` reports ID-shaped values whose check digit fails.** They were left in cleartext with no
  signal anywhere, and `residual()` called the file clean. `mask` now counts them on stderr, and
  `--suspect` masks them.

  Masking them by default is deliberately not the answer. An invoice or protocol number in CPF shape is a
  suspect too, and `mask` output replaces the document.
  PT: agora avisa no stderr com a contagem, e `--suspect` mascara. Mascarar por omissão não é a resposta,
  porque número de nota ou de protocolo com cara de CPF também é suspeito.

- **`Vault(key=...)` goes through the same guard as `mask(salt=...)`.** `Vault(key=b"senha")` was accepted
  and emitted deterministic tokens, so the reversible path, the one with the higher consequence, was the
  only one without the weak-key check. `key=b""` now raises instead of quietly generating a random key: a
  caller who lost their key used to get working tokens that joined with nothing. `key=None` still generates
  a random key and is not validated.
  PT: o `Vault` aceitava chave fraca, e era o único caminho sem a guarda.

- **Score flags refuse NaN, inf and anything outside [0.0, 1.0].** `--min-score nan` made every comparison
  False, dropped every finding and returned exit 0. PT: agora exit 2.

### Added / Novo

- `residual(text, report_invalid=True)` returns ID-shaped values whose check digit fails. Without it, a
  masked file whose only leftover is a mistyped CPF came back as an empty list, which reads as clean.
- `--suspect` moved to the shared options, so `mask --suspect` exists.

### Fixed / Corrigido

- `residual()` dropped `valid_dv` when it rebuilt each `Match` to restore the original offsets, so a suspect
  that reached it came back labelled valid. PT: o `residual()` descartava o `valid_dv`.

- `README.md` and the `cli.py` header both recommended `tarja scan - --min-score 0.9` as the CI idiom. A
  valid CPF with no context word scores 0.85, so that command ignored real CPFs and the pipeline passed.

- `examples/rag_pipeline.py` defaulted its corpus key to `"00" * 32`. Valid hex, 32 bytes, worthless, in the
  file people copy into a real ingestion job. It now requires `TARJA_CORPUS_KEY`.

  No fallback to a random key, on purpose: that changes the tokens on every run and silently stops today's
  index joining with yesterday's.
  PT: o exemplo de RAG tinha chave nula por omissão. Sem chave aleatória de propósito.

- The same example called `residual(..., min_score=0.5)` a fail-closed gate. That threshold let
  `BR_MATRICULA_IMOVEL` (0.40) and an out-of-context `BR_CEP` or `BR_IPTU` (0.30) into the index.

### Removed / Removido

- **`mask(strategy="hash")`**, renamed to `pseudonym_stable` back in 0.5 with a warning that promised it
  would go in 0.6. It was still accepted in 0.8.0, three releases late.

  Removed here, because a deprecation notice from a project that misses its own dates buys nothing, and this
  release issues one for `--min-score`. The error now names the replacement.
  PT: renomeado na 0.5 com aviso prometendo remoção na 0.6, e seguia aceito na 0.8.0. Removido aqui, porque
  aviso de depreciação de projeto que não cumpre prazo não vale nada.

### Deprecated / Depreciado

- `--min-score` is now `--report-min-score`. The old name read as "the minimum score I care about", which is
  why raising it was expected to be conservative and did the opposite. Renamed rather than re-documented,
  because the name was the defect.

  The old spelling still works and warns on stderr, not as a `DeprecationWarning`, which Python hides by
  default on a command line. It goes away in 1.0.0.
  PT: o nome era o defeito, então foi renomeado. O antigo segue funcionando e avisa no stderr. Sai na 1.0.0.

### Benchmark

EN: unchanged. Nothing here changes what `find()` returns at no threshold, and the figures were re-measured
on 0.9.0 to confirm it: synthetic_controlled exact F1 0.978, synthetic_adversarial 0.825, semireal 0.9768,
all on bench data v0.3, identical to the 0.8.0 run. What changed is the command line's report and exit code.
PT: inalterado, e remedido na 0.9.0 p/ confirmar. O que mudou foi o relatório e o exit code da linha de
comando, não a detecção.

### Notes / Notas

EN: expect more pipelines to fail after upgrading. That is the fix working, not a new false positive. On
3.5 MB of federal law, `find()` at no threshold produces 4 false positives, all `BR_MATRICULA_IMOVEL` at
score 0.40, all in the public-registry act. That is a cost measurement on legal prose and says nothing about
administrative text, where N1 and N2 entities are common.
PT: espere mais pipelines falhando depois de atualizar. É a correção funcionando.

EN: the report is now filtered after overlap resolution instead of before, so raising the threshold only
removes rows. The command line is monotone by construction. An entity added through `register_entity()` with
an N1 score below an overlapping N2 score can still break that property in the library, and the fix for it
is a check inside `register_entity()`, not here.
PT: o filtro passou a rodar depois da resolução de sobreposição. Entidade registrada por terceiro pode
quebrar a propriedade na biblioteca, e o conserto disso é dentro do `register_entity()`.

## [0.8.0] and earlier / e anteriores

EN: no changelog was kept before 0.9.0. See the git history.
PT: não havia changelog antes da 0.9.0. Veja o histórico do git.
