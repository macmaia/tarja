# tarja/validators/cnh.py
# [CNH] EN: driving licence number validation (CNH registration number, "numero de registro"), 11 digits.
# [CNH] PT: validacao do numero de registro da CNH, 11 digitos.
#
# EN: Rule (widely used Denatran/Senatran routine):
#   DV1: sum(base[i] * (9..1)) % 11, >= 10 -> 0 and then discount = 2
#   DV2: sum(base[i] * (1..9)) % 11, >= 10 -> 0, otherwise minus the discount (wrapped into 0..10, 10 -> 0)
# PT: Regra (rotina Denatran/Senatran mais usada):
#   DV1: soma(base[i] * (9..1)) % 11, >= 10 -> 0 e ai desconto = 2
#   DV2: soma(base[i] * (1..9)) % 11, >= 10 -> 0, senao menos o desconto (ajustado p/ 0..10, 10 -> 0)
#
# EN: WARNING: there's no public official spec, implementations disagree on the DV2 edge case.
#     Status stays "experimental" until checked against real-format public examples.
# PT: ATENCAO: nao ha especificacao oficial publica, as implementacoes divergem no caso de borda do DV2.
#     Status fica "experimental" ate conferir c/ exemplos publicos em formato real.
#   TODO EN/PT: official Senatran source / fonte oficial Senatran

from __future__ import annotations

import re

# [CNH-REGEX] EN: strips dots, dashes, whitespace / PT: tira ponto, traco, espaco
_STRIP = re.compile(r"[\s.\-]")
_DIGITS11 = re.compile(r"\d{11}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. PT: Tira pontuacao e espaco."""
    return _STRIP.sub("", value)


def compute_check_digits(base9: str) -> str:
    """EN: 9 base digits -> 2 check digits. PT: 9 digitos base -> 2 DVs."""
    # [CNH-DV]
    if not re.fullmatch(r"\d{9}", base9):
        raise ValueError("base9 must have 9 digits / base9 precisa ter 9 digitos")
    discount = 0
    # EN: DV1, weights 9..1 / PT: DV1, pesos 9..1
    d1 = sum(int(d) * w for d, w in zip(base9, range(9, 0, -1), strict=True)) % 11
    if d1 >= 10:
        d1, discount = 0, 2
    # EN: DV2, weights 1..9 / PT: DV2, pesos 1..9
    d2 = sum(int(d) * w for d, w in zip(base9, range(1, 10), strict=True)) % 11
    d2 = 0 if d2 >= 10 else (d2 - discount) % 11
    # EN: wrap can land on 10 -> 0 / PT: o ajuste pode cair em 10 -> 0
    d2 = 0 if d2 >= 10 else d2
    return f"{d1}{d2}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CNH number with correct check digits. PT: True se for CNH c/ DV certo."""
    # [CNH-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _DIGITS11.fullmatch(v) or len(set(v)) == 1:
        return False
    return compute_check_digits(v[:9]) == v[9:]
