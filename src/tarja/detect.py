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
from functools import lru_cache

from tarja.entities import ENTITIES, TIER_RANK, EntitySpec
from tarja.normalise import fold, has_invisible_near_digit, normalise_text, strip_invisible


# [DETECT-MATCH] EN: hand-written instead of a dataclass, and that is the whole point. As a dataclass it
#   hid the value from repr() and from to_dict(), and leaked it through `dataclasses.asdict(match)` and
#   `vars(match)`, which is exactly what a structured logging or monitoring library calls. A control the
#   docs promise and two standard serialisers walk around is not a control. With __slots__ and no dataclass
#   decorator, both of those raise TypeError instead of returning the identifier, and the message says where
#   to go. Fail loudly beats leak quietly.
#   PT: escrito a mao em vez de dataclass, e e esse o ponto. Como dataclass ele escondia o valor do repr() e
#   do to_dict(), e vazava pelo asdict() e pelo vars(), q e o q biblioteca de log estruturado chama.
#
#   The cost, stated: Match is immutable and comparable, so __eq__ and __hash__ are written out below. If you
#   add a field, add it to __slots__, to __init__ and to _key, or equality quietly stops seeing it.
class Match:
    """EN: One detected identifier. start/end are offsets in the ORIGINAL text (text[start:end] == value).
    PT: 1 identificador achado. start/end sao offsets no texto ORIGINAL (text[start:end] == value).

    EN: the value is reachable as `.value` and through `to_dict()`. It is deliberately NOT reachable through
    `dataclasses.asdict()` or `vars()`, which both raise. Serialise with `to_dict(include_value=False)`.
    PT: o valor esta em `.value` e no `to_dict()`. De proposito NAO esta no `asdict()` nem no `vars()`.
    """

    # [DETECT-SLOTS] no __dict__, so vars(match) raises instead of handing over the identifier
    __slots__ = ("entity", "start", "end", "_value", "score", "tier", "pattern", "has_context", "valid_dv")

    # [DETECT-TYPES] EN: annotations without values. They create no class attribute, so they do not clash
    #   with __slots__, and they are the only way a type checker learns what this object carries once the
    #   dataclass decorator is gone. Dropping the decorator silently took these with it and mypy reported
    #   104 errors, every one of them "Match has no attribute ...". The behaviour was correct and the
    #   declaration was missing, which is the quiet half of hand-writing a class the tooling used to write.
    #   PT: anotacao sem valor, q nao cria atributo de classe e nao conflita com __slots__. E o unico jeito
    #   de o verificador de tipo saber o q este objeto carrega depois q o decorator saiu.
    entity: str
    start: int
    end: int
    _value: str
    score: float
    tier: str
    pattern: str
    has_context: bool
    valid_dv: bool

    def __init__(
        self,
        entity: str,
        start: int,
        end: int,
        value: str,
        score: float,
        tier: str,
        pattern: str,
        has_context: bool,
        # [DETECT-SUSPECT] False = right shape, WRONG check digit (only with find(report_invalid=True),
        #   score 0). A suspect is NOT harmless: it is a sequence shaped like a document, which usually means
        #   a typo or OCR noise on a REAL identifier. Treat it like the identifier itself. Do not log it, do
        #   not put it in an error message and do not ship it to a monitoring service.
        valid_dv: bool = True,
    ) -> None:
        # [DETECT-INIT] object.__setattr__ because __setattr__ below refuses, which is what frozen means
        for name, val in (
            ("entity", entity), ("start", start), ("end", end), ("_value", value), ("score", score),
            ("tier", tier), ("pattern", pattern), ("has_context", has_context), ("valid_dv", valid_dv),
        ):  # fmt: skip
            object.__setattr__(self, name, val)

    @property
    def value(self) -> str:
        """EN: The raw identifier. Asking for it is the point. PT: O identificador cru."""
        return self._value

    # [DETECT-FROZEN] immutable, as the dataclass version was
    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"Match is immutable, cannot set {name!r} / Match e imutavel")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"Match is immutable, cannot delete {name!r} / Match e imutavel")

    def _key(self) -> tuple:
        # [DETECT-KEY] one place that decides identity, used by both __eq__ and __hash__
        return (self.entity, self.start, self.end, self._value, self.score, self.tier, self.pattern,
                self.has_context, self.valid_dv)  # fmt: skip

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Match) and self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __repr__(self) -> str:
        """EN: Never prints the identifier. PT: Nunca imprime o identificador."""
        # [DETECT-REPR] the default repr would put the raw value into every log line, traceback and
        #   monitoring event that touches a Match. The value is still there, reachable as .value and through
        #   to_dict(), it just takes asking for it.
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


