<!-- Add to docs/supported_entities.md, as a new "Brazil" section in the country-specific table -->

### Brazil

| FieldType | Description | Detection Method |
|---|---|---|
| BR_CPF | The Brazilian individual taxpayer registration number (Cadastro de Pessoas Físicas). 11 digits with 2 modulo-11 check digits. | Pattern match, context and checksum |
| BR_CNPJ | The Brazilian company registration number (Cadastro Nacional da Pessoa Jurídica), numeric and the alphanumeric format issued since July 2026. 14 characters with 2 modulo-11 check digits. | Pattern match, context and checksum |
