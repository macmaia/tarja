# tarja/mask.py
# [MASK] replace detected identifiers in text. Three strategies:
#   - "redact"           -> <BR_CPF>                  (default, nothing left of the value)
#   - "pseudonym"        -> <BR_CPF_1>, <BR_CPF_2>    (consistent within one call: same value -> same label)
#   - "pseudonym_stable" -> <BR_CPF:3f9a1c0b2e7d>     (HMAC-SHA256 with YOUR key, same value -> same label in
#                                                      every document, which is the point and also the risk)
#
# [MASK-NOT-ANON] none of these anonymises under the LGPD. "pseudonym_stable" was called "hash" until 0.5: the
#   old name suggested a one-way function, and it is not one. CPF has only 10^9 valid values, so whoever holds
#   the key rebuilds the whole table and reverses every label. The key is a key, not a salt in the classic
#   sense: it defends nothing once it leaks. For irreversibility use redact, or Vault with a stored map.

from __future__ import annotations

import hashlib
import hmac
import re
import warnings
from collections.abc import Iterable

from tarja.detect import Match, find

STRATEGIES = ("redact", "pseudonym", "pseudonym_stable")
# [MASK-ALIAS] old name, still accepted, warns once per call site
STRATEGY_ALIASES = {"hash": "pseudonym_stable"}
# [MASK-SALT] refused, not warned about: a weak key in production is the whole attack. Length alone is not
#   enough ("aaaaaaaaaaaaaaaa" is 16 bytes and worthless), so the distinct-byte count goes with it.
MIN_SALT_BYTES = 16
MIN_SALT_DISTINCT = 8
WEAK_SALTS = frozenset({
    "admin", "change-me", "changeme", "default", "example", "letmein", "mysalt", "mysecret", "passwd",
    "password", "s3cr3t", "salt", "sample", "secret", "tarja", "test", "testing", "your-secret", "yoursecret",
})  # fmt: skip


def check_salt(salt: str | bytes) -> bytes:
    """EN: Return the key as bytes, or raise ValueError saying what is wrong with it.
    PT: Devolve a chave em bytes, ou levanta ValueError dizendo o q esta errado nela.
    """
    # [MASK-SALT-CHECK] order matters: a weak word is usually short too, and its message is the useful one
    key = salt.encode() if isinstance(salt, str) else bytes(salt)
    how = 'python -c "import secrets; print(secrets.token_hex(32))"'
    # [MASK-SALT-WEAK] prefix, not equality: "changeme_please_123" is long enough and still a placeholder
    low = key.decode("utf-8", "replace").strip().lower().strip("_-.")
    if any(low.startswith(w) for w in WEAK_SALTS):
        raise ValueError(f"salt is a known placeholder, generate a real one: {how} / salt e um placeholder")
    if len(key) < MIN_SALT_BYTES:
        raise ValueError(
            f"salt must be at least {MIN_SALT_BYTES} bytes, got {len(key)}: {how} / "
            f"salt precisa de pelo menos {MIN_SALT_BYTES} bytes"
        )
    if len(set(key)) < MIN_SALT_DISTINCT:
        raise ValueError(
            f"salt has only {len(set(key))} distinct bytes, too little entropy: {how} / "
            f"salt c/ poucos bytes distintos, entropia baixa"
        )
    return key


# [MASK-KEY] canonical form used for hashing/pseudonyms, so "529.982.247-25" == "52998224725"
_NON_ALNUM = re.compile(r"[^0-9A-Za-z]")


def _canonical(value: str) -> str:
    return _NON_ALNUM.sub("", value).upper()


def mask(
    text: str,
    strategy: str = "redact",
    salt: str | bytes | None = None,
    matches: Iterable[Match] | None = None,
    **find_kwargs,
) -> str:
    """EN: Return text with identifiers replaced. Pass matches to reuse a previous find(), otherwise
    find(text, **find_kwargs) runs here. strategy="pseudonym_stable" needs a salt (a secret key).
    PT: Devolve o texto c/ identificadores substituidos. Passe matches p/ reusar um find() anterior,
    senao roda find(text, **find_kwargs) aqui. strategy="pseudonym_stable" precisa de salt (chave secreta).
    """
    # [MASK-CHECK]
    if strategy in STRATEGY_ALIASES:
        warnings.warn(
            f"strategy={strategy!r} was renamed to {STRATEGY_ALIASES[strategy]!r}, the old name goes away in 0.6",
            DeprecationWarning,
            stacklevel=2,
        )
        strategy = STRATEGY_ALIASES[strategy]
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of / strategy tem q ser uma de: {STRATEGIES}")
    if strategy == "pseudonym_stable" and not salt:
        raise ValueError("pseudonym_stable needs a salt / pseudonym_stable precisa de salt")
    # [MASK-KEY] always bytes, so the type is not Optional downstream. Empty only when the strategy needs no
    #   key, which the check above already guarantees.
    key = check_salt(salt) if salt is not None else b""
    found = list(matches) if matches is not None else find(text, **find_kwargs)

    # [MASK-LABELS] build one label per match
    labels: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def label(m: Match) -> str:
        if strategy == "redact":
            return f"<{m.entity}>"
        canon = _canonical(m.value)
        if strategy == "pseudonym_stable":
            digest = hmac.new(key, f"{m.entity}:{canon}".encode(), hashlib.sha256).hexdigest()[:12]
            return f"<{m.entity}:{digest}>"
        # pseudonym
        k = (m.entity, canon)
        if k not in labels:
            counters[m.entity] = counters.get(m.entity, 0) + 1
            labels[k] = f"<{m.entity}_{counters[m.entity]}>"
        return labels[k]

    # [MASK-APPLY] number labels in reading order, then replace from the end so offsets stay valid
    ordered = sorted(found, key=lambda m: m.start)
    replacements = [(m.start, m.end, label(m)) for m in ordered]
    out = text
    for start, end, lab in reversed(replacements):
        out = out[:start] + lab + out[end:]
    return out
