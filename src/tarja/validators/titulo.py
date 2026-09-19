# tarja/validators/titulo.py
# [TITULO] voter ID validation ("titulo de eleitor"), 12 digits: 8 sequence + 2 state code + 2 check digits.
#
# Rule:
#   state code (positions 9-10) must be 01..28 (28 = voters abroad)
#   DV1 = sum(seq[i] * (2..9)) % 11, 10 -> 0
#   DV2 = (uf[0]*7 + uf[1]*8 + DV1*9) % 11, 10 -> 0
#   quirk: for SP (01) and MG (02), a remainder of 0 becomes 1, for both digits
#
# Source: TSE Res. 23.659/2021, art. 36 (read): 12 digits, 8 sequence + state code table 01..28 + 2 DVs
#     "com base no Modulo 11", DV1 over the sequence, DV2 over state code + DV1. Weights and the SP/MG rule are
#     NOT in the text, they come from the long-standing public routine (e.g. Wikipedia / Ghiorzi).

from __future__ import annotations

import re

# [TITULO-REGEX] strips dots, dashes, slashes, whitespace
_STRIP = re.compile(r"[\s.\-/]")
# [TITULO-REGEX] 12 digits once cleaned
_DIGITS12 = re.compile(r"\d{12}")

# [TITULO-UF] state codes, for reference and for format_state()
STATES = {
    "01": "SP", "02": "MG", "03": "RJ", "04": "RS", "05": "BA", "06": "PR", "07": "CE",
    "08": "PE", "09": "SC", "10": "GO", "11": "MA", "12": "PB", "13": "PA", "14": "ES",
    "15": "PI", "16": "RN", "17": "AL", "18": "MT", "19": "MS", "20": "DF", "21": "SE",
    "22": "AM", "23": "RO", "24": "AC", "25": "AP", "26": "RR", "27": "TO", "28": "ZZ",
}  # fmt: skip


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida.
    """
    return _STRIP.sub("", value)


def compute_check_digits(sequence8: str, state2: str) -> str:
    """EN: 8-digit sequence + 2-digit state code -> 2 check digits (e.g. "06").
    PT: sequencial de 8 digitos + codigo da UF de 2 -> 2 DVs (ex: "06").
    """
    # [TITULO-DV] input check
    if not re.fullmatch(r"\d{8}", sequence8) or state2 not in STATES:
        raise ValueError("need 8 digits + state code 01..28 / precisa de 8 digitos + UF 01..28")
    sp_mg = state2 in ("01", "02")
    # DV1, weights 2..9
    r1 = sum(int(d) * w for d, w in zip(sequence8, range(2, 10), strict=True)) % 11
    d1 = 0 if r1 == 10 else r1
    if sp_mg and r1 == 0:
        d1 = 1
    # DV2, state digits (weights 7, 8) + DV1 (weight 9)
    r2 = (int(state2[0]) * 7 + int(state2[1]) * 8 + d1 * 9) % 11
    d2 = 0 if r2 == 10 else r2
    if sp_mg and r2 == 0:
        d2 = 1
    return f"{d1}{d2}"


def is_valid(value: str) -> bool:
    """EN: True if value is a voter ID with valid state code and check digits. Accepts 0043 5687 0906 or digits.
    PT: True se for titulo c/ UF e DVs validos. Aceita 0043 5687 0906 ou so digitos.
    """
    # [TITULO-VALID] wrong type / format -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _DIGITS12.fullmatch(v) or len(set(v)) == 1 or v[8:10] not in STATES:
        return False
    return compute_check_digits(v[:8], v[8:10]) == v[10:]


def state(value: str) -> str | None:
    """EN: State (UF) the voter ID was issued in, or None if invalid. PT: UF do titulo, ou None se invalido."""
    # [TITULO-STATE]
    v = normalise(value) if isinstance(value, str) else ""
    return STATES[v[8:10]] if is_valid(v) else None
