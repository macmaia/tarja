# tarja/validators/cpf.py
# [CPF] CPF validation (Brazilian individual taxpayer ID, "Cadastro de Pessoas Fisicas")
#
# Rule (mod 11):
#   check digit 1 -> weights 10..2 over the first 9 digits
#   check digit 2 -> weights 11..2 over the first 9 digits + check digit 1
#   for each: remainder = sum % 11 -> digit = 0 if remainder < 2, else 11 - remainder
#
# Source: Receita Federal (Brazilian tax authority), CPF formation rule
# also cross-checked against python-stdnum (stdnum.br.cpf)
#
# Note: changing one base digit does NOT always invalidate a CPF (when the remainder is 10
#     the check digit becomes 0 and collides). That's a limit of the official algorithm, not a bug.

from __future__ import annotations

import re

# [CPF-REGEX] strips dots, dashes, slashes and whitespace
_STRIP = re.compile(r"[\s.\-/]")
# [CPF-REGEX] once cleaned, must be exactly 11 digits
_DIGITS11 = re.compile(r"\d{11}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida nada.
    """
    return _STRIP.sub("", value)


def _check_digit(digits: str) -> int:
    # [CPF-DV] computes one check digit. starting weight = len + 1 (10 for digit 1, 11 for digit 2)
    weight = len(digits) + 1
    # weighted sum, weight drops by 1 each position
    total = sum(int(d) * (weight - i) for i, d in enumerate(digits))
    remainder = total % 11
    # remainder 0 or 1 -> digit 0
    return 0 if remainder < 2 else 11 - remainder


def compute_check_digits(base9: str) -> str:
    """EN: Take the 9 base digits, return the 2 check digits (e.g. "25").
    PT: Recebe os 9 digitos base e devolve os 2 DVs (ex: "25").
    """
    # [CPF-DV] base must be 9 digits
    if not re.fullmatch(r"\d{9}", base9):
        raise ValueError("base9 must have exactly 9 digits / base9 precisa ter 9 digitos")
    d1 = _check_digit(base9)
    # digit 2 uses base + digit 1
    d2 = _check_digit(base9 + str(d1))
    return f"{d1}{d2}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CPF with correct check digits. Accepts 123.456.789-09 or digits only.
    PT: True se for CPF c/ DV certo. Aceita 123.456.789-09 ou so digitos.
    """
    # [CPF-VALID] wrong type (None, int...) -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # wrong length/format -> False. All-same digits (000..., 111...) pass mod 11 but are never issued -> False
    if not _DIGITS11.fullmatch(v) or len(set(v)) == 1:
        return False
    # recompute check digits and compare with the last 2
    return compute_check_digits(v[:9]) == v[9:]


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as 000.000.000-00. Raises ValueError if invalid.
    PT: Formata como 000.000.000-00. Da ValueError se for invalido.
    """
    # [CPF-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CPF / CPF invalido")
    return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