# [DETECT-EMBEDDED-LEN] EN: how many plain digits each N1 pattern accepts, probed once at import by
#   fullmatching a run of zeros. There is no length field on EntitySpec, and hard-coding 11 for CPF here
#   would be a second source of truth that drifts from the regex. 8 to 20 covers every built-in.
#   PT: quantos digitos crus cada padrao N1 aceita, medido 1x no import. Nao ha campo de tamanho no
#   EntitySpec, e escrever 11 na mao aqui seria uma segunda fonte de verdade q desgarra do regex.
EMBEDDED_MIN_DIGITS = 8
EMBEDDED_MAX_DIGITS = 20
# [DETECT-EMBEDDED-CAP] a 400-digit run would otherwise cost 400 windows per length per entity. Runs longer
#   than this are examined only in their first and last EMBEDDED_RUN_CAP digits.
EMBEDDED_RUN_CAP = 64


def _digit_lengths() -> dict[str, tuple[tuple[str, int], ...]]:
    out: dict[str, tuple[tuple[str, int], ...]] = {}
    for eid, spec in ENTITIES.items():
        if spec.tier != "N1" or spec.validator is None:
            continue
        pairs = []
        for pat in spec.patterns:
            for n in range(EMBEDDED_MIN_DIGITS, EMBEDDED_MAX_DIGITS + 1):
                # [DETECT-EMBEDDED-PROBE] every digit, not just "0": BR_CNS only starts with 1, 2, 7 or 8,
                #   so a run of zeros never fullmatched it and the entity silently fell out of this pass.
                if any(pat.regex.fullmatch(d * n) for d in "0123456789"):
                    pairs.append((pat.name, n))
                    break
        if pairs:
            out[eid] = tuple(pairs)
    return out


EMBEDDED_LENGTHS = _digit_lengths()
_DIGIT_RUN = re.compile(r"\d+")


