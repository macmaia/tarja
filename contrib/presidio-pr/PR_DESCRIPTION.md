## Add Brazilian CPF and CNPJ recognizers (incl. alphanumeric CNPJ)

### What
Two new country-specific recognizers under `predefined_recognizers/country_specific/br/`:

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
- [ ] Tests pass locally (`pytest`), coverage >= 90% on changed lines
- [ ] `ruff` clean
- [ ] Recognizers in `country_specific/br/`, `COUNTRY_CODE` set (ISO 3166-1 alpha-2)
- [ ] Added to `default_recognizers.yaml`, to `predefined_recognizers/__init__.py` imports and to `__all__`
- [ ] `supported_entities.md` updated
- [ ] `CHANGELOG.md` not touched (generated at release)
- [ ] No new dependencies
- [ ] I have the right to contribute this code under the project's MIT licence
