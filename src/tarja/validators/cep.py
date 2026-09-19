# tarja/validators/cep.py
# [CEP] EN: postcode (CEP) FORMAT check, 8 digits, no check digit. Collides with lots of other numbers,
#     so the spec requires a context word ("cep") nearby.
# [CEP] PT: checagem de FORMATO do CEP, 8 digitos, sem DV. Colide c/ muito numero, entao a spec
#     exige palavra de contexto ("cep") perto.
#
# EN: Source: Correios / PT: Fonte: Correios  https://www.correios.com.br

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s.\-]")
_DIGITS8 = re.compile(r"\d{8}")


def normalise(value: str) -> str:
    """EN: Strip punctuation. PT: Tira pontuacao."""
    return _STRIP.sub("", value)


def is_valid(value: str) -> bool:
    """EN: True for 8 digits in the used range (01000-000 and up).
    PT: True p/ 8 digitos na faixa usada (01000-000 p/ cima).
    """
    # [CEP-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    return bool(_DIGITS8.fullmatch(v)) and int(v) >= 1000000
