# tarja/validators/matricula.py
# [MATRICULA] EN: traditional property registry number (matricula do imovel), LOOSE format check.
#   It's a plain sequence per registry office, no check digit: 1 to 7 digits, dots allowed (12.345).
#   The spec requires a context word ("matricula do imovel", "registro de imoveis"...). Tier N3.
#   For the national 16-digit code with check digits, see cnm.py (BR_CNM).
# [MATRICULA] PT: matricula tradicional do imovel, checagem FROUXA de formato.
#   E um sequencial de cada cartorio, sem DV: 1 a 7 digitos, c/ ponto opcional (12.345).
#   A spec exige palavra de contexto ("matricula do imovel", "registro de imoveis"...). Nivel N3.
#   P/ o codigo nacional de 16 digitos c/ DV, ver cnm.py (BR_CNM).
#
# EN: Source: Lei 6.015/1973 (Lei de Registros Publicos), art. 176 / PT: Fonte: Lei 6.015/1973, art. 176
#   https://www.planalto.gov.br/ccivil_03/leis/l6015compilada.htm

from __future__ import annotations

import re

_STRIP = re.compile(r"[.\s]")
_DIGITS = re.compile(r"\d{1,7}")


def normalise(value: str) -> str:
    """EN: Strip dots and spaces. PT: Tira ponto e espaco."""
    return _STRIP.sub("", value)


def is_valid(value: str) -> bool:
    """EN: True for 1-7 digits, not zero. PT: True p/ 1-7 digitos, diferente de zero."""
    # [MATRICULA-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    return bool(_DIGITS.fullmatch(v)) and int(v) > 0
