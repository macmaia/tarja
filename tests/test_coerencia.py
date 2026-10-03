# tests/test_coerencia.py
# EN: guards that stop a published claim from drifting away from the code. Each test here exists because a
#   claim in a published file was found to be false, and fixing the line by hand had already failed twice.
#   These tests sweep EVERY text file instead of checking one line, which is the whole point.
# PT: guardas q impedem afirmacao publicada de descolar do codigo. Cada teste aqui existe pq uma afirmacao
#   em arquivo publicado foi achada falsa, e consertar linha a linha ja tinha falhado 2x.
#
# [COER] file anchor. Sub-tags: [COER-CONTAGEM], [COER-TIER], [COER-INTERNO].

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _guarantees import Swept, guarantees

from tarja.entities import ENTITIES

ROOT = Path(__file__).resolve().parent.parent

# [COER-CONST] everything tunable lives here, so a reader never hunts a literal in the body below.

# EN: extensions worth sweeping. Binary and generated trees are excluded by SKIP_PARTS.
TEXT_SUFFIXES = (".md", ".py", ".yml", ".yaml", ".toml", ".txt", ".ipynb", ".cfg")

# EN: directories that are not ours to police, or are generated.
SKIP_PARTS = ("/.git/", "/_build/", "/node_modules/", "/__pycache__/", "/.ruff_cache/", "/dist/", "/.venv/")

# EN: files deliberately outside the sweep. PENDING.md is internal working notes and keeps its history,
#   including superseded counts. decisions.md is a dated log where old entries stay as written.
SKIP_NAMES = ("PENDING.md", "decisions.md", "test_coerencia.py")

# EN: number words that could stand in for an entity count, in both languages, mapped to their value.
#   A count written as a word is exactly what slipped through twice: "catorze" and "sixteen".
NUMBER_WORDS = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
    "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
}  # fmt: skip

# EN: a count sits at most this many words before the noun: "all 16 tarja entities" needs 2.
MAX_WORDS_BETWEEN = 2

# EN: the noun that marks an entity count, in both languages.
_NOUN = r"entit(?:y|ies)|entidades?|identifier types?|tipos? de identificador"

# EN: <count> [up to MAX_WORDS_BETWEEN words] <noun>. The count group accepts ONLY a digit run or a word
#   that NUMBER_WORDS knows. The first draft of this regex accepted any 3-to-10 letter word there, so in
#   "all 16 tarja entities" the word "all" won the leftmost match, came back unknown, and was skipped. The
#   test then passed on the one line it was written to catch. Build the alternation from the data instead.
_COUNT = r"\d{1,3}|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
COUNT_BEFORE_NOUN = re.compile(
    rf"\b({_COUNT})\s+(?:[\w.-]+\s+){{0,{MAX_WORDS_BETWEEN}}}?(?:{_NOUN})\b",
    re.IGNORECASE,
)

# EN: counts that legitimately are not the entity total. A tier count is a real, different number.
#   Keep this list short and justified: every entry here is a hole in the guard.
ALLOWED_OTHER_COUNTS = {
    11,  # N1 entities
    3,  # N2 entities, and N3 entities
    7,  # entities that require context
    1,  # "one entity", "1 recognizer per entity"
    2,  # "two entities moved", CPF + CNPJ in the Presidio PR
    15,  # the total minus CPF and CNPJ: what the plugin still adds if Presidio PR 2281 lands
    8,  # tier-N1 entities needing no context word: the set tarja-presidio sends at confidence 1.0
}

# EN: a word here right before the noun makes the number a RATE, not a count: "200 values per entity",
#   "three to four wordings per entity". Without this the sweep reports every rate as a wrong total.
RATE_MARKERS = ("per", "por", "each", "cada")

# EN: strings that must never appear in a file that ships or is published, because they point the reader at
#   an internal working file or at internal process vocabulary.
INTERNAL_LEAKS = ("PENDING.md", "PENDING_", "review board", "the third board", "the fourth board")


def _sweepable() -> list[Path]:
    # [COER-SWEEP] one place that decides what gets read, so three tests cannot drift apart
    out = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        posix = "/" + p.relative_to(ROOT).as_posix()
        if any(part in posix for part in SKIP_PARTS) or p.name in SKIP_NAMES:
            continue
        out.append(p)
    return out


