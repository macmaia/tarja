# tarja/validators/iptu.py
# [IPTU] EN: IPTU property registration number (inscricao imobiliaria), LOOSE format check.
#   Every municipality has its own format (e.g. Sao Paulo "SQL" 000.000.0000-0, Rio 0.000.000-0), and not all have
#   a check digit. So: 6 to 20 digits after stripping dots, dashes and slashes, and the spec requires the word "iptu"
#   (or similar) nearby. Tier N3, no accuracy promise.
# [IPTU] PT: inscricao imobiliaria do IPTU, checagem FROUXA de formato.
#   Cada prefeitura tem seu formato (ex: SP "SQL" 000.000.0000-0, Rio 0.000.000-0), e nem toda tem DV.
#   Entao: 6 a 20 digitos depois de tirar ponto, traco e barra, e a spec exige a palavra "iptu" (ou parecida)
#   perto. Nivel N3, sem promessa de precisao.
#
# EN: Source: none national, municipal tax codes / PT: Fonte: nao ha nacional, codigo tributario de cada municipio
#   TODO EN: add per-city validators with DV (SP, RJ, BH...) as N1 later / PT: add validador por cidade c/ DV depois

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
