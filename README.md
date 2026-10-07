# tarja

**EN** · Detects, validates and masks Brazilian personal identifiers in free text, using Portuguese context and check digits. Cover the data before it goes to an LLM, logs, BI, wherever.

Built for anyone shipping software in Brazil, incl. foreign companies adapting to the LGPD (Brazil's GDPR). Plenty of CPF/CNPJ validators exist already (brutils, validate-docbr). What's missing is finding the ID *inside* text, scoring it with Portuguese context, and covering what paid DLPs skip: alphanumeric CNPJ (Jul/2026), CNS (health card), CNJ case numbers.

Status: alpha (`0.12.0`). The API can still change before 1.0.

**PT** · Detecta, valida e mascara identificadores pessoais brasileiros em texto livre, c/ contexto em português e dígito verificador. Cobre o dado antes de mandar p/ LLM, log, BI, onde for.

Serve p/ qq um q desenvolve p/ o Brasil, inclusive empresa gringa se adaptando à LGPD. Validador de CPF/CNPJ já tem de monte (brutils, validate-docbr). O q falta é achar o doc *dentro* do texto, dar score c/ contexto em pt-BR e cobrir o q os DLPs pagos ignoram: CNPJ alfanumérico (jul/2026), CNS, nº de processo CNJ.

Status: alfa (`0.12.0`). A API ainda pode mudar antes da 1.0.

## when you'd reach for this / quando isso serve

EN: five situations where tarja is the right tool. If yours is not one of them, it probably is not.

- **Before text goes to an LLM.** You have a support archive, a case file, a set of medical notes, and you want to do RAG or summarising over it with a provider you do not control. Swap the identifiers out first. tarja gives the same identifier the same token in every document and every request, which is the part that matters here: destructive redaction breaks retrieval, and a token that changes per request breaks it just as badly.
- **As a gate on the way out.** `tarja scan file.txt && send.sh` only sends a file that came back clean. Exit 1 when something is found, 0 when clean, 2 on error, which is what makes it usable in CI or in a cron job.
- **To measure exposure.** Point it at an archive and get an answer to "how many documents carry a CPF, which kinds, and where". Compliance questions tend to arrive without a number attached, and this produces one.
- **Before handing data to someone who should not see it.** An analyst, a vendor, a staging environment. Cover the identifier and the rest of the document still works.
- **To check someone else's work.** `residual()` is a second pass over text that has already been masked, by you or by another tool, and it reports what survived.

PT: cinco situações em que o tarja é a ferramenta certa. Se a sua não é uma delas, provavelmente não é.

- **Antes do texto ir p/ um LLM.** Você tem um acervo de atendimento, processo, prontuário, e quer fazer RAG ou resumo com um provedor q não é seu. Troque os identificadores antes. O tarja dá ao mesmo identificador o mesmo token em todo documento e em toda requisição, e é isso q importa aqui: redação destrutiva quebra a busca, e token q muda a cada requisição quebra igual.
- **Como portão de saída.** O `tarja scan arquivo.txt && enviar.sh` só envia arquivo q voltou limpo. Sai 1 se achou, 0 se limpo, 2 em erro, q é o q torna isso usável em CI ou em cron.
- **P/ medir exposição.** Aponte p/ um acervo e tenha resposta p/ "quantos documentos têm CPF, de q tipo, e onde". Pergunta de conformidade costuma chegar sem número, e aqui sai um.
- **Antes de entregar dado p/ quem não precisa dele.** Analista, fornecedor, ambiente de homologação. Cobre o identificador e o resto do documento continua servindo.
- **P/ conferir o trabalho de outro.** O `residual()` é uma segunda passada em texto q já foi mascarado, por você ou por outra ferramenta, e diz o q sobrou.

## intended use / uso pretendido

EN: tarja exists so that whoever holds personal data can find it and cover it before the data leaves for an LLM, a log, a BI tool or a third party. That is the use it is built, tested and documented for.

EN: **it is dual use, and pretending otherwise would be dishonest.** A detector that finds identifiers in order to mask them also finds identifiers, full stop. Pointing it at documents you have no business holding, to harvest CPFs, is a use this project rejects. It is also already unlawful in Brazil: under the LGPD, data that was made public does not become free data (art. 7, para. 3, keeps purpose and good faith in force), and art. 42 attaches liability for the damage caused. None of that depends on tarja existing.

EN: the licence is Apache 2.0 and does not restrict fields of use, on purpose. A "do no evil" clause would stop being open source under the OSI definition, would block contribution upstream, and would not deter anyone who already ignores the law. So this section is not a legal instrument. It states what good faith looks like here, which is what makes "I did not know what it was for" indefensible.

### what is deliberately absent / o que falta de propósito

EN: these are design decisions, not gaps waiting to be filled. Pull requests adding them will be declined.

- **No collector.** tarja reads text you already have. It does not crawl, does not call any official gazette, registry or open-data API, and ships no mass-collection script. One narrow exception, named so nobody has to find it: `bench/fetch_public_texts.py` downloads 14 compiled federal laws from planalto.gov.br, paced at two seconds apart, to build the benchmark's background text. That is the benchmark, not the library, and the library never calls it. The research pipeline used for our own gazette study lives outside this repository and is not published.
- **No enrichment.** A detected identifier is never resolved into a name, an address or a record. tarja never queries the Receita Federal, any government service or any external database. It has zero runtime dependencies, so it cannot phone anywhere.
- **No value output by default.** `tarja scan` prints entity type, offsets and score, and hides the values. Printing them takes an explicit `--show-values`, so nothing leaks into a terminal history, a log or a CI artefact by accident.
- **No stored mapping.** `Vault` keeps its map in memory for one process and it dies with the object (see limits above).

PT: o tarja existe p/ quem tem dado pessoal achar e cobrir esse dado antes dele sair p/ um LLM, um log, um BI ou um terceiro. É p/ isso q ele foi feito, testado e documentado.

PT: **é uso dual, e fingir o contrário seria desonesto.** Um detector q acha identificador p/ mascarar também acha identificador, ponto. Apontar p/ documento q não é seu, p/ garimpar CPF, é uso q este projeto rejeita. E já é ilícito no Brasil: na LGPD, dado tornado público não vira dado livre (art. 7, par. 3, mantém finalidade e boa-fé), e o art. 42 responsabiliza por dano. Nada disso depende de o tarja existir.

PT: a licença é Apache 2.0 e não restringe campo de uso, de propósito. Cláusula de "não usar p/ o mal" deixaria de ser open source pela definição da OSI, travaria a contribuição upstream e não deteria quem já ignora a lei. Então esta seção não é instrumento jurídico. Ela diz o q é boa-fé aqui, q é o q torna indefensável o "não sabia p/ q servia".

### o que falta de propósito

PT: são decisões de desenho, não lacunas esperando preenchimento. PR q adicionar isso será recusado.

- **Sem coletor.** O tarja lê texto q vc já tem. Não rastreia, não chama API de diário oficial, cartório ou dados abertos, e não traz script de coleta em massa. Uma exceção estreita, dita p/ ninguém ter q descobrir: o `bench/fetch_public_texts.py` baixa 14 leis federais compiladas do planalto.gov.br, c/ 2 s de pausa, p/ montar o texto de fundo do benchmark. Isso é o benchmark, não a biblioteca, e a biblioteca nunca chama ele. O pipeline da nossa própria pesquisa c/ diários fica fora deste repositório e não é publicado.
- **Sem enriquecimento.** Identificador detectado nunca vira nome, endereço ou cadastro. O tarja não consulta a Receita, nenhum serviço público e nenhuma base externa. Ele tem zero dependência em tempo de execução, então não tem p/ onde ligar.
- **Sem mostrar valor por padrão.** O `tarja scan` imprime tipo, posição e score, e esconde os valores. P/ imprimir, exige `--show-values`, então nada vaza p/ histórico de terminal, log ou artefato de CI por descuido.
- **Sem mapa guardado.** O `Vault` mantém o mapa em memória num processo só e ele morre c/ o objeto (ver limites acima).

## install / instalar

```bash
pip install tarja                 # EN: core, no runtime dependency / PT: nucleo, sem dependencia de runtime
pip install tarja-presidio        # EN: Presidio plugin / PT: plugin do Presidio
```

EN: from a clone, for development / PT: a partir de um clone, p/ desenvolver:

```bash
pip install -e ".[dev]" -e "packages/tarja-presidio[dev]"
```

## usage / uso

EN: docs and a runnable notebook: <https://macmaia.github.io/tarja/> ·
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/macmaia/tarja/blob/main/notebooks/tarja_quickstart.ipynb)
PT: documentação e um caderno que roda no navegador, sem instalar nada.


