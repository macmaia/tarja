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
from collections.abc import Iterable

from tarja.detect import Match, find
from tarja.normalise import normalise_text
from tarja.normalise import strip_invisible as _strip_invisible_pair
from tarja.vault import key_id

STRATEGIES = ("redact", "pseudonym", "pseudonym_stable")
# [MASK-ALIAS-GONE] EN: strategy="hash" was renamed in 0.5 and the deprecation warning said it went away in
#   0.6. It was still accepted in 0.8.0, three releases past the announced date, which is why the deprecation
#   notice on --report-min-score would have had no credit. Removed in 0.9.0, and the removed names stay
#   listed here so the error message can name the replacement instead of just listing the valid options.
#   PT: o strategy="hash" foi renomeado na 0.5 e o aviso prometia remocao na 0.6. Seguia aceito na 0.8.0,
#   tres versoes depois do prazo. Removido na 0.9.0, e o nome antigo fica listado so p/ o erro ser util.
REMOVED_STRATEGIES = {"hash": "pseudonym_stable"}
# [MASK-SALT] refused, not warned about: a weak key in production is the whole attack. Length alone is not
#   enough ("aaaaaaaaaaaaaaaa" is 16 bytes and worthless), so the distinct-byte count goes with it.
MIN_SALT_BYTES = 16
MIN_SALT_DISTINCT = 8
# [MASK-WEAK-SALTS] matched with startswith on the lowercased salt, so "secret-key-2026" is caught by
#   "secret". The Portuguese half is not decoration: this library exists for Brazilian Portuguese text, and a
#   Brazilian developer reaching for a placeholder types "chave-secreta" or "senha", not "password". Until
#   28/09/2026 the list was English only, so the guard rejected "example-key-..." and waved through
#   "chave-de-exemplo-...", which is the guard failing exactly where its users are. Found while writing the
#   companion book, where the English placeholder was refused and the Portuguese one was not.
WEAK_SALTS = frozenset({
    # EN
    "admin", "change-me", "changeme", "default", "example", "letmein", "mysalt", "mysecret", "passwd",
    "password", "s3cr3t", "salt", "sample", "secret", "tarja", "test", "testing", "your-secret", "yoursecret",
    # PT
    "chave", "exemplo", "minhachave", "minha-chave", "minhasenha", "minha-senha", "mude-me", "mudeme",
    "mudar", "padrao", "segredo", "senha", "teste", "testando", "troca", "trocar", "troque-me", "troqueme",
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
    # [MASK-CANON-NORM] EN: normalise BEFORE dropping punctuation, or the same identifier produces two
    #   different stable labels. Two ways it broke: a circled digit answers True to isalnum(), so it
    #   survived the filter and "CPF 529..." and "CPF ⑤②⑨..." hashed differently; and a value carrying an
    #   invisible character (the evasion pass returns the original slice, invisibles included) canonicalised
    #   to something else again. The whole point of pseudonym_stable is that the same person gets the same
    #   label everywhere, so a value that two documents spell differently has to canonicalise to one thing.
    #   PT: normalizar ANTES de tirar a pontuacao, senao o mesmo identificador gera dois rotulos estaveis
    #   diferentes. Digito cercado passava pelo isalnum(), e valor com invisivel canonizava de outro jeito.
    return _NON_ALNUM.sub("", normalise_text(_strip_invisible_pair(value)[0])).upper()


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
    if strategy in REMOVED_STRATEGIES:
        raise ValueError(
            f"strategy={strategy!r} was renamed to {REMOVED_STRATEGIES[strategy]!r} in 0.5 and removed in "
            f"0.9.0 / strategy={strategy!r} virou {REMOVED_STRATEGIES[strategy]!r} na 0.5 e saiu na 0.9.0"
        )
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of / strategy tem q ser uma de: {STRATEGIES}")
    if strategy == "pseudonym_stable" and not salt:
        raise ValueError("pseudonym_stable needs a salt / pseudonym_stable precisa de salt")
    # [MASK-KEY] always bytes, so the type is not Optional downstream. Empty only when the strategy needs no
    #   key, which the check above already guarantees.
    key = check_salt(salt) if salt is not None else b""
    kid = key_id(key) if key else ""
    found = list(matches) if matches is not None else find(text, **find_kwargs)

    # [MASK-DISJOINT] EN: substitution below walks the matches from the end backwards, which is only correct
    #   while the spans do not overlap. find() guarantees that through resolve_overlaps, so for the normal
    #   path this check never fires. A hand-built list passed as matches= has no such guarantee, and an
    #   overlapping pair silently produces a corrupted document: measured on 01/10/2026, two overlapping
    #   spans turned "CPF 529.982.247-25 tail" into "CPF <BR_CPF>" (the tail eaten) and, with other offsets,
    #   into "CPF <BR_CPF>P> tail" (half a label left behind). A masking function that quietly returns a
    #   damaged document is worse than one that refuses, because the caller ships the damage.
    #   PT: a substituicao abaixo anda de tras p/ frente, o q so esta certo enquanto os spans nao se
    #   sobrepoem. O find() garante isso, uma lista montada a mao nao. Par sobreposto corrompia o documento
    #   em silencio.
    ordered = sorted(found, key=lambda m: (m.start, m.end))
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        if later.start < earlier.end:
            raise ValueError(
                f"overlapping matches at {earlier.start}:{earlier.end} ({earlier.entity}) and "
                f"{later.start}:{later.end} ({later.entity}). mask() needs disjoint spans, use find() or "
                f"resolve them first / spans sobrepostos, o mask() precisa de spans disjuntos"
            )

    # [MASK-LABELS] build one label per match
    labels: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def label(m: Match) -> str:
        if strategy == "redact":
            return f"<{m.entity}>"
        canon = _canonical(m.value)
        if strategy == "pseudonym_stable":
            # [MASK-KEY-ID] the label goes INTO the document and stays there, so it has to say which key
            #   generation produced it. Without that, rotating the key silently breaks the join between a
            #   document masked yesterday and one masked today. See [VAULT-KEY-ID].
            digest = hmac.new(key, f"{m.entity}:{canon}".encode(), hashlib.sha256).hexdigest()[:12]
            return f"<{m.entity}:{kid}:{digest}>"
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