class TestContagemDeEntidades(unittest.TestCase):
    """EN: no file may state an entity count that disagrees with the registry."""

    @guarantees("G-DOC-COUNT")
    def test_every_stated_entity_count_matches_the_registry(self):
        # [COER-CONTAGEM] EN: this is the test that docs/presidio.md needed. The 16 -> 17 fix was applied by
        #   hand to one line of that file and missed another line in the same file, twice. A sweep cannot
        #   miss a line.
        total = len(ENTITIES)
        self.assertEqual(total, 17, "registry size changed, update the published counts and this number")
        wrong = []
        # [COER-SWEPT] floor measured 01/10/2026: the repository has far more than this, and the number is
        #   low on purpose. It is here to catch the sweep going to zero, not to track the file count.
        files = Swept(_sweepable(), "text files in the repository", minimum=30)
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            # [COER-WRAP] scan the WHOLE text, not line by line. A prose file wraps at 120 columns, so
            #   "the 8 tier-N1\nentities" puts the count and its noun on different lines and a per-line
            #   sweep walks straight past it. That is exactly how the first version of this test missed a
            #   claim in a file it had just been pointed at. Line number comes from the match offset.
            for m in COUNT_BEFORE_NOUN.finditer(text):
                token = m.group(1).strip().lower()
                value = int(token) if token.isdigit() else NUMBER_WORDS.get(token)
                if value is None or value in ALLOWED_OTHER_COUNTS or value == total:
                    continue
                # [COER-RATE] the word just before the noun decides count against rate
                words = m.group(0).lower().split()
                if len(words) > 1 and words[-2] in RATE_MARKERS:
                    continue
                n = text.count("\n", 0, m.start()) + 1
                quoted = " ".join(m.group(0).split())
                where = f"{path.relative_to(ROOT)}:{n}"
                wrong.append(f"{where}: states {value} entities, registry has {total}\n    ...{quoted}...")
        files.check(self)
        self.assertEqual(wrong, [], "entity count disagrees with the registry:\n" + "\n".join(wrong))


class TestSemVazamentoInterno(unittest.TestCase):
    """EN: nothing that ships may send the reader to an internal file."""

    @guarantees("G-DOC-INTERNAL")
    def test_no_shipped_file_points_at_internal_notes(self):
        # [COER-INTERNO] EN: help(tarja.Vault) used to tell every PyPI user to read PENDING.md, which is not
        #   in the repo, not in the wheel, and not meant for them.
        leaks = []
        files = Swept(_sweepable(), "text files in the repository", minimum=30)
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                for needle in INTERNAL_LEAKS:
                    if needle.lower() in line.lower():
                        leaks.append(f"{path.relative_to(ROOT)}:{n}: mentions {needle!r}\n    {line.strip()[:120]}")
        files.check(self)
        self.assertEqual(leaks, [], "shipped file points at internal notes or process:\n" + "\n".join(leaks))


class TestInvarianteDeTier(unittest.TestCase):
    """EN: the invariant tarja-presidio relies on to map confidence. Tested here, in the core, because the
    plugin's own tests need Presidio installed and this property belongs to the registry anyway."""

    @guarantees("G-PRESIDIO-TIER")
    def test_only_n1_entities_carry_a_check_digit(self):
        # [COER-TIER] EN: tarja-presidio turns "validator passed" into Presidio confidence 1.0. That is only
        #   honest for an entity whose validator checks a check digit, which is exactly tier N1. For N2 and
        #   N3 the validator checks a format or a range, so a plate matching ABC1D23 must NOT reach Presidio
        #   with the same confidence as a CPF whose check digit was verified.
        for name, spec in ENTITIES.items():
            with self.subTest(entity=name):
                if spec.tier == "N1":
                    self.assertIsNotNone(spec.validator, f"{name} is N1 and must have a check-digit validator")
                else:
                    self.assertIn(spec.tier, ("N2", "N3"), f"{name} has an unexpected tier {spec.tier!r}")

    def test_format_only_entities_are_identifiable_without_the_plugin(self):
        # [COER-TIER] EN: the set the plugin must hold back from confidence 1.0. Pinned by name so adding an
        #   N2/N3 entity without revisiting the plugin fails here.
        format_only = sorted(n for n, s in ENTITIES.items() if s.tier != "N1")
        self.assertEqual(
            format_only,
            ["BR_CEP", "BR_IPTU", "BR_MATRICULA_IMOVEL", "BR_PIX_EVP", "BR_PLACA", "BR_TELEFONE"],
            "tier N2/N3 membership changed, revisit TarjaRecognizer.validate_result",
        )