```python
import os

import tarja

text = "Paciente CPF 529.982.247-25, cartao SUS 729 1417 7763 1701, processo 0000001-83.2017.8.26.0100"

for m in tarja.find(text):
    print(m.entity, m.start, m.end, m.score)  # BR_CPF 13 27 0.95 ...

tarja.mask(text)  # "Paciente CPF <BR_CPF>, cartao SUS <BR_CNS>, processo <BR_CNJ>"
tarja.mask(text, strategy="pseudonym")  # <BR_CPF_1>, same value -> same label / mesmo valor -> mesmo rotulo
# EN: same label in EVERY document, key from a secrets manager / PT: mesmo rotulo em TODO documento
tarja.mask(text, strategy="pseudonym_stable", salt=os.environ["TARJA_SALT"])  # <BR_CPF:24da:3f9a1c0b2e7d>, 24da = geracao da chave

tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35")  # True (alphanumeric CNPJ / CNPJ alfanum)

# EN: your own entity, no fork needed. Call it ONCE, at start-up, before serving requests: the registry is
#     process-wide, so registering inside a request handler changes detection for everything else running in
#     that process. tarja.freeze() closes it afterwards. / PT: entidade própria, sem fork. Chame 1x, no
#     start-up, antes de servir requisição: o registro vale p/ o processo inteiro. O tarja.freeze() fecha dps.
tarja.register_entity(
    "ACME_EMPLOYEE_ID",
    [("acme", r"\bAC-\d{6}\b", 0.3)],
    context_words=["matricula acme"],  # EN: lowercase, no accents / PT: minúsculo, sem acento
)

# EN: typos with a wrong check digit, score 0, valid_dv=False / PT: digitacao c/ DV errado, score 0, valid_dv=False
tarja.find("cpf 529.982.247-24", report_invalid=True)

# EN: reversible tokens, e.g. before sending text to an LLM / PT: token reversivel, ex. antes de mandar p/ um LLM
vault = tarja.Vault()
safe = vault.protect(text)  # "Paciente CPF <BR_CPF:cfa1:4b1a3edcd5f6c2e81a9d07b3>, ..."
answer = call_your_llm(safe)                  # EN: safe is a plain str / PT: safe e uma str normal
vault.reveal(answer, issued_by=safe)          # EN: only the tokens safe issued / PT: so os tokens do safe
tarja.residual(safe)  # [] = nothing leaked / nada vazou
```

