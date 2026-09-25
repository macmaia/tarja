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
import heapq
import hmac
import itertools
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

# [VAULT-TOKEN-RE-LENIENT] the smallest tolerance that survives a language model, and nothing more. A model
#   asked to keep a token often returns it wrapped across a line, spaced out, or with the hex in upper case.
#   Whitespace and letter case carry no information here, so accepting them costs no entropy: the twelve or
#   twenty-four hex digits still have to match exactly, and an attacker is no closer to forging one than
#   before. Anything beyond this (a missing digit, a transposition, an edit distance) WOULD lower the bar,
#   so reveal() does not do it. Decision B3 of the third board, 24/09/2026, recorded in PENDING.md.
_HEX = r"[0-9a-fA-F]"
TOKEN_RE_LENIENT = re.compile(
    r"<\s*([A-Z][A-Z0-9_]+)\s*:\s*"
    + rf"(?:((?:{_HEX}\s*){{{KEY_ID_HEX}}}):\s*)?"
    # 24 hex first, then 12, so a full vault token is never cut short by the shorter alternative
    + rf"((?:{_HEX}\s*){{24}}|(?:{_HEX}\s*){{12}})"
    + r">",
    re.ASCII,
)


def canonical_token(match: re.Match[str]) -> str:
    """EN: The strict spelling of a token matched leniently. PT: A grafia estrita de um token casado c/ folga."""
    # [VAULT-TOKEN-CANON] strip the whitespace the model added, fold the hex to lower case, rebuild the token
    entity, kid, digest = match.group(1), match.group(2), match.group(3)
    digest = re.sub(r"\s+", "", digest).lower()
    kid = re.sub(r"\s+", "", kid).lower() if kid else None
    return f"<{entity}:{kid}:{digest}>" if kid else f"<{entity}:{digest}>"


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
    __slots__ = ("tokens", "expires_at", "used", "retired")

    def __init__(self, tokens: set[str], ttl: float | None):
        self.tokens = tokens
        self.expires_at = None if ttl is None else time.monotonic() + ttl
        self.used = False
        # [VAULT-SCOPE-RETIRED] a retired scope no longer keeps its values alive, see Vault.purge
        self.retired = False

    def expired(self, now: float) -> bool:
        return self.expires_at is not None and now > self.expires_at


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

    ONE PROCESS ONLY. The map from token to value lives in this object's memory and goes nowhere else. Two
    replicas behind a load balancer do not reveal each other's tokens, so protect() and reveal() for one
    document have to land on the same process. This is deliberate, not an oversight: durable storage for that
    map needs identity and an audit trail to be safe, which is the paid Tarja Gateway. See AD-02 in PENDING.md.

    PT: key=None gera chave aleatoria (token muda a cada execucao, de proposito). ttl é o tempo de vida padrao de
    cada escopo do protect(), em segundos, None p/ nao expirar.

    UM PROCESSO SO. O mapa de token p/ valor vive na memoria deste objeto e nao vai p/ lugar nenhum. Duas
    replicas atras de um balanceador nao revelam o token uma da outra, entao protect() e reveal() do mesmo
    documento tem q cair no mesmo processo. E de proposito: guardar esse mapa de forma duravel exige identidade
    e trilha de auditoria p/ ser seguro, o q e o Gateway pago. Ver AD-02 no PENDING.md.
    """

    def __init__(self, key: bytes | str | None = None, ttl: float | None = DEFAULT_TTL):
        # [VAULT-INIT]
        self._key = key.encode() if isinstance(key, str) else (key or os.urandom(32))
        self._key_id = key_id(self._key)
        self._ttl = ttl
        self._map: dict[str, str] = {}
        self._canon: dict[str, str] = {}
        # [VAULT-SCOPES] scopes that can expire, in a heap ordered by expiry, plus the ones that never do.
        #   A plain list meant purge() walked every scope on every protect(), which is quadratic over the life
        #   of a process: 8x the documents cost 15x the time, measured 24/09/2026. The heap only ever touches
        #   what is actually due. _seq breaks ties so two scopes with the same deadline never compare _Scope.
        self._expiring: list[tuple[float, int, _Scope]] = []
        self._eternal: list[_Scope] = []
        self._seq = itertools.count()

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
        scope = _Scope(issued, self._ttl if ttl == -1.0 else ttl)
        protected._scope = scope
        protected._vault = id(self)
        if scope.expires_at is None:
            self._eternal.append(scope)
        else:
            heapq.heappush(self._expiring, (scope.expires_at, next(self._seq), scope))
        self.purge()
        return protected

    def purge(self) -> int:
        """EN: Drop the originals held only by scopes that have expired. Returns how many were dropped.
        Runs on its own inside protect() and reveal(), so you rarely call it. A scope with ttl=None never
        expires, so its values are kept on purpose.
        PT: Solta os originais presos so por escopo vencido. Devolve quantos saiu. Roda sozinho dentro do
        protect() e do reveal(). Escopo c/ ttl=None nunca vence, entao o valor fica de proposito.
        """
        # [VAULT-PURGE] the scope stopped working when it expired but the map kept the value in the clear for
        #   the life of the process, so declared retention and real retention were different things. An
        #   expired scope now releases what it held, and a value survives only while some live scope still
        #   names its token. Retiring on use instead of on expiry would break reveal(reuse=True).
        now = time.monotonic()
        retired_any = False
        # [VAULT-PURGE-HEAP] the earliest deadline is at the top, so the loop stops at the first live scope
        while self._expiring and self._expiring[0][0] <= now:
            _, _, sc = heapq.heappop(self._expiring)
            if not sc.retired:
                sc.retired = True
                retired_any = True
        if not retired_any:
            return 0
        return self._drop_unreferenced()

    def _drop_unreferenced(self) -> int:
        # [VAULT-DROP] a value survives only while some live scope still names its token
        self._eternal = [sc for sc in self._eternal if not sc.retired]
        self._expiring = [e for e in self._expiring if not e[2].retired]
        heapq.heapify(self._expiring)
        live: set[str] = set()
        for sc in self._eternal:
            live |= sc.tokens
        for _, _, sc in self._expiring:
            live |= sc.tokens
        gone = [tok for tok in self._map if tok not in live]
        for tok in gone:
            del self._map[tok]
            self._canon.pop(tok, None)
        return len(gone)

    def forget(self, protected: ProtectedText) -> int:
        """EN: Retire one scope now, without waiting for its ttl. Returns how many originals were dropped.
        PT: Aposenta um escopo agora, sem esperar o ttl. Devolve quantos originais sairam.
        """
        # [VAULT-FORGET] the explicit way out for a long-lived process that knows it is done with a document
        if not isinstance(protected, ProtectedText) or protected._vault != id(self):
            raise VaultScopeError("this text did not come from this vault / este texto nao veio deste cofre")
        protected._scope.retired = True
        return self._drop_unreferenced()

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
        self.purge()
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
            # [VAULT-REVEAL-LENIENT] look up the strict spelling, put back the text as it was on no match
            tok = canonical_token(m)
            if allowed is not None and tok not in allowed:
                return m.group(0)
            return self._map.get(tok, m.group(0))

        return TOKEN_RE_LENIENT.sub(put_back, text)

    def __len__(self) -> int:
        return len(self._map)


def residual(text: str, min_score: float = 0.0) -> list[Match]:
    """EN: Second-pass check: identifiers still present AFTER masking (should be empty). Tokens are ignored.
    PT: Checagem de 2a passada: identificadores q sobraram DEPOIS de mascarar (devia ser vazio). Tokens ignorados.
    """
    # [VAULT-RESIDUAL] blank tokens out (same length) so offsets still point at the original text. Lenient,
    #   because a token a model reflowed is still a token and must not be reported as leftover personal data.
    blanked = TOKEN_RE_LENIENT.sub(lambda m: " " * len(m.group(0)), text)
    found = find(blanked, min_score=min_score)
    return [Match(m.entity, m.start, m.end, text[m.start : m.end], m.score, m.tier, m.pattern, m.has_context)
            for m in found]  # fmt: skip
