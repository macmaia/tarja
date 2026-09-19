# bench/ids.py
# [BENCH-IDS] EN: random VALID identifiers per entity, plus renderers (formatted / compact / spaced) and
#   invalid look-alikes for distractors. Every valid value is double-checked with tarja's validator, which
#   was itself checked against the official sources (docs/SOURCES.md).
# [BENCH-IDS] PT: identificadores VALIDOS aleatorios por entidade, mais renderizadores (formatado / compacto /
#   c/ espaco) e parecidos invalidos p/ distratores. Todo valor valido e conferido c/ o validador do tarja, q
#   foi conferido c/ as fontes oficiais (docs/SOURCES.md).

from __future__ import annotations

import random
import re
import string
import uuid

from tarja.entities import ENTITIES
from tarja.validators import cartao, cib, cnh, cnj, cnm, cnpj, cns, cpf, nis, renavam, telefone, titulo

DIG = string.digits
ALNUM = string.digits + string.ascii_uppercase


def _d(rng: random.Random, n: int) -> str:
    # [BENCH-IDS-DIGITS] EN: n random digits, never all equal / PT: n digitos aleatorios, nunca todos iguais
    while True:
        s = "".join(rng.choice(DIG) for _ in range(n))
        if len(set(s)) > 1:
            return s


# [BENCH-IDS-GEN] EN: one generator per entity, returns the CANONICAL value (digits/chars only)
# [BENCH-IDS-GEN] PT: 1 gerador por entidade, devolve o valor CANONICO (so digitos/caracteres)
def _cpf(rng):
    b = _d(rng, 9)
    return b + cpf.compute_check_digits(b)


def _cnpj(rng):
    # EN: half alphanumeric (Jul/2026 format), half numeric / PT: metade alfanum (formato jul/2026), metade numerico
    b = "".join(rng.choice(ALNUM) for _ in range(12)) if rng.random() < 0.5 else _d(rng, 8) + "0001"
    return b + cnpj.compute_check_digits(b)


def _cns(rng):
    # EN: half definitive (1/2, official routine), half provisional (7/8/9) / PT: metade definitivo, metade provisorio
    if rng.random() < 0.5:
        return cns.definitive_from_pis(rng.choice("12") + _d(rng, 10))
    while True:
        base = rng.choice("789") + _d(rng, 13)
        ok = [c for c in DIG if cns.weighted_sum(base + c) % 11 == 0]
        if ok:
            return base + ok[0]


def _nis(rng):
    b = "1" + _d(rng, 9)
    return b + nis.compute_check_digit(b)


def _cnj(rng):
    seq = _d(rng, 7)
    rest = f"{rng.randint(1995, 2026)}{rng.choice('123456789')}{rng.randint(1, 27):02d}{rng.randint(1, 9999):04d}"
    return seq + cnj.compute_check_digits(seq, rest) + rest


def _cnm(rng):
    b = _d(rng, 6) + rng.choice("23") + _d(rng, 7)
    return b + cnm.compute_check_digits(b)


def _cib(rng):
    while True:
        b = "".join(rng.choice(cib.ALPHABET) for _ in range(7))
        if any(c.isalpha() for c in b) and any(c.isdigit() for c in b):
            return b + cib.compute_check_char(b)


def _titulo(rng):
    seq = _d(rng, 8)
    uf = rng.choice(sorted(titulo.STATES))
    return seq + uf + titulo.compute_check_digits(seq, uf)


def _cnh(rng):
    b = _d(rng, 9)
    return b + cnh.compute_check_digits(b)


def _renavam(rng):
    b = "0" + _d(rng, 9)
    return b + renavam.compute_check_digit(b)


def _placa(rng):
    letters = "".join(rng.choice(string.ascii_uppercase) for _ in range(3))
    if rng.random() < 0.5:
        return letters + _d(rng, 4)
    return letters + rng.choice(DIG) + rng.choice(string.ascii_uppercase) + _d(rng, 2)


def _pix(rng):
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def _telefone(rng):
    ddd = rng.choice(sorted(telefone.DDDS))
    return ddd + ("9" + _d(rng, 8) if rng.random() < 0.7 else rng.choice("2345") + _d(rng, 7))


def _cep(rng):
    return f"{rng.randint(1000000, 99999999):08d}"


def _iptu(rng):
    return _d(rng, 11)


def _matricula(rng):
    return str(rng.randint(100, 999999))


def _cartao(rng):
    # [BENCH-IDS-CARTAO] EN: Visa-like test PAN, "4" + 14 digits + Luhn / PT: PAN de teste tipo Visa, "4" + 14 digitos + Luhn
    body = "4" + _d(rng, 14)
    return body + cartao.luhn_check_digit(body)


GENERATORS = {
    "BR_CPF": _cpf, "BR_CNPJ": _cnpj, "BR_CNS": _cns, "BR_NIS": _nis, "BR_CNJ": _cnj, "BR_CNM": _cnm,
    "BR_CIB": _cib, "BR_TITULO_ELEITOR": _titulo, "BR_CNH": _cnh, "BR_RENAVAM": _renavam, "BR_PLACA": _placa,
    "BR_PIX_EVP": _pix, "BR_TELEFONE": _telefone, "BR_CEP": _cep, "BR_IPTU": _iptu,
    "BR_MATRICULA_IMOVEL": _matricula, "BR_CARTAO": _cartao,
}  # fmt: skip


