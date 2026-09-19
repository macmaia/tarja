# tarja

**EN** · Finds Brazilian personal identifiers (CPF, CNPJ etc) in free text, so you can mask them before data goes to an LLM, logs, BI, wherever.

Built for anyone shipping software in Brazil, incl. foreign companies adapting to the LGPD (Brazil's GDPR). Plenty of CPF/CNPJ validators exist already (brutils, validate-docbr). What's missing is finding the ID *inside* text, scoring it with Portuguese context, and covering what paid DLPs skip: alphanumeric CNPJ (Jul/2026), CNS (health card), CNJ case numbers.

Status: pre-alpha (`0.4.0.dev0`). API will change.

**PT** · Detecta docs brasileiros (CPF, CNPJ etc) em texto livre, p/ mascarar antes de mandar dado p/ LLM, log, BI, onde for.

Serve p/ qq um q desenvolve p/ o Brasil, inclusive empresa gringa se adaptando à LGPD. Validador de CPF/CNPJ já tem de monte (brutils, validate-docbr). O q falta é achar o doc *dentro* do texto, dar score c/ contexto em pt-BR e cobrir o q os DLPs pagos ignoram: CNPJ alfanumérico (jul/2026), CNS, nº de processo CNJ.

Status: pré-alfa (`0.4.0.dev0`). A API ainda muda.

## install / instalar

```bash
pip install -e ".[dev]"
```

## usage / uso

```python
import tarja

text = "Paciente CPF 529.982.247-25, cartao SUS 729 1417 7763 1701, processo 0000001-83.2017.8.26.0100"

for m in tarja.find(text):
    print(m.entity, m.start, m.end, m.score)  # BR_CPF 13 27 0.95 ...

tarja.mask(text)  # "Paciente CPF <BR_CPF>, cartao SUS <BR_CNS>, processo <BR_CNJ>"
tarja.mask(text, strategy="pseudonym")  # <BR_CPF_1>, same value -> same label / mesmo valor -> mesmo rotulo
tarja.mask(text, strategy="hash", salt="your-secret")  # <BR_CPF:3f9a1c0b2e7d>

tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35")  # True (alphanumeric CNPJ / CNPJ alfanum)

# EN: your own entity, no fork needed / PT: entidade própria, sem fork
tarja.register_entity(
    "ACME_EMPLOYEE_ID",
    [("acme", r"\bAC-\d{6}\b", 0.3)],
    context_words=["matricula acme"],  # EN: lowercase, no accents / PT: minúsculo, sem acento
)

# EN: typos with a wrong check digit, score 0, valid_dv=False / PT: digitacao c/ DV errado, score 0, valid_dv=False
tarja.find("cpf 529.982.247-24", report_invalid=True)

# EN: reversible tokens, e.g. before sending text to an LLM / PT: token reversivel, ex. antes de mandar p/ um LLM
vault = tarja.Vault()
safe = vault.protect(text)  # "Paciente CPF <BR_CPF:4b1a3edcd5f6c2e81a9d07b3>, ..."
vault.reveal(safe)  # original text / texto original
tarja.residual(safe)  # [] = nothing leaked / nada vazou
```

EN: tokens are 96-bit HMACs, and a clash raises `VaultCollisionError` instead of mixing two people up. `reveal()` restores any token the vault issued, so use one vault per user or session. `Vault` keeps the mapping in memory for one process. For multi-tenant production use (key in KMS, per-session rehydration, probing quotas, audit trail) see the paid Tarja Gateway.
PT: token é HMAC de 96 bits, e colisão levanta `VaultCollisionError` em vez de trocar uma pessoa por outra. O `reveal()` devolve qq token q o cofre emitiu, então use um cofre por usuário ou sessão. O `Vault` guarda o mapa em memória num processo só. P/ produção multi-tenant (chave em KMS, reidratação por sessão, quota anti-sondagem, trilha de auditoria) veja o Tarja Gateway pago.

EN: `hash` is pseudonymisation, not anonymisation under the LGPD: whoever has the salt can link it back. **Treat the salt as a secret key.** There are only 10⁹ possible CPFs, so anyone holding the salt can hash all of them in minutes and reverse every token. Use a random salt of at least 16 bytes (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`), keep it in a secrets manager, never in code or logs, and rotate it if it leaks. tarja warns when the salt is shorter than 16 bytes.
PT: `hash` é pseudonimização, não anonimização na LGPD: quem tem o salt consegue religar. **Trate o salt como chave secreta.** Só existem 10⁹ CPFs possíveis, então quem tiver o salt calcula o hash de todos em minutos e reverte qq token. Use salt aleatório de pelo menos 16 bytes, guarde num cofre de segredos, nunca em código ou log, e troque se vazar. O tarja avisa qdo o salt tem menos de 16 bytes.

### command line / linha de comando

```bash
tarja scan contrato.txt                  # JSON lines, values hidden / valores escondidos
tarja scan contrato.txt --format table
tarja scan contrato.txt --show-values    # EN: raw values, careful / PT: valor cru, cuidado
tarja scan contrato.txt --suspect        # EN: also wrong check digits / PT: tb DV errado
tarja mask contrato.txt > limpo.txt
cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ --min-score 0.9
```

EN: exit code 1 when something is found, 0 when clean, 2 on error. Handy in CI. Input is capped at 50 MB (`--max-mb`).
PT: exit code 1 qdo acha algo, 0 qdo limpo, 2 em erro. Útil em CI. Entrada limitada a 50 MB (`--max-mb`).

## entities / entidades

| code | what it is / o q é | tier | status |
|---|---|---|---|
| `BR_CPF` | individual taxpayer ID / CPF | N1 | beta |
| `BR_CNPJ` | company ID, numeric + alphanumeric / CNPJ numérico + alfanum | N1 | beta |
| `BR_CNS` | national health card / cartão SUS | N1 | beta |
| `BR_NIS` | NIS / PIS / PASEP / NIT | N1 | experimental |
| `BR_CNJ` | court case number / nº de processo CNJ | N1 | beta |
| `BR_TITULO_ELEITOR` | voter ID / título de eleitor | N1 | beta |
| `BR_CNH` | driving licence / CNH (needs context / exige contexto) | N1 | experimental |
| `BR_RENAVAM` | vehicle registry / RENAVAM (needs context / exige contexto) | N1 | beta |
| `BR_PLACA` | number plate, old + Mercosur / placa antiga + Mercosul | N2 | beta |
| `BR_PIX_EVP` | PIX random key / chave PIX aleatória (needs context / exige contexto) | N2 | beta |
| `BR_TELEFONE` | phone / telefone | N2 | beta |
| `BR_CEP` | postcode / CEP (needs context / exige contexto) | N3 | beta |
| `BR_CNM` | national property registry number / Código Nacional de Matrícula | N1 | beta |
| `BR_CIB` | national property cadastre / Cadastro Imobiliário Brasileiro (needs context / exige contexto) | N1 | beta |
| `BR_IPTU` | municipal property tax ID / inscrição do IPTU (needs context / exige contexto) | N3 | experimental |
| `BR_MATRICULA_IMOVEL` | property registry number / matrícula do imóvel (needs context / exige contexto) | N3 | experimental |
| `BR_CARTAO` | payment card, Luhn / cartão de crédito ou débito | N1 | beta |

EN: N1 = strong check digit, N2 = format only, N3 = needs context, N4 = NER. Scores: N1 0.95 with a context word nearby, 0.8 to 0.9 without. N2 0.7 / 0.5. N3 only with context, 0.5. Wrong check digit = dropped (unless `report_invalid=True`). Speed: ~1 ms per 100 tokens, 17 entities.
PT: N1 = DV forte, N2 = só formato, N3 = depende de contexto, N4 = NER. Score: N1 0.95 c/ palavra de contexto perto, 0.8 a 0.9 sem. N2 0.7 / 0.5. N3 só c/ contexto, 0.5. DV errado = descartado (exceto c/ `report_invalid=True`). Velocidade: ~1 ms por 100 tokens, 17 entidades.

## layout / organização

EN:
- `spec/entities/*.yaml`: one file per entity (regex, check digit, context, score, official source). Single source of truth, everything else is generated/tested from here.
- `spec/schema.json`: schema for those yaml files.
- `src/tarja/validators/`: check digits per document, stdlib only.
- `tests/`: `python -m unittest discover -s tests` or `pytest`.
- Tip: code comments carry tags like `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, so ctrl+f finds anything. Every comment is EN first, PT right after.

PT:
- `spec/entities/*.yaml`: 1 arquivo por entidade (regex, DV, contexto, score, fonte oficial). Fonte única, o resto é gerado/testado daqui.
- `spec/schema.json`: schema desses yaml.
- `src/tarja/validators/`: DV de cada doc, só stdlib.
- `tests/`: `python -m unittest discover -s tests` ou `pytest`.
- Dica: os comentários têm tags tipo `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, dá p/ achar tudo c/ ctrl+f. Todo comentário é EN primeiro, PT logo dps.

EN: official source for each rule, and whether it was checked: `docs/SOURCES.md`. Presidio plugin and upstream PR: `docs/presidio.md`. Benchmark: `bench/README.md`.
PT: fonte oficial de cada regra, e se foi conferida: `docs/SOURCES.md`. Plugin do Presidio e PR: `docs/presidio.md`. Benchmark: `bench/README.md`.

## licence / licença

Apache 2.0. EN: chosen for its explicit patent grant, which matters to companies. PT: escolhida pela cláusula explícita de patentes, que pesa p/ empresas.

Maintained by / mantido por [@macmaia](https://github.com/macmaia) · tarja@micah6ai.com