EN: tokens are 96-bit HMACs, and a clash raises `VaultCollisionError` instead of mixing two people up. `reveal()` is scoped to the `protect()` call that issued the tokens, so a token echoed from someone else's text does not resolve, even when one vault serves several users. A scope is single use (`reuse=True` to repeat it) and expires after an hour (`Vault(ttl=...)`, `None` for never). `reveal(text, any_token=True)` turns all of that off and restores anything the vault ever issued: only for text you trust. Whoever holds the `Vault` object can reveal everything, same as holding a decryption key, and the mapping lives in memory for one process. For multi-tenant production use (key in KMS, rehydration tied to an authenticated session, probing quotas, audit trail) see the paid Tarja Gateway.
PT: token é HMAC de 96 bits, e colisão levanta `VaultCollisionError` em vez de trocar uma pessoa por outra. O `reveal()` fica preso à chamada do `protect()` q emitiu os tokens, então token ecoado do texto de outra pessoa não resolve, mesmo c/ um cofre só p/ vários usuários. O escopo é de uso único (`reuse=True` p/ repetir) e vence em 1h (`Vault(ttl=...)`, `None` p/ nunca). O `reveal(texto, any_token=True)` desliga tudo isso e devolve qq token q o cofre já emitiu: só p/ texto confiável. Quem tem o objeto `Vault` na mão reverte tudo, igual a quem tem a chave, e o mapa fica em memória num processo só. P/ produção multi-tenant (chave em KMS, reidratação amarrada a sessão autenticada, quota anti-sondagem, trilha de auditoria) veja o Tarja Gateway pago.

