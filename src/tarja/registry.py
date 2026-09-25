# tarja/registry.py
# [REGISTRY] public API to add your own entities (a state IE, an internal employee ID...) without forking.
#   Custom entities live in the same ENTITIES dict the engine reads, so find(), mask(), Vault and the CLI
#   pick them up. Built-in entities are protected unless replace=True.
#   Not thread-safe: register at start-up, before serving requests.

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Iterable

from tarja.entities import ENTITIES, TIER_RANK, EntitySpec, Pattern

_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_LOCK = threading.RLock()
_FROZEN = False


class RegistryFrozenError(RuntimeError):
    """EN: The registry was frozen and no longer accepts changes. PT: O registro foi congelado."""


class UnsafeRegexError(ValueError):
    """EN: The pattern has a shape known to backtrack catastrophically. PT: Padrao c/ retrocesso catastrofico."""


# [REGISTRY-REDOS] find() runs registered patterns over text a stranger submitted, and Python's regex engine
#   backtracks. A repeat inside something that is itself repeated, (\d+)+, or a repeated alternation whose
#   branches match the same input, (a|a)*, can take exponential time on an input a few dozen characters long,
#   so one custom entity can hang the process. Refusing at registration is the only point where the cost
#   is bounded and the message can be
#   useful, because a timeout in Python is neither portable nor reliable.
#
#   This is a SHAPE check, not a proof. It catches two textbook shapes, the nested quantifier and the
#   repeated alternation with identical branches. It does NOT catch branches that merely overlap, such as
#   (a|ab)*, because deciding that in general is undecidable. A pattern it accepts is not certified safe.
#
#   It also refuses patterns that are in fact fine, and the clearest example is in this repository: the
#   lenient token regex in vault.py, (?:[0-9a-fA-F]\s*){24}, is safe because hex and whitespace cannot match
#   the same character, so there is nothing to backtrack over. This check cannot see that, and deciding it in
#   general is the same undecidable problem. That is what unsafe_regex=True is for.
#   Decision B4 of the third board, 24/09/2026, recorded in PENDING.md.
_OPEN_QUANT = ("*", "+")


def _brace_is_variable(spec: str) -> bool:
    """EN: Can this {..} match a varying number of times? PT: Esse {..} pode casar um numero variavel de vezes?"""
    # [REGISTRY-REDOS-VARIABLE] the INNER test. Ambiguity needs a repeat that can end in more than one place:
    #   {3} always consumes exactly three, so (\d{3}\.){2} has a single parse and is perfectly safe. Treating
    #   an exact count as ambiguous refused ordinary patterns, which is worse than useless, because people
    #   then reach for unsafe_regex=True by habit and the check stops meaning anything.
    inner = spec.strip()
    try:
        if inner.endswith(","):
            return True
        if "," in inner:
            low, high = inner.split(",", 1)
            return True if not high.strip() else int(high) > int(low or 0)
        return False
    except ValueError:
        return False


def _brace_repeats(spec: str) -> bool:
    """EN: Does {n}, {n,} or {n,m} repeat enough to matter? PT: Esse {n} repete o bastante p/ importar?"""
    # [REGISTRY-REDOS-BRACE] {n} with n >= 2 counts. (\d+){10} was slipping through because an exact count
    #   was not treated as a repeat at all, and ten ambiguous splits of the same run is a polynomial blow-up,
    #   not a safe pattern. A malformed quantifier is not our error to report: say no repeat and let
    #   re.compile raise its own, much clearer, message a few lines later.
    inner = spec.strip()
    if not inner:
        return False
    try:
        if inner.endswith(","):
            return True
        if "," in inner:
            low, high = inner.split(",", 1)
            return int(high) >= 2 if high.strip() else True
        return int(inner) >= 2
    except ValueError:
        return False


def _top_level_quantifier(body: str) -> bool:
    # [REGISTRY-REDOS-BODY] is there a VARIABLE repeat anywhere in this group, outside a class or an escape
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < len(body) and body[j] == "^":
                j += 1
            if j < len(body) and body[j] == "]":
                j += 1
            while j < len(body) and body[j] != "]":
                j += 2 if body[j] == "\\" else 1
            i = j + 1
            continue
        if c in _OPEN_QUANT:
            return True
        if c == "{":
            close = body.find("}", i)
            if close != -1 and _brace_is_variable(body[i + 1 : close]):
                return True
            if close != -1:
                i = close + 1
                continue
        i += 1
    return False


