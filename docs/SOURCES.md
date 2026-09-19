# sources / fontes

EN: official source for each entity's rule, and whether it was actually read and checked against the code.
PT: fonte oficial da regra de cada entidade, e se foi lida e conferida c/ o código de verdade.

EN: checked on 2026-09-19. Local copies of the PDFs live outside the repo, in `../Fontes oficiais/`.
PT: conferido em 19/09/2026. As cópias locais dos PDFs ficam fora do repo, em `../Fontes oficiais/`.

| entity | source / fonte | read and checked? / lida e conferida? | status |
|---|---|---|---|
| `BR_CPF` | [Receita, CPF](https://www.gov.br/receitafederal/pt-br/assuntos/meu-cpf) | no / não: EN: Receita pages don't publish the calculation, algorithm is the long-standing public one / PT: páginas da Receita não publicam o cálculo, algoritmo é o público de sempre | beta |
| `BR_CNPJ` | [Receita, FAQ CNPJ alfanumérico (PDF)](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf), [Serpro, cálculo do DV (PDF)](https://www.serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf) | yes / sim: ASCII - 48, weights 2..9 right to left, mod 11, example 12.ABC.345/01DE-35 matches / exemplo bate | beta |
| `BR_CNJ` | [CNJ, Res. 65/2008 compilada, Anexo VIII](https://atos.cnj.jus.br/atos/detalhar/119) | yes / sim: EN: annex formula DD = 98 - (N AAAA J TR OOOO 00 mod 97), check mod 97 == 1, J 1..9 / PT: fórmula do anexo idêntica ao código | beta |
| `BR_CNM` | [CNJ, Provimento 143/2023, art. 1 (PDF)](https://atos.cnj.jus.br/files/original15183420230426644940cabe4c2.pdf) | yes / sim: CCCCCC.L.NNNNNNN-DD, "Módulo 97 Base 10, ISO 7064:2003" | beta |
| `BR_CNS` | [Anvisa RNI, Validação CNS](https://rni-docs.anvisa.gov.br/docs/regras_gerais/validacoes/validacaoCNS/) (MS algorithm in annex / algoritmo do MS em anexo) | yes / sim: EN: official Java routine ported line by line, official example 898 0000 0004 3208 matches. Found and FIXED a bug: definitive cards (1/2) must be pis + 000/001 + dv / PT: rotina Java oficial portada linha a linha, exemplo oficial bate. Achei e CORRIGI um bug: cartão definitivo (1/2) tem q ser pis + 000/001 + dv | beta |
| `BR_CIB` | [Receita, Identificador do Cafir/CIB](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cafir/identificador-do-cafir), [Receita, CIB](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/sinter/cib) | yes / sim: EN: Crockford base 32; numeric: weights 8..2 mod 11; alphanumeric: weights 4,3,9,5,7,1,8 mod 31; official example A3N8Z4F-Y matches / PT: exemplo oficial bate | beta |
| `BR_RENAVAM` | [Denatran, Portaria 27/2013 (PDF)](https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/portarias/2013/portaria0272013.pdf) | yes / sim: "11 dígitos... módulo 11, peso 9" | beta |
| `BR_TITULO_ELEITOR` | [TSE, Res. 23.659/2021, art. 36](https://www.tse.jus.br/legislacao/compilada/res/2021/resolucao-no-23-659-de-26-de-outubro-de-2021) | partial / parcial: EN: layout, state table 01..28 and "Módulo 11" confirmed; weights and SP/MG rule not in the text / PT: layout, tabela de UF e "Módulo 11" confirmados; pesos e regra SP/MG não estão no texto | beta |
| `BR_PLACA` | [Contran, Res. 969/2022 (PDF)](https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-contran/resolucoes/resolucao9692022.pdf) | partial / parcial: EN: "AAA-1111" and "2nd numeric char swapped" confirmed, Annex II table is an image / PT: confirmado, tabela do Anexo II é imagem | beta |
| `BR_NIS` | EN: none found (Caixa, eSocial, Serpro searched) / PT: nenhuma achada (Caixa, eSocial, Serpro) | no / não | experimental |
| `BR_CNH` | EN: none found (Senatran, Contran, Serpro Datavalid searched) / PT: nenhuma achada (Senatran, Contran, Serpro Datavalid) | no / não | experimental |
| `BR_PIX_EVP` | [BCB, Pix](https://www.bcb.gov.br/estabilidadefinanceira/pix) | EN: UUID, RFC 4122 | beta |
| `BR_TELEFONE` | [Anatel, numeração](https://www.gov.br/anatel/pt-br/regulado/numeracao) | EN: area code list / PT: lista de DDD | beta |
| `BR_CEP` | [Correios](https://www.correios.com.br) | EN: format only / PT: só formato | beta |
| `BR_IPTU` | [CTN, art. 32](https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm) | EN: no national format / PT: sem formato nacional | experimental |
| `BR_MATRICULA_IMOVEL` | [Lei 6.015/1973, art. 176](https://www.planalto.gov.br/ccivil_03/leis/l6015compilada.htm) | EN: plain sequence, no DV / PT: sequencial, sem DV | experimental |

EN: rule: no official source found = `experimental`. Only a "yes" row can ever go `stable`.
PT: regra: sem fonte oficial = `experimental`. Só linha c/ "sim" pode virar `stable`.
