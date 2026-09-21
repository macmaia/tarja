# Datasheet · tarja-bench v0.1

EN: structure follows Gebru et al., "Datasheets for Datasets" (CACM 64(12), 2021, doi:10.1145/3458723). Portuguese version below.
PT: estrutura segue Gebru et al., "Datasheets for Datasets" (CACM 64(12), 2021, doi:10.1145/3458723). Versão em português abaixo.

---

## EN

### 1. Motivation

- **Related benchmarks.** REDACT (Vats et al., 2026) and Brazilian-PHI (Eduardo, 2026) are concurrent 2026 preprints. Neither contains identifiers that fail a check digit, and neither varies surface format. See `bench/README.md`.
- **Purpose.** Measure how well tools find Brazilian personal identifiers (CPF, CNPJ incl. the alphanumeric CNPJ, CNS, NIS, court case numbers, voter ID, CNH, RENAVAM, plates, PIX keys, phones, CEP, property records, payment cards) in Portuguese free text. No public benchmark covered these identifiers, their check digits or the noise found in real Brazilian documents.
- **Creators.** Maria Alice Maia (https://github.com/macmaia), FGV EBAPE and Micah 6 AI.
- **Funding.** The author holds a CAPES doctoral scholarship (Coordenação de Aperfeiçoamento de Pessoal de Nível Superior, Brasil, Finance Code 001). No project-specific funding. Conflict of interest: the author runs Micah 6 AI, which may sell services built on tarja (see the paid line in the planning doc).

### 2. Composition

- **Instances.** Short Portuguese documents (one to seven sentences) with character-offset annotations `{start, end, entity}`.
- **Subsets in v0.1.**

| subset | dev | test | spans (test) | levels | source |
|---|---|---|---|---|---|
| synthetic_controlled | 1,500 | 3,500 | 13,752 | D0, D1 | templates + generator, seed 42 |
| synthetic_adversarial | 900 | 2,100 | 8,145 | D2 to D5 | templates + generator, seed 42 |
| semireal | 30% | 70% | varies | D0 | real public law text + inserted synthetic IDs, seed 7 |

- **Entities.** 17 types, listed in `spec/entities/`. Tier N1 (check digit), N2 (format), N3 (needs context).
- **Difficulty levels.** D0 canonical layout. D1 no punctuation or spaces as separators. D2 line breaks, glued tokens, table cells. D3 invalid look-alikes as distractors (not annotated). D4 OCR noise, O for 0 and l for 1 (annotated). D5 misleading context (the word says CPF, the number is a NIS).
- **Domains.** health, legal, administrative, financial (templates in `bench/templates.py`). Semi-real adds federal law text.
- **Labels.** Produced by the generator itself, so they are exact by construction. Every N1 value is checked against tarja's validator AND an independent reference implementation (`bench/reference.py`, no tarja imports) before it is written. CNH, CNM and CIB have no reference yet.
- **Circularity.** The benchmark author also wrote tarja. Templates, noise levels and context phrases may favour tarja's design. D0 scores near 1.0 are expected by construction. Mitigations: independent reference validators, optional validate-docbr cross-check, semi-real subset, hand-annotated sample (E4.4). Report all results with this caveat.
- **Personal data.** None. Every identifier is randomly generated. A generated value may coincide with a real number by chance, which is unavoidable for short numeric IDs, but nothing links it to a person. Semi-real texts are federal laws and official acts, which contain no personal data.
- **Splits.** 30% dev, 70% test, fixed by seed. The test split is for reporting only.
- **Known gaps.** No names, addresses or free-form personal data (out of scope, tier N4). Synthetic sentences are simpler than real documents. The semi-real subset only has D0 noise.

### 3. Collection process

- Synthetic subsets: `python -m bench.generate --seed 42`. Output is byte-identical across runs, and `manifest.json` stores the sha256 of each file, checked by the test suite.
- Semi-real subset: `bench/fetch_public_texts.py` downloads compiled federal laws from planalto.gov.br. `bench/semireal.py` keeps paragraphs where tarja finds nothing, then inserts 1 to 3 generated identifiers with a context phrase at sentence boundaries. Source URL and retrieval date are stored per document.
- No crowdworkers. No human subjects. No ethics review needed (no personal data, no participants).

### 4. Preprocessing and labelling

- Whitespace normalised in semi-real paragraphs. Revoked text (struck through on planalto) removed.
- Paragraphs already containing something tarja flags are dropped from the semi-real pool, so gold stays clean. This favours tarja on precision in that subset and is reported as a limitation.
- A 10% sample is double-annotated by hand to confirm generator labels, reported with span F1 and character-level Cohen's kappa (`bench/iaa.py`). [pending, E4.4]

### 5. Uses

- **Intended.** Comparing PII detectors, DLP products, NER models and LLMs on Brazilian identifiers. Regression tests for detectors.
- **Not intended.** Training a model and reporting on the same test split. Claims about real-world prevalence of personal data. Any attempt to re-identify people.
- **Dual use.** Every identifier here is generated, so the dataset itself carries no re-identification risk. The tool it evaluates does: a detector that finds identifiers in order to mask them also finds identifiers. This dataset must not be used to tune or advertise a system whose purpose is to harvest personal data from documents its operator has no lawful basis to process. Under the LGPD, data made public does not become free data (art. 7, para. 3) and art. 42 attaches liability for the damage caused. The intended-use statement in the tarja README applies to anything built with this benchmark.
- **Bias and risk.** Results on synthetic text overstate performance on messy real documents. Tools tuned on English defaults are disadvantaged by design, which is the point of the comparison but must be stated when reporting.

### 6. Distribution

- **Where.** GitHub (code) and Zenodo (frozen data, DOI). [DOI pending, E4.9]
- **Licence.** Code Apache 2.0. Data CC BY 4.0. Law texts are public domain in Brazil (Lei 9.610/1998, art. 8, IV).
- **Citation.** See `CITATION.cff` in the Zenodo package.

### 7. Maintenance

- Maintainer: tarja@micah6ai.com. Issues on GitHub.
- Versioning: semantic. Any change to templates, generators or seeds bumps the version and the manifest. Old versions stay on Zenodo.
- Errata are listed in `bench/README.md`.

---

## PT

### 1. Motivação

- **Benchmarks relacionados.** REDACT (Vats et al., 2026) e Brazilian-PHI (Eduardo, 2026), preprints de 2026. Nenhum tem identificador q falha no DV nem varia o formato de superfície. Ver o `bench/README.md`.
- **Finalidade.** Medir quão bem as ferramentas acham identificadores pessoais brasileiros (CPF, CNPJ inclusive alfanumérico, CNS, NIS, processo CNJ, título, CNH, RENAVAM, placa, chave PIX, telefone, CEP, registros de imóvel, cartão) em texto livre em português. Nenhum benchmark público cobria esses identificadores, seus DVs nem o ruído de documento brasileiro real.
- **Autoria.** Maria Alice Maia (https://github.com/macmaia), FGV EBAPE e Micah 6 AI.
- **Financiamento.** A autora é bolsista de doutorado CAPES (Coordenação de Aperfeiçoamento de Pessoal de Nível Superior, Brasil, Código de Financiamento 001). Sem financiamento específico do projeto. Conflito de interesse: a autora dirige a Micah 6 AI, q pode vender serviços baseados no tarja.

### 2. Composição

- **Instâncias.** Documentos curtos em português (1 a 7 frases) c/ anotação por offset de caractere `{start, end, entity}`.
- **Subconjuntos da v0.1.** Ver a tabela da seção EN (mesmos números).
- **Entidades.** 17 tipos, em `spec/entities/`. N1 (DV), N2 (formato), N3 (exige contexto).
- **Níveis.** D0 layout canônico. D1 sem pontuação ou espaço como separador. D2 quebra de linha, colado, célula de tabela. D3 parecido inválido como distrator (não anotado). D4 ruído de OCR, O no lugar de 0, l no lugar de 1 (anotado). D5 contexto enganoso (palavra diz CPF, número é NIS).
- **Domínios.** saúde, jurídico, administrativo, financeiro. O semi-real acrescenta texto de lei federal.
- **Rótulos.** Gerados pelo próprio gerador, exatos por construção. Todo valor N1 passa no validador do tarja E numa implementação de referência independente (`bench/reference.py`, sem importar o tarja) antes de ser gravado. CNH, CNM e CIB ainda sem referência.
- **Circularidade.** A autora do benchmark também escreveu o tarja. Templates, níveis de ruído e frases de contexto podem favorecer o desenho do tarja. Score perto de 1,0 no D0 é esperado por construção. Mitigações: validadores de referência independentes, comparação opcional c/ validate-docbr, subconjunto semi-real, amostra anotada à mão (E4.4). Todo resultado deve ser reportado c/ essa ressalva.
- **Dado pessoal.** Nenhum. Todo identificador é aleatório. Um valor gerado pode coincidir por acaso c/ um número real, o q é inevitável em ID numérico curto, mas nada o liga a uma pessoa. Os textos semi-reais são leis e atos oficiais, sem dado pessoal.
- **Partições.** 30% dev, 70% teste, fixas pela seed. Teste só p/ reportar.
- **Lacunas.** Sem nome, endereço ou dado pessoal livre (fora do escopo, N4). Frases sintéticas são mais simples q documento real. O semi-real só tem ruído D0.

### 3. Coleta

- Sintéticos: `python -m bench.generate --seed 42`. Saída idêntica byte a byte, e o `manifest.json` guarda o sha256 de cada arquivo, conferido pelos testes.
- Semi-real: `bench/fetch_public_texts.py` baixa leis federais compiladas do planalto.gov.br. `bench/semireal.py` fica só c/ parágrafos onde o tarja não acha nada e insere 1 a 3 identificadores gerados c/ frase de contexto em fronteira de frase. URL e data de coleta ficam em cada documento.
- Sem crowdworkers, sem participantes humanos, sem necessidade de comitê de ética.

### 4. Pré-processamento e rotulagem

- Espaços normalizados nos parágrafos semi-reais. Texto revogado (riscado no planalto) removido.
- Parágrafo q já tem algo q o tarja marca sai do pool semi-real, p/ manter o gold limpo. Isso favorece o tarja em precisão nesse subconjunto e vai reportado como limitação.
- Amostra de 10% c/ dupla anotação humana p/ conferir os rótulos, c/ F1 de span e kappa de Cohen por caractere (`bench/iaa.py`). [pendente, E4.4]

### 5. Usos

- **Previstos.** Comparar detectores de PII, DLPs, NER e LLMs em identificadores brasileiros. Teste de regressão.
- **Não previstos.** Treinar e reportar na mesma partição de teste. Afirmar prevalência real de dado pessoal. Qualquer tentativa de reidentificação.
- **Uso dual.** Todo identificador aqui é gerado, então o conjunto em si não tem risco de reidentificação. A ferramenta q ele avalia tem: detector q acha identificador p/ mascarar também acha identificador. Este conjunto não deve ser usado p/ ajustar ou divulgar sistema cuja finalidade seja garimpar dado pessoal em documento q o operador não tem base legal p/ tratar. Na LGPD, dado tornado público não vira dado livre (art. 7, par. 3) e o art. 42 responsabiliza por dano. A seção de uso pretendido do README do tarja vale p/ qualquer coisa construída c/ este benchmark.
- **Viés e risco.** Resultado em texto sintético superestima o desempenho em documento real bagunçado. Ferramentas c/ padrão em inglês ficam em desvantagem por desenho, o q é o objetivo da comparação mas precisa ser dito ao reportar.

### 6. Distribuição

- **Onde.** GitHub (código) e Zenodo (dados congelados, DOI). [DOI pendente, E4.9]
- **Licença.** Código Apache 2.0. Dados CC BY 4.0. Texto de lei é domínio público no Brasil (Lei 9.610/1998, art. 8, IV).
- **Citação.** Ver `CITATION.cff` no pacote do Zenodo.

### 7. Manutenção

- Contato: tarja@micah6ai.com. Issues no GitHub.
- Versão semântica. Qualquer mudança em template, gerador ou seed sobe a versão e o manifest. Versões antigas ficam no Zenodo.
- Erratas em `bench/README.md`.
