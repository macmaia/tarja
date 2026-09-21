# tarja

**EN** · Finds Brazilian personal identifiers (CPF, CNPJ etc) in free text, so you can mask them before data goes to an LLM, logs, BI, wherever.

Built for anyone shipping software in Brazil, incl. foreign companies adapting to the LGPD (Brazil's GDPR). Plenty of CPF/CNPJ validators exist already (brutils, validate-docbr). What's missing is finding the ID *inside* text, scoring it with Portuguese context, and covering what paid DLPs skip: alphanumeric CNPJ (Jul/2026), CNS (health card), CNJ case numbers.

Status: alpha (`0.5.0`, first release on PyPI). The API can still change before 1.0.

**PT** · Detecta docs brasileiros (CPF, CNPJ etc) em texto livre, p/ mascarar antes de mandar dado p/ LLM, log, BI, onde for.

Serve p/ qq um q desenvolve p/ o Brasil, inclusive empresa gringa se adaptando à LGPD. Validador de CPF/CNPJ já tem de monte (brutils, validate-docbr). O q falta é achar o doc *dentro* do texto, dar score c/ contexto em pt-BR e cobrir o q os DLPs pagos ignoram: CNPJ alfanumérico (jul/2026), CNS, nº de processo CNJ.

Status: alfa (`0.5.0`, 1ª versão no PyPI). A API ainda pode mudar antes da 1.0.

## limits / limites

EN: tarja is a detection aid, **not a guarantee of LGPD compliance**, and not an anonymiser in the sense of art. 12. What it does not do, on purpose:

| limit | why / what to do instead |
|---|---|
| **No names, addresses, e-mails, dates of birth or health data.** Only structured identifiers (tiers N1 to N3). | Those are tier N4 and need NER, which is not implemented here. Combine tarja with a NER model, or register your own entity with `register_entity()`. Sector NER for health and legal is a paid product. |
| **False negatives exist.** An identifier tarja misses stays in the text. | Run `tarja.residual()` as a second pass and keep a human in the loop for high-risk data. A miss is a quality bug, not a vulnerability (see `SECURITY.md`). |
| **`Vault` keeps its map in memory, in one process.** The map dies with the object, so an ingestion job cannot hand tokens to a serving process. | The map IS the personal data. Persisting it drags in key custody, access control, retention, deletion on request, backups and audit, which are decisions about your risk, not a library default. Persistence with a KMS key, authenticated sessions and an audit trail is the paid Tarja Gateway. |
| **`pseudonym_stable` is reversible by whoever holds the key.** | It is pseudonymisation, not anonymisation. Use `redact` when nothing may come back, or `Vault` when reversal must stay under your control. |
| **Text in, text out. No OCR, no scanned PDF.** | Extract the text first with a tool of your choice. |

EN: none of this removes your own obligations: legal basis, records, security measures and answering data subjects stay with you.

PT: o tarja ajuda a detectar, **não garante conformidade c/ a LGPD** e não anonimiza no sentido do art. 12. O q ele não faz, de propósito:

| limite | por quê / o q fazer no lugar |
|---|---|
| **Não pega nome, endereço, e-mail, data de nascimento nem dado de saúde.** Só identificador estruturado (níveis N1 a N3). | Isso é nível N4 e depende de NER, q não está implementado aqui. Combine o tarja c/ um modelo de NER, ou registre sua entidade c/ `register_entity()`. NER setorial p/ saúde e jurídico é produto pago. |
| **Falso negativo existe.** Identificador q o tarja não pega fica no texto. | Use o `tarja.residual()` como 2ª passada e mantenha revisão humana p/ dado de alto risco. Falha de detecção é bug de qualidade, não vulnerabilidade (ver `SECURITY.md`). |
| **O `Vault` guarda o mapa em memória, num processo só.** O mapa morre c/ o objeto, então um job de ingestão não consegue passar token p/ o processo q serve. | O mapa É o dado pessoal. Persistir puxa junto guarda de chave, controle de acesso, retenção, exclusão a pedido, backup e auditoria, q são decisões sobre o seu risco, não padrão de biblioteca. Persistência c/ chave em KMS, sessão autenticada e trilha de auditoria é o Tarja Gateway pago. |
| **O `pseudonym_stable` é reversível por quem tem a chave.** | É pseudonimização, não anonimização. Use `redact` qdo nada pode voltar, ou o `Vault` qdo a reversão tem q ficar sob seu controle. |
| **Entra texto, sai texto. Sem OCR, sem PDF escaneado.** | Extraia o texto antes, c/ a ferramenta q preferir. |

PT: nada disso tira as suas obrigações: base legal, registros, medidas de segurança e resposta ao titular continuam suas.

## install / instalar

```bash
pip install -e ".[dev]"
```

## usage / uso

```python
import os

import tarja

text = "Paciente CPF 529.982.247-25, cartao SUS 729 1417 7763 1701, processo 0000001-83.2017.8.26.0100"

for m in tarja.find(text):
    print(m.entity, m.start, m.end, m.score)  # BR_CPF 13 27 0.95 ...

tarja.mask(text)  # "Paciente CPF <BR_CPF>, cartao SUS <BR_CNS>, processo <BR_CNJ>"
tarja.mask(text, strategy="pseudonym")  # <BR_CPF_1>, same value -> same label / mesmo valor -> mesmo rotulo
# EN: same label in EVERY document, key from a secrets manager / PT: mesmo rotulo em TODO documento
tarja.mask(text, strategy="pseudonym_stable", salt=os.environ["TARJA_SALT"])  # <BR_CPF:3f9a1c0b2e7d>

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
answer = call_your_llm(safe)                  # EN: safe is a plain str / PT: safe e uma str normal
vault.reveal(answer, issued_by=safe)          # EN: only the tokens safe issued / PT: so os tokens do safe
tarja.residual(safe)  # [] = nothing leaked / nada vazou
```

EN: tokens are 96-bit HMACs, and a clash raises `VaultCollisionError` instead of mixing two people up. `reveal()` is scoped to the `protect()` call that issued the tokens, so a token echoed from someone else's text does not resolve, even when one vault serves several users. A scope is single use (`reuse=True` to repeat it) and expires after an hour (`Vault(ttl=...)`, `None` for never). `reveal(text, any_token=True)` turns all of that off and restores anything the vault ever issued: only for text you trust. Whoever holds the `Vault` object can reveal everything, same as holding a decryption key, and the mapping lives in memory for one process. For multi-tenant production use (key in KMS, rehydration tied to an authenticated session, probing quotas, audit trail) see the paid Tarja Gateway.
PT: token é HMAC de 96 bits, e colisão levanta `VaultCollisionError` em vez de trocar uma pessoa por outra. O `reveal()` fica preso à chamada do `protect()` q emitiu os tokens, então token ecoado do texto de outra pessoa não resolve, mesmo c/ um cofre só p/ vários usuários. O escopo é de uso único (`reuse=True` p/ repetir) e vence em 1h (`Vault(ttl=...)`, `None` p/ nunca). O `reveal(texto, any_token=True)` desliga tudo isso e devolve qq token q o cofre já emitiu: só p/ texto confiável. Quem tem o objeto `Vault` na mão reverte tudo, igual a quem tem a chave, e o mapa fica em memória num processo só. P/ produção multi-tenant (chave em KMS, reidratação amarrada a sessão autenticada, quota anti-sondagem, trilha de auditoria) veja o Tarja Gateway pago.

EN: `pseudonym_stable` is pseudonymisation, not anonymisation under the LGPD. The `salt` is not a salt in the classic sense, it is **a secret key**: there are only 10⁹ valid CPFs, so whoever holds it hashes all of them in minutes and reverses every label. It was called `hash` until 0.5, and the name was wrong: nothing here is one way. tarja **refuses** a key under 16 bytes, one with fewer than 8 distinct bytes, and known placeholders like `changeme`. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`, keep it in a secrets manager, never in code, env files committed to git, or logs, and rotate it if it leaks. If you need something that cannot be reversed, use `redact`. If you need reversal under your control, use `Vault`.
PT: `pseudonym_stable` é pseudonimização, não anonimização na LGPD. O `salt` não é salt no sentido clássico, é **chave secreta**: só existem 10⁹ CPFs válidos, então quem tem a chave calcula todos em minutos e reverte qq rótulo. Até a 0.5 a estratégia se chamava `hash`, e o nome estava errado: nada aqui é de mão única. O tarja **recusa** chave c/ menos de 16 bytes, c/ menos de 8 bytes distintos e placeholder conhecido tipo `changeme`. Gere c/ `secrets.token_hex(32)`, guarde num cofre de segredos, nunca em código, `.env` commitado ou log, e troque se vazar. Se precisa do q não volta, use `redact`. Se precisa reverter sob seu controle, use o `Vault`.

### command line / linha de comando

```bash
tarja scan contrato.txt                  # JSON lines, values hidden / valores escondidos
tarja scan contrato.txt --format table
tarja scan contrato.txt --show-values    # EN: raw values, careful / PT: valor cru, cuidado
tarja scan contrato.txt --suspect        # EN: also wrong check digits / PT: tb DV errado
tarja mask contrato.txt > limpo.txt
tarja mask contrato.txt --strategy pseudonym_stable --salt "$TARJA_SALT"
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
- Tip: code comments carry tags like `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, so ctrl+f finds anything. Comments are short and in English. Public docstrings are bilingual, EN then PT.

PT:
- `spec/entities/*.yaml`: 1 arquivo por entidade (regex, DV, contexto, score, fonte oficial). Fonte única, o resto é gerado/testado daqui.
- `spec/schema.json`: schema desses yaml.
- `src/tarja/validators/`: DV de cada doc, só stdlib.
- `tests/`: `python -m unittest discover -s tests` ou `pytest`.
- Dica: os comentários têm tags tipo `[CPF-DV]`, `[CNPJ-REGEX]`, `[TEST-SPEC]`, dá p/ achar tudo c/ ctrl+f. Comentário é curto e em inglês. Docstring pública é bilíngue, EN e dps PT.

EN: official source for each rule, and whether it was checked: `docs/SOURCES.md`. Presidio plugin and upstream PR: `docs/presidio.md`. Benchmark: `bench/README.md`.
PT: fonte oficial de cada regra, e se foi conferida: `docs/SOURCES.md`. Plugin do Presidio e PR: `docs/presidio.md`. Benchmark: `bench/README.md`.

## licence / licença

Apache 2.0. EN: chosen for its explicit patent grant, which matters to companies. PT: escolhida pela cláusula explícita de patentes, que pesa p/ empresas.

Maintained by / mantido por [@macmaia](https://github.com/macmaia) · tarja@micah6ai.com