def generate(entity: str, rng: random.Random) -> str:
    """EN: Canonical valid value, asserted against tarja's validator. PT: Valor canonico valido, conferido c/ o tarja."""
    # [BENCH-IDS-GENERATE]
    v = GENERATORS[entity](rng)
    spec = ENTITIES[entity]
    if spec.validator is not None:
        assert spec.validator(render(entity, v, "formatted")), (entity, v)
    return v


def render(entity: str, v: str, style: str) -> str:
    """EN: style = formatted (canonical layout), compact (no punctuation), spaced (separators -> spaces).
    PT: style = formatted (layout canonico), compact (sem pontuacao), spaced (separadores -> espaco).
    """
    # [BENCH-IDS-RENDER]
    f = {
        "BR_CPF": lambda: f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}",
        "BR_CNPJ": lambda: f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}",
        "BR_CNS": lambda: f"{v[:3]} {v[3:7]} {v[7:11]} {v[11:]}",
        "BR_NIS": lambda: f"{v[:3]}.{v[3:8]}.{v[8:10]}-{v[10]}",
        "BR_CNJ": lambda: f"{v[:7]}-{v[7:9]}.{v[9:13]}.{v[13]}.{v[14:16]}.{v[16:]}",
        "BR_CNM": lambda: f"{v[:6]}.{v[6]}.{v[7:14]}-{v[14:]}",
        "BR_CIB": lambda: f"{v[:7]}-{v[7]}",
        "BR_TITULO_ELEITOR": lambda: f"{v[:4]} {v[4:8]} {v[8:]}",
        "BR_CNH": lambda: v,
        "BR_RENAVAM": lambda: v,
        "BR_PLACA": lambda: f"{v[:3]}-{v[3:]}" if v[4].isdigit() else v,
        "BR_PIX_EVP": lambda: v,
        "BR_TELEFONE": lambda: f"({v[:2]}) {v[2:-4]}-{v[-4:]}",
        "BR_CEP": lambda: f"{v[:5]}-{v[5:]}",
        "BR_IPTU": lambda: f"{v[:3]}.{v[3:6]}.{v[6:10]}-{v[10]}",
        "BR_MATRICULA_IMOVEL": lambda: f"{int(v):,}".replace(",", "."),
        "BR_CARTAO": lambda: f"{v[:4]} {v[4:8]} {v[8:12]} {v[12:]}",
    }[entity]()
    if style == "formatted":
        return f
    if style == "compact":
        # EN: PIX keys and plates keep their dashes / PT: chave PIX e placa mantem o traco
        if entity in ("BR_PIX_EVP", "BR_PLACA"):
            return f
        return re.sub(r"[\s.\-/()]", "", f)
    if style == "spaced":
        return re.sub(r"[.\-/]", " ", f) if entity not in ("BR_PIX_EVP",) else f
    raise ValueError(style)


# [BENCH-IDS-DV] EN: entities with a REAL check digit. Loose format checks (IPTU, matricula, CEP, phone, plate,
#   PIX) accept almost any number, so they don't count when deciding if a look-alike is "valid for something".
# [BENCH-IDS-DV] PT: entidades c/ DV DE VERDADE. Checagens frouxas de formato (IPTU, matricula, CEP, telefone,
#   placa, PIX) aceitam quase qq numero, entao nao contam p/ decidir se um parecido e "valido p/ algo".
DV_ENTITIES = (
    "BR_CPF", "BR_CNPJ", "BR_CNS", "BR_NIS", "BR_CNJ", "BR_CNM", "BR_CIB", "BR_TITULO_ELEITOR", "BR_CNH",
    "BR_RENAVAM", "BR_CARTAO",
)  # fmt: skip


def invalid_lookalike(entity: str, rng: random.Random) -> str | None:
    """EN: Same layout as a valid value but WRONG check digit (D3 distractor, not annotated). None if no DV.
    PT: Mesmo layout de um valor valido mas DV ERRADO (distrator D3, nao anotado). None se nao tem DV.
    """
    # [BENCH-IDS-INVALID]
    spec = ENTITIES[entity]
    if spec.validator is None or entity not in DV_ENTITIES:
        return None
    for _ in range(50):
        v = generate(entity, rng)
        last = v[-1]
        pool = cib.ALPHABET if entity == "BR_CIB" else DIG
        bad = v[:-1] + rng.choice([c for c in pool if c != last])
        s = render(entity, bad, "formatted")
        # EN: must be invalid for EVERY check-digit entity, or a detector would be right to flag it
        # PT: tem q ser invalido p/ TODA entidade c/ DV, senao o detector acertaria ao marcar
        if not any(ENTITIES[e].validator(s) for e in DV_ENTITIES):
            return s
    return None
