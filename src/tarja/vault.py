# tarja/vault.py
# [VAULT] reversible tokenisation, the open-source basic version. protect() swaps identifiers for tokens
#   (<BR_CPF:3f9a1c0b2e7d4a6581c90f2b>, HMAC-SHA256 with your key), reveal() puts the originals back, only for tokens THIS
#   vault issued. Typical use: mask text before sending it to an LLM, un-mask the answer.
#   Out of scope here (that's the paid Tarja Gateway): keys in KMS/HSM, per-tenant keys, session-scoped
#   rehydration tied to an authenticated identity, anti-probing quotas, append-only audit trail, persistence.
# [VAULT] memory only; the mapping dies with the object. Don't log it: it IS the personal data.
# [VAULT-TRUST] reveal() restores ANY token this vault issued, wherever it shows up. If untrusted text (e.g. an
#   LLM answer steered by a user) can echo tokens from another user's text, it gets that user's value back.
#   Use one Vault per user/session. Enforcing that across requests is the Gateway's job, not this class.

from __future__ import annotations

import hashlib
import hmac
import os
import re

from tarja.detect import Match, find

# [VAULT-TOKEN-LEN] 24 hex = 96 bits. 12 hex (48 bits) made collisions plausible at millions of values
TOKEN_HEX = 24
# [VAULT-TOKEN-RE] vault tokens (24 hex) and mask(strategy="hash") tokens (12 hex), both blanked by residual()
TOKEN_RE = re.compile(r"<(BR_[A-Z0-9_]+):([0-9a-f]{12}(?:[0-9a-f]{12})?)>")


class VaultCollisionError(ValueError):
    """EN: Two different values produced the same token. PT: Dois valores diferentes geraram o mesmo token."""


def _canonical(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


class Vault:
    """EN: key=None generates a random key (tokens change every run, on purpose).
    PT: key=None gera chave aleatoria (token muda a cada execucao, de proposito).
    """

    def __init__(self, key: bytes | str | None = None):
        # [VAULT-INIT]
        self._key = key.encode() if isinstance(key, str) else (key or os.urandom(32))
        self._map: dict[str, str] = {}
        self._canon: dict[str, str] = {}

    def token(self, entity: str, value: str) -> str:
        """EN: Deterministic token for (entity, value) under this key. PT: Token deterministico p/ (entidade, valor)."""
        # [VAULT-HMAC] canonical value, so 529.982.247-25 and 52998224725 share a token
        digest = hmac.new(self._key, f"{entity}:{_canonical(value)}".encode(), hashlib.sha256).hexdigest()
        return f"<{entity}:{digest[:TOKEN_HEX]}>"

    def protect(self, text: str, matches: list[Match] | None = None, **find_kwargs) -> str:
        """EN: Replace identifiers with tokens and remember them. Raises VaultCollisionError on a token clash.
        PT: Troca identificador por token e guarda. Levanta VaultCollisionError se dois valores colidirem.
        """
        # [VAULT-PROTECT]
        found = matches if matches is not None else find(text, **find_kwargs)
        out = text
        edge = len(text) + 1
        for m in sorted(found, key=lambda m: m.start, reverse=True):
            # [VAULT-OVERLAP] suspects are never tokenised, overlapping spans (resolve=False) are skipped
            if not m.valid_dv or m.end > edge:
                continue
            tok = self.token(m.entity, m.value)
            canon = _canonical(m.value)
            if self._canon.get(tok, canon) != canon:
                # [VAULT-COLLISION] never map one token to two people
                raise VaultCollisionError(f"token collision for {m.entity}")
            self._canon[tok] = canon
            self._map.setdefault(tok, m.value)
            out = out[: m.start] + tok + out[m.end :]
            edge = m.start
        return out

    def reveal(self, text: str) -> str:
        """EN: Put back originals for tokens this vault issued, unknown tokens stay as they are. A value seen in
        several layouts comes back in the first one seen. See [VAULT-TRUST] before feeding untrusted text.
        PT: Devolve os originais dos tokens q este cofre emitiu, token desconhecido fica como esta. Valor visto em
        varios formatos volta no primeiro. Ver [VAULT-TRUST] antes de passar texto nao confiavel.
        """
        # [VAULT-REVEAL]
        return TOKEN_RE.sub(lambda m: self._map.get(m.group(0), m.group(0)), text)

    def __len__(self) -> int:
        return len(self._map)


def residual(text: str, min_score: float = 0.0) -> list[Match]:
    """EN: Second-pass check: identifiers still present AFTER masking (should be empty). Tokens are ignored.
    PT: Checagem de 2a passada: identificadores q sobraram DEPOIS de mascarar (devia ser vazio). Tokens ignorados.
    """
    # [VAULT-RESIDUAL] blank tokens out (same length) so offsets still point at the original text
    blanked = TOKEN_RE.sub(lambda m: " " * len(m.group(0)), text)
    blanked = re.sub(r"<BR_[A-Z0-9_]+(?:_\d+)?>", lambda m: " " * len(m.group(0)), blanked)
    found = find(blanked, min_score=min_score)
    return [Match(m.entity, m.start, m.end, text[m.start : m.end], m.score, m.tier, m.pattern, m.has_context)
            for m in found]  # fmt: skip
