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

EN: `Vault.reveal()` restoring tokens that appear in untrusted text is documented behaviour (see `[VAULT-TRUST]` in `vault.py`), use one vault per user or session.
PT: o `Vault.reveal()` devolver token q aparece em texto não confiável é comportamento documentado (ver `[VAULT-TRUST]` no `vault.py`), use um cofre por usuário ou sessão.

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
