# tarja/validators/cartao.py
# [CARTAO] EN: payment card number check (credit/debit, incl. Brazilian brands like Elo and Hipercard).
#   13 to 19 digits, Luhn (mod 10) check digit. Not Brazil-specific, but always present in Brazilian data.
# [CARTAO] PT: checagem de numero de cartao (credito/debito, inclusive bandeiras BR como Elo e Hipercard).
#   13 a 19 digitos, DV Luhn (mod 10). Nao e so do Brasil, mas aparece sempre em dado brasileiro.
#
# EN: Source: ISO/IEC 7812-1 (issuer identification numbers and the Luhn check digit)
# PT: Fonte: ISO/IEC 7812-1 (numeros de identificacao do emissor e o DV Luhn)
#   https://www.iso.org/standard/70484.html

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s\-]")
_DIGITS = re.compile(r"\d{13,19}")


def normalise(value: str) -> str:
    """EN: Strip spaces and dashes. PT: Tira espaco e traco."""
    return _STRIP.sub("", value)


def luhn_ok(digits: str) -> bool:
    """EN: Luhn check: double every 2nd digit from the right, sum, must end in 0.
    PT: Luhn: dobra 1 digito sim 1 nao a partir da direita, soma, tem q terminar em 0.
    """
    # [CARTAO-LUHN]
    total = 0
    for i, c in enumerate(reversed(digits)):
        n = int(c)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def luhn_check_digit(base: str) -> str:
    """EN: Digit that makes base + digit pass Luhn. PT: Digito q faz base + digito passar no Luhn."""
    # [CARTAO-LUHN-DV]
    return next(d for d in "0123456789" if luhn_ok(base + d))


def is_valid(value: str) -> bool:
    """EN: True for 13-19 digits passing Luhn, not all equal. PT: True p/ 13-19 digitos q passam no Luhn."""
    # [CARTAO-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    return bool(_DIGITS.fullmatch(v)) and len(set(v)) > 1 and luhn_ok(v)
