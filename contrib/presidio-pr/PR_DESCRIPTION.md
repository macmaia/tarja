## Add Brazilian CPF and CNPJ recognizers (incl. alphanumeric CNPJ)

### What
Two new country-specific recognizers under `predefined_recognizers/country_specific/brazil/`:

- `BrCpfRecognizer` (`BR_CPF`): individual taxpayer number, 11 digits, modulo-11 check digits.
- `BrCnpjRecognizer` (`BR_CNPJ`): company number, numeric **and the alphanumeric format the Receita Federal started issuing in July 2026** (`12.ABC.345/01DE-35`). Same modulo-11 algorithm over `ord(c) - 48`.

Both declare `COUNTRY_CODE = "br"`, default `supported_language="pt"`, and are registered with `enabled: false` and `country_code: br` in `default_recognizers.yaml`, following CONTRIBUTING.md.

### Why
Presidio has no Brazilian recognizers today. CPF and CNPJ are the most common identifiers in Brazilian text, and the alphanumeric CNPJ breaks digit-only patterns, so existing regex-based setups miss it.

### How accuracy was tested
- Checksums validated against the official Receita Federal example (`12.ABC.345/01DE-35`) and the Serpro calculation guide (links in the docstrings).
- Unit tests cover valid, wrong check digit, repeated digits, wrong length, compact vs formatted, lowercase alphanumeric, check digit as letter.
- The same algorithms are property-tested (thousands of generated numbers) and mutation-tested in [tarja](https://github.com/macmaia/tarja), with a public benchmark to follow.

### Checklist
- [x] Tests pass locally (`pytest`): 23 passed, 100% coverage on the three new files
- [x] `ruff check` clean
- [x] Recognizers in `country_specific/brazil/`, `COUNTRY_CODE` set (ISO 3166-1 alpha-2)
- [x] Added to `default_recognizers.yaml`, to `predefined_recognizers/__init__.py` imports and to `__all__`
- [x] `supported_entities.md` updated
- [x] `CHANGELOG.md` not touched (generated at release)
- [x] No new dependencies
- [x] I have the right to contribute this code under the project's MIT licence

## One question for the maintainers

Both recognizers are declared with `supported_languages: [pt]` and `enabled: false`, following the pattern
used by the country-specific recognizers that ship disabled. `pt` does not appear anywhere in
`default_recognizers.yaml` today, so this would be the first entry for that language. Brazilian documents do
appear in English-language text, so `en` is also defensible, the way the Indian recognizers are declared.
Happy to switch if you prefer `en`, or to add both.
