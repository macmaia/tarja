# tarja/validators/cib.py
# [CIB] CIB validation (Cadastro Imobiliario Brasileiro, national property cadastre ID, LC 214/2025).
#   Layout: 7 chars + 1 check char, e.g. A3N8Z4F-Y. Alphabet = Crockford base 32 (no I, L, O, U).
#   Two rules, per the Receita Federal:
#   - all-numeric code (legacy NIRF): weights 8,7,6,5,4,3,2, sum % 11, DV = 11 - remainder, remainder 0 or 1 -> 0
#   - alphanumeric code: Crockford values, weights 4,3,9,5,7,1,8, sum % 31 = value of the DV character
#
# Source (read and checked, official example A3N8Z4F-Y reproduced in the tests):

from __future__ import annotations

import re

# [CIB-ALPHABET] Crockford base 32, value = position
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_VALUE = {c: i for i, c in enumerate(ALPHABET)}
# [CIB-DECODE] look-alikes read as digits (Crockford rule, also in the Receita text): I/L -> 1, O -> 0
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
        # legacy NIRF rule
        r = sum(int(c) * w for c, w in zip(b, _NUM_WEIGHTS, strict=True)) % 11
        return "0" if r < 2 else str(11 - r)
    # alphanumeric rule, remainder is the DV's value
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


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as XXXXXXX-D. PT: Formata como XXXXXXX-D."""
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CIB / CIB invalido")
    return f"{v[:7]}-{v[7]}"