### which strategy / qual estratégia

EN: the three are not degrees of the same thing, they answer different questions. Pick by what you need to be
able to do afterwards.

| | what comes out | same value gives the same label | reversible | what it is for |
|---|---|---|---|---|
| `redact` | `<BR_CPF>` | no, everything looks alike | no, the value is gone | you never need it back and must not be able to get it back |
| `pseudonym` | `<BR_CPF_1>` | **within one call only** | no | counting people in one document, reading it without the numbers |
| `pseudonym_stable` | `<BR_CPF:24da:3f9a…>` | **across every document, under one key** | yes, by whoever holds the key | joining records about the same person across files and over time |

EN: the column that decides is the middle one. `pseudonym` numbers what it sees in **that call** and starts
again at 1 on the next, so you cannot join two documents, and that is the point. `pseudonym_stable` derives
the label from the value and a secret key, so it is the same everywhere that key is, which is what lets you
build a dataset about a person without the person's number in it. That power is the risk: a stable label is
pseudonymisation, not anonymisation, and under the LGPD it is still personal data. If nothing may ever come
back, use `redact`.

PT: as três não são graus da mesma coisa, respondem perguntas diferentes. Escolha pelo que você precisa
conseguir fazer depois.

| | o que sai | mesmo valor dá o mesmo rótulo | reversível | p/ quê |
|---|---|---|---|---|
| `redact` | `<BR_CPF>` | não, tudo fica igual | não, o valor sumiu | você nunca vai precisar de volta e não pode conseguir |
| `pseudonym` | `<BR_CPF_1>` | **só dentro de uma chamada** | não | contar pessoas num documento, ler sem os números |
| `pseudonym_stable` | `<BR_CPF:24da:3f9a…>` | **em todo documento, sob uma chave** | sim, por quem tem a chave | juntar registros da mesma pessoa entre arquivos e ao longo do tempo |

PT: a coluna que decide é a do meio. O `pseudonym` numera o que vê **naquela chamada** e recomeça do 1 na
próxima, então você não junta dois documentos, e é essa a intenção. O `pseudonym_stable` deriva o rótulo do
valor e de uma chave secreta, e esse poder é o risco: rótulo estável é pseudonimização, não anonimização, e
na LGPD continua sendo dado pessoal. Se nada pode voltar, use `redact`.

