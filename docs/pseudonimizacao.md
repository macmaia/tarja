---
title: "Pseudonymisation and the key"
description: "What a stable label is, the key generation marker, what happens when you rotate the key, and what tarja deliberately does not do with key material."
---

# pseudonymisation and the key / pseudonimização e a chave

EN: this page is the long version of the `which strategy` table in the README. Read that first if you only
need to pick one.
PT: esta página é a versão longa da tabela `qual estratégia` do README. Leia aquela antes se você só precisa
escolher uma.

## what a stable label costs / o que custa um rótulo estável


EN: both `Vault` and `pseudonym_stable` produce a **stable** label: the same value always yields the same
label. That stability holds under one key and only one. Rotate the key and the same CPF gets a different
label, so a document masked last month stops joining with one masked today.

EN: tarja makes that visible instead of silent. Every label carries a 4-hex **key generation marker** derived
from the key itself (`<BR_CPF:24da:3f9a1c0b2e7d>`). Same key, same marker, on any machine and in any process.
Different key, different marker. `Vault.key_id` exposes it, and `tarja.vault.key_id(key)` computes it for any
key. It is not a secret and not an integrity check: it tells you which generation a label belongs to, so you
can reindex incrementally and run two generations side by side during a migration.

EN: what tarja does **not** do, and will not pretend to:

- **No rotation.** There is no re-keying helper. Rotating means re-masking the source data under the new key,
  which only you can schedule, because only you know where the documents are.
- **No key storage.** The key lives in memory as `bytes`, for as long as your process holds it. CPython gives
  no reliable way to wipe a `bytes` object: it may have been copied by the interpreter, the allocator or the
  operating system's swap. Anything claiming to zeroise it in pure Python is theatre. The honest control is to
  shorten the key's life, not to pretend it was erased: build the object late, drop the reference early, and
  keep long-lived key material in a KMS or HSM where the process never sees it.
- **No per-tenant keys, no audit of who revealed what.** That needs identity and durable storage, which is the
  paid Tarja Gateway.

PT: o `Vault` e o `pseudonym_stable` produzem rótulo **estável**: o mesmo valor sempre dá o mesmo rótulo. Essa
estabilidade vale sob uma chave, e só uma. Trocou a chave, o mesmo CPF vira outro rótulo, e documento
mascarado mês passado deixa de casar c/ um mascarado hoje.

PT: o tarja torna isso visível em vez de silencioso. Todo rótulo leva um **marcador de geração da chave** de 4
hex, derivado da própria chave (`<BR_CPF:24da:3f9a1c0b2e7d>`). Mesma chave, mesmo marcador, em qq máquina.
O `Vault.key_id` expõe, e o `tarja.vault.key_id(chave)` calcula p/ qq chave. Não é segredo nem verificação de
integridade: diz a qual geração o rótulo pertence, o q permite reindexar aos poucos e manter duas gerações
durante uma migração.

PT: o q o tarja **não** faz, e não vai fingir q faz: não tem rotação (rotacionar é remascarar a origem sob a
chave nova, e só vc sabe onde os documentos estão), não guarda chave (ela fica em memória como `bytes`, e o
CPython não dá jeito confiável de apagar, porque pode ter sido copiada pelo interpretador, pelo alocador ou
pela troca de memória do sistema, então quem diz q apaga em Python puro está fazendo teatro, e o controle
honesto é encurtar a vida da chave, não fingir q apagou), e não tem chave por tenant nem auditoria de quem
reidentificou, q dependem de identidade e gravação durável e são o Tarja Gateway pago.

EN: `pseudonym_stable` is pseudonymisation, not anonymisation under the LGPD. The `salt` is not a salt in the classic sense, it is **a secret key**: there are only 10⁹ valid CPFs, so whoever holds it hashes all of them in minutes and reverses every label. It was called `hash` until 0.5, and the name was wrong: nothing here is one way. tarja **refuses** a key under 16 bytes, one with fewer than 8 distinct bytes, and one that begins with a known placeholder word in English or Portuguese. The placeholder test is a prefix test, which is why `changeme_please_123` is refused even though it is long enough, and also why a strong key that happens to start with one of those words is refused too. Generate the key and the question does not come up. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`, keep it in a secrets manager, never in code, env files committed to git, or logs, and rotate it if it leaks. If you need something that cannot be reversed, use `redact`. If you need reversal under your control, use `Vault`.
PT: `pseudonym_stable` é pseudonimização, não anonimização na LGPD. O `salt` não é salt no sentido clássico, é **chave secreta**: só existem 10⁹ CPFs válidos, então quem tem a chave calcula todos em minutos e reverte qq rótulo. Até a 0.5 a estratégia se chamava `hash`, e o nome estava errado: nada aqui é de mão única. O tarja **recusa** chave c/ menos de 16 bytes, c/ menos de 8 bytes distintos e chave q **começa** c/ palavra de placeholder conhecida, em inglês ou português. O teste é de prefixo, e é por isso q `changeme_please_123` é recusado mesmo sendo longo, e tb por isso q chave forte q por acaso comece c/ uma dessas palavras é recusada. Gere a chave e a questão não aparece. Gere c/ `secrets.token_hex(32)`, guarde num cofre de segredos, nunca em código, `.env` commitado ou log, e troque se vazar. Se precisa do q não volta, use `redact`. Se precisa reverter sob seu controle, use o `Vault`.


---

EN: source at [github.com/macmaia/tarja](https://github.com/macmaia/tarja). Contact: tarja@micah6ai.com
