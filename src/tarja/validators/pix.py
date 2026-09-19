# tarja/validators/pix.py
# [PIX] PIX random key ("chave aleatoria", EVP) FORMAT check. It's a UUID (RFC 4122), no check digit.
#     PIX keys can also be a CPF, CNPJ, phone or e-mail, those are caught by their own entities.
#
# Source: Banco Central do Brasil, PIX regulation (DICT manual)
#   https://www.bcb.gov.br/estabilidadefinanceira/pix

from __future__ import annotations

import re

# [PIX-REGEX] 8-4-4-4-12 hex, version nibble 1-5, variant 8/9/a/b
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def is_valid(value: str) -> bool:
    """EN: True if value looks like a PIX random key (UUID). PT: True se parecer chave PIX aleatoria (UUID)."""
    # [PIX-VALID]
    return isinstance(value, str) and bool(_UUID.fullmatch(value.strip().lower()))
