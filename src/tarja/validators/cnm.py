# tarja/validators/cnm.py
# [CNM] CNM validation (Codigo Nacional de Matricula, national property registry number), 16 digits.
#
# Layout CCCCCC.L.NNNNNNN-DD
#   CCCCCC = registry office code (CNS da serventia), L = book 2 or 3, NNNNNNN = matricula sequence, DD = check digits
#   Rule: ISO 7064 mod 97-10 (same family as the CNJ case number). DD = 98 - (int(first 14 digits + "00") % 97).
#
# Source: CNJ Provimento 143/2023, art. 1
#   https://atos.cnj.jus.br/atos/detalhar/5057

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s.\-]")
# [CNM-REGEX] 6 office + book 2/3 + 7 sequence + 2 DV
_CNM = re.compile(r"\d{6}[23]\d{9}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. PT: Tira pontuacao e espaco."""
    return _STRIP.sub("", value)


def compute_check_digits(base14: str) -> str:
    """EN: 14 base digits (office + book + sequence) -> DD. PT: 14 digitos base (serventia + livro + ordem) -> DD."""
    # [CNM-DV] ISO 7064 mod 97-10
    if not re.fullmatch(r"\d{14}", base14):
        raise ValueError("base14 must have 14 digits / base14 precisa ter 14 digitos")
    return f"{98 - int(base14 + '00') % 97:02d}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CNM with correct check digits. PT: True se for CNM c/ DV certo."""
    # [CNM-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _CNM.fullmatch(v):
        return False
    return compute_check_digits(v[:14]) == v[14:]


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as CCCCCC.L.NNNNNNN-DD. PT: Formata como CCCCCC.L.NNNNNNN-DD."""
    # [CNM-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNM / CNM invalido")
    return f"{v[:6]}.{v[6]}.{v[7:14]}-{v[14:]}"
