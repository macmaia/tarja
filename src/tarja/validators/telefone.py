# tarja/validators/telefone.py
# [TELEFONE] Brazilian phone number check (no check digit). Validates the area code (DDD) and the shape:
#   mobile = 9 digits starting with 9, landline = 8 digits starting with 2-5. Country code +55 optional.
#
# Source: Anatel, national numbering plan (area codes)
#   https://www.gov.br/anatel/pt-br/regulado/numeracao

from __future__ import annotations

import re

# [TELEFONE-DDD] valid area codes
DDDS = frozenset(
    {
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "21", "22", "24", "27", "28",
        "31", "32", "33", "34", "35", "37", "38", "41", "42", "43", "44", "45", "46", "47", "48", "49",
        "51", "53", "54", "55", "61", "62", "63", "64", "65", "66", "67", "68", "69",
        "71", "73", "74", "75", "77", "79", "81", "82", "83", "84", "85", "86", "87", "88", "89",
        "91", "92", "93", "94", "95", "96", "97", "98", "99",
    }
)  # fmt: skip
_NON_DIGIT = re.compile(r"\D")


def normalise(value: str) -> str:
    """EN: Digits only, country code 55 dropped when the rest is 10-11 digits. PT: So digitos, sem o 55 do pais."""
    v = _NON_DIGIT.sub("", value)
    if v.startswith("55") and len(v) in (12, 13):
        v = v[2:]
    return v


def is_valid(value: str) -> bool:
    """EN: True for a valid DDD + mobile/landline number. PT: True p/ DDD valido + celular/fixo."""
    # [TELEFONE-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if len(v) == 11:
        return v[:2] in DDDS and v[2] == "9"
    if len(v) == 10:
        return v[:2] in DDDS and v[2] in "2345"
    return False
