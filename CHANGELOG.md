# Changelog

EN: notable changes per release. Format: Keep a Changelog. Versioning: SemVer, with the 0.x caveat that a
minor bump may change behaviour.
PT: mudanças relevantes por versão. Formato: Keep a Changelog. Versionamento: SemVer, c/ a ressalva de 0.x,
onde um minor pode mudar comportamento.

## [Unreleased]

## [0.12.0] - 2026-10-06

EN: 0.11.0 was tagged but never published, because the release workflow broke on an unrelated pip change.
Its contents ship here. 0.9.0, the only version live on PyPI, is yanked on release of this one.
PT: a 0.11.0 foi marcada e nunca publicada, pq o workflow de release quebrou numa mudanca do pip. O
conteudo dela sai aqui. A 0.9.0, unica viva no PyPI, e yanked no lancamento desta.

### Added / Novo

- **`decide()` and `require_clean()`.** The fail-closed decision as a library call, not only as the exit
  code of `tarja scan`. `decide(text)` returns a `Decision` that is falsy when blocked and carries
  `blocked_by` and `reason()`, so `if not tarja.decide(text): refuse()` reads correctly and a log line can
  say what was blocked without carrying the value. `require_clean(text)` is the same engine raising
  `BlockedError` for code that would rather not branch.

  **It blocks a value with a failing check digit by default, and `tarja scan` still does not.** That
  difference is deliberate. An exit code is a one-byte channel with nowhere to put a reason, and gating it
  on suspects teaches people to write `|| true`, which removes the gate for valid identifiers too.
  `decide()` returns an object, so it can say why, and the person reading the reason is the person who
  decides. `on_suspect="allow"` opts out. The README now carries a three-row table stating the policy of
  `mask()`, `scan` and `decide()` side by side.
  PT: a decisão de bloquear como chamada de biblioteca, e não só como código de saída do `tarja scan`. Ela
  barra valor c/ DV errado por padrão, e o `scan` não, de propósito.

- **`tarja scan` says the consequence, not just the count.** The stderr warning about ignored suspects now
  states that about 93% of CPFs with one corrupted digit reconstruct to a single valid CPF, and names both
  `--suspect` and `--fail-on-suspect`. A count in a CI log is not information.

### Fixed / Corrigido

- **The release workflow.** `pip install --python X` became `pip --python X install`: pip used to tolerate
  the option after the subcommand and now refuses it. It broke the v0.11.0 release with nothing changed in
  the project, because pip is installed unpinned on the runner.
  PT: o `--python` do pip passou a exigir posição antes do subcomando, e quebrou o release sem nada ter
  mudado no projeto.

## [0.11.0] - 2026-10-06

EN: a round of review that started from the written promises instead of the code. Three of these survived
97.97% line coverage and 71 killed mutants, which is the point.
PT: uma rodada de revisão que partiu das promessas escritas, não do código. Três destes sobreviveram a
97,97% de cobertura e 71 mutantes mortos.

### Security / Segurança

- **`mask()` no longer returns text containing a value whose check digit failed.** It defaulted to
  `report_invalid=False`, so `mask("CPF 111.444.777-36 e CPF 111.444.777-35")` returned the first CPF
  verbatim while the call succeeded. Eleven legible digits in the output of the function whose whole job is
  that they are gone. The CLI warned on stderr, and stderr is not what a pipeline keeps.
  PT: o `mask()` não devolve mais texto com valor de DV errado em claro. Ele forçava
  `report_invalid=False`, então o valor ficava na saída enquanto a chamada dizia ter mascarado.

- **A built-in entity can no longer be replaced.** `register_entity("BR_CPF", ..., tier="N1",
  replace=True)` with a validator of the caller's choosing was accepted, so `BR_CPF` kept its name and
  validated everything. `unregister_entity()` already refused to remove a built-in, which made the promise
  look kept while the next door was open.
  PT: entidade nativa não pode mais ser substituída. O `unregister_entity()` já recusava remover, e o
  `replace=True` entrava pela porta seguinte.

### Added / Novo

- **`tarja scan --fail-on-suspect`.** Exits 1 when a value has the shape of an identifier and fails its
  check digit. The default exit code is unchanged and stays what it was: a documented, accepted risk. What
  was missing was any way at all to opt out of it, so `tarja scan f.txt && send.sh` could not be made
  conservative by any combination of options. The flag changes the exit code only, never the report.
  PT: sai 1 quando o valor tem cara de identificador e o DV não fecha. O padrão não mudou. O que faltava
  era poder optar por não correr esse risco.

- **An identifier glued to another digit is detected when a context word names it.** `cpf 0052998224725`
  returned nothing at all, not even a suspect, because every pattern is anchored with a word boundary. In a
  database dump or a concatenated log that is the ordinary shape of the data.

  The window is kept only when the check digit closes **and** a context word is near. Requiring the check
  digit alone was measured first and discarded: 90.1% of random 24-digit runs produced a false finding over
  2000 draws per length, because a long run offers many windows and each closes a CPF about 1 in 100 times.
  With the context word the same measurement gives 0.0% to 2.5%. An unlabelled run is therefore still not
  detected, on purpose, and that is a documented limit rather than an oversight.
  PT: identificador colado a outro dígito é detectado quando há palavra de contexto perto. Só o DV foi
  medido primeiro e descartado: 90,1% de falso positivo em corrida de 24 dígitos. Com contexto, 0,0% a 2,5%.
  Corrida sem rótulo segue não detectada, de propósito.

### Changed / Mudou

- **Breaking: `tarja mask` masks values with a failing check digit by default.** `--suspect` is now its
  default behaviour. To keep one in the text, call the library with `mask(text, report_invalid=False)`,
  which is explicit at the call site rather than a default nobody reads.
  PT: quebra de contrato. O `tarja mask` mascara valor de DV errado por padrão.

EN: **0.10.0 was never published to PyPI.** Its changes ship here, in 0.11.0, together with the ones
below. 0.9.0 is yanked on release of this version: it masks a document while leaving an eleven-digit value
with a failing check digit inside it, and it misses an identifier split by an invisible character.
PT: a **0.10.0 nunca foi publicada no PyPI**. As mudancas dela saem aqui, na 0.11.0. A 0.9.0 e yanked no
lancamento desta: ela mascara o documento deixando dentro dele um valor de 11 digitos c/ DV errado.

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
