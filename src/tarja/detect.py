# tarja/detect.py
# [DETECT] detection engine. Pipeline per entity:
#   1. normalise the text (same length, offsets kept)
#   2. run every candidate regex
#   3. validate the check digit (drop if wrong)
#   4. look for context words around the match -> final score
#   5. resolve overlaps between entities

from __future__ import annotations

import bisect
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from tarja.entities import ENTITIES, TIER_RANK, EntitySpec
from tarja.normalise import fold, normalise_text


@dataclass(frozen=True, repr=False)
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

    def __repr__(self) -> str:
        """EN: Never prints the identifier. PT: Nunca imprime o identificador."""
        # [DETECT-REPR] the default dataclass repr would put the raw value into every log line, traceback and
        #   monitoring event that touches a Match, which is exactly what find()'s own warning forbids. A
        #   control the docs demand and the code does not enforce is not a control. The value is still there,
        #   reachable as .value and through to_dict(), it just takes asking for it.
        keep = "" if self.valid_dv else ", SUSPECT"
        return (
            f"Match({self.entity} {self.start}:{self.end} score={self.score} "
            f"pattern={self.pattern} context={self.has_context}{keep}, value hidden/valor oculto)"
        )

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


def _has_context(norm: str, start: int, end: int, spec: EntitySpec) -> bool:
    # [DETECT-CONTEXT] search window before and after the match, folded (lowercase, no accent) on demand.
    #   fold() is one character in, one character out, so folding a slice gives exactly what slicing the
    #   folded whole would give. Folding the whole text cost 6.3 ms on a 78 KB document, 13% of find(), and
    #   a second full copy of it in memory, to serve windows of a hundred characters around each match.
    #   Break-even is around 34,000 matches in one document, which no real document reaches.
    if spec.context_before or spec.context_after:
        # [DETECT-ADJACENT] tight mode, see EntitySpec.context_gap
        pre, post = _adjacent_regexes(spec.context_before, spec.context_after, spec.context_gap)
        reach = max((len(w) for w in spec.context_before), default=0) + spec.context_gap + 3
        before = fold(norm[max(0, start - reach) : start])
        return bool(pre.search(before)) or bool(post.search(fold(norm[end : end + 40])))
    lo = max(0, start - spec.context_window)
    hi = min(len(norm), end + spec.context_window)
    # blank out the match itself so the number can't count as its own context
    window = fold(norm[lo:start]) + " " + fold(norm[end:hi])
    return _context_regex(spec.context_words).search(window) is not None


# [DETECT-SUSPECT-MIN] only "formatted" patterns (base score >= 0.5) can raise a suspect, so random digit
#   runs don't flood the report
SUSPECT_MIN_PATTERN_SCORE = 0.5

# [DETECT-MAX-CHARS] a default ceiling on the input, because find() is often called straight on text a stranger
#   submitted. The CLI has had --max-mb from the start and the library had nothing, so a service built on it
#   accepted any size. Generous enough that ordinary documents never notice, small enough that one request
#   cannot hold a worker. Pass max_chars=None to lift it deliberately.
MAX_CHARS = 5_000_000


def _candidates(norm: str, text: str, spec: EntitySpec, report_invalid: bool = False) -> Iterable[Match]:
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
                    ctx = _has_context(norm, m.start(), m.end(), spec)
                    yield Match(spec.id, m.start(), m.end(), text[m.start() : m.end()], 0.0, spec.tier, pat.name, ctx, False)
                continue
            ctx = _has_context(norm, m.start(), m.end(), spec)
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

    # [DETECT-OVERLAP-SWEEP] kept is held sorted by start and never overlaps, so a candidate can only clash
    #   with its immediate neighbours. Comparing against every kept match instead made this quadratic: 16x the
    #   input cost 93x the time, and a dense 4 MB document did not finish. Measured 24/09/2026.
    kept: list[Match] = []
    starts: list[int] = []
    for m in sorted(matches, key=key):
        i = bisect.bisect_left(starts, m.start)
        if i and kept[i - 1].end > m.start:
            continue
        if i < len(kept) and m.end > kept[i].start:
            continue
        starts.insert(i, m.start)
        kept.insert(i, m)
    return kept


