# tarja/validators/renavam.py
# [RENAVAM] RENAVAM validation (national vehicle registry code), 11 digits (old 9-digit codes are left-padded with 0).
#
# Rule: weights 3,2,9,8,7,6,5,4,3,2 over the first 10 digits, DV = (sum * 10) % 11, 10 -> 0.
#     Note: this gives the SAME digit as the NIS/PIS rule, so bare numbers can't be told apart by the digit.
#     That's why the spec requires a context word ("renavam") for this entity.
#
# Source: Denatran Portaria 27/2013 (11 digits, "modulo 11, peso 9")
#   https://www.gov.br/transportes/pt-br/assuntos/transito/arquivos-senatran/portarias/2013/portaria0272013.pdf

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s.\-]")
# [RENAVAM-REGEX] 9 or 11 digits
_DIGITS = re.compile(r"\d{9}|\d{11}")
_WEIGHTS = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def normalise(value: str) -> str:
    """EN: Strip punctuation/whitespace, left-pad 9-digit codes to 11. PT: Tira pontuacao, completa 9 -> 11 c/ zero."""
    v = _STRIP.sub("", value)
    return v.zfill(11) if len(v) == 9 and v.isdigit() else v


def compute_check_digit(base10: str) -> str:
    """EN: 10 base digits -> check digit. PT: 10 digitos base -> DV."""
    # [RENAVAM-DV]
    if not re.fullmatch(r"\d{10}", base10):
        raise ValueError("base10 must have 10 digits / base10 precisa ter 10 digitos")
    d = sum(int(c) * w for c, w in zip(base10, _WEIGHTS, strict=True)) * 10 % 11
    return "0" if d == 10 else str(d)


def is_valid(value: str) -> bool:
    """EN: True if value is a RENAVAM with correct check digit. PT: True se for RENAVAM c/ DV certo."""
    # [RENAVAM-VALID]
    if not isinstance(value, str):
        return False
    raw = _STRIP.sub("", value)
    if not _DIGITS.fullmatch(raw):
        return False
    v = normalise(value)
    if len(set(v)) == 1:
        return False
    return compute_check_digit(v[:10]) == v[10]
