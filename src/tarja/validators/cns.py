# tarja/validators/cns.py
# [CNS] EN: CNS validation (Cartao Nacional de Saude, Brazil's national health card / SUS card), 15 digits.
# [CNS] PT: validacao do CNS (Cartao Nacional de Saude / cartao do SUS), 15 digitos.
#
# EN: Rules, straight from the Ministry of Health routine (Java code attached to the Anvisa RNI doc):
#   - starts with 1 or 2 (definitive, derived from PIS): take the first 11 digits (pis), sum pis[i] * (15..5),
#     dv = 11 - sum % 11, dv 11 -> 0. If dv == 10: add 2 to the sum, recompute, and the card is pis + "001" + dv.
#     Otherwise the card is pis + "000" + dv. The whole 15-digit number must equal that.
#   - starts with 7, 8 or 9 (provisional): sum of all 15 digits * (15..1) must be divisible by 11.
# PT: Regras, direto da rotina do Ministerio da Saude (codigo Java anexo ao doc da Anvisa RNI):
#   - comeca c/ 1 ou 2 (definitivo, derivado do PIS): pega os 11 primeiros (pis), soma pis[i] * (15..5),
#     dv = 11 - soma % 11, dv 11 -> 0. Se dv == 10: soma + 2, recalcula, e o cartao e pis + "001" + dv.
#     Senao o cartao e pis + "000" + dv. O numero de 15 digitos tem q ser igual a isso.
#   - comeca c/ 7, 8 ou 9 (provisorio): soma dos 15 digitos * (15..1) tem q ser divisivel por 11.
#
# EN: Source (read and checked): Anvisa RNI, "Validacao CNS", Ministry of Health algorithm in annex
# PT: Fonte (lida e conferida): Anvisa RNI, "Validacao CNS", algoritmo do Ministerio da Saude em anexo
#   https://rni-docs.anvisa.gov.br/docs/regras_gerais/validacoes/validacaoCNS/
#   EN: official example in that doc: 898 0000 0004 3208 / PT: exemplo oficial do doc: 898 0000 0004 3208

from __future__ import annotations

import re

# [CNS-REGEX] EN: strips dots, dashes, whitespace / PT: tira ponto, traco, espaco
_STRIP = re.compile(r"[\s.\-]")
# [CNS-REGEX] EN: 15 digits, first one in 1,2,7,8,9 / PT: 15 digitos, 1o em 1,2,7,8,9
_CNS = re.compile(r"[12789]\d{14}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida.
    """
    return _STRIP.sub("", value)


def weighted_sum(digits: str) -> int:
    """EN: Sum of digit * weight, weights 15..1 (or len..1). Exposed for tests and generators.
    PT: Soma de digito * peso, pesos 15..1 (ou len..1). Exposto p/ testes e geradores.
    """
    # [CNS-SUM]
    n = len(digits)
    return sum(int(d) * (n - i) for i, d in enumerate(digits))


def definitive_from_pis(pis11: str) -> str:
    """EN: Build the definitive CNS (prefix 1/2) from its 11-digit PIS part, per the official routine.
    PT: Monta o CNS definitivo (prefixo 1/2) a partir da parte PIS de 11 digitos, pela rotina oficial.
    """
    # [CNS-DEFINITIVE]
    if not re.fullmatch(r"[12]\d{10}", pis11):
        raise ValueError("pis11 must be 11 digits starting with 1 or 2 / pis11 precisa de 11 digitos comecando c/ 1 ou 2")
    total = sum(int(d) * (15 - i) for i, d in enumerate(pis11))
    dv = 11 - total % 11
    if dv == 11:
        dv = 0
    if dv == 10:
        # EN: the "001" branch / PT: o ramo "001"
        dv = 11 - (total + 2) % 11
        return f"{pis11}001{dv}"
    return f"{pis11}000{dv}"


def is_valid(value: str) -> bool:
    """EN: True if value is a valid CNS (definitive or provisional). Accepts 898 0000 0004 3208 or digits only.
    PT: True se for CNS valido (definitivo ou provisorio). Aceita 898 0000 0004 3208 ou so digitos.
    """
    # [CNS-VALID] EN: wrong type -> False / PT: tipo errado -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # EN: wrong format / first digit -> False / PT: formato ou 1o digito errado -> False
    if not _CNS.fullmatch(v):
        return False
    if v[0] in "12":
        # EN: definitive: must be exactly what the routine builds / PT: definitivo: tem q ser exatamente o q a rotina monta
        return definitive_from_pis(v[:11]) == v
    # EN: provisional: weighted sum multiple of 11 / PT: provisorio: soma ponderada multipla de 11
    return weighted_sum(v) % 11 == 0


def format(value: str) -> str:  # noqa: A001  EN: shadows builtin on purpose / PT: nome igual ao builtin, proposital
    """EN: Format as 000 0000 0000 0000. Raises ValueError if invalid.
    PT: Formata como 000 0000 0000 0000. Da ValueError se for invalido.
    """
    # [CNS-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNS / CNS invalido")
    return f"{v[:3]} {v[3:7]} {v[7:11]} {v[11:]}"
