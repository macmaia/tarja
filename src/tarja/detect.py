# tarja/detect.py
# [DETECT] EN: detection engine. Pipeline per entity:
#   1. normalise the text (same length, offsets kept)
#   2. run every candidate regex
#   3. validate the check digit (drop if wrong)
#   4. look for context words around the match -> final score
#   5. resolve overlaps between entities
# [DETECT] PT: motor de deteccao. Pipeline por entidade:
#   1. normaliza o texto (mesmo tamanho, offset preservado)
#   2. roda todas as regex de candidato
#   3. valida o DV (descarta se errado)
#   4. procura palavra de contexto em volta -> score final
#   5. resolve sobreposicao entre entidades

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from tarja.entities import ENTITIES, TIER_RANK, EntitySpec
from tarja.normalise import fold, normalise_text


@dataclass(frozen=True)
class Match:
    """EN: One detected identifier. start/end are offsets in the ORIGINAL text (text[start:end] == value).
    PT: 1 identificador achado. start/end sao offsets no texto ORIGINAL (text[start:end] == value).
    """

    entity: str
    start: int
    end: int
    value: str
    score: float
    tier: str
    pattern: str
    has_context: bool
    # [DETECT-SUSPECT] EN: False = right shape, WRONG check digit (only with find(report_invalid=True), score 0)
    # [DETECT-SUSPECT] PT: False = formato certo, DV ERRADO (so c/ find(report_invalid=True), score 0)
    valid_dv: bool = True

    def to_dict(self, include_value: bool = True) -> dict:
        """EN: Plain dict for JSON output. include_value=False drops the raw identifier.
        PT: Dict simples p/ saida JSON. include_value=False tira o identificador cru.
        """
        # [DETECT-DICT]
        d = {
            "entity": self.entity,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "tier": self.tier,
            "pattern": self.pattern,
            "has_context": self.has_context,
            "valid_dv": self.valid_dv,
        }
        if include_value:
            d["value"] = self.value
        return d


@lru_cache(maxsize=64)
def _context_regex(words: tuple[str, ...]) -> re.Pattern[str]:
    # [DETECT-CONTEXT-RE] EN: one regex per word list, whole words only ("sus" must not hit "suspenso")
    # [DETECT-CONTEXT-RE] PT: 1 regex por lista, so palavra inteira ("sus" nao pode casar c/ "suspenso")
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![0-9a-z])(?:{alternatives})(?![0-9a-z])")


def _has_context(folded: str, start: int, end: int, spec: EntitySpec) -> bool:
    # [DETECT-CONTEXT] EN: search window before and after the match in the folded (lowercase, no accent) text
    # [DETECT-CONTEXT] PT: busca na janela antes e dps do match no texto dobrado (minusculo, sem acento)
    lo = max(0, start - spec.context_window)
    hi = min(len(folded), end + spec.context_window)
    # EN: blank out the match itself so the number can't count as its own context
    # PT: apaga o proprio match p/ o numero nao contar como contexto de si mesmo
    window = folded[lo:start] + " " + folded[end:hi]
    return _context_regex(spec.context_words).search(window) is not None


# [DETECT-SUSPECT-MIN] EN: only "formatted" patterns (base score >= 0.5) can raise a suspect, so random digit
#   runs don't flood the report / PT: so padrao "formatado" (score base >= 0.5) gera suspeito, p/ sequencia
#   aleatoria de digitos nao inundar o relatorio
SUSPECT_MIN_PATTERN_SCORE = 0.5


def _candidates(norm: str, folded: str, text: str, spec: EntitySpec, report_invalid: bool = False) -> Iterable[Match]:
    # [DETECT-CANDIDATES] EN: every regex hit that passes the check digit, one Match per distinct span
    # [DETECT-CANDIDATES] PT: todo hit de regex q passa no DV, 1 Match por trecho distinto
    seen: set[tuple[int, int]] = set()
    for pat in spec.patterns:
        for m in pat.regex.finditer(norm):
            span = (m.start(), m.end())
            if span in seen:
                continue
            seen.add(span)
            # EN: validate on the normalised slice (ASCII digits etc) / PT: valida no trecho normalizado
            if spec.validator is not None and not spec.validator(m.group(0)):
                # [DETECT-SUSPECT-EMIT] EN: N1 look-alike with wrong DV, reported with score 0 when asked
                # [DETECT-SUSPECT-EMIT] PT: parecido N1 c/ DV errado, reportado c/ score 0 qdo pedido
                if report_invalid and spec.tier == "N1" and pat.score >= SUSPECT_MIN_PATTERN_SCORE:
                    ctx = _has_context(folded, m.start(), m.end(), spec)
                    yield Match(spec.id, m.start(), m.end(), text[m.start() : m.end()], 0.0, spec.tier, pat.name, ctx, False)
                continue
            ctx = _has_context(folded, m.start(), m.end(), spec)
            # EN: entities that require context are dropped without it / PT: entidade q exige contexto cai sem ele
            if spec.context_required and not ctx:
                continue
            score = spec.score_with_context if ctx else spec.score_without_context
            yield Match(
                entity=spec.id,
                start=m.start(),
                end=m.end(),
                value=text[m.start() : m.end()],
                score=score,
                tier=spec.tier,
                pattern=pat.name,
                has_context=ctx,
            )