def _split_branches(body: str) -> list[str]:
    # [REGISTRY-REDOS-ALT] top-level alternation only, so "(a|(b|c))" splits into "a" and "(b|c)"
    out: list[str] = []
    depth = start = i = 0
    while i < len(body):
        c = body[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = body.find("]", i + 1)
            i = (j + 1) if j != -1 else len(body)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "|" and depth == 0:
            out.append(body[start:i])
            start = i + 1
        i += 1
    out.append(body[start:])
    return out


def _duplicate_branches(body: str) -> bool:
    # [REGISTRY-REDOS-DUP] two branches that match the same input give the engine two ways to consume every
    #   character, which multiplies. Only exact duplicates are caught: deciding whether two regexes overlap
    #   is undecidable in general, so this is the cheap half of the problem, honestly scoped.
    branches = [b.strip() for b in _split_branches(body)]
    if branches and branches[0].startswith("?:"):
        branches[0] = branches[0][2:].strip()
    return len(branches) > 1 and len(set(branches)) < len(branches)


def check_regex(pattern: str) -> None:
    """EN: Raise UnsafeRegexError when the pattern repeats something that already repeats.
    PT: Levanta UnsafeRegexError qdo o padrao repete algo q ja se repete.
    """
    # [REGISTRY-REDOS-SCAN] walk the string, remember where each group opened, and when one closes look at
    #   what follows it and at what it contains
    stack: list[int] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < len(pattern) and pattern[j] == "^":
                j += 1
            if j < len(pattern) and pattern[j] == "]":
                j += 1
            while j < len(pattern) and pattern[j] != "]":
                j += 2 if pattern[j] == "\\" else 1
            i = j + 1
            continue
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            start = stack.pop()
            nxt = pattern[i + 1 : i + 2]
            repeated = nxt in _OPEN_QUANT
            if nxt == "{":
                close = pattern.find("}", i + 1)
                repeated = close != -1 and _brace_repeats(pattern[i + 2 : close])
            body = pattern[start + 1 : i]
            if repeated and (_top_level_quantifier(body) or _duplicate_branches(body)):
                raise UnsafeRegexError(
                    f"unsafe repeat at position {start} in {pattern!r}: a repeat inside a repeat, or a "
                    "repeated alternation whose branches match the same thing, can "
                    "take exponential time on hostile input. Rewrite it, or pass unsafe_regex=True to take "
                    "the risk yourself. / quantificador aninhado: repeticao dentro de repeticao pode levar "
                    "tempo exponencial. Reescreva, ou passe unsafe_regex=True e assuma o risco."
                )
        i += 1


def freeze() -> None:
    """EN: Close the registry. Any later register_entity() or unregister_entity() raises RegistryFrozenError.
    Call it once, after start-up registration and before serving requests. Idempotent.
    PT: Fecha o registro. Registro posterior levanta RegistryFrozenError. Chame 1x, dps do start-up e antes de
    servir requisicao. Idempotente.
    """
    # [REGISTRY-FREEZE]
    global _FROZEN
    with _LOCK:
        _FROZEN = True


def unfreeze() -> None:
    """EN: Reopen the registry. For tests and for a deliberate hot reload, not for request handling.
    PT: Reabre o registro. P/ teste e recarga deliberada, nao p/ tratar requisicao.
    """
    # [REGISTRY-UNFREEZE]
    global _FROZEN
    with _LOCK:
        _FROZEN = False


def is_frozen() -> bool:
    return _FROZEN


def _check_open() -> None:
    if _FROZEN:
        raise RegistryFrozenError(
            "registry is frozen: register entities at start-up, before freeze() / "
            "registro congelado: registre as entidades no start-up, antes do freeze()"
        )


# ids shipped with tarja, frozen at import so replace/unregister can protect them
BUILTIN_IDS = frozenset(ENTITIES)


def register_entity(
    entity_id: str,
    patterns: Iterable[tuple[str, str, float]],
    *,
    tier: str = "N3",
    validator: Callable[[str], bool] | None = None,
    context_words: Iterable[str] = (),
    context_window: int = 50,
    context_required: bool | None = None,
    score_with_context: float = 0.8,
    score_without_context: float = 0.5,
    replace: bool = False,
    unsafe_regex: bool = False,
) -> EntitySpec:
    """EN: Add a custom entity. Call this ONCE, at start-up, before serving requests: the registry is
    process-wide, so a call inside a request handler changes detection for every other caller in that
    process, including libraries that never asked for your entity. Follow it with freeze(). See AD-05.

    patterns = [(name, regex, base_score), ...]. A pattern whose shape backtracks catastrophically is
    refused, see check_regex; unsafe_regex=True takes the risk yourself. context_words are matched on
    lowercase, accent-free text, so write them that way ("inscricao estadual"). N1 needs a validator.
    context_required defaults to True for N3 and False otherwise. Returns the stored EntitySpec.
    PT: Adiciona entidade propria. Chame 1x, no start-up, antes de servir requisicao: o registro vale p/ o
    processo inteiro, entao chamada dentro de handler muda a deteccao de todo mundo. Dps use freeze().
    Padrao c/ forma de retrocesso catastrofico e recusado, ver check_regex, e unsafe_regex=True assume o
    risco. patterns = [(nome, regex, score_base), ...]. Palavras de contexto sao
    comparadas em minusculo sem acento, escreva assim ("inscricao estadual"). N1 exige validador.
    context_required padrao True p/ N3 e False nos outros. Devolve o EntitySpec gravado.

    >>> register_entity("BR_IE_SP", [("ie_sp", r"\\b\\d{3}\\.\\d{3}\\.\\d{3}\\.\\d{3}\\b", 0.5)],
    ...                 context_words=["inscricao estadual", "ie"])  # doctest: +SKIP
    """
    # [REGISTRY-CHECK] fail loudly at registration, not later inside find()
    if not _ID_RE.match(entity_id):
        raise ValueError(f"entity id must be UPPER_SNAKE_CASE, 2-64 chars: {entity_id!r}")
    if entity_id in ENTITIES and not replace:
        raise ValueError(f"{entity_id} already registered, pass replace=True to override")
    if tier not in TIER_RANK:
        raise ValueError(f"tier must be one of {sorted(TIER_RANK)}")
    if tier == "N1" and validator is None:
        raise ValueError("N1 means a strong check digit: pass a validator")
    for s in (score_with_context, score_without_context):
        if not 0.0 <= s <= 1.0:
            raise ValueError("scores must be between 0 and 1")
    # [REGISTRY-CHECK-REDOS] see check_regex. unsafe_regex=True is the deliberate way past it, and it moves
    #   the risk to whoever passed it: find() will run that pattern on whatever text the caller receives.
    if not unsafe_regex:
        for _name, _regex, _score in patterns:
            check_regex(_regex)
    compiled = []
    for name, regex, score in patterns:
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"pattern {name}: score must be between 0 and 1")
        compiled.append(Pattern(name, re.compile(regex), float(score)))
    if not compiled:
        raise ValueError("at least one pattern is required")
    words = tuple(w.lower() for w in context_words)
    required = (tier == "N3") if context_required is None else context_required
    if required and not words:
        raise ValueError("context_required=True needs context_words")
    spec = EntitySpec(
        id=entity_id,
        tier=tier,
        patterns=tuple(compiled),
        validator=validator,
        context_words=words,
        context_window=context_window,
        context_required=required,
        score_with_context=score_with_context,
        score_without_context=score_without_context,
    )
    with _LOCK:
        _check_open()
        ENTITIES[entity_id] = spec
    return spec


def unregister_entity(entity_id: str) -> None:
    """EN: Remove a custom entity. Built-ins can't be removed (use find(entities=[...]) to skip them).
    PT: Remove entidade propria. As nativas nao saem (use find(entities=[...]) p/ pular).
    """
    # [REGISTRY-REMOVE]
    if entity_id in BUILTIN_IDS:
        raise ValueError(f"{entity_id} is built in, filter it with find(entities=...) instead")
    with _LOCK:
        _check_open()
        ENTITIES.pop(entity_id, None)
