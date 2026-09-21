# bench/reference.py
# [BENCH-REF] Reference check-digit validators, kept apart from src/tarja on purpose.
#   The generator asserts every value against BOTH tarja and these, so the benchmark gold does not rest on
#   tarja's own code alone. Written straight from the official rules (docs/SOURCES.md) in a deliberately
#   different style: no shared helpers and no imports from tarja. The card brand table is the one place
#   that uses regexes, precisely because the library states the same rule as numeric prefix ranges:
#   two different notations for one rule is what makes the cross-check worth anything.
#   Entities without a reference here (CNH, CNM, CIB) are flagged in the datasheet as tarja-only checks.
#   Third-party cross-check: tests/test_bench.py also compares with validate-docbr when it is installed.

from __future__ import annotations

import re
from collections.abc import Callable


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def _mod11_dv(body: str, weights: list[int]) -> int:
    rest = sum(int(d) * w for d, w in zip(body, weights, strict=True)) % 11
    return 0 if rest < 2 else 11 - rest


def cpf(value: str) -> bool:
    # [BENCH-REF-CPF] Receita Federal, weights 10..2 then 11..2
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    dv1 = _mod11_dv(d[:9], list(range(10, 1, -1)))
    dv2 = _mod11_dv(d[:9] + str(dv1), list(range(11, 1, -1)))
    return d[9:] == f"{dv1}{dv2}"


def cnpj(value: str) -> bool:
    # [BENCH-REF-CNPJ] Receita Federal, alphanumeric rule: char value = ASCII code - 48, DVs stay numeric
    s = "".join(ch for ch in value.upper() if ch.isalnum())
    if len(s) != 14 or not s[12:].isdigit() or s == s[0] * 14:
        return False
    vals = [ord(ch) - 48 for ch in s[:12]]
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    r1 = sum(v * w for v, w in zip(vals, w1, strict=True)) % 11
    dv1 = 0 if r1 < 2 else 11 - r1
    w2 = [6] + w1
    r2 = sum(v * w for v, w in zip(vals + [dv1], w2, strict=True)) % 11
    dv2 = 0 if r2 < 2 else 11 - r2
    return s[12:] == f"{dv1}{dv2}"


def cns(value: str) -> bool:
    # [BENCH-REF-CNS] Ministry of Health routine: 1/2 derived from PIS, 7/8/9 weighted sum divisible by 11
    d = _digits(value)
    if len(d) != 15 or d[0] not in "12789":
        return False
    if d[0] in "789":
        return sum(int(x) * (15 - i) for i, x in enumerate(d)) % 11 == 0
    pis = d[:11]
    total = sum(int(x) * (15 - i) for i, x in enumerate(pis))
    dv = 11 - total % 11
    if dv == 11:
        dv = 0
    if dv == 10:
        total += 2
        dv = 11 - total % 11
        return d == f"{pis}001{dv}"
    return d == f"{pis}000{dv}"


def nis(value: str) -> bool:
    # [BENCH-REF-NIS] PIS/PASEP/NIT, weights 3,2,9,8,7,6,5,4,3,2, result 10 or 11 -> 0
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    r = 11 - sum(int(x) * w for x, w in zip(d[:10], [3, 2, 9, 8, 7, 6, 5, 4, 3, 2], strict=True)) % 11
    return int(d[10]) == (0 if r >= 10 else r)


def cnj(value: str) -> bool:
    # [BENCH-REF-CNJ] Res. CNJ 65/2008 annex VIII: NNNNNNN-DD.AAAA.J.TR.OOOO, DD = 98 - (N A J TR O 00 mod 97)
    d = _digits(value)
    if len(d) != 20:
        return False
    n, dd, rest = d[:7], d[7:9], d[9:]
    return int(dd) == 98 - int(n + rest + "00") % 97


