# tarja/validators/iptu.py
# [IPTU] IPTU property registration number (inscricao imobiliaria), LOOSE format check.
#   Every municipality has its own format (e.g. Sao Paulo "SQL" 000.000.0000-0, Rio 0.000.000-0), and not all have
#   a check digit. So: 6 to 20 digits after stripping dots, dashes and slashes, and the spec requires the word "iptu"
#   (or similar) nearby. Tier N3, no accuracy promise.
#
# Source: none national, municipal tax codes
#   TODO: add per-city validators with DV (SP, RJ, BH...) as N1 later

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s.\-/]")
_DIGITS = re.compile(r"\d{6,20}")


def normalise(value: str) -> str:
    """EN: Strip punctuation. PT: Tira pontuacao."""
    return _STRIP.sub("", value)


def is_valid(value: str) -> bool:
    """EN: True for 6-20 digits, not all the same. PT: True p/ 6-20 digitos, nao todos iguais."""
    # [IPTU-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    return bool(_DIGITS.fullmatch(v)) and len(set(v)) > 1
