# tarja/registry.py
# [REGISTRY] public API to add your own entities (a state IE, an internal employee ID...) without forking.
#   Custom entities live in the same ENTITIES dict the engine reads, so find(), mask(), Vault and the CLI
#   pick them up. Built-in entities are protected unless replace=True.
#   Not thread-safe: register at start-up, before serving requests.

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from tarja.entities import ENTITIES, TIER_RANK, EntitySpec, Pattern

_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
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
) -> EntitySpec:
    """EN: Add a custom entity. patterns = [(name, regex, base_score), ...]. context_words are matched on
    lowercase, accent-free text, so write them that way ("inscricao estadual"). N1 needs a validator.
    context_required defaults to True for N3 and False otherwise. Returns the stored EntitySpec.
    PT: Adiciona entidade propria. patterns = [(nome, regex, score_base), ...]. Palavras de contexto sao
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
    ENTITIES[entity_id] = spec
    return spec


def unregister_entity(entity_id: str) -> None:
    """EN: Remove a custom entity. Built-ins can't be removed (use find(entities=[...]) to skip them).
    PT: Remove entidade propria. As nativas nao saem (use find(entities=[...]) p/ pular).
    """
    # [REGISTRY-REMOVE]
    if entity_id in BUILTIN_IDS:
        raise ValueError(f"{entity_id} is built in, filter it with find(entities=...) instead")
    ENTITIES.pop(entity_id, None)