EN: key handling, the generation marker, what happens when you rotate, and why there is no re-keying helper:
[pseudonymisation and the key](https://macmaia.github.io/tarja/pseudonimizacao.html).
PT: guarda de chave, marcador de geração, o que acontece ao trocar a chave e por que não existe ajudante de
rotação: [pseudonimização e a chave](https://macmaia.github.io/tarja/pseudonimizacao.html).

### command line / linha de comando

```bash
tarja scan contrato.txt                  # JSON lines, values hidden / valores escondidos
tarja scan contrato.txt --format table
tarja scan contrato.txt --show-values    # EN: raw values, careful / PT: valor cru, cuidado
tarja scan contrato.txt --suspect        # EN: also wrong check digits / PT: tb DV errado
tarja scan contrato.txt --fail-on-suspect  # EN: exit 1 on them too / PT: sai 1 neles tb
tarja mask contrato.txt > limpo.txt
tarja mask contrato.txt               # EN: wrong check digits are masked too / PT: DV errado tb
tarja mask contrato.txt --strategy pseudonym_stable --salt "$TARJA_SALT"
cat log.txt | tarja scan - --entities BR_CPF,BR_CNPJ   # EN: gate / PT: portão
tarja scan contrato.txt --report-min-score 0.9         # EN: report filter only, NOT a gate
                                                       # PT: só filtra o relatório, NÃO é portão
```

EN: exit code 1 when something is found, 0 when clean, 2 on error. Handy in CI. Input is capped at 50 units of 1,048,576 characters (`--max-mb`), so about 52.4 M characters. The guard
exists against memory exhaustion, which scales with characters, not with bytes on disk: an accented
UTF-8 file can be larger than 50 MB on disk and still pass.
PT: exit code 1 qdo acha algo, 0 qdo limpo, 2 em erro. Útil em CI. Entrada limitada a 50 unidades de 1.048.576 caracteres (`--max-mb`), ~52,4 M de caracteres. A trava
existe contra estouro de memoria, q escala c/ caractere e nao c/ byte em disco: arquivo UTF-8 acentuado
pode ter mais de 50 MB em disco e ainda passar.

EN: the exit code is decided over every VALID candidate found, BEFORE `--report-min-score` is applied.
Raising the threshold hides rows from the report and never turns exit 1 into exit 0, so
`tarja scan f.txt && send.sh` stays fail-closed. Two things do narrow the gate, and both say so out loud.
Narrowing `--entities` narrows it, because an entity nobody searches for cannot be found. And a value with
the right shape and a WRONG check digit (a suspect, usually a typo or OCR noise on a real identifier) is not
counted unless you pass `--suspect`, because an invoice or protocol number in CPF shape is a suspect too and
would block every pipeline. `--fail-on-suspect` is the opt-out: it adds suspects to the exit code without
changing the report, for whoever would rather stop the send than accept that risk. Without either flag,
`scan` writes a counted warning to stderr saying how many it ignored. `mask` has no threshold flag at all,
because it has no report to filter, and since 0.10.0 it masks suspects by default: a command that replaces
your document must not leave an eleven-digit value in it.
PT: o exit code é decidido sobre todo candidato VÁLIDO achado, ANTES do `--report-min-score`. Subir o limiar
esconde linhas do relatório e nunca vira exit 0, então `tarja scan f.txt && send.sh` continua falhando
fechado. Duas coisas reduzem o portão, e as duas avisam. Reduzir o `--entities` reduz, pq entidade não
procurada não é achada. E valor c/ a forma certa e DV ERRADO (suspeito, normalmente erro de digitação ou
ruído de OCR num identificador real) não conta sem `--suspect`, pq nota fiscal e protocolo em forma de CPF
também são suspeitos e travariam todo pipeline. O `--fail-on-suspect` é a saída: soma suspeito ao exit code
sem mudar o relatório. Sem nenhuma das duas flags, o `scan` escreve no stderr quantos ignorou. O `mask` não
tem flag de limiar, pq não tem relatório para filtrar, e desde a 0.10.0 mascara suspeito por padrão.

## three functions, three policies / três funções, três políticas

EN: a **suspect** is a value shaped like an identifier whose check digit does not close. It is usually a
real identifier with a typo: measured, about 93% of CPFs with one corrupted digit reconstruct to a single
valid CPF. The three entry points treat it differently, on purpose.

| | suspect | why / por quê |
|---|---|---|
| `mask()` | masked | the function promises the value is gone from the text it returns, so leaving an eleven-digit value in there would be a broken promise |
| `tarja scan` | exit code unchanged | an exit code is a one-byte channel with nowhere to put a reason, and gating on suspects teaches people to write `\|\| true`, which removes the gate for valid identifiers too. `--fail-on-suspect` opts in |
| `decide()` / `require_clean()` | blocked | returns an object, so it can say what it blocked and why. The person reading the reason is the person who decides. `on_suspect="allow"` opts out |

PT: **suspeito** é valor c/ cara de identificador cujo DV não fecha, normalmente identificador real c/ erro
de digitação. As três portas tratam diferente, de propósito: o `mask()` mascara, pq promete q o valor saiu
do texto. O `scan` não muda o exit code, pq código de saída não tem onde pôr motivo e travar nele ensina a
escrever `|| true`. O `decide()` barra, pq devolve objeto e consegue dizer o q barrou e por quê.

## limits / limites

EN: tarja is a detection aid, **not a guarantee of LGPD compliance**, and not an anonymiser in the sense of
art. 12. Six things it does not do, on purpose:

| limit | why / what to do instead |
|---|---|
| **No names, addresses, e-mails, dates of birth or health data.** Only structured identifiers, tiers N1 to N3. | Those are tier N4 and need NER. Combine tarja with a NER model, or add your own with `register_entity()`. |
| **False negatives exist.** An identifier tarja misses stays in the text. | Run `residual(report_invalid=True)` as a second pass and keep a human in the loop for high-risk data. A miss is a quality bug, not a vulnerability (`SECURITY.md`). |
| **`Vault` keeps its map in memory, in one process.** | The map IS the personal data. Persisting it drags in key custody, access control, retention and audit, which are decisions about your risk, not a library default. |
| **`pseudonym_stable` is reversible by whoever holds the key.** | Pseudonymisation, not anonymisation. Use `redact` when nothing may come back, or `Vault` when reversal must stay under your control. |
| **Text in, text out.** No OCR, no scanned PDF. | Extract the text first, with a tool of your choice. |
| **An identifier glued to other digits is only found when a context word names it.** `cpf 0052998224725` is found, `registro 0052998224725` is not. | The check digit alone is too weak a filter there: 90% of random 24-digit runs close some identifier by chance. Label your columns, or pre-split the runs. |
| **A suspect is not debug output.** A number shaped like a document with a failing check digit is nearly always a REAL identifier with a typo. | Treat it like the identifier itself. `repr()` on a `Match` hides the value, so logs and tracebacks never carry it by accident. |

EN: none of this removes your own obligations: legal basis, records, security measures and answering data
subjects stay with you.

PT: o tarja ajuda a detectar, **não garante conformidade c/ a LGPD** e não anonimiza no sentido do art. 12.
Seis coisas q ele não faz, de propósito:

| limite | por quê / o q fazer no lugar |
|---|---|
| **Não pega nome, endereço, e-mail, data de nascimento nem dado de saúde.** Só identificador estruturado, N1 a N3. | Isso é N4 e depende de NER. Combine c/ um modelo de NER, ou registre a sua c/ `register_entity()`. |
| **Falso negativo existe.** Identificador q o tarja não pega fica no texto. | Use `residual(report_invalid=True)` como 2ª passada e mantenha revisão humana p/ dado de alto risco. |
| **O `Vault` guarda o mapa em memória, num processo só.** | O mapa É o dado pessoal. Persistir puxa guarda de chave, controle de acesso, retenção e auditoria, q são decisões sobre o seu risco. |
| **O `pseudonym_stable` é reversível por quem tem a chave.** | Pseudonimização, não anonimização. Use `redact` qdo nada pode voltar, ou o `Vault` qdo a reversão fica c/ você. |
| **Entra texto, sai texto.** Sem OCR, sem PDF escaneado. | Extraia o texto antes. |
| **Identificador colado a outros dígitos só é achado com palavra de contexto perto.** `cpf 0052998224725` acha, `registro 0052998224725` não. | O DV sozinho é filtro fraco ali: 90% das corridas de 24 dígitos fecham algum identificador por acaso. |
| **Suspeito não é saída de depuração.** Número c/ cara de documento e DV errado quase sempre é identificador REAL c/ erro de digitação. | Trate como o próprio identificador. O `repr()` de um `Match` esconde o valor. |

PT: nada disso tira as suas obrigações: base legal, registros, medidas de segurança e resposta ao titular
continuam suas.

EN: persistence with a KMS key, authenticated sessions and an audit trail, plus per-tenant keys and sector
NER for health and legal, are the paid Tarja Gateway.
PT: persistência c/ chave em KMS, sessão autenticada e trilha de auditoria, mais chave por tenant e NER
setorial, são o Tarja Gateway pago.

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
| `BR_CARTAO` | payment card: issuer prefix + Luhn / cartão, prefixo de emissor + Luhn | N1 | beta |

EN: **changed in 0.6.** `BR_CARTAO` now also requires a registered issuer prefix and the length that issuer uses, not the Luhn digit alone. Luhn on its own accepts about one in ten long numeric sequences, and administrative text is full of protocol and account numbers that long. `tarja.validators.cartao.is_valid(value, require_brand=False)` keeps the old behaviour when you really want it, and `cartao.brand(value)` returns the network.
PT: **mudou na 0.6.** O `BR_CARTAO` passou a exigir tb prefixo de emissor registrado e o comprimento daquela bandeira, não só o DV Luhn. Luhn sozinho aceita ~1 em 10 sequências numéricas longas. O `is_valid(valor, require_brand=False)` mantém o comportamento antigo, e o `cartao.brand(valor)` devolve a bandeira.

EN: N1 = strong check digit, N2 = format only, N3 = needs context, N4 = NER. Scores: N1 0.95 with a context word nearby, 0.8 to 0.9 without. N2 0.7 / 0.5. N3 only with context, 0.5, except `BR_MATRICULA_IMOVEL` at 0.4. Wrong check digit = dropped (unless `report_invalid=True`). Speed: ~1 ms per 100 tokens, 17 entities.
PT: N1 = DV forte, N2 = só formato, N3 = depende de contexto, N4 = NER. Score: N1 0.95 c/ palavra de contexto perto, 0.8 a 0.9 sem. N2 0.7 / 0.5. N3 só c/ contexto, 0.5, exceto `BR_MATRICULA_IMOVEL` c/ 0.4. DV errado = descartado (exceto c/ `report_invalid=True`). Velocidade: ~1 ms por 100 tokens, 17 entidades.

## stability / estabilidade

EN: **0.x means the API can change.** Until 1.0 a public name may be renamed or removed in a minor release.
Two already moved: `mask(strategy="hash")` became `pseudonym_stable` in 0.5 and went in 0.9.0, and the
Presidio plugin shipped as `tarja-presidio`. Before 1.0 you can rely on four things:

- a rename ships with the old name working for at least one minor release, warning on stderr rather than as
  a `DeprecationWarning`, which Python hides by default on a command line
- a removal announced in a warning is kept. `strategy="hash"` was announced for 0.6 and only went in 0.9.0,
  which is why `--min-score` now carries the version it goes away in, 1.0.0
- a change to what `find()` detects is announced in `CHANGELOG.md` with the benchmark numbers before and
  after, and a release that only changes the command line says so and gives the figures it re-measured
- after 1.0, the usual rule: no breaking change outside a major release

EN: pin an exact version if you want none of this reaching you, but read `CHANGELOG.md` first. Versions
0.6.0, 0.7.0 and 0.8.0 are yanked on PyPI: in those, a score threshold could turn `tarja scan` exit 1 into
exit 0, so a `&&` pipeline passed with personal data in the file.

PT: **0.x quer dizer q a API pode mudar.** Até a 1.0, nome público pode ser renomeado ou sumir numa versão
menor. Dois já se moveram. Antes da 1.0 dá p/ contar com quatro coisas:

- renomeação sai c/ o nome antigo funcionando por pelo menos 1 versão menor, avisando no stderr e não c/
  `DeprecationWarning`, q o Python esconde por omissão na linha de comando
- remoção anunciada num aviso é cumprida
- mudança no q o `find()` detecta é anunciada no `CHANGELOG.md` c/ o número do benchmark antes e depois
- dps da 1.0, a regra de sempre: nada q quebra fora de versão maior

PT: fixe a versão exata se não quiser nada disso, mas leia o `CHANGELOG.md` antes. As versões 0.6.0, 0.7.0 e
0.8.0 estão yankadas no PyPI: nelas um limiar podia virar o exit 1 do `tarja scan` em exit 0.

## more / mais

EN: official source for each rule and whether it was checked, [SOURCES](https://macmaia.github.io/tarja/SOURCES.html). Presidio plugin and upstream PR, [presidio](https://macmaia.github.io/tarja/presidio.html). Key handling, [pseudonymisation](https://macmaia.github.io/tarja/pseudonimizacao.html). Benchmark, `bench/README.md`. Repository layout and how to add an entity, `CONTRIBUTING.md`.
PT: fonte oficial de cada regra e se foi conferida, [SOURCES](https://macmaia.github.io/tarja/SOURCES.html). Plugin do Presidio e PR, [presidio](https://macmaia.github.io/tarja/presidio.html). Guarda de chave, [pseudonimização](https://macmaia.github.io/tarja/pseudonimizacao.html). Benchmark, `bench/README.md`. Organização do repositório e como adicionar entidade, `CONTRIBUTING.md`.

## licence / licença

Apache 2.0. EN: chosen for its explicit patent grant, which matters to companies. PT: escolhida pela cláusula explícita de patentes, que pesa p/ empresas.

Maintained by / mantido por [@macmaia](https://github.com/macmaia) · tarja@micah6ai.com
