# tarja/validators/titulo.py
# [TITULO] EN: voter ID validation ("titulo de eleitor"), 12 digits: 8 sequence + 2 state code + 2 check digits.
# [TITULO] PT: validacao do titulo de eleitor, 12 digitos: 8 sequencial + 2 codigo da UF + 2 DVs.
#
# EN: Rule:
#   state code (positions 9-10) must be 01..28 (28 = voters abroad)
#   DV1 = sum(seq[i] * (2..9)) % 11, 10 -> 0
#   DV2 = (uf[0]*7 + uf[1]*8 + DV1*9) % 11, 10 -> 0
#   quirk: for SP (01) and MG (02), a remainder of 0 becomes 1, for both digits
# PT: Regra:
#   codigo da UF (posicoes 9-10) tem q ser 01..28 (28 = exterior)
#   DV1 = soma(seq[i] * (2..9)) % 11, 10 -> 0
#   DV2 = (uf[0]*7 + uf[1]*8 + DV1*9) % 11, 10 -> 0
#   pegadinha: p/ SP (01) e MG (02), resto 0 vira 1, nos 2 DVs
#
# EN: Source: TSE (Brazilian electoral court), Res. 21.538/2003 / PT: Fonte: TSE, Res. 21.538/2003
#   TODO EN: attach official TSE doc for the check-digit rule / PT: anexar doc oficial do TSE da regra do DV
#   https://www.tse.jus.br/legislacao/compilada/res/2003/resolucao-no-21-538-de-14-de-outubro-de-2003

from __future__ import annotations

import re

# [TITULO-REGEX] EN: strips dots, dashes, slashes, whitespace / PT: tira ponto, traco, barra, espaco
_STRIP = re.compile(r"[\s.\-/]")
# [TITULO-REGEX] EN: 12 digits once cleaned / PT: 12 digitos depois de limpo
_DIGITS12 = re.compile(r"\d{12}")

# [TITULO-UF] EN: state codes, for reference and for format_state() / PT: codigos de UF, p/ consulta e p/ state()
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
    # [TITULO-DV] EN: input check / PT: confere entrada
    if not re.fullmatch(r"\d{8}", sequence8) or state2 not in STATES:
        raise ValueError("need 8 digits + state code 01..28 / precisa de 8 digitos + UF 01..28")
    sp_mg = state2 in ("01", "02")
    # EN: DV1, weights 2..9 / PT: DV1, pesos 2..9
    r1 = sum(int(d) * w for d, w in zip(sequence8, range(2, 10), strict=True)) % 11
    d1 = 0 if r1 == 10 else r1
    if sp_mg and r1 == 0:
        d1 = 1
    # EN: DV2, state digits (weights 7, 8) + DV1 (weight 9) / PT: DV2, digitos da UF (pesos 7, 8) + DV1 (peso 9)
    r2 = (int(state2[0]) * 7 + int(state2[1]) * 8 + d1 * 9) % 11
    d2 = 0 if r2 == 10 else r2
    if sp_mg and r2 == 0:
        d2 = 1
    return f"{d1}{d2}"


def is_valid(value: str) -> bool:
    """EN: True if value is a voter ID with valid state code and check digits. Accepts 0043 5687 0906 or digits.
    PT: True se for titulo c/ UF e DVs validos. Aceita 0043 5687 0906 ou so digitos.
    """
    # [TITULO-VALID] EN: wrong type / format -> False / PT: tipo / formato errado -> False
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
