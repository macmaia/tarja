# tests/test_board3.py
# [TEST-BOARD3] the four defects the third review board confirmed on 24/09/2026, one test class each.
#   Each test fails against the code as it was before the fix, which is the only reason to write it.

from __future__ import annotations

import io
import logging
import time
import unittest

import tarja
from tarja.detect import MAX_CHARS, Match, resolve_overlaps

CPF = "529.982.247-25"


class TestMatchNeverPrintsTheValue(unittest.TestCase):
    """A1: the default dataclass repr put the identifier into every log line and traceback."""

    def setUp(self) -> None:
        self.match = tarja.find(f"CPF {CPF}")[0]

    def test_repr_hides_the_value(self) -> None:
        # [TEST-A1-REPR]
        self.assertNotIn(CPF, repr(self.match))
        self.assertNotIn("52998224725", repr(self.match))
        self.assertIn("BR_CPF", repr(self.match))

    def test_str_hides_the_value(self) -> None:
        # [TEST-A1-STR] str falls back to __repr__, and f-strings use str
        self.assertNotIn(CPF, str(self.match))
        self.assertNotIn(CPF, f"{self.match}")

    def test_a_list_of_matches_hides_the_values(self) -> None:
        # [TEST-A1-LIST] printing the result of find() is the commonest way this leaked
        self.assertNotIn(CPF, str(tarja.find(f"CPF {CPF}")))

    def test_logging_the_result_does_not_leak(self) -> None:
        # [TEST-A1-LOG] the exact call the README forbids, now safe by construction
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        log = logging.getLogger("tarja.test.board3")
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        self.addCleanup(log.removeHandler, handler)
        log.info("achados: %s", tarja.find(f"CPF {CPF}"))
        self.assertNotIn(CPF, buf.getvalue())
        self.assertIn("BR_CPF", buf.getvalue())

    def test_a_suspect_also_hides_its_value(self) -> None:
        # [TEST-A1-SUSPECT] a suspect is near-personal-data, so it must not leak through repr either
        suspect = tarja.find("cpf 529.982.247-24", report_invalid=True)[0]
        self.assertFalse(suspect.valid_dv)
        self.assertNotIn("529.982.247-24", repr(suspect))
        self.assertIn("SUSPECT", repr(suspect))

    def test_the_value_is_still_reachable_on_purpose(self) -> None:
        # [TEST-A1-STILL-THERE] hidden from printing, not removed: asking for it still works
        self.assertEqual(self.match.value, CPF)
        self.assertEqual(self.match.to_dict()["value"], CPF)
        self.assertNotIn("value", self.match.to_dict(include_value=False))


class TestOverlapResolutionScales(unittest.TestCase):
    """A2: comparing each candidate against every kept match made this quadratic."""

    def test_same_result_as_the_naive_rule_on_random_overlaps(self) -> None:
        # [TEST-A2-EQUIV] the sweep must decide exactly what the all-pairs rule decided. Real text rarely
        #   overlaps, so this builds spans that do, at random, and compares the two rules on 200 draws.
        import random

        from tarja.entities import TIER_RANK

        order = {e: i for i, e in enumerate(tarja.ENTITIES)}
        ids = list(tarja.ENTITIES)[:5]

        def sort_key(m: Match) -> tuple:
            return (TIER_RANK.get(m.tier, 9), -m.score, -(m.end - m.start), order.get(m.entity, 99), m.start)

        rng = random.Random(20260924)
        for draw in range(200):
            spans = []
            for _ in range(rng.randint(2, 25)):
                start = rng.randint(0, 60)
                end = start + rng.randint(1, 12)
                eid = rng.choice(ids)
                spans.append(
                    Match(eid, start, end, "x" * (end - start), round(rng.uniform(0.1, 1.0), 2),
                          tarja.ENTITIES[eid].tier, "p", bool(rng.getrandbits(1)))
                )  # fmt: skip
            naive: list[Match] = []
            for m in sorted(spans, key=sort_key):
                if all(m.end <= k.start or m.start >= k.end for k in naive):
                    naive.append(m)
            expected = sorted((m.start, m.end, m.entity) for m in naive)
            got = [(m.start, m.end, m.entity) for m in resolve_overlaps(spans)]
            self.assertEqual(got, expected, f"divergiu no sorteio {draw}")

    def test_result_is_sorted_and_does_not_overlap(self) -> None:
        # [TEST-A2-INVARIANT]
        kept = tarja.find("CPF 529.982.247-25 " * 200)
        self.assertEqual(kept, sorted(kept, key=lambda m: (m.start, m.end)))
        for a, b in zip(kept, kept[1:], strict=False):
            self.assertLessEqual(a.end, b.start)

    def test_dense_input_stays_roughly_linear(self) -> None:
        # [TEST-A2-SCALE] four times the input must not cost anywhere near sixteen times the time. Generous
        #   bound, because a shared runner is noisy: the bug being guarded here cost 93x for 16x.
        def took(n: int) -> float:
            text = f"CPF {CPF} " * n
            start = time.perf_counter()
            tarja.find(text)
            return time.perf_counter() - start

        small = max(took(1000), 1e-4)
        large = took(4000)
        self.assertLess(large / small, 8.0, f"escala ruim: {small:.3f}s -> {large:.3f}s")


