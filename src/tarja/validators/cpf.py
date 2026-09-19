# tarja/validators/cpf.py
# [CPF] EN: CPF validation (Brazilian individual taxpayer ID, "Cadastro de Pessoas Fisicas")
# [CPF] PT: validacao de CPF (Cadastro de Pessoas Fisicas)
#
# EN: Rule (mod 11):
#   check digit 1 -> weights 10..2 over the first 9 digits
#   check digit 2 -> weights 11..2 over the first 9 digits + check digit 1
#   for each: remainder = sum % 11 -> digit = 0 if remainder < 2, else 11 - remainder
# PT: Regra (mod 11):
#   DV1 -> pesos 10..2 nos 9 primeiros digitos
#   DV2 -> pesos 11..2 nos 9 primeiros + DV1
#   p/ cada DV: resto = soma % 11 -> DV = 0 se resto < 2, senao 11 - resto
#
# EN: Source: Receita Federal (Brazilian tax authority), CPF formation rule
# PT: Fonte: Receita Federal (regra de formacao do CPF)
#   https://www.gov.br/receitafederal/pt-br/assuntos/meu-cpf
# EN: also cross-checked against python-stdnum (stdnum.br.cpf)
# PT: conferido tb contra o python-stdnum (stdnum.br.cpf)
#
# EN: Note: changing one base digit does NOT always invalidate a CPF (when the remainder is 10
#     the check digit becomes 0 and collides). That's a limit of the official algorithm, not a bug.
# PT: Obs: trocar 1 digito da base NEM sempre invalida o CPF (qdo o resto da 10 o DV vira 0 e
#     colide). Limitacao do algoritmo oficial, nao bug nosso.

from __future__ import annotations

import re

# [CPF-REGEX] EN: strips dots, dashes, slashes and whitespace
# [CPF-REGEX] PT: tira ponto, traco, barra e espaco
_STRIP = re.compile(r"[\s.\-/]")
# [CPF-REGEX] EN: once cleaned, must be exactly 11 digits
# [CPF-REGEX] PT: depois de limpo tem q ter exatamente 11 digitos
_DIGITS11 = re.compile(r"\d{11}")


def normalise(value: str) -> str:
    """EN: Strip punctuation and whitespace. Does not validate.
    PT: Tira pontuacao e espaco. Nao valida nada.
    """
    return _STRIP.sub("", value)


def _check_digit(digits: str) -> int:
    # [CPF-DV] EN: computes one check digit. starting weight = len + 1 (10 for digit 1, 11 for digit 2)
    # [CPF-DV] PT: calcula 1 DV. peso inicial = len + 1 (10 p/ DV1, 11 p/ DV2)
    weight = len(digits) + 1
    # EN: weighted sum, weight drops by 1 each position
    # PT: soma ponderada, peso cai de 1 em 1
    total = sum(int(d) * (weight - i) for i, d in enumerate(digits))
    remainder = total % 11
    # EN: remainder 0 or 1 -> digit 0
    # PT: resto 0 ou 1 -> DV 0
    return 0 if remainder < 2 else 11 - remainder


def compute_check_digits(base9: str) -> str:
    """EN: Take the 9 base digits, return the 2 check digits (e.g. "25").
    PT: Recebe os 9 digitos base e devolve os 2 DVs (ex: "25").
    """
    # [CPF-DV] EN: base must be 9 digits / PT: base tem q ter 9 digitos
    if not re.fullmatch(r"\d{9}", base9):
        raise ValueError("base9 must have exactly 9 digits / base9 precisa ter 9 digitos")
    d1 = _check_digit(base9)
    # EN: digit 2 uses base + digit 1 / PT: DV2 usa a base + DV1
    d2 = _check_digit(base9 + str(d1))
    return f"{d1}{d2}"


def is_valid(value: str) -> bool:
    """EN: True if value is a CPF with correct check digits. Accepts 123.456.789-09 or digits only.
    PT: True se for CPF c/ DV certo. Aceita 123.456.789-09 ou so digitos.
    """
    # [CPF-VALID] EN: wrong type (None, int...) -> False / PT: tipo errado (None, int...) -> False
    if not isinstance(value, str):
        return False
    v = normalise(value)
    # EN: wrong length/format -> False. All-same digits (000..., 111...) pass mod 11 but are never issued -> False
    # PT: tamanho/formato errado -> False. Tudo igual (000..., 111...) passa no mod 11 mas nao existe -> False
    if not _DIGITS11.fullmatch(v) or len(set(v)) == 1:
        return False
    # EN: recompute check digits and compare with the last 2
    # PT: recalcula os DVs e compara c/ os 2 ultimos
    return compute_check_digits(v[:9]) == v[9:]


def format(value: str) -> str:  # noqa: A001  EN: shadows builtin on purpose / PT: nome igual ao builtin, proposital
    """EN: Format as 000.000.000-00. Raises ValueError if invalid.
    PT: Formata como 000.000.000-00. Da ValueError se for invalido.
    """
    # [CPF-FORMAT]
    v = normalise(value)
    if not is_valid(v):
        raise ValueError("invalid CPF / CPF invalido")
    return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
