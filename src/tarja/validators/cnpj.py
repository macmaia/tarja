# tarja/validators/cnpj.py
# [CNPJ] EN: CNPJ validation (Brazilian company ID), numeric AND alphanumeric
# [CNPJ] PT: validacao de CNPJ numerico E alfanumerico
#
# EN: Since Jul/2026 the Receita Federal issues CNPJs with letters: the first 12 positions accept
#     [0-9A-Z], the 2 check digits stay numeric. Old numeric CNPJs remain valid, and the same
#     algorithm works for both.
# PT: Desde jul/2026 a Receita emite CNPJ c/ letras: as 12 primeiras posicoes aceitam [0-9A-Z],
#     os 2 DVs continuam numericos. Os antigos (so numeros) seguem validos, e o mesmo algoritmo
#     serve p/ os dois.
#
# EN: Rule (mod 11):
#   value of each char = ord(c) - 48  -> '0'..'9' = 0..9, 'A'..'Z' = 17..42
#   check digit 1 -> weights 5,4,3,2,9,8,7,6,5,4,3,2 over the 12 positions
#   check digit 2 -> weights 6,5,4,3,2,9,8,7,6,5,4,3,2 over the 12 positions + digit 1
#   for each: remainder = sum % 11 -> digit = 0 if remainder < 2, else 11 - remainder
# PT: Regra (mod 11):
#   valor de cada caractere = ord(c) - 48  -> '0'..'9' = 0..9, 'A'..'Z' = 17..42
#   DV1 -> pesos 5,4,3,2,9,8,7,6,5,4,3,2 nas 12 posicoes
#   DV2 -> pesos 6,5,4,3,2,9,8,7,6,5,4,3,2 nas 12 posicoes + DV1
#   p/ cada DV: resto = soma % 11 -> DV = 0 se resto < 2, senao 11 - resto
#
# EN: Source / PT: Fonte: Receita Federal, CNPJ Alfanumerico (IN RFB 2.229/2024)
#   https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico
# EN: official example used in the tests / PT: exemplo oficial usado nos testes: 12.ABC.345/01DE-35

from __future__ import annotations

import re

# [CNPJ-REGEX] EN: strips dots, dashes, slashes and whitespace / PT: tira ponto, traco, barra e espaco
_STRIP = re.compile(r"[\s.\-/]")
# [CNPJ-REGEX] EN: full CNPJ: 12 alphanumeric + 2 digits / PT: CNPJ completo: 12 alfanum + 2 digitos
_FULL = re.compile(r"[0-9A-Z]{12}\d{2}")
# [CNPJ-REGEX] EN: base only (root + branch) / PT: so a base (raiz + ordem)
_BASE = re.compile(r"[0-9A-Z]{12}")
# [CNPJ-WEIGHTS] EN: weights for digit 1 and digit 2 (digit 2 = 6 prepended to digit 1 weights)
# [CNPJ-WEIGHTS] PT: pesos do DV1 e do DV2 (DV2 = 6 na frente + pesos do DV1)
_W1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_W2 = (6,) + _W1


def normalise(value: str) -> str:
    """EN: Strip punctuation/whitespace and uppercase. Does not validate.
    PT: Tira pontuacao/espaco e passa p/ maiuscula. Nao valida.
    """
    return _STRIP.sub("", value).upper()


def _check_digit(chars: str, weights: tuple[int, ...]) -> int:
    # [CNPJ-DV] EN: weighted sum using ord(c) - 48 (works for digits and letters)
    # [CNPJ-DV] PT: soma ponderada usando ord(c) - 48 (funciona p/ digito e letra)
    total = sum((ord(c) - 48) * w for c, w in zip(chars, weights, strict=True))
    remainder = total % 11
    # EN: remainder 0 or 1 -> digit 0 / PT: resto 0 ou 1 -> DV 0
    return 0 if remainder < 2 else 11 - remainder


def compute_check_digits(base12: str) -> str:
    """EN: Take the 12 base positions, return the 2 check digits (e.g. "35").
    PT: Recebe as 12 posicoes base e devolve os 2 DVs (ex: "35").
    """
    # [CNPJ-DV] EN: lowercase accepted, validated as uppercase / PT: aceita minuscula, valida em maiuscula
    b = base12.upper()
    if not _BASE.fullmatch(b):
        raise ValueError("base12 must be 12 chars [0-9A-Z] / base12 precisa ter 12 caracteres [0-9A-Z]")
    d1 = _check_digit(b, _W1)
    # EN: digit 2 uses base + digit 1 / PT: DV2 usa a base + DV1
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
    # [CNPJ-VALID] EN: wrong type -> False / PT: tipo errado -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # EN: wrong format or all-same (00000000000000...) -> False
    # PT: formato errado ou tudo igual (00000000000000...) -> False
    if not _FULL.fullmatch(v) or len(set(v)) == 1:
        return False
    # EN: recompute and compare with the last 2 / PT: recalcula e compara c/ os 2 ultimos
    return compute_check_digits(v[:12]) == v[12:]


def format(value: str) -> str:  # noqa: A001  EN: shadows builtin on purpose / PT: nome igual ao builtin, proposital
    """EN: Format as XX.XXX.XXX/XXXX-XX. Raises ValueError if invalid.
    PT: Formata como XX.XXX.XXX/XXXX-XX. Da ValueError se for invalido.
    """
    # [CNPJ-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNPJ / CNPJ invalido")
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
