# tarja/validators/cib.py
# [CIB] EN: CIB validation (Cadastro Imobiliario Brasileiro, national property cadastre ID, LC 214/2025).
#   Layout: 7 chars + 1 check char, e.g. A3N8Z4F-Y. Alphabet = Crockford base 32 (no I, L, O, U).
#   Two rules, per the Receita Federal:
#   - all-numeric code (legacy NIRF): weights 8,7,6,5,4,3,2, sum % 11, DV = 11 - remainder, remainder 0 or 1 -> 0
#   - alphanumeric code: Crockford values, weights 4,3,9,5,7,1,8, sum % 31 = value of the DV character
# [CIB] PT: validacao do CIB (Cadastro Imobiliario Brasileiro, LC 214/2025).
#   Layout: 7 caracteres + 1 DV, ex: A3N8Z4F-Y. Alfabeto = base 32 de Crockford (sem I, L, O, U).
#   Duas regras, segundo a Receita:
#   - codigo so numerico (NIRF antigo): pesos 8,7,6,5,4,3,2, soma % 11, DV = 11 - resto, resto 0 ou 1 -> 0
#   - codigo alfanumerico: valores Crockford, pesos 4,3,9,5,7,1,8, soma % 31 = valor do caractere do DV
#
# EN: Source (read and checked, official example A3N8Z4F-Y reproduced in the tests):
# PT: Fonte (lida e conferida, exemplo oficial A3N8Z4F-Y reproduzido nos testes):
#   https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cafir/identificador-do-cafir

from __future__ import annotations

import re

# [CIB-ALPHABET] EN: Crockford base 32, value = position / PT: base 32 de Crockford, valor = posicao
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_VALUE = {c: i for i, c in enumerate(ALPHABET)}
# [CIB-DECODE] EN: look-alikes read as digits (Crockford rule, also in the Receita text): I/L -> 1, O -> 0
# [CIB-DECODE] PT: parecidos lidos como digito (regra Crockford, tb no texto da Receita): I/L -> 1, O -> 0
_ALIASES = str.maketrans({"I": "1", "L": "1", "O": "0"})
_STRIP = re.compile(r"[\s\-]")
_CIB = re.compile(rf"[{ALPHABET}]{{8}}")
_NUM_WEIGHTS = (8, 7, 6, 5, 4, 3, 2)
_ALNUM_WEIGHTS = (4, 3, 9, 5, 7, 1, 8)


def normalise(value: str) -> str:
    """EN: Strip dash/space, uppercase, map I/L -> 1 and O -> 0. PT: Tira traco/espaco, maiuscula, I/L -> 1, O -> 0."""
    return _STRIP.sub("", value).upper().translate(_ALIASES)


def compute_check_char(base7: str) -> str:
    """EN: 7 base chars -> check char. PT: 7 caracteres base -> caractere do DV."""
    # [CIB-DV]
    b = normalise(base7)
    if not re.fullmatch(rf"[{ALPHABET}]{{7}}", b):
        raise ValueError("base7 must be 7 Crockford base-32 chars / base7 precisa de 7 caracteres base 32")
    if b.isdigit():
        # EN: legacy NIRF rule / PT: regra antiga do NIRF
        r = sum(int(c) * w for c, w in zip(b, _NUM_WEIGHTS, strict=True)) % 11
        return "0" if r < 2 else str(11 - r)
    # EN: alphanumeric rule, remainder is the DV's value / PT: regra alfanum, o resto e o valor do DV
    r = sum(_VALUE[c] * w for c, w in zip(b, _ALNUM_WEIGHTS, strict=True)) % 31
    return ALPHABET[r]


def is_valid(value: str) -> bool:
    """EN: True if value is a CIB with the right check char. PT: True se for CIB c/ DV certo."""
    # [CIB-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _CIB.fullmatch(v) or len(set(v)) == 1:
        return False
    return compute_check_char(v[:7]) == v[7]


def format(value: str) -> str:  # noqa: A001  EN: shadows builtin on purpose / PT: nome igual ao builtin, proposital
    """EN: Format as XXXXXXX-D. PT: Formata como XXXXXXX-D."""
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CIB / CIB invalido")
    return f"{v[:7]}-{v[7]}"