class TestVarreduraNaoPassaVazia(unittest.TestCase):
    """EN: the counter that makes a vacuous sweep impossible, tested on itself."""

    @guarantees("G-SWEEP-NONEMPTY")
    def test_a_sweep_that_examined_nothing_fails(self):
        # [COER-SWEPT-SELF] EN: proved by sabotage on 01/10/2026: emptying _sweepable() made both sweeps in
        #   this file fail loudly instead of passing. Before the counter they passed, which is the whole
        #   defect. Tested here against an empty iterable rather than by breaking the real sweep.
        empty = Swept([], "nothing at all", minimum=1)
        list(empty)
        with self.assertRaises(AssertionError) as cm:
            empty.check(self)
        self.assertIn("examined 0 item", str(cm.exception))

    @guarantees("G-SWEEP-NONEMPTY")
    def test_a_sweep_below_its_floor_fails(self):
        # [COER-SWEPT-FLOOR] a sweep that shrank to a third still examined something, and "something" is
        #   the bar that let the three broken guards through. The floor is what makes it a real check.
        short = Swept([1, 2, 3], "three items", minimum=30)
        list(short)
        with self.assertRaises(AssertionError):
            short.check(self)
        self.assertEqual(short.count, 3)

    @guarantees("G-SWEEP-NONEMPTY")
    def test_a_sweep_cannot_declare_a_floor_of_zero(self):
        # [COER-SWEPT-ZERO] minimum=0 would be the loophole: it turns the counter back into decoration.
        with self.assertRaises(ValueError):
            Swept([], "anything", minimum=0)


class TestValorNaoVazaNaSerializacao(unittest.TestCase):
    """EN: the promise is that a Match can reach a log, a traceback or a monitoring event without carrying
    the identifier. repr() honoured it and two standard serialisers walked around it."""

    @guarantees("G-SERIALISE-HIDES")
    def test_asdict_and_vars_refuse_instead_of_handing_over_the_value(self):
        # [COER-SERIAL] EN: this fails against any version where Match is a plain dataclass. A structured
        #   logging library calls dataclasses.asdict or vars, not repr, so hiding the value from repr alone
        #   left the control open on the path that actually reaches a log pipeline.
        import dataclasses

        from tarja import find

        match = find("CPF 529.982.247-25")[0]
        self.assertEqual(match.value, "529.982.247-25", "the value must still be reachable on purpose")
        with self.assertRaises(TypeError, msg="dataclasses.asdict must not return the identifier"):
            dataclasses.asdict(match)
        with self.assertRaises(TypeError, msg="vars() must not return the identifier"):
            vars(match)
        for text in (repr(match), str(match), f"{match}"):
            self.assertNotIn("529", text)
        self.assertNotIn("value", match.to_dict(include_value=False))

    def test_the_match_contract_the_rewrite_had_to_keep(self):
        # [COER-SERIAL-CONTRACT] EN: dropping the dataclass decorator hands back __eq__, __hash__ and
        #   immutability, so they are written out and pinned here. A silent loss of __eq__ would make every
        #   assertEqual on a list of Match compare by identity and pass for the wrong reason.
        from tarja import find

        a, b = find("CPF 529.982.247-25")[0], find("CPF 529.982.247-25")[0]
        self.assertIsNot(a, b)
        self.assertEqual(a, b)
        self.assertEqual(len({a, b}), 1, "equal Matches must hash the same")
        self.assertNotEqual(a, "not a match")
        with self.assertRaises(AttributeError):
            a.entity = "BR_CNPJ"


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
