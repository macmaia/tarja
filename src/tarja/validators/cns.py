# tarja/validators/cns.py
# [CNS] EN: CNS validation (Cartao Nacional de Saude, Brazil's national health card / SUS card), 15 digits.
# [CNS] PT: validacao do CNS (Cartao Nacional de Saude / cartao do SUS), 15 digitos.
#
# EN: Rule: first digit must be 1, 2, 7, 8 or 9.
#   Weighted sum of all 15 digits with weights 15..1 must be divisible by 11.
#   - 1/2 = definitive cards (derived from the holder's PIS)
#   - 7/8/9 = provisional cards
#   Both families satisfy the same mod-11 check, which is what we test here.
# PT: Regra: 1o digito tem q ser 1, 2, 7, 8 ou 9.
#   Soma ponderada dos 15 digitos c/ pesos 15..1 tem q ser divisivel por 11.
#   - 1/2 = definitivo (derivado do PIS do titular)
#   - 7/8/9 = provisorio
#   As 2 familias batem na mesma regra mod 11, q e o q a gente testa aqui.
#
# EN: Source: Ministerio da Saude / DATASUS, CNS validation routine (published with the CADSUS integration docs)
# PT: Fonte: Ministerio da Saude / DATASUS, rotina de validacao do CNS (docs de integracao do CADSUS)
#   https://rni-docs.anvisa.gov.br/docs/regras_gerais/validacoes/validacaoCNS/
#   https://datasus.saude.gov.br/cartao-nacional-de-saude/ (Java validation routine / rotina Java de validacao)
#   TODO EN: compare with the DATASUS Java routine line by line / PT: comparar c/ a rotina Java do DATASUS linha a linha
# EN: status in the spec stays "experimental" until that's done / PT: status na spec fica "experimental" ate isso

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


def is_valid(value: str) -> bool:
    """EN: True if value is a CNS passing the mod-11 check. Accepts 898 0012 3456 7890 or digits only.
    PT: True se for CNS q passa no mod 11. Aceita 898 0012 3456 7890 ou so digitos.
    """
    # [CNS-VALID] EN: wrong type -> False / PT: tipo errado -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # EN: wrong format / first digit -> False / PT: formato ou 1o digito errado -> False
    if not _CNS.fullmatch(v):
        return False
    # EN: weighted sum must be a multiple of 11 / PT: soma ponderada tem q ser multiplo de 11
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
