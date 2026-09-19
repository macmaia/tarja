# tarja/validators/cnj.py
# [CNJ] Brazilian court case number validation (numero unico de processo, CNJ standard), 20 digits.
#
# Layout: NNNNNNN-DD.AAAA.J.TR.OOOO
#   N = sequence, DD = check digits, AAAA = year filed, J = justice branch, TR = court, OOOO = origin unit
#   Rule: ISO 7064 mod 97-10. DD = 98 - (int(N AAAA J TR OOOO "00") % 97).
#   Equivalent check: int(N AAAA J TR OOOO DD) % 97 == 1.
#
# Source (read and checked): CNJ Resolution 65/2008, Annex VIII, items II, III and VI, J values 1..9 in art. 1 par. 4

from __future__ import annotations

import re

# [CNJ-REGEX] strips dots, dashes, whitespace
_STRIP = re.compile(r"[\s.\-]")
# [CNJ-REGEX] 20 digits, J (position 14) can't be 0
_CNJ = re.compile(r"\d{13}[1-9]\d{6}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida.
    """
    return _STRIP.sub("", value)


def _split(v: str) -> tuple[str, str, str]:
    # [CNJ-SPLIT] 20-digit string -> (sequence N, check digits DD, rest AAAA J TR OOOO)
    return v[:7], v[7:9], v[9:]


def compute_check_digits(sequence: str, rest: str) -> str:
    """EN: sequence = 7 digits (NNNNNNN), rest = 11 digits (AAAA J TR OOOO). Returns DD (e.g. "08").
    PT: sequence = 7 digitos (NNNNNNN), rest = 11 digitos (AAAA J TR OOOO). Devolve o DD (ex: "08").
    """
    # [CNJ-DV] input check
    if not (re.fullmatch(r"\d{7}", sequence) and re.fullmatch(r"\d{11}", rest)):
        raise ValueError("sequence needs 7 digits and rest 11 / sequence precisa de 7 digitos e rest de 11")
    # ISO 7064 mod 97-10
    return f"{98 - int(sequence + rest + '00') % 97:02d}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CNJ case number with correct check digits. Accepts formatted or digits only.
    PT: True se for numero CNJ c/ DV certo. Aceita formatado ou so digitos.
    """
    # [CNJ-VALID] wrong type -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _CNJ.fullmatch(v):
        return False
    seq, dd, rest = _split(v)
    # mod 97 of the full number in N DD... order would differ, so recompute DD
    return compute_check_digits(seq, rest) == dd


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as NNNNNNN-DD.AAAA.J.TR.OOOO. Raises ValueError if invalid.
    PT: Formata como NNNNNNN-DD.AAAA.J.TR.OOOO. Da ValueError se for invalido.
    """
    # [CNJ-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNJ case number / numero CNJ invalido")
    return f"{v[:7]}-{v[7:9]}.{v[9:13]}.{v[13]}.{v[14:16]}.{v[16:]}"
