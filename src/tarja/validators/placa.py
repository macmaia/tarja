# tarja/validators/placa.py
# [PLACA] vehicle number plate FORMAT check (no check digit exists). Two layouts:
#   old Brazilian: ABC1234 (or ABC-1234)      Mercosur (since 2018): ABC1D23
#
# Source: Contran Res. 969/2022 (replaced 780/2019): old "AAA-1111" layout, 2nd digit swapped on conversion (Annex II)

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s\-]")
# [PLACA-REGEX] old and Mercosur layouts
_OLD = re.compile(r"[A-Z]{3}\d{4}")
_MERCOSUR = re.compile(r"[A-Z]{3}\d[A-Z]\d{2}")


def normalise(value: str) -> str:
    """EN: Strip dash/space, uppercase. PT: Tira traco/espaco, maiuscula."""
    return _STRIP.sub("", value).upper()


def is_valid(value: str) -> bool:
    """EN: True if value has a valid plate layout. PT: True se tiver layout de placa valido."""
    # [PLACA-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    return bool(_OLD.fullmatch(v) or _MERCOSUR.fullmatch(v))


def is_mercosur(value: str) -> bool:
    """EN: True for the Mercosur layout. PT: True p/ o layout Mercosul."""
    return isinstance(value, str) and bool(_MERCOSUR.fullmatch(normalise(value)))


def to_mercosur(value: str) -> str:
    """EN: Convert an old plate to Mercosur (5th char digit -> letter, 0->A ... 9->J). PT: Converte antiga p/ Mercosul."""
    # [PLACA-CONVERT] official conversion table
    v = normalise(value)
    if _MERCOSUR.fullmatch(v):
        return v
    if not _OLD.fullmatch(v):
        raise ValueError("invalid plate / placa invalida")
    return v[:4] + "ABCDEFGHIJ"[int(v[4])] + v[5:]