def find(
    text: str,
    entities: Iterable[str] | None = None,
    min_score: float = 0.0,
    resolve: bool = True,
    report_invalid: bool = False,
    max_chars: int | None = MAX_CHARS,
) -> list[Match]:
    """EN: Find Brazilian identifiers in text.
    entities: subset of ids (e.g. ["BR_CPF"]), default all.
    min_score: drop anything below. It applies to VALID matches only: a suspect always scores 0 and is
    returned whenever report_invalid=True, so find(text, min_score=0.9, report_invalid=True) still yields
    suspects. Filter them with [m for m in found if m.valid_dv] when you do not want them.
    resolve: resolve overlaps between entities (default True).
    report_invalid: also return N1 look-alikes with a WRONG check digit (valid_dv=False, score 0), e.g. typos.
    max_chars: refuse input longer than this (default 5 million, None to lift it). It exists because find() is
    often called on text someone else submitted, and an unbounded call is an unbounded amount of work.

    WARNING on report_invalid: a suspect is near-personal-data, not debug output. A number shaped like a CPF
    whose digit does not close is usually a REAL identifier with a typo or an OCR error, so it is roughly as
    sensitive as the identifier itself and often re-identifies the same person. Do not log suspects, do not put
    them in error messages, exception text or monitoring events. Count them, or carry them with
    Match.to_dict(include_value=False), which drops the raw value.

    PT: Acha identificadores brasileiros no texto.
    entities: subconjunto de ids (ex: ["BR_CPF"]), padrao todos.
    min_score: descarta abaixo disso. Vale so p/ match VALIDO: suspeito sempre tem score 0 e volta sempre q
    report_invalid=True, entao find(texto, min_score=0.9, report_invalid=True) ainda devolve suspeito. Filtre
    c/ [m for m in found if m.valid_dv] se nao quiser.
    resolve: resolve sobreposicao entre entidades (padrao True).
    report_invalid: devolve tb parecidos N1 c/ DV ERRADO (valid_dv=False, score 0), ex: erro de digitacao.
    max_chars: recusa entrada maior q isso (padrao 5 milhoes, None p/ tirar o limite). Existe pq o find()
    costuma ser chamado em texto q outra pessoa mandou, e chamada sem limite e trabalho sem limite.

    AVISO sobre o report_invalid: suspeito e quase dado pessoal, nao e saida de depuracao. Numero c/ cara de
    CPF cujo DV nao fecha costuma ser um identificador REAL c/ erro de digitacao ou de OCR, entao e quase tao
    sensivel quanto o identificador e muitas vezes reidentifica a mesma pessoa. Nao logue suspeito, nao ponha
    em mensagem de erro nem em evento de monitoramento. Conte, ou use to_dict(include_value=False).
    """
    # [FIND] type check
    if not isinstance(text, str):
        raise TypeError("text must be str / text precisa ser str")
    # [FIND-LIMIT] the message says the size and the way out, so nobody has to read the source to unblock
    if max_chars is not None and len(text) > max_chars:
        raise ValueError(
            f"text is {len(text)} chars, over the {max_chars} limit. Split it, or pass max_chars=None. / "
            f"texto tem {len(text)} caracteres, acima do limite de {max_chars}. Divida, ou passe max_chars=None."
        )
    ids = list(entities) if entities is not None else list(ENTITIES)
    unknown = [e for e in ids if e not in ENTITIES]
    if unknown:
        raise ValueError(f"unknown entities / entidades desconhecidas: {unknown}")
    # [FIND-PREP] normalise once. Folding happens per context window, see _has_context.
    norm = normalise_text(text)
    found: list[Match] = []
    for eid in ids:
        found.extend(_candidates(norm, text, ENTITIES[eid], report_invalid))
    # [FIND-SPLIT] suspects never compete with valid matches
    suspects = [m for m in found if not m.valid_dv]
    found = [m for m in found if m.valid_dv and m.score >= min_score]
    # [FIND-RESOLVE]
    kept = resolve_overlaps(found, ids) if resolve else sorted(found, key=lambda m: (m.start, m.end))
    if suspects:
        # [FIND-SUSPECT-FREE] a suspect survives only where no valid match sits. kept is sorted by start and
        #   does not overlap, so binary search on the neighbours, not a scan over everything.
        kept_starts = [k.start for k in kept]

        def _free(x: Match) -> bool:
            i = bisect.bisect_left(kept_starts, x.start)
            if i and kept[i - 1].end > x.start:
                return False
            return not (i < len(kept) and x.end > kept[i].start)

        free = [x for x in suspects if _free(x)]
        kept = sorted(kept + resolve_overlaps(free, ids), key=lambda m: (m.start, m.end))
    return kept