class TestInputSizeLimit(unittest.TestCase):
    """A3: find() accepted any size, so a single request could hold a worker."""

    def test_over_the_limit_is_refused(self) -> None:
        # [TEST-A3-REFUSE]
        with self.assertRaises(ValueError) as ctx:
            tarja.find("a" * (MAX_CHARS + 1))
        self.assertIn("max_chars", str(ctx.exception))

    def test_the_limit_can_be_lifted_deliberately(self) -> None:
        # [TEST-A3-OPT-OUT]
        self.assertEqual(tarja.find("a" * (MAX_CHARS + 1), max_chars=None), [])

    def test_an_ordinary_document_is_untouched(self) -> None:
        # [TEST-A3-NORMAL] the ceiling must not be something a real document runs into
        self.assertEqual(len(tarja.find(f"CPF {CPF} " + "texto " * 10000)), 1)


class TestVaultReleasesExpiredValues(unittest.TestCase):
    """A4: the scope expired but the map kept the value in the clear for the life of the process."""

    def test_an_expired_scope_releases_its_value(self) -> None:
        # [TEST-A4-EXPIRY] this is the gap between declared retention and real retention
        vault = tarja.Vault(ttl=0.05)
        vault.protect(f"CPF {CPF}")
        self.assertEqual(len(vault), 1)
        time.sleep(0.1)
        self.assertEqual(vault.purge(), 1)
        self.assertEqual(len(vault), 0)

    def test_purge_runs_on_its_own(self) -> None:
        # [TEST-A4-AUTO] nobody should have to remember to call purge
        vault = tarja.Vault(ttl=0.05)
        vault.protect(f"CPF {CPF}")
        time.sleep(0.1)
        vault.protect("SUS 729 1417 7763 1701")
        self.assertEqual(len(vault), 1)

    def test_a_live_scope_keeps_its_value(self) -> None:
        # [TEST-A4-LIVE] purging must not break a scope that is still within its ttl
        vault = tarja.Vault(ttl=60)
        protected = vault.protect(f"CPF {CPF}")
        vault.purge()
        self.assertEqual(vault.reveal(protected, issued_by=protected), f"CPF {CPF}")

    def test_a_value_two_scopes_share_survives_the_first_expiry(self) -> None:
        # [TEST-A4-SHARED] same value, two documents: retiring one must not blind the other
        vault = tarja.Vault(ttl=None)
        first = vault.protect(f"CPF {CPF}")
        second = vault.protect(f"outro doc, CPF {CPF}")
        vault.forget(first)
        self.assertEqual(len(vault), 1)
        self.assertIn(CPF, vault.reveal(second, issued_by=second))

    def test_forget_releases_now(self) -> None:
        # [TEST-A4-FORGET] the explicit way out, for ttl=None
        vault = tarja.Vault(ttl=None)
        protected = vault.protect(f"CPF {CPF}")
        self.assertEqual(vault.forget(protected), 1)
        self.assertEqual(len(vault), 0)

    def test_forget_refuses_text_from_another_vault(self) -> None:
        # [TEST-A4-FORGET-SCOPE]
        mine, theirs = tarja.Vault(), tarja.Vault()
        protected = theirs.protect(f"CPF {CPF}")
        with self.assertRaises(tarja.VaultScopeError):
            mine.forget(protected)

    def test_a_never_expiring_scope_is_kept_on_purpose(self) -> None:
        # [TEST-A4-TTL-NONE] ttl=None means keep, and that must stay true
        vault = tarja.Vault(ttl=None)
        vault.protect(f"CPF {CPF}")
        self.assertEqual(vault.purge(), 0)
        self.assertEqual(len(vault), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class TestRevealToleratesOnlyReflow(unittest.TestCase):
    """B3: a model reflows a token across a line or upper-cases the hex. Nothing beyond that is accepted."""

    def setUp(self) -> None:
        import re

        self.vault = tarja.Vault()
        self.protected = self.vault.protect(f"Paciente CPF {CPF}")
        found = re.search(r"<BR_CPF:([0-9a-f]{4}):([0-9a-f]{24})>", self.protected)
        assert found is not None
        self.token, self.kid, self.digest = found.group(0), found.group(1), found.group(2)

    def revealed(self, text: str) -> bool:
        return CPF in self.vault.reveal(text, issued_by=self.protected, reuse=True)

    def test_the_untouched_token_resolves(self) -> None:
        # [TEST-B3-EXACT]
        self.assertTrue(self.revealed(f"resposta: {self.token}"))

    def test_upper_case_hex_resolves(self) -> None:
        # [TEST-B3-CASE] case carries no information in hex, so accepting it costs no entropy
        self.assertTrue(self.revealed(f"<BR_CPF:{self.kid.upper()}:{self.digest.upper()}>"))

    def test_a_token_broken_across_a_line_resolves(self) -> None:
        # [TEST-B3-REFLOW] the break lands mid-digest, which is where a model actually wraps
        self.assertTrue(self.revealed(self.token[:20] + "\n" + self.token[20:]))

    def test_a_token_spaced_out_resolves(self) -> None:
        # [TEST-B3-SPACES]
        spaced = " ".join(self.digest[i : i + 4] for i in range(0, 24, 4))
        self.assertTrue(self.revealed(f"<BR_CPF:{self.kid}:{spaced}>"))

    def test_a_missing_digit_does_not_resolve(self) -> None:
        # [TEST-B3-SHORT] tolerance stops at whitespace and case: entropy must not drop
        self.assertFalse(self.revealed(f"<BR_CPF:{self.kid}:{self.digest[:-1]}>"))

    def test_a_changed_digit_does_not_resolve(self) -> None:
        # [TEST-B3-FORGE] the forging attempt the decision was written to refuse
        flipped = self.digest[:-1] + ("0" if self.digest[-1] != "0" else "1")
        self.assertFalse(self.revealed(f"<BR_CPF:{self.kid}:{flipped}>"))

    def test_another_entity_does_not_resolve(self) -> None:
        # [TEST-B3-ENTITY] the entity is part of what was signed
        self.assertFalse(self.revealed(f"<BR_CNS:{self.kid}:{self.digest}>"))

    def test_residual_ignores_a_reflowed_token(self) -> None:
        # [TEST-B3-RESIDUAL] a token a model reflowed is still a token, not leftover personal data
        self.assertEqual(tarja.residual(self.token[:20] + "\n" + self.token[20:]), [])


class TestUnsafeRegexIsRefusedAtRegistration(unittest.TestCase):
    """B4: find() runs registered patterns on text a stranger submitted."""

    def tearDown(self) -> None:
        for eid in ("TEST_B4", "TEST_B4_OK"):
            if eid in tarja.ENTITIES:
                tarja.unregister_entity(eid)

    def test_ordinary_patterns_are_accepted(self) -> None:
        # [TEST-B4-SAFE] every built-in shape must keep passing, or the check is useless in practice
        for pattern in (r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", r"\bAC-\d{6}\b", r"[0-9a-f]{12}", r"(?:abc)+", r"(a|b|c)+"):
            with self.subTest(pattern=pattern):
                tarja.check_regex(pattern)

    def test_a_nested_quantifier_is_refused(self) -> None:
        # [TEST-B4-NESTED]
        for pattern in (r"(\d+)+", r"(\w+\s?)*$", r"([0-9]{1,30})+"):
            with self.subTest(pattern=pattern), self.assertRaises(tarja.UnsafeRegexError):
                tarja.check_regex(pattern)

    def test_a_repeated_alternation_with_equal_branches_is_refused(self) -> None:
        # [TEST-B4-DUP]
        for pattern in (r"(a|a)*b", r"(?:x|x)+"):
            with self.subTest(pattern=pattern), self.assertRaises(tarja.UnsafeRegexError):
                tarja.check_regex(pattern)

    def test_overlapping_branches_are_not_caught_and_that_is_documented(self) -> None:
        # [TEST-B4-LIMIT] pins the honest limit: accepting this is a known gap, not an oversight
        tarja.check_regex(r"(a|ab)*")

    def test_register_entity_refuses_and_the_escape_works(self) -> None:
        # [TEST-B4-REGISTER] refusal at registration, and the deliberate way past it
        with self.assertRaises(tarja.UnsafeRegexError):
            tarja.register_entity("TEST_B4", [("x", r"(\d+)+", 0.5)], context_words=["x"])
        self.assertNotIn("TEST_B4", tarja.ENTITIES)
        spec = tarja.register_entity("TEST_B4", [("x", r"(\d+)+", 0.5)], context_words=["x"], unsafe_regex=True)
        self.assertEqual(spec.id, "TEST_B4")

    def test_a_safe_custom_entity_still_registers_normally(self) -> None:
        # [TEST-B4-NO-REGRESSION] the check must not get in the way of the documented use
        tarja.register_entity("TEST_B4_OK", [("acme", r"\bAC-\d{6}\b", 0.3)], context_words=["matricula acme"])
        self.assertEqual(tarja.find("matricula acme AC-123456")[0].entity, "TEST_B4_OK")


class TestBoardReReview(unittest.TestCase):
    """What the board found on its own work, in the same session. Every one of these passed before the
    second look and failed the moment somebody asked for an example rather than a claim."""

    def test_an_exact_count_around_a_variable_repeat_is_refused(self) -> None:
        # [TEST-RR-EXACT] (\\d+){10} slipped through: an exact count was not treated as a repeat at all
        for pattern in (r"(\d+){10}", r"(\d+){2}"):
            with self.subTest(pattern=pattern), self.assertRaises(tarja.UnsafeRegexError):
                tarja.check_regex(pattern)

    def test_an_exact_count_inside_is_not_ambiguous(self) -> None:
        # [TEST-RR-INNER] (\\d{3}\\.){2} has exactly one parse, and refusing it taught people to reach for
        #   unsafe_regex=True by habit, which is how a check stops meaning anything
        tarja.check_regex(r"(\d{3}\.){2}")
        tarja.check_regex(r"(?:[0-9a-fA-F]){24}")

    def test_an_inner_range_that_cannot_vary_is_not_ambiguous(self) -> None:
        # [TEST-RR-RANGE] {2,5} inside a repeated group is ambiguous, {2,2} is not: it always consumes the
        #   same number of characters, so there is a single parse and nothing to backtrack over. A surviving
        #   mutant on 24/09/2026 showed no test could tell the two apart, which meant the distinction in the
        #   code was decoration. Either test it or delete it.
        tarja.check_regex(r"(\d{4,4}-){2}")
        tarja.check_regex(r"(\d{4}-){2}")
        with self.assertRaises(tarja.UnsafeRegexError):
            tarja.check_regex(r"(\d{2,5}-){2}")

    def test_a_malformed_quantifier_does_not_raise_from_the_checker(self) -> None:
        # [TEST-RR-MALFORMED] the checker used to raise "invalid literal for int()" on {2,abc}, which tells
        #   the caller nothing about their pattern. It must stay quiet and leave the pattern to re, which
        #   accepts {2,abc} as literal text rather than a quantifier. Writing this test is how we found that
        #   out: the first version assumed re would reject it, registered the entity for real, and broke two
        #   unrelated tests through the global registry. AD-05, in practice.
        tarja.check_regex(r"(\d+){2,abc}")
        self.addCleanup(lambda: tarja.unregister_entity("TEST_RR") if "TEST_RR" in tarja.ENTITIES else None)
        spec = tarja.register_entity("TEST_RR", [("x", r"AC(\d+){2,abc}", 0.5)], context_words=["x"])
        self.assertEqual(spec.id, "TEST_RR")

    def test_purge_does_not_walk_every_scope_on_every_protect(self) -> None:
        # [TEST-RR-PURGE-SCALE] the same quadratic shape as the overlap bug, in the code written to fix it:
        #   purge scanned the whole scope list on every protect. Sixteen times the documents must not cost
        #   anywhere near sixteen squared. Generous bound, shared runners are noisy.
        def took(n: int) -> float:
            vault = tarja.Vault(ttl=3600)
            start = time.perf_counter()
            for i in range(n):
                vault.protect(f"doc {i} CPF {CPF}")
            return time.perf_counter() - start

        small = max(took(200), 1e-4)
        large = took(1600)
        self.assertLess(large / small, 24.0, f"escala ruim: {small:.3f}s -> {large:.3f}s")

    def test_expiry_still_works_with_many_scopes(self) -> None:
        # [TEST-RR-PURGE-HEAP] the heap must not lose a deadline it has not reached yet
        vault = tarja.Vault(ttl=None)
        forever = vault.protect(f"eterno CPF {CPF}")
        short = tarja.Vault(ttl=0.05)
        short.protect("SUS 729 1417 7763 1701")
        time.sleep(0.1)
        self.assertEqual(short.purge(), 1)
        self.assertEqual(vault.reveal(forever, issued_by=forever), f"eterno CPF {CPF}")


class TestLazyFoldingIsEquivalent(unittest.TestCase):
    """E2: find() folds context windows on demand instead of folding the whole text. That is only correct
    because fold() is one character in, one character out, so this pins the property the optimisation rests
    on. If fold() ever grows or shrinks the string, these fail and the window slicing must go back."""

    def test_folding_a_slice_equals_slicing_the_fold(self) -> None:
        # [TEST-E2-INVARIANT]
        from tarja.normalise import fold, normalise_text

        texts = [
            "Paciente MARIA JOSÉ, CPF 529.982.247-25, Inscrição nº 1234",
            "AÇÃO ordinária, ÔNUS, coração, ÜBER, ﬁm",  # acentos e ligadura
            "ＣＰＦ １２３ CNPJ 12.ABC.345/01DE-35",  # largura inteira
            "linha um\nlinha dois\tcom tabulação\r\n",
        ]
        for text in texts:
            norm = normalise_text(text)
            whole = fold(norm)
            self.assertEqual(len(whole), len(norm), "fold mudou o comprimento")
            for start in range(0, len(norm), 3):
                for size in (1, 5, 17):
                    with self.subTest(text=text[:20], start=start, size=size):
                        self.assertEqual(fold(norm[start : start + size]), whole[start : start + size])

    def test_context_detection_is_unchanged(self) -> None:
        # [TEST-E2-BEHAVIOUR] the cases where context decides the score, across both context modes
        with_context = tarja.find("Inscrição: 1234 5678 9012, título de eleitor")
        self.assertTrue(any(m.has_context for m in with_context) or not with_context)
        cep = tarja.find("CEP 22290-140")
        self.assertTrue(all(m.has_context for m in cep if m.entity == "BR_CEP"))
        self.assertEqual(tarja.find("22290-140"), [])
