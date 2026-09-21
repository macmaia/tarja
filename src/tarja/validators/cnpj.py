# tarja/validators/cnpj.py
# [CNPJ] CNPJ validation (Brazilian company ID), numeric AND alphanumeric
#
# Since Jul/2026 the Receita Federal issues CNPJs with letters: the first 12 positions accept
#     [0-9A-Z], the 2 check digits stay numeric. Old numeric CNPJs remain valid, and the same
#     algorithm works for both.
#
# Rule (mod 11):
#   value of each char = ord(c) - 48  -> '0'..'9' = 0..9, 'A'..'Z' = 17..42
#   check digit 1 -> weights 5,4,3,2,9,8,7,6,5,4,3,2 over the 12 positions
#   check digit 2 -> weights 6,5,4,3,2,9,8,7,6,5,4,3,2 over the 12 positions + digit 1
#   for each: remainder = sum % 11 -> digit = 0 if remainder < 2, else 11 - remainder
#
# Source
#   https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico
# official example used in the tests

from __future__ import annotations

import re

# [CNPJ-REGEX] strips dots, dashes, slashes and whitespace
_STRIP = re.compile(r"[\s.\-/]")
# [CNPJ-REGEX] full CNPJ: 12 alphanumeric + 2 digits
_FULL = re.compile(r"[0-9A-Z]{12}\d{2}")
# [CNPJ-REGEX] base only (root + branch)
_BASE = re.compile(r"[0-9A-Z]{12}")
# [CNPJ-WEIGHTS] weights for digit 1 and digit 2 (digit 2 = 6 prepended to digit 1 weights)
_W1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_W2 = (6,) + _W1


def normalise(value: str) -> str:
    """EN: Strip punctuation/whitespace and uppercase. Does not validate.
    PT: Tira pontuacao/espaco e passa p/ maiuscula. Nao valida.
    """
    return _STRIP.sub("", value).upper()


def _check_digit(chars: str, weights: tuple[int, ...]) -> int:
    # [CNPJ-DV] weighted sum using ord(c) - 48 (works for digits and letters)
    total = sum((ord(c) - 48) * w for c, w in zip(chars, weights, strict=True))
    remainder = total % 11
    # remainder 0 or 1 -> digit 0
    return 0 if remainder < 2 else 11 - remainder


def compute_check_digits(base12: str) -> str:
    """EN: Take the 12 base positions, return the 2 check digits (e.g. "35").
    PT: Recebe as 12 posicoes base e devolve os 2 DVs (ex: "35").
    """
    # [CNPJ-DV] lowercase accepted, validated as uppercase
    b = base12.upper()
    if not _BASE.fullmatch(b):
        raise ValueError("base12 must be 12 chars [0-9A-Z] / base12 precisa ter 12 caracteres [0-9A-Z]")
    d1 = _check_digit(b, _W1)
    # digit 2 uses base + digit 1
    d2 = _check_digit(b + str(d1), _W2)
    return f"{d1}{d2}"


def is_alphanumeric(value: str) -> bool:
    """EN: True if the CNPJ has at least one letter (new format).
    PT: True se o CNPJ tem pelo menos 1 letra (formato novo).
    """
    # [CNPJ-ALNUM]
    return any(c.isalpha() for c in normalise(value))


def is_valid(value: str) -> bool:
    """EN: True if value is a CNPJ (numeric or alphanumeric) with correct check digits.
    PT: True se for CNPJ (numerico ou alfanum) c/ DV certo.
    """
    # [CNPJ-VALID] wrong type -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # wrong format or all-same (00000000000000...) -> False
    if not _FULL.fullmatch(v) or len(set(v)) == 1:
        return False
    # recompute and compare with the last 2
    return compute_check_digits(v[:12]) == v[12:]


def format(value: str) -> str:  # noqa: A001  shadows builtin on purpose
    """EN: Format as XX.XXX.XXX/XXXX-XX. Raises ValueError if invalid.
    PT: Formata como XX.XXX.XXX/XXXX-XX. Da ValueError se for invalido.
    """
    # [CNPJ-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNPJ / CNPJ invalido")
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