def titulo(value: str) -> bool:
    # [BENCH-REF-TITULO] TSE: 8 seq + 2 UF (01..28) + 2 DV. SP (01) and MG (02): remainder 0 gives DV 1
    d = _digits(value)
    if len(d) != 12:
        return False
    seq, uf, dv = d[:8], d[8:10], d[10:]
    if not 1 <= int(uf) <= 28:
        return False
    r1 = sum(int(x) * w for x, w in zip(seq, range(2, 10), strict=True)) % 11
    dv1 = 1 if (r1 == 0 and uf in ("01", "02")) else (0 if r1 == 10 else r1)
    r2 = (int(uf[0]) * 7 + int(uf[1]) * 8 + dv1 * 9) % 11
    dv2 = 1 if (r2 == 0 and uf in ("01", "02")) else (0 if r2 == 10 else r2)
    return dv == f"{dv1}{dv2}"


def renavam(value: str) -> bool:
    # [BENCH-REF-RENAVAM] Denatran: first 10 digits x 3,2,9,8,7,6,5,4,3,2, DV = (sum x 10) mod 11, 10 -> 0
    d = _digits(value)
    if len(d) != 11:
        return False
    total = sum(int(x) * w for x, w in zip(d[:10], [3, 2, 9, 8, 7, 6, 5, 4, 3, 2], strict=True))
    dv = total * 10 % 11
    return int(d[10]) == (0 if dv == 10 else dv)


# [BENCH-REF-IIN] written as regexes on purpose, so this stays an INDEPENDENT implementation of the same rule
#   the library expresses as numeric prefix ranges. If the two ever disagree, one of them is wrong, which is
#   the whole point of keeping this file.
_CARD_BRANDS = (
    (r"3[47]\d{13}",),  # amex, 15
    (r"3(?:0[0-5]|[689]\d)\d{11}",),  # diners, 14
    (r"30(?:95)\d{10}",),  # diners, 14
    (r"35(?:2[89]|[3-8]\d)\d{12}",),  # jcb, 16
    (r"3841\d{12}", r"3841\d{15}"),  # hipercard
    (r"4\d{12}", r"4\d{15}", r"4\d{18}"),  # visa, 13/16/19
    (r"5[1-5]\d{14}",),  # mastercard, 16
    (r"2(?:22[1-9]|2[3-9]\d|[3-6]\d\d|7[01]\d|720)\d{12}",),  # mastercard 2-series, 16
    (r"6011\d{12}", r"6011\d{15}"),  # discover
    (
        r"62(?:212[6-9]|21[3-9]\d|2[2-8]\d\d|29(?:[01]\d|2[0-5]))\d{10}",
        r"62(?:212[6-9]|21[3-9]\d|2[2-8]\d\d|29(?:[01]\d|2[0-5]))\d{13}",
    ),  # discover 622126-622925, 16/19
    (r"64[4-9]\d{13}", r"64[4-9]\d{16}", r"65\d{14}", r"65\d{17}"),  # discover, 16/19
    (r"606282\d{10}", r"606282\d{13}"),  # hipercard
    (r"627780\d{10}", r"636297\d{10}", r"636368\d{10}"),  # elo
)


def cartao(value: str) -> bool:
    # [BENCH-REF-CARTAO] ISO/IEC 7812-1: registered issuer prefix with the brand's length, plus the Luhn digit
    d = _digits(value)
    if not 13 <= len(d) <= 19 or d == d[0] * len(d):
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        x = int(ch) * (2 if i % 2 else 1)
        total += x - 9 if x > 9 else x
    if total % 10:
        return False
    return any(re.fullmatch(pat, d) for group in _CARD_BRANDS for pat in group)


REFERENCE: dict[str, Callable[[str], bool]] = {
    "BR_CPF": cpf,
    "BR_CNPJ": cnpj,
    "BR_CNS": cns,
    "BR_NIS": nis,
    "BR_CNJ": cnj,
    "BR_TITULO_ELEITOR": titulo,
    "BR_RENAVAM": renavam,
    "BR_CARTAO": cartao,
}
