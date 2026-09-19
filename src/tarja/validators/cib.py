# tarja/validators/cib.py
# [CIB] EN: CIB FORMAT check (Cadastro Imobiliario Brasileiro, national property cadastre ID, Lei Complementar 214/2025).
#   Layout: 7 alphanumeric chars + 1 check digit, e.g. ABC1234-5.
#   The check-digit algorithm is NOT published by the Receita Federal (checked 2026-09-19), so we only check the shape.
# [CIB] PT: checagem de FORMATO do CIB (Cadastro Imobiliario Brasileiro, LC 214/2025).
#   Layout: 7 caracteres alfanum + 1 DV, ex: ABC1234-5.
#   O algoritmo do DV NAO e publicado pela Receita (conferido em 19/09/2026), entao so checa o formato.
#
# EN: Source / PT: Fonte: Receita Federal, CIB
#   https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/sinter/cib
#   TODO EN: add the DV check once the algorithm is published / PT: add o DV qdo o algoritmo for publicado

from __future__ import annotations

import re

# [CIB-REGEX] EN: 7 alphanumeric, optional dash, 1 digit / PT: 7 alfanum, traco opcional, 1 digito
_CIB = re.compile(r"[0-9A-Z]{7}-?\d")


def normalise(value: str) -> str:
    """EN: Strip spaces, uppercase. PT: Tira espaco, maiuscula."""
    return value.replace(" ", "").upper()


def is_valid(value: str) -> bool:
    """EN: True if value has the CIB shape (at least one letter and one digit in the first 7).
    PT: True se tiver o formato do CIB (pelo menos 1 letra e 1 digito nos 7 primeiros).
    """
    # [CIB-VALID] EN: requiring both a letter and a digit avoids matching plain words or numbers
    # [CIB-VALID] PT: exigir letra e digito evita casar c/ palavra ou numero comum
    if not isinstance(value, str):
        return False
    v = normalise(value)
    if not _CIB.fullmatch(v):
        return False
    head = v[:7]
    return any(c.isalpha() for c in head) and any(c.isdigit() for c in head)
