# tarja/detect.py
# [DETECT] detection engine. Pipeline per entity:
#   1. normalise the text (same length, offsets kept)
#   2. run every candidate regex
#   3. validate the check digit (drop if wrong)
#   4. look for context words around the match -> final score
#   5. resolve overlaps between entities

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
    # [DETECT-SUSPECT] False = right shape, WRONG check digit (only with find(report_invalid=True), score 0).
    #   A suspect is NOT harmless: it is a sequence shaped like a document, which usually means a typo or
    #   OCR noise on a REAL identifier. Treat it like the identifier itself. Do not log it, do not put it
    #   in an error message and do not ship it to a monitoring service. Use to_dict(include_value=False).
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
    # [DETECT-CONTEXT-RE] one regex per word list, whole words only ("sus" must not hit "suspenso")
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![0-9a-z])(?:{alternatives})(?![0-9a-z])")


@lru_cache(maxsize=64)
def _adjacent_regexes(before: tuple[str, ...], after: tuple[str, ...], gap: int) -> tuple[re.Pattern[str], re.Pattern[str]]:
    # [DETECT-ADJACENT-RE] word + up to gap non-alphanumerics (+ an optional "o" from a folded "nº") at the END of the
    #   text before, and up to gap non-alphanumerics + one optional 1-3 letter linking word ("no", "do") + word at the
    #   START of the text after
    alt = lambda ws: "|".join(re.escape(w) for w in sorted(ws, key=len, reverse=True)) or "(?!)"  # noqa: E731
    pre = re.compile(rf"(?<![0-9a-z])(?:{alt(before)})[^0-9a-z]{{0,{gap}}}(?:o[^0-9a-z]{{1,2}})?$")
    post = re.compile(rf"^[^0-9a-z]{{0,{gap}}}(?:[a-z]{{1,3}}[^0-9a-z]{{1,2}})?(?:{alt(after)})(?![0-9a-z])")
    return pre, post


def _has_context(folded: str, start: int, end: int, spec: EntitySpec) -> bool:
    # [DETECT-CONTEXT] search window before and after the match in the folded (lowercase, no accent) text
    if spec.context_before or spec.context_after:
        # [DETECT-ADJACENT] tight mode, see EntitySpec.context_gap
        pre, post = _adjacent_regexes(spec.context_before, spec.context_after, spec.context_gap)
        reach = max((len(w) for w in spec.context_before), default=0) + spec.context_gap + 3
        return bool(pre.search(folded[max(0, start - reach) : start])) or bool(post.search(folded[end : end + 40]))
    lo = max(0, start - spec.context_window)
    hi = min(len(folded), end + spec.context_window)
    # blank out the match itself so the number can't count as its own context
    window = folded[lo:start] + " " + folded[end:hi]
    return _context_regex(spec.context_words).search(window) is not None


# [DETECT-SUSPECT-MIN] only "formatted" patterns (base score >= 0.5) can raise a suspect, so random digit
#   runs don't flood the report
SUSPECT_MIN_PATTERN_SCORE = 0.5


def _candidates(norm: str, folded: str, text: str, spec: EntitySpec, report_invalid: bool = False) -> Iterable[Match]:
    # [DETECT-CANDIDATES] every regex hit that passes the check digit, one Match per distinct span
    seen: set[tuple[int, int]] = set()
    for pat in spec.patterns:
        for m in pat.regex.finditer(norm):
            span = (m.start(), m.end())
            if span in seen:
                continue
            seen.add(span)
            # validate on the normalised slice (ASCII digits etc)
            if spec.validator is not None and not spec.validator(m.group(0)):
                # [DETECT-SUSPECT-EMIT] N1 look-alike with wrong DV, reported with score 0 when asked
                if report_invalid and spec.tier == "N1" and pat.score >= SUSPECT_MIN_PATTERN_SCORE:
                    ctx = _has_context(folded, m.start(), m.end(), spec)
                    yield Match(spec.id, m.start(), m.end(), text[m.start() : m.end()], 0.0, spec.tier, pat.name, ctx, False)
                continue
            ctx = _has_context(folded, m.start(), m.end(), spec)
            # entities that require context are dropped without it
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
        # sort key, best first
        return (TIER_RANK.get(m.tier, 9), -m.score, -(m.end - m.start), rank.get(m.entity, 99), m.start)

    kept: list[Match] = []
    for m in sorted(matches, key=key):
        # keep only if it doesn't touch anything already kept
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

    WARNING on report_invalid: a suspect is near-personal-data, not debug output. A number shaped like a CPF
    whose digit does not close is usually a REAL identifier with a typo or an OCR error, so it is roughly as
    sensitive as the identifier itself and often re-identifies the same person. Do not log suspects, do not put
    them in error messages, exception text or monitoring events. Count them, or carry them with
    Match.to_dict(include_value=False), which drops the raw value.

    PT: Acha identificadores brasileiros no texto.
    entities: subconjunto de ids (ex: ["BR_CPF"]), padrao todos. min_score: descarta abaixo disso.
    resolve: resolve sobreposicao entre entidades (padrao True).
    report_invalid: devolve tb parecidos N1 c/ DV ERRADO (valid_dv=False, score 0), ex: erro de digitacao.

    AVISO sobre o report_invalid: suspeito e quase dado pessoal, nao e saida de depuracao. Numero c/ cara de
    CPF cujo DV nao fecha costuma ser um identificador REAL c/ erro de digitacao ou de OCR, entao e quase tao
    sensivel quanto o identificador e muitas vezes reidentifica a mesma pessoa. Nao logue suspeito, nao ponha
    em mensagem de erro nem em evento de monitoramento. Conte, ou use to_dict(include_value=False).
    """
    # [FIND] type check
    if not isinstance(text, str):
        raise TypeError("text must be str / text precisa ser str")
    ids = list(entities) if entities is not None else list(ENTITIES)
    unknown = [e for e in ids if e not in ENTITIES]
    if unknown:
        raise ValueError(f"unknown entities / entidades desconhecidas: {unknown}")
    # [FIND-PREP] normalise once, fold once
    norm = normalise_text(text)
    folded = fold(norm)
    found: list[Match] = []
    for eid in ids:
        found.extend(_candidates(norm, folded, text, ENTITIES[eid], report_invalid))
    # [FIND-SPLIT] suspects never compete with valid matches
    suspects = [m for m in found if not m.valid_dv]
    found = [m for m in found if m.valid_dv and m.score >= min_score]
    # [FIND-RESOLVE]
    kept = resolve_overlaps(found, ids) if resolve else sorted(found, key=lambda m: (m.start, m.end))
    if suspects:
        # a suspect survives only where no valid match sits
        free = [x for x in suspects if all(x.end <= k.start or x.start >= k.end for k in kept)]
        kept = sorted(kept + resolve_overlaps(free, ids), key=lambda m: (m.start, m.end))
    return kept
