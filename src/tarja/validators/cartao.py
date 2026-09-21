# tarja/validators/cartao.py
# [CARTAO] payment card number check (credit/debit, incl. Brazilian brands like Elo and Hipercard).
#   Luhn (mod 10) alone is a one-digit check: any 13-19 digit sequence passes about 1 time in 10. Administrative
#   and financial text is full of protocol numbers, process numbers and account references that long, so Luhn on
#   its own produces roughly one false positive per ten long numeric strings. A real card also starts with a
#   registered issuer identification number and has the length that issuer uses, and requiring both cuts the
#   false positives by more than an order of magnitude at almost no cost in recall.
#
# Source: ISO/IEC 7812-1 (issuer identification numbers and the Luhn check digit)

from __future__ import annotations

import re

_STRIP = re.compile(r"[\s\-]")
_DIGITS = re.compile(r"\d{13,19}")

# [CARTAO-IIN] (low prefix, high prefix, allowed lengths, brand). A value matches when its first N digits, N
#   being the width of the prefix, fall in [low, high]. The international ranges are the published ones for
#   each network. [VERIFICAR] the Elo and Hipercard ranges against the acquirer's current table before relying
#   on them commercially: those two publish less, and the ranges move.
_IIN: tuple[tuple[str, str, frozenset[int], str], ...] = (
    ("34", "34", frozenset({15}), "amex"),
    ("37", "37", frozenset({15}), "amex"),
    ("300", "305", frozenset({14}), "diners"),
    ("3095", "3095", frozenset({14}), "diners"),
    ("36", "36", frozenset({14}), "diners"),
    ("3841", "3841", frozenset({16, 19}), "hipercard"),
    ("38", "39", frozenset({14}), "diners"),
    ("3528", "3589", frozenset({16}), "jcb"),
    ("4", "4", frozenset({13, 16, 19}), "visa"),
    ("2221", "2720", frozenset({16}), "mastercard"),
    ("51", "55", frozenset({16}), "mastercard"),
    ("6011", "6011", frozenset({16, 19}), "discover"),
    ("622126", "622925", frozenset({16, 19}), "discover"),
    ("644", "649", frozenset({16, 19}), "discover"),
    ("65", "65", frozenset({16, 19}), "discover"),
    ("606282", "606282", frozenset({16, 19}), "hipercard"),
    ("627780", "627780", frozenset({16}), "elo"),
    ("636297", "636297", frozenset({16}), "elo"),
    ("636368", "636368", frozenset({16}), "elo"),
)


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


def brand(value: str) -> str | None:
    """EN: Issuer network for a card-shaped value, or None when no registered range and length match.
    Does NOT check the Luhn digit, so use is_valid() to decide whether something is a card.
    PT: Bandeira emissora de um valor c/ cara de cartao, ou None se nenhuma faixa e comprimento batem.
    NAO confere o DV, entao use is_valid() p/ decidir se e cartao.
    """
    # [CARTAO-BRAND]
    if not isinstance(value, str):
        return None
    v = normalise(value)
    if not _DIGITS.fullmatch(v):
        return None
    for low, high, lengths, name in _IIN:
        if len(v) in lengths and low <= v[: len(low)] <= high:
            return name
    return None


def is_valid(value: str, *, require_brand: bool = True) -> bool:
    """EN: True for a value with a registered issuer prefix, the length that issuer uses, and a valid Luhn
    digit. require_brand=False falls back to Luhn alone, which is the pre-0.6 behaviour and is noisy: expect
    about one false positive per ten long numeric strings.
    PT: True p/ valor c/ prefixo de emissor registrado, comprimento daquela bandeira e DV Luhn valido.
    require_brand=False volta ao Luhn sozinho, comportamento ate a 0.5, q e barulhento.
    """
    # [CARTAO-VALID]
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _DIGITS.fullmatch(v) or len(set(v)) < 2 or not luhn_ok(v):
        return False
    return brand(v) is not None if require_brand else True
