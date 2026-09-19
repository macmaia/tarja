# tarja/mask.py
# [MASK] replace detected identifiers in text. Three strategies:
#   - "redact"    -> <BR_CPF>                      (default, nothing left of the value)
#   - "hash"      -> <BR_CPF:3f9a1c0b2e7d>         (HMAC-SHA256 with YOUR salt, same value -> same hash across docs)
#   - "pseudonym" -> <BR_CPF_1>, <BR_CPF_2>...     (consistent within one call: same value -> same label)
#
# Note: hash is pseudonymisation, NOT anonymisation under the LGPD. With the salt, it can be linked back.

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Iterable

from tarja.detect import Match, find

STRATEGIES = ("redact", "hash", "pseudonym")

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
    find(text, **find_kwargs) runs here. strategy="hash" needs a salt.
    PT: Devolve o texto c/ identificadores substituidos. Passe matches p/ reusar um find() anterior,
    senao roda find(text, **find_kwargs) aqui. strategy="hash" precisa de salt.
    """
    # [MASK-CHECK]
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of / strategy tem q ser uma de: {STRATEGIES}")
    if strategy == "hash" and not salt:
        raise ValueError("hash needs a salt / hash precisa de salt")
    key = salt.encode() if isinstance(salt, str) else salt
    found = list(matches) if matches is not None else find(text, **find_kwargs)

    # [MASK-LABELS] build one label per match
    labels: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def label(m: Match) -> str:
        if strategy == "redact":
            return f"<{m.entity}>"
        canon = _canonical(m.value)
        if strategy == "hash":
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