def _embedded_candidates(norm: str, text: str, ids: list[str], taken: set[tuple[int, int]]) -> list[Match]:
    """EN: Valid identifiers sitting inside a longer digit or alphanumeric token, which the word-boundary
    anchors in the patterns cannot reach.
    PT: Identificadores validos dentro de um token maior de digitos ou alfanumerico, onde o \b dos padroes
    nao chega.
    """
    # [DETECT-EMBEDDED] EN: `0052998224725`, `5299822472500` and `x52998224725x` all carry a CPF whose check
    #   digit closes, and find() returned nothing at all for the three, not even a suspect, because every
    #   pattern is anchored with \b and the neighbouring character is a word character. In a database dump
    #   or a concatenated log that is the common shape, not the exotic one, and `scan` called the file clean.
    #   Measured 02/10/2026 on the blind attack round, and the project chose to accept the false positives
    #   this pass brings rather than keep the silent miss.
    #
    #   The whole false-positive control is the check digit: a window is kept ONLY when the validator
    #   accepts it. A random 11-digit window closes a CPF about 1 in 100 times, so a long digit run can
    #   still produce one, and that is the accepted cost. N2 has no check digit and therefore no control at
    #   all, so it stays out of this pass. Suspects are not emitted here either: without \b there is no
    #   reason to believe an unvalidated window was ever meant to be an identifier.
    #   PT: o controle de falso positivo e inteiro o DV. A janela so fica se o validador aceitar. Uma janela
    #   aleatoria de 11 digitos fecha um CPF ~1 em 100, entao sequencia longa ainda produz um, e esse e o
    #   custo aceito. N2 nao tem DV, logo nao tem controle, e fica fora. Suspeito tb nao sai daqui.
    out: list[Match] = []
    specs = [(eid, ENTITIES[eid]) for eid in ids if eid in EMBEDDED_LENGTHS]
    if not specs:
        return out
    # [DETECT-EMBEDDED-STRUCTURAL] EN: spans that any pattern of any entity matches, with no validation and
    #   no context requirement. A window strictly inside one of these is digging into a value that already
    #   has the shape of a complete identifier of some other kind, and that is where the damage was: the
    #   hyphen-delimited tail of a PIX UUID is twelve plain digits, `426614174000`, and a NIS window inside
    #   it closed. Checking letters in the token was not enough, because that tail has none.
    #   PT: spans q qualquer padrao de qualquer entidade casa, sem validar e sem exigir contexto. Janela
    #   estritamente dentro de um deles esta cavando em valor q ja tem forma de identificador completo de
    #   outro tipo. Olhar letra no token nao bastou: a cauda do UUID do PIX nao tem letra.
    #   The span only protects when the value PASSES its own entity's check: shape alone would protect too
    #   much, because a 13-digit card pattern matches the whole of `0052998224725` and would have shielded
    #   the CPF inside it. Luhn fails there, so it is not a real card and the window goes through, while the
    #   PIX UUID does validate and is left alone. Context is deliberately ignored, so a value nobody asked
    #   for still protects its own digits.
    #   PT: o span so protege se o valor PASSA no teste da propria entidade: forma sozinha protegeria demais,
    #   pq um padrao de cartao de 13 digitos casa o `0052998224725` inteiro e blindaria o CPF dentro dele.
    structural: list[tuple[int, int]] = []
    for spec in ENTITIES.values():
        for pat in spec.patterns:
            for sm in pat.regex.finditer(norm):
                if spec.validator is not None and not spec.validator(sm.group(0)):
                    continue
                # [DETECT-EMBEDDED-STRUCTURAL-CTX] EN: an entity that needs a context word only protects
                #   where that word is present. Every built-in carries a validator, and BR_IPTU's is a
                #   loose length and range check, so "passes its validator" alone let IPTU shield any
                #   13-digit run and the embedded pass found nothing at all. Context is what separates a
                #   value someone actually wrote from a shape that happens to fit.
                #   PT: entidade q exige palavra de contexto so protege onde a palavra esta. Todas as
                #   nativas tem validador, e o do BR_IPTU e so tamanho e faixa, entao "passa no validador"
                #   sozinho deixava o IPTU blindar qualquer sequencia de 13 digitos.
                if spec.context_required and not _has_context(norm, sm.start(), sm.end(), spec):
                    continue
                structural.append((sm.start(), sm.end()))

    def _inside_structural(a: int, b: int) -> bool:
        return any(sa <= a and b <= sb and (sb - sa) > (b - a) for sa, sb in structural)

    for run in _DIGIT_RUN.finditer(norm):
        r0, r1 = run.start(), run.end()
        run_len = r1 - r0
        if run_len < EMBEDDED_MIN_DIGITS:
            continue
        # [DETECT-EMBEDDED-GUARD] a run that is already a standalone token of an accepted length was found
        #   by the ordinary pass, so there is nothing here. Only a longer run, or one glued to a letter,
        #   gets the sliding window.
        # [DETECT-EMBEDDED-NOLETTER] EN: the window is only taken inside a token made of digits. A letter
        #   touching the run means another encoding, and the measurement showed what that costs: a PIX key
        #   is a UUID, `123e4567-e89b-42d3-a456-426614174000` carries `26614174000`, which closes as a valid
        #   NIS, and the NIS won the overlap and ERASED the PIX key. Accepting false positives was the
        #   decision, destroying a true positive of another entity was not. So `x52998224725x` is NOT
        #   detected and that stays a documented limit. Measured 03/10/2026.
        #   PT: a janela so vale dentro de token de digitos. Letra encostada quer dizer outra codificacao, e
        #   a medicao mostrou o preco: chave PIX e UUID, e o `26614174000` dentro dela fecha como NIS
        #   valido, o NIS ganhou a sobreposicao e APAGOU a chave PIX. Aceitar falso positivo foi a decisao,
        #   destruir verdadeiro positivo de outra entidade nao foi.
        t0, t1 = r0, r1
        while t0 > 0 and norm[t0 - 1].isalnum():
            t0 -= 1
        while t1 < len(norm) and norm[t1].isalnum():
            t1 += 1
        if any(c.isalpha() for c in norm[t0:t1]):
            continue
        glued = t1 - t0 > run_len or run_len > EMBEDDED_MIN_DIGITS
        if not glued:
            continue
        # [DETECT-EMBEDDED-WINDOWS] a very long run is examined only at its two ends. A 400-digit field is
        #   machine output, not a document where someone wrote an identifier, and walking all of it costs
        #   one window per position per length per entity.
        if run_len <= EMBEDDED_RUN_CAP:
            windows: list[int] = list(range(r0, r1))
        else:
            windows = list(range(r0, r0 + EMBEDDED_RUN_CAP)) + list(range(r1 - EMBEDDED_RUN_CAP, r1))
        for eid, spec in specs:
            for pat_name, n in EMBEDDED_LENGTHS[eid]:
                for a in windows:
                    b = a + n
                    if b > r1 or (a, b) in taken:
                        continue
                    if not glued and a == r0 and b == r1:
                        continue
                    if spec.validator is None or not spec.validator(norm[a:b]):
                        continue
                    if _inside_structural(a, b):
                        continue
                    ctx = _has_context(norm, a, b, spec)
                    if not ctx:
                        continue
                    out.append(
                        Match(
                            spec.id,
                            a,
                            b,
                            text[a:b],
                            spec.score_with_context if ctx else spec.score_without_context,
                            spec.tier,
                            pat_name + "_embedded",
                            ctx,
                        )  # fmt: skip
                    )
                    taken.add((a, b))
    return out


