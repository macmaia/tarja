# tarja/validators/cnj.py
# [CNJ] EN: Brazilian court case number validation (numero unico de processo, CNJ standard), 20 digits.
# [CNJ] PT: validacao do numero unico de processo (padrao CNJ), 20 digitos.
#
# EN: Layout: NNNNNNN-DD.AAAA.J.TR.OOOO
#   N = sequence, DD = check digits, AAAA = year filed, J = justice branch, TR = court, OOOO = origin unit
#   Rule: ISO 7064 mod 97-10. DD = 98 - (int(N AAAA J TR OOOO "00") % 97).
#   Equivalent check: int(N AAAA J TR OOOO DD) % 97 == 1.
# PT: Layout: NNNNNNN-DD.AAAA.J.TR.OOOO
#   N = sequencial, DD = DV, AAAA = ano, J = segmento da justica, TR = tribunal, OOOO = origem
#   Regra: ISO 7064 mod 97-10. DD = 98 - (int(N AAAA J TR OOOO "00") % 97).
#   Checagem equivalente: int(N AAAA J TR OOOO DD) % 97 == 1.
#
# EN: Source: CNJ Resolution 65/2008, annex / PT: Fonte: Resolucao CNJ 65/2008, anexo
#   https://atos.cnj.jus.br/atos/detalhar/119

from __future__ import annotations

import re

# [CNJ-REGEX] EN: strips dots, dashes, whitespace / PT: tira ponto, traco, espaco
_STRIP = re.compile(r"[\s.\-]")
# [CNJ-REGEX] EN: 20 digits, J (position 14) can't be 0 / PT: 20 digitos, J (posicao 14) nao pode ser 0
_CNJ = re.compile(r"\d{13}[1-9]\d{6}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida.
    """
    return _STRIP.sub("", value)


def _split(v: str) -> tuple[str, str, str]:
    # [CNJ-SPLIT] EN: 20-digit string -> (sequence N, check digits DD, rest AAAA J TR OOOO)
    # [CNJ-SPLIT] PT: string de 20 digitos -> (sequencial N, DV DD, resto AAAA J TR OOOO)
    return v[:7], v[7:9], v[9:]


def compute_check_digits(sequence: str, rest: str) -> str:
    """EN: sequence = 7 digits (NNNNNNN), rest = 11 digits (AAAA J TR OOOO). Returns DD (e.g. "08").
    PT: sequence = 7 digitos (NNNNNNN), rest = 11 digitos (AAAA J TR OOOO). Devolve o DD (ex: "08").
    """
    # [CNJ-DV] EN: input check / PT: confere entrada
    if not (re.fullmatch(r"\d{7}", sequence) and re.fullmatch(r"\d{11}", rest)):
        raise ValueError("sequence needs 7 digits and rest 11 / sequence precisa de 7 digitos e rest de 11")
    # EN: ISO 7064 mod 97-10 / PT: ISO 7064 mod 97-10
    return f"{98 - int(sequence + rest + '00') % 97:02d}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CNJ case number with correct check digits. Accepts formatted or digits only.
    PT: True se for numero CNJ c/ DV certo. Aceita formatado ou so digitos.
    """
    # [CNJ-VALID] EN: wrong type -> False / PT: tipo errado -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _CNJ.fullmatch(v):
        return False
    seq, dd, rest = _split(v)
    # EN: mod 97 of the full number in N DD... order would differ, so recompute DD / PT: recalcula o DD
    return compute_check_digits(seq, rest) == dd


def format(value: str) -> str:  # noqa: A001  EN: shadows builtin on purpose / PT: nome igual ao builtin, proposital
    """EN: Format as NNNNNNN-DD.AAAA.J.TR.OOOO. Raises ValueError if invalid.
    PT: Formata como NNNNNNN-DD.AAAA.J.TR.OOOO. Da ValueError se for invalido.
    """
    # [CNJ-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CNJ case number / numero CNJ invalido")
    return f"{v[:7]}-{v[7:9]}.{v[9:13]}.{v[13]}.{v[14:16]}.{v[16:]}"
