# tarja/vault.py
# [VAULT] EN: reversible tokenisation, the open-source basic version. protect() swaps identifiers for tokens
#   (<BR_CPF:3f9a1c0b2e7d>, HMAC-SHA256 with your key), reveal() puts the originals back, only for tokens THIS
#   vault issued. Typical use: mask text before sending it to an LLM, un-mask the answer.
#   Out of scope here (that's the paid Tarja Gateway): keys in KMS/HSM, per-tenant keys, session-scoped
#   rehydration tied to an authenticated identity, anti-probing quotas, append-only audit trail, persistence.
# [VAULT] EN: memory only; the mapping dies with the object. Don't log it: it IS the personal data.
# [VAULT] PT: tokenizacao reversivel, a versao basica aberta. protect() troca identificador por token
#   (<BR_CPF:3f9a1c0b2e7d>, HMAC-SHA256 c/ sua chave), reveal() devolve os originais, so p/ token q ESTE cofre
#   emitiu. Uso tipico: mascarar o texto antes de mandar p/ um LLM, desmascarar a resposta.
#   Fora do escopo aqui (isso e o Tarja Gateway pago): chave em KMS/HSM, chave por tenant, reidratacao por
#   sessao ligada a identidade autenticada, cota contra sondagem, trilha de auditoria imutavel, persistencia.
# [VAULT] PT: so em memoria; o mapa morre c/ o objeto. Nao logar: ele E o dado pessoal.

from __future__ import annotations

import hashlib
import hmac
import os
import re

from tarja.detect import Match, find

# [VAULT-TOKEN-RE] EN: tokens this module emits / PT: tokens q este modulo emite
TOKEN_RE = re.compile(r"<(BR_[A-Z0-9_]+):([0-9a-f]{12})>")


class Vault:
    """EN: key=None generates a random key (tokens change every run, on purpose).
    PT: key=None gera chave aleatoria (token muda a cada execucao, de proposito).
    """

    def __init__(self, key: bytes | str | None = None):
        # [VAULT-INIT]
        self._key = key.encode() if isinstance(key, str) else (key or os.urandom(32))
        self._map: dict[str, str] = {}

    def token(self, entity: str, value: str) -> str:
        """EN: Deterministic token for (entity, value) under this key. PT: Token deterministico p/ (entidade, valor)."""
        # [VAULT-HMAC] EN: canonical value, so 529.982.247-25 and 52998224725 share a token
        # [VAULT-HMAC] PT: valor canonico, entao 529.982.247-25 e 52998224725 tem o mesmo token
        canon = re.sub(r"[^0-9A-Za-z]", "", value).upper()
        return f"<{entity}:{hmac.new(self._key, f'{entity}:{canon}'.encode(), hashlib.sha256).hexdigest()[:12]}>"

    def protect(self, text: str, matches: list[Match] | None = None, **find_kwargs) -> str:
        """EN: Replace identifiers with tokens and remember them. PT: Troca identificador por token e guarda."""
        # [VAULT-PROTECT]
        found = matches if matches is not None else find(text, **find_kwargs)
        out = text
        for m in sorted(found, key=lambda m: m.start, reverse=True):
            if not m.valid_dv:
                continue
            tok = self.token(m.entity, m.value)
            self._map.setdefault(tok, m.value)
            out = out[: m.start] + tok + out[m.end :]
        return out

    def reveal(self, text: str) -> str:
        """EN: Put back originals for tokens this vault issued; unknown tokens stay as they are.
        PT: Devolve os originais dos tokens q este cofre emitiu; token desconhecido fica como esta.
        """
        # [VAULT-REVEAL]
        return TOKEN_RE.sub(lambda m: self._map.get(m.group(0), m.group(0)), text)

    def __len__(self) -> int:
        return len(self._map)


def residual(text: str, min_score: float = 0.0) -> list[Match]:
    """EN: Second-pass check: identifiers still present AFTER masking (should be empty). Tokens are ignored.
    PT: Checagem de 2a passada: identificadores q sobraram DEPOIS de mascarar (devia ser vazio). Tokens ignorados.
    """
    # [VAULT-RESIDUAL] EN: blank tokens out (same length) so offsets still point at the original text
    # [VAULT-RESIDUAL] PT: apaga os tokens (mesmo tamanho) p/ os offsets ainda apontarem p/ o texto original
    blanked = TOKEN_RE.sub(lambda m: " " * len(m.group(0)), text)
    blanked = re.sub(r"<BR_[A-Z0-9_]+(?:_\d+)?>", lambda m: " " * len(m.group(0)), blanked)
    found = find(blanked, min_score=min_score)
    return [Match(m.entity, m.start, m.end, text[m.start : m.end], m.score, m.tier, m.pattern, m.has_context)
            for m in found]  # fmt: skip
