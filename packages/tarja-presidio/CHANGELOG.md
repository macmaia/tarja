# Changelog, tarja-presidio

EN: notable changes per release. The core library has its own `CHANGELOG.md` at the repository root.
PT: mudanças relevantes por versão. A biblioteca do núcleo tem o `CHANGELOG.md` dela na raiz do repositório.

## [0.1.1] - 2026-10-01

### Security / Segurança

- **A format-only match no longer reaches Presidio at confidence 1.0.** `validate_result` returned `True`
  whenever the tarja validator passed and the entity needed no context word. For `BR_PLACA` and
  `BR_TELEFONE` the validator checks a format, not a check digit, so a seven-character plate arrived with
  the same confidence as a CPF whose check digit had actually been verified. At 1.0 it also sat out of reach
  of the `score_threshold` the README tells people to filter with.

  Those two now keep their base score of 0.5 and rely on Presidio's context enhancer, like every other
  entity without a verified check digit. What decides confidence 1.0 is the tier, not "the validator
  passed": only tier N1 validates a check digit.

  EN: if you filter at `score_threshold=0.6` or above you will stop seeing plates and phone numbers that
  carry no nearby context word. That is the correction, not a regression. Lower the threshold or pass those
  two entities explicitly.
  PT: um casamento só de formato não chega mais ao Presidio com confiança 1.0. Placa e telefone voltam p/ o
  score base de 0.5. Quem filtra em 0.6 ou acima deixa de ver placa e telefone sem palavra de contexto perto,
  e isso é a correção, não regressão.

### Fixed / Corrigido

- The module header documented a fifth case, "entity with no check digit -> None", that never ran: every
  built-in entity has a validator. The branch stays, because an entity added through tarja's
  `register_entity()` may not have one, and the header now says so.
  PT: o cabeçalho documentava um caso que nunca executava.

## [0.1.0] - 2026-09-26

EN: first release. One `PatternRecognizer` per tarja entity, built from tarja's registry so regex, context
words and check digits never drift from the core library.
PT: primeira versão. 1 `PatternRecognizer` por entidade do tarja, montado a partir do registro do tarja.
