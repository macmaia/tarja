# tarja/validators/nis.py
# [NIS] NIS / PIS / PASEP / NIT validation (Brazilian social security worker ID). All four share one number format.
#
# Rule (mod 11), 11 digits:
#   weights 3,2,9,8,7,6,5,4,3,2 over the first 10 digits
#   remainder = sum % 11 -> digit = 11 - remainder, and if that gives 10 or 11 -> 0
#
# Source: Caixa Economica Federal (PIS manager)
#   TODO: attach the official Caixa/INSS technical note link
# cross-checked against validate-docbr (PIS)

from __future__ import annotations

import re

# [NIS-REGEX] strips dots, dashes, slashes, whitespace
_STRIP = re.compile(r"[\s.\-/]")
# [NIS-REGEX] 11 digits once cleaned
_DIGITS11 = re.compile(r"\d{11}")
# [NIS-WEIGHTS] weights for the single check digit
_WEIGHTS = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida.
    """
    return _STRIP.sub("", value)


def compute_check_digit(base10: str) -> str:
    """EN: Take the 10 base digits, return the check digit (e.g. "3").
    PT: Recebe os 10 digitos base e devolve o DV (ex: "3").
    """
    # [NIS-DV] base must be 10 digits
    if not re.fullmatch(r"\d{10}", base10):
        raise ValueError("base10 must have exactly 10 digits / base10 precisa ter 10 digitos")
    total = sum(int(d) * w for d, w in zip(base10, _WEIGHTS, strict=True))
    digit = 11 - total % 11
    # 10 or 11 -> 0
    return "0" if digit >= 10 else str(digit)


def is_valid(value: str) -> bool:
    """EN: True if value is a NIS/PIS/PASEP/NIT with a correct check digit. Accepts 123.45678.90-1 or digits only.
    PT: True se for NIS/PIS/PASEP/NIT c/ DV certo. Aceita 123.45678.90-1 ou so digitos.
    """
    # [NIS-VALID] wrong type -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # wrong format or all-same digits -> False
    if not _DIGITS11.fullmatch(v) or len(set(v)) == 1:
        return False
    return compute_check_digit(v[:10]) == v[10]


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as 000.00000.00-0. Raises ValueError if invalid.
    PT: Formata como 000.00000.00-0. Da ValueError se for invalido.
    """
    # [NIS-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid NIS / NIS invalido")
    return f"{v[:3]}.{v[3:8]}.{v[8:10]}-{v[10]}"