def _evaded_candidates(text: str, ids: list[str], report_invalid: bool) -> list[Match]:
    """EN: Candidates that only appear once invisible characters are taken out of the text.
    PT: Candidatos q so aparecem depois de tirar os caracteres invisiveis do texto.
    """
    # [DETECT-EVADED] EN: one U+200B between two digits of a valid CPF made find() return nothing at all,
    #   not even a suspect. The reader does not see the character, a language model reads the identifier
    #   normally, and the gate reported the file clean. Measured on ten characters across five classes,
    #   01/10/2026. It is not only an attack: soft hyphens and zero-width characters come out of ordinary
    #   PDF and Word extraction on their own, so this was also a silent false negative in normal use.
    #
    #   Why a second pass instead of removing them in the normaliser: the normaliser is length-preserving,
    #   and that is what lets a Match offset point into the ORIGINAL text. Removing a character shortens the
    #   text and breaks every offset, so the removal happens here, against an index map that translates back.
    #
    #   The result is VALID, not suspect. An identifier that only resolves once the invisible characters are
    #   removed is not a doubtful candidate, it is an identifier with evasion built in. Reporting it as a
    #   suspect would file it in a channel that does not gate anything.
    #   PT: um U+200B entre dois digitos de um CPF valido fazia o find() nao devolver nada, nem suspeito.
    #   Passada separada pq o normalizador preserva o tamanho, q e o q faz o offset apontar p/ o original.
    if not has_invisible_near_digit(text):
        return []
    stripped, index_map = strip_invisible(text)
    if not stripped or len(stripped) == len(text):
        return []
    norm = normalise_text(stripped)
    out: list[Match] = []
    for eid in ids:
        for m in _candidates(norm, stripped, ENTITIES[eid], report_invalid):
            if m.end <= m.start or m.end > len(index_map):
                continue  # pragma: no cover
            start, end = index_map[m.start], index_map[m.end - 1] + 1
            # [DETECT-EVADED-BAR] EN: joining across a removed character is a stronger claim than matching
            #   plain text, so the evaded candidate has to clear a higher bar. A check digit does that by
            #   itself (a wrong join closes the digit about one time in a hundred). A tier without a check
            #   digit has nothing to fall back on, so it is only accepted with a context word nearby.
            #   Without this, removing a soft hyphen at a line break joins two unrelated number groups and
            #   invents a finding.
            #   PT: juntar atraves de um caractere removido e afirmacao mais forte, entao o candidato tem de
            #   passar numa barra mais alta. DV ja faz isso. Nivel sem DV so entra com contexto perto.
            if ENTITIES[eid].tier != "N1" and not m.has_context:
                continue
            out.append(
                Match(
                    m.entity, start, end, text[start:end], m.score, m.tier, m.pattern, m.has_context, m.valid_dv
                )  # fmt: skip
            )
    return out


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
    # [FIND-EVADED] EN: the extra pass feeds the SAME list, before the split and before resolve_overlaps, so
    #   the union is resolved once and the output keeps its one invariant: spans do not overlap. Merging the
    #   two lists any later would hand mask() overlapping spans, and mask() substitutes from the end
    #   backwards, which quietly corrupts the document. Measured 01/10/2026, and mask() now refuses them.
    #   PT: a passada extra alimenta a MESMA lista, antes da divisao e do resolve, p/ a uniao ser resolvida
    #   uma vez so. Juntar depois entregaria spans sobrepostos ao mask(), q corrompe o documento em silencio.
    found.extend(_evaded_candidates(text, ids, report_invalid))
    # [FIND-EMBEDDED] same list, same reason as the evaded pass: one resolve over the union.
    found.extend(_embedded_candidates(norm, text, ids, {(m.start, m.end) for m in found}))
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
