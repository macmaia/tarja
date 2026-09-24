# tarja/vault.py
# [VAULT] reversible tokenisation, the open-source basic version. protect() swaps identifiers for tokens
#   (<BR_CPF:3f9a1c0b2e7d4a6581c90f2b>, HMAC-SHA256 with your key), reveal() puts them back. Typical use: mask
#   text before sending it to an LLM, un-mask the answer.
#   Out of scope here (that's the paid Tarja Gateway): keys in KMS/HSM, per-tenant keys, rehydration tied to an
#   authenticated identity, anti-probing quotas, append-only audit trail, persistence.
# [VAULT] memory only; the mapping dies with the object. Don't log it: it IS the personal data.
# [VAULT-TRUST] reveal() is scoped to the protect() call that issued the tokens, so a token echoed from someone
#   else's text does not resolve, even when one vault serves several users. The scope is single use and expires.
#   any_token=True turns all of that off and restores anything this vault ever issued: only for trusted text.
#   Whoever holds the Vault object can still reveal everything, same as holding a decryption key. Binding a vault
#   to an authenticated session, quotas and audit are the Gateway's job.

from __future__ import annotations

import hashlib
import hmac
import os
import re
import time

from tarja.detect import Match, find

# [VAULT-TOKEN-LEN] 24 hex = 96 bits. 12 hex (48 bits) made collisions plausible at millions of values
TOKEN_HEX = 24
# [VAULT-KEY-ID] 16 bits of key generation, derived from the key itself. It exists because a stable token is
#   only stable under one key: rotate the key and the same value yields a different token, so a token stored
#   yesterday stops joining with one computed today, silently. The id makes that visible instead of silent, and
#   lets two generations coexist during a migration. It is HMAC of a fixed label under the key, so it changes
#   when the key changes, needs no bookkeeping from the caller, and reveals nothing about the key.
#   It is NOT a secret and NOT an integrity check: it says which generation, not that the token is authentic.
KEY_ID_HEX = 4
KEY_ID_LABEL = b"tarja-key-id-v1"
# [VAULT-TOKEN-RE] matches vault tokens (24 hex) and mask(strategy="pseudonym_stable") tokens (12 hex), with or
#   without the key id, so residual() still blanks tokens written before 0.7. Both are blanked by residual().
TOKEN_RE = re.compile(r"<([A-Z][A-Z0-9_]+):(?:([0-9a-f]{" + str(KEY_ID_HEX) + r"}):)?([0-9a-f]{12}(?:[0-9a-f]{12})?)>")


def key_id(key: bytes) -> str:
    """EN: Short generation marker for a key. Same key, same id. PT: Marcador curto de geracao da chave."""
    # [VAULT-KEY-ID-DERIVE]
    return hmac.new(key, KEY_ID_LABEL, hashlib.sha256).hexdigest()[:KEY_ID_HEX]


# [VAULT-TTL] one hour covers an LLM round trip and a normal batch job, and kills replay much later
DEFAULT_TTL = 3600.0


class VaultError(ValueError):
    """EN: Base class for vault errors. PT: Classe base dos erros do cofre."""


class VaultCollisionError(VaultError):
    """EN: Two different values produced the same token. PT: Dois valores diferentes geraram o mesmo token."""


class VaultScopeError(VaultError):
    """EN: reveal() called without saying which protect() issued the tokens.
    PT: reveal() chamado sem dizer qual protect() emitiu os tokens.
    """


class VaultExpiredError(VaultError):
    """EN: The scope is past its time to live. PT: O escopo passou do tempo de vida."""


class VaultConsumedError(VaultError):
    """EN: The scope was already revealed once. PT: O escopo já foi revelado uma vez."""


def _canonical(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value).upper()


class _Scope:
    # [VAULT-SCOPE] the tokens one protect() call issued, plus its expiry and single-use flag
    __slots__ = ("tokens", "expires_at", "used")

    def __init__(self, tokens: set[str], ttl: float | None):
        self.tokens = tokens
        self.expires_at = None if ttl is None else time.monotonic() + ttl
        self.used = False


class ProtectedText(str):
    """EN: The text protect() returns. It is a normal str, so it goes to an LLM or a file unchanged, and it also
    carries the scope that reveal() needs.
    PT: O texto q o protect() devolve. É uma str normal, então vai p/ o LLM ou p/ um arquivo igual, e ainda
    carrega o escopo q o reveal() precisa.
    """

    # [VAULT-PROTECTED-TEXT] str is a variable-length type, so no __slots__ here
    _scope: _Scope
    _vault: int

    @property
    def tokens(self) -> frozenset[str]:
        """EN: Tokens issued in this call. PT: Tokens emitidos nesta chamada."""
        return frozenset(self._scope.tokens)