def resolve_overlaps(matches: Iterable[Match], order: list[str] | None = None) -> list[Match]:
    """EN: Keep the best match wherever spans overlap. Priority: stronger tier, then higher score,
    then longer span, then registry order. Result is sorted by position.
    PT: Fica c/ o melhor match onde os trechos se sobrepoem. Prioridade: nivel mais forte, dps score
    maior, dps trecho mais longo, dps ordem do registro. Resultado ordenado por posicao.
    """
    # [DETECT-OVERLAP]
    order = order or list(ENTITIES)
    rank = {e: i for i, e in enumerate(order)}

    def key(m: Match) -> tuple:
        # EN: sort key, best first / PT: chave de ordenacao, melhor primeiro
        return (TIER_RANK.get(m.tier, 9), -m.score, -(m.end - m.start), rank.get(m.entity, 99), m.start)

    kept: list[Match] = []
    for m in sorted(matches, key=key):
        # EN: keep only if it doesn't touch anything already kept / PT: so fica se nao encosta em nada ja aceito
        if all(m.end <= k.start or m.start >= k.end for k in kept):
            kept.append(m)
    return sorted(kept, key=lambda m: (m.start, m.end))


def find(
    text: str,
    entities: Iterable[str] | None = None,
    min_score: float = 0.0,
    resolve: bool = True,
    report_invalid: bool = False,
) -> list[Match]:
    """EN: Find Brazilian identifiers in text.
    entities: subset of ids (e.g. ["BR_CPF"]), default all. min_score: drop anything below.
    resolve: resolve overlaps between entities (default True).
    report_invalid: also return N1 look-alikes with a WRONG check digit (valid_dv=False, score 0), e.g. typos.
    PT: Acha identificadores brasileiros no texto.
    entities: subconjunto de ids (ex: ["BR_CPF"]), padrao todos. min_score: descarta abaixo disso.
    resolve: resolve sobreposicao entre entidades (padrao True).
    report_invalid: devolve tb parecidos N1 c/ DV ERRADO (valid_dv=False, score 0), ex: erro de digitacao.
    """
    # [FIND] EN: type check / PT: confere tipo
    if not isinstance(text, str):
        raise TypeError("text must be str / text precisa ser str")
    ids = list(entities) if entities is not None else list(ENTITIES)
    unknown = [e for e in ids if e not in ENTITIES]
    if unknown:
        raise ValueError(f"unknown entities / entidades desconhecidas: {unknown}")
    # [FIND-PREP] EN: normalise once, fold once / PT: normaliza 1x, dobra 1x
    norm = normalise_text(text)
    folded = fold(norm)
    found: list[Match] = []
    for eid in ids:
        found.extend(_candidates(norm, folded, text, ENTITIES[eid], report_invalid))
    # [FIND-SPLIT] EN: suspects never compete with valid matches / PT: suspeito nunca compete c/ match valido
    suspects = [m for m in found if not m.valid_dv]
    found = [m for m in found if m.valid_dv and m.score >= min_score]
    # [FIND-RESOLVE]
    kept = resolve_overlaps(found, ids) if resolve else sorted(found, key=lambda m: (m.start, m.end))
    if suspects:
        # EN: a suspect survives only where no valid match sits / PT: suspeito so fica onde nao tem match valido
        free = [x for x in suspects if all(x.end <= k.start or x.start >= k.end for k in kept)]
        kept = sorted(kept + resolve_overlaps(free, ids), key=lambda m: (m.start, m.end))
    return kept
