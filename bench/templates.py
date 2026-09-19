# bench/templates.py
# [BENCH-TEMPLATES] EN: Portuguese sentence templates per domain. {ENTITY} slots get filled with generated values.
#   Each slot sits next to a natural context word, the way these numbers show up in real documents.
#   Fixed text avoids digit runs that could form an identifier by accident (checked in tests).
# [BENCH-TEMPLATES] PT: modelos de frase em PT por dominio. Os slots {ENTIDADE} recebem valores gerados.
#   Cada slot fica perto de uma palavra de contexto natural, como esses numeros aparecem em doc real.
#   O texto fixo evita sequencia de digitos q forme identificador sem querer (checado nos testes).

TEMPLATES = {
    # [BENCH-TEMPLATES-HEALTH] EN: health / PT: saude
    "saude": [
        "Paciente atendida na UBS, cartão SUS {BR_CNS}, CPF {BR_CPF}.",
        "Encaminhamento: portador do CNS {BR_CNS}, contato pelo telefone {BR_TELEFONE}.",
        "Prontuário atualizado. Responsável legal inscrito no CPF {BR_CPF}, residente no CEP {BR_CEP}.",
        "Solicitação de exame para o usuário do SUS de cartão nacional de saúde {BR_CNS}.",
        "Beneficiário com NIS {BR_NIS} e cartão SUS {BR_CNS} deve retornar em trinta dias.",
        "Ficha de notificação: CPF {BR_CPF}, celular {BR_TELEFONE}, CEP {BR_CEP}.",
    ],
    # [BENCH-TEMPLATES-LEGAL] EN: legal / PT: juridico
    "juridico": [
        "Autos do processo {BR_CNJ}, em que figura como autor o titular do CPF {BR_CPF}.",
        "A empresa ré, inscrita no CNPJ {BR_CNPJ}, foi intimada no processo {BR_CNJ}.",
        "Recurso interposto nos autos {BR_CNJ} pela pessoa jurídica de CNPJ {BR_CNPJ}.",
        "O imóvel da matrícula do imóvel {BR_MATRICULA_IMOVEL} no registro de imóveis, CNM {BR_CNM}, foi penhorado.",
        "Consta da certidão o CIB {BR_CIB} e a inscrição do IPTU {BR_IPTU} do imóvel.",
        "Testemunha portadora do título de eleitor {BR_TITULO_ELEITOR} e CPF {BR_CPF}.",
    ],
    # [BENCH-TEMPLATES-ADMIN] EN: administrative / PT: administrativo
    "administrativo": [
        "Nomear o servidor inscrito no CPF {BR_CPF}, PIS/PASEP {BR_NIS}, para o cargo.",
        "Autuação do veículo placa {BR_PLACA}, renavam {BR_RENAVAM}, conduzido por titular da CNH {BR_CNH}.",
        "Contrato com a empresa CNPJ {BR_CNPJ}, sediada no CEP {BR_CEP}.",
        "Eleitor com inscrição eleitoral {BR_TITULO_ELEITOR} requer segunda via.",
        "Notificação do lançamento de IPTU da inscrição imobiliária {BR_IPTU}.",
        "Licenciamento anual: carro de placa {BR_PLACA} e código renavam {BR_RENAVAM}.",
    ],
    # [BENCH-TEMPLATES-FINANCE] EN: financial / PT: financeiro
    "financeiro": [
        "Pagamento via chave pix {BR_PIX_EVP}, favorecido CPF {BR_CPF}.",
        "Transferência recebida da empresa CNPJ {BR_CNPJ}, chave aleatória {BR_PIX_EVP}.",
        "Cadastro do cliente: CPF {BR_CPF}, whatsapp {BR_TELEFONE}.",
        "Boleto emitido para a empresa CNPJ {BR_CNPJ}, contato pelo telefone {BR_TELEFONE}.",
        "Financiamento do imóvel com CNM {BR_CNM}, cadastro imobiliário brasileiro {BR_CIB}.",
        "Estorno solicitado pelo titular do CPF {BR_CPF} referente à chave pix {BR_PIX_EVP}.",
    ],
}

# [BENCH-TEMPLATES-FILLER] EN: neutral sentences with NO identifiers, to pad documents
# [BENCH-TEMPLATES-FILLER] PT: frases neutras SEM identificador, p/ encher o documento
FILLER = [
    "Nada mais havendo a tratar, encerra-se o presente registro.",
    "O documento segue anexo para conferência.",
    "Valor total de R$ mil duzentos e trinta reais.",
    "Prazo de trinta dias a contar da ciência.",
    "Sem outras observações.",
]

# [BENCH-TEMPLATES-CONFUSABLE] EN: D5 swaps: the context word says A, the number is really B
# [BENCH-TEMPLATES-CONFUSABLE] PT: trocas D5: a palavra de contexto diz A, o numero e na verdade B
CONFUSABLE = {
    "BR_CPF": ["BR_NIS", "BR_CNH", "BR_RENAVAM"],
    "BR_NIS": ["BR_CPF"],
    "BR_CNH": ["BR_CPF"],
    "BR_RENAVAM": ["BR_CPF", "BR_NIS"],
    "BR_CNPJ": ["BR_CPF"],
    "BR_CNS": ["BR_CPF"],
}
