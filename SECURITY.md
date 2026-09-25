# security / segurança

## supported versions / versões c/ suporte

EN: latest 0.x only. PT: só a última 0.x.

## what to report / o q reportar

EN:
- regex at risk of ReDoS.
- real personal data in the repo, its history, an issue or the published package.
- a flaw in a dependency of the adapter packages.

PT:
- regex c/ risco de ReDoS.
- dado pessoal real no repo, no histórico, em issue ou no pacote publicado.
- falha em dependência dos pacotes adaptadores.

## not a vulnerability / não é vulnerabilidade

EN: detection misses (a valid CPF/CNPJ layout tarja does not catch) and false positives are quality bugs, not security issues. Open a public issue with the `detection` label, using generated examples only.
PT: falha de detecção (layout válido de CPF/CNPJ q o tarja não pega) e falso positivo são bug de qualidade, não de segurança. Abra issue pública c/ o rótulo `detection`, só c/ exemplo gerado.

EN: `Vault.reveal()` is scoped to one `protect()` call, so an echoed token from another user does not resolve. Calling it with `any_token=True` opts out of that and is documented behaviour (see `[VAULT-TRUST]` in `vault.py`), not a vulnerability. Same for whoever holds the `Vault` object: it is the key.
PT: o `Vault.reveal()` fica preso a uma chamada do `protect()`, então token ecoado de outro usuário não resolve. Chamar c/ `any_token=True` abre mão disso e é comportamento documentado (ver `[VAULT-TRUST]` no `vault.py`), não é vulnerabilidade. Idem p/ quem tem o objeto `Vault`: ele é a chave.

## if an identifier reached a log / se um identificador foi parar num log

EN: this is the commonest incident with a library like this one, and it is not a vulnerability report, it is
your incident. Since 0.8 printing a `Match` is safe, `repr()` hides the value, so the usual causes are
`--show-values`, `to_dict()` with the default, `m.value` written out by hand, or a version before 0.8.

1. Stop the source first. A log that keeps writing makes every later step bigger.
2. Find how far it spread: the log file, the log pipeline, the monitoring service, the error tracker, backups,
   and anything downstream that indexes them. A hosted error tracker is a third party who now holds the data.
3. Rotate nothing and delete nothing before you have recorded what happened, when, and how many records. You
   need that record whatever you decide next.
4. Treat a suspect, a number with the right shape and a wrong check digit, exactly like an identifier. It is
   usually a real one with a typo.
5. Decide on notification with your data protection officer. In Brazil the LGPD, art. 48, requires the
   controller to notify the ANPD and the data subjects of an incident that may bring relevant risk or damage,
   and the assessment is the controller's, not this project's.

EN: we cannot do any of this for you and we do not want the data. Do not send log excerpts to
tarja@micah6ai.com, and do not paste them into an issue.

PT: é o incidente mais comum com uma biblioteca destas, e não é relato de vulnerabilidade, é incidente seu.
Desde a 0.8 imprimir um `Match` é seguro, o `repr()` esconde o valor, então a causa costuma ser
`--show-values`, `to_dict()` no padrão, `m.value` escrito à mão, ou versão anterior à 0.8.

1. Pare a origem antes de tudo. Log que continua escrevendo aumenta todos os passos seguintes.
2. Descubra até onde foi: arquivo de log, esteira de log, serviço de monitoramento, rastreador de erro, backup
   e o que indexa isso depois. Rastreador de erro hospedado é um terceiro que agora tem o dado.
3. Não rotacione nem apague nada antes de registrar o que aconteceu, quando, e quantos registros. Você vai
   precisar desse registro de qualquer forma.
4. Trate suspeito, número c/ formato certo e DV errado, igual a identificador. Costuma ser um real c/ erro de
   digitação.
5. Decida a comunicação c/ o encarregado. No Brasil a LGPD, art. 48, manda o controlador comunicar a ANPD e os
   titulares em incidente q possa acarretar risco ou dano relevante, e a avaliação é do controlador, não deste
   projeto.

PT: não fazemos nada disso por você e não queremos o dado. Não mande trecho de log p/ tarja@micah6ai.com, e
não cole em issue.

## how / como

EN: don't open a public issue. Email tarja@micah6ai.com, use GitHub's "Report a vulnerability" (Security tab), or DM [@macmaia](https://github.com/macmaia). Send a description, steps to reproduce and the version. **No real data**, generated examples only.
PT: não abre issue pública. Manda e-mail p/ tarja@micah6ai.com, usa o "Report a vulnerability" do GitHub (aba Security) ou chama [@macmaia](https://github.com/macmaia). Manda descrição, passo a passo e versão. **Sem dado real**, só exemplo gerado.

## timelines / prazos

EN:
- acknowledgement within 3 working days
- first assessment within 10 working days
- real data exposed: removed immediately, history rewritten if needed, data subject notified where applicable (LGPD art. 48)

PT:
- confirmo recebimento em até 3 dias úteis
- 1ª avaliação em até 10 dias úteis
- dado real exposto: remove na hora, reescreve histórico se precisar e avisa o titular qdo for o caso (LGPD art. 48)
