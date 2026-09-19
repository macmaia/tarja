# sources / fontes

EN: official source for each entity's rule, and whether it was actually read and checked against the code.
PT: fonte oficial da regra de cada entidade, e se foi lida e conferida c/ o código de verdade.

Checked on / conferido em: 2026-09-19

| entity | source / fonte | read and checked? / lida e conferida? | status |
|---|---|---|---|
| `BR_CPF` | [Receita Federal, CPF](https://www.gov.br/receitafederal/pt-br/assuntos/meu-cpf) + python-stdnum | EN: algorithm widely documented / PT: algoritmo amplamente documentado | beta |
| `BR_CNPJ` | [Receita, CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico), [FAQ PDF](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf) | yes / sim: FAQ PDF read, ASCII-48, mod 11, example 12.ABC.345/01DE-35 matches / FAQ lido, ASCII-48, mod 11, exemplo bate | beta |
| `BR_CNJ` | [CNJ, Resolução 65/2008](https://atos.cnj.jus.br/atos/detalhar/119) | EN: ISO 7064 mod 97-10, standard / PT: ISO 7064 mod 97-10, padrão | beta |
| `BR_CNM` | [CNJ, Provimento 143/2023, art. 1](https://atos.cnj.jus.br/atos/detalhar/5057), [PDF](https://atos.cnj.jus.br/files/original15183420230426644940cabe4c2.pdf) | yes / sim: layout CCCCCC.L.NNNNNNNDD + "Módulo 97 Base 10, ISO 7064:2003" (EN: via a notary office transcription, CNJ site blocked / PT: via transcrição do 26º Tabelionato, site do CNJ bloqueado) | beta |
| `BR_RENAVAM` | [Denatran, Portaria 27/2013](https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/portarias/2013/portaria0272013.pdf) | yes / sim: "11 dígitos... módulo 11, peso 9" | beta |
| `BR_CNS` | [Anvisa RNI, validação CNS](https://rni-docs.anvisa.gov.br/docs/regras_gerais/validacoes/validacaoCNS/), [DATASUS, Cartão Nacional de Saúde](https://datasus.saude.gov.br/cartao-nacional-de-saude/) | partial / parcial: EN: blocked when fetched, open by hand / PT: bloqueado no acesso automático, abrir à mão | experimental |
| `BR_NIS` | [Caixa, PIS](https://www.caixa.gov.br/beneficios-trabalhador/pis/Paginas/default.aspx) | no / não: EN: no official algorithm doc found / PT: sem doc oficial do algoritmo | experimental |
| `BR_TITULO_ELEITOR` | [TSE, Res. 21.538/2003](https://www.tse.jus.br/legislacao/compilada/res/2003/resolucao-no-21-538-de-14-de-outubro-de-2003), [Wikipedia (not official)](https://pt.wikipedia.org/wiki/T%C3%ADtulo_de_eleitor) | no / não: EN: TSE doesn't publish the DV rule / PT: TSE não publica a regra do DV | experimental |
| `BR_CNH` | [Senatran](https://www.gov.br/transportes/pt-br/assuntos/transito/senatran) | no / não: EN: no public official spec / PT: sem especificação oficial pública | experimental |
| `BR_PLACA` | Contran, Res. 780/2019 | EN: format only / PT: só formato | beta |
| `BR_PIX_EVP` | [BCB, Pix](https://www.bcb.gov.br/estabilidadefinanceira/pix) | EN: UUID, RFC 4122 | beta |
| `BR_TELEFONE` | [Anatel, numeração](https://www.gov.br/anatel/pt-br/regulado/numeracao) | EN: area code list / PT: lista de DDD | beta |
| `BR_CEP` | [Correios](https://www.correios.com.br) | EN: format only / PT: só formato | beta |
| `BR_CIB` | [Receita, CIB](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/sinter/cib), [FAQ](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/perguntas-frequentes/cadastros/cib) | yes / sim: EN: layout ABC1234-5, DV algorithm NOT published / PT: layout ABC1234-5, algoritmo do DV NÃO publicado | experimental |
| `BR_IPTU` | [CTN, art. 32](https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm) | EN: no national format / PT: sem formato nacional | experimental |
| `BR_MATRICULA_IMOVEL` | [Lei 6.015/1973, art. 176](https://www.planalto.gov.br/ccivil_03/leis/l6015compilada.htm) | EN: plain sequence, no DV / PT: sequencial, sem DV | experimental |

EN: rule: no official source found = `experimental`. Only a "yes" row can ever go `stable`.
PT: regra: sem fonte oficial = `experimental`. Só linha c/ "sim" pode virar `stable`.