class Vault:
    """EN: key=None generates a random key (tokens change every run, on purpose). ttl is the default time to live
    of each protect() scope, in seconds, None for no expiry.
    PT: key=None gera chave aleatoria (token muda a cada execucao, de proposito). ttl é o tempo de vida padrao de
    cada escopo do protect(), em segundos, None p/ nao expirar.
    """

    def __init__(self, key: bytes | str | None = None, ttl: float | None = DEFAULT_TTL):
        # [VAULT-INIT]
        self._key = key.encode() if isinstance(key, str) else (key or os.urandom(32))
        self._key_id = key_id(self._key)
        self._ttl = ttl
        self._map: dict[str, str] = {}
        self._canon: dict[str, str] = {}

    def token(self, entity: str, value: str) -> str:
        """EN: Deterministic token for (entity, value) under this key. PT: Token deterministico p/ (entidade, valor)."""
        # [VAULT-HMAC] canonical value, so 529.982.247-25 and 52998224725 share a token
        digest = hmac.new(self._key, f"{entity}:{_canonical(value)}".encode(), hashlib.sha256).hexdigest()
        return f"<{entity}:{self._key_id}:{digest[:TOKEN_HEX]}>"

    @property
    def key_id(self) -> str:
        """EN: Which key generation this vault issues under. PT: Sob qual geracao de chave este cofre emite."""
        return self._key_id

    def protect(
        self,
        text: str,
        matches: list[Match] | None = None,
        *,
        ttl: float | None = -1.0,
        **find_kwargs,
    ) -> ProtectedText:
        """EN: Replace identifiers with tokens and remember them. The result carries the scope reveal() asks for.
        ttl overrides the vault default for this call. Raises VaultCollisionError on a token clash.
        PT: Troca identificador por token e guarda. O resultado carrega o escopo q o reveal() pede. O ttl
        sobrescreve o padrao do cofre nesta chamada. Levanta VaultCollisionError se dois valores colidirem.
        """
        # [VAULT-PROTECT] ttl=-1.0 is the sentinel for "use the vault default", since None means "never expires"
        found = matches if matches is not None else find(text, **find_kwargs)
        out = text
        edge = len(text) + 1
        issued: set[str] = set()
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
            issued.add(tok)
            out = out[: m.start] + tok + out[m.end :]
            edge = m.start
        protected = ProtectedText(out)
        protected._scope = _Scope(issued, self._ttl if ttl == -1.0 else ttl)
        protected._vault = id(self)
        return protected

    def _scope_for(self, issued_by: ProtectedText | None, text: str) -> _Scope:
        # [VAULT-SCOPE-PICK] explicit scope first, then the text itself when it came from this vault
        source = issued_by if issued_by is not None else text
        if not isinstance(source, ProtectedText) or source._vault != id(self):
            raise VaultScopeError(
                "reveal() needs the text protect() returned: reveal(answer, issued_by=protected). "
                "Pass any_token=True only for text you trust. / "
                "o reveal() precisa do texto q o protect() devolveu, veja issued_by"
            )
        return source._scope

    def reveal(
        self,
        text: str,
        issued_by: ProtectedText | None = None,
        *,
        any_token: bool = False,
        reuse: bool = False,
    ) -> str:
        """EN: Put back the originals for the tokens issued by one protect() call. Tokens from another call, from
        another user or from a scope that expired or was already used stay as they are. any_token=True restores
        anything this vault ever issued, for trusted text only. See [VAULT-TRUST].
        PT: Devolve os originais dos tokens emitidos por uma chamada do protect(). Token de outra chamada, de
        outro usuario ou de escopo vencido ou ja usado fica como esta. any_token=True devolve qq token q este
        cofre emitiu, so p/ texto confiavel. Ver [VAULT-TRUST].
        """
        # [VAULT-REVEAL]
        allowed: set[str] | None = None
        if not any_token:
            scope = self._scope_for(issued_by, text)
            if scope.expires_at is not None and time.monotonic() > scope.expires_at:
                raise VaultExpiredError("this scope expired, protect() the text again / escopo vencido")
            if scope.used and not reuse:
                raise VaultConsumedError(
                    "this scope was already revealed, pass reuse=True to allow it again / escopo ja usado"
                )
            scope.used = True
            allowed = scope.tokens

        def put_back(m: re.Match[str]) -> str:
            tok = m.group(0)
            if allowed is not None and tok not in allowed:
                return tok
            return self._map.get(tok, tok)

        return TOKEN_RE.sub(put_back, text)

    def __len__(self) -> int:
        return len(self._map)


def residual(text: str, min_score: float = 0.0) -> list[Match]:
    """EN: Second-pass check: identifiers still present AFTER masking (should be empty). Tokens are ignored.
    PT: Checagem de 2a passada: identificadores q sobraram DEPOIS de mascarar (devia ser vazio). Tokens ignorados.
    """
    # [VAULT-RESIDUAL] blank tokens out (same length) so offsets still point at the original text
    blanked = TOKEN_RE.sub(lambda m: " " * len(m.group(0)), text)
    found = find(blanked, min_score=min_score)
    return [Match(m.entity, m.start, m.end, text[m.start : m.end], m.score, m.tier, m.pattern, m.has_context)
            for m in found]  # fmt: skip
