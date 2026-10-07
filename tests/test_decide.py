# tests/test_decide.py
# [DEC] the fail-closed primitive. Until 0.12.0 the only way to ask "may this text leave" was the exit code
#   of `tarja scan`, so a public promise about blocking applied to the command line and to nothing that
#   `import tarja` could reach.

import unittest

from _guarantees import guarantees

import tarja
from tarja.decide import Decision

VALID_CPF = "CPF 529.982.247-25"
BAD_DV_CPF = "CPF 111.444.777-36"
CLEAN = "Prezado cliente, seu pedido foi entregue na data combinada."


class TestDecideBlocksSuspectByDefault(unittest.TestCase):
    """[DEC-SUSPECT] the policy difference against `tarja scan` is deliberate and documented. This is the
    test that pins the default, because a default nobody pins is a default that drifts.
    """

    @guarantees("G-DECIDE-BLOCKS-SUSPECT")
    def test_a_suspect_alone_blocks(self):
        d = tarja.decide(BAD_DV_CPF)
        self.assertFalse(d, "a value whose check digit fails must not pass by default")
        self.assertFalse(d.allowed)
        self.assertEqual([m.valid_dv for m in d.blocked_by], [False])

    def test_allowing_a_suspect_takes_an_explicit_word(self):
        self.assertTrue(tarja.decide(BAD_DV_CPF, on_suspect="allow"))
        # and the word is checked, so a typo does not silently fall back to the default
        with self.assertRaises(ValueError):
            tarja.decide(BAD_DV_CPF, on_suspect="permitir")

    def test_a_threshold_cannot_open_the_gate_on_a_suspect(self):
        # [DEC-THRESHOLD] a suspect always scores 0. If min_score filtered it, raising a display threshold
        #   would open the gate, which is the exact class of defect that renamed --min-score in 0.8.0.
        self.assertFalse(tarja.decide(BAD_DV_CPF, min_score=0.99))

    def test_a_valid_identifier_blocks_and_clean_text_passes(self):
        self.assertFalse(tarja.decide(VALID_CPF))
        self.assertTrue(tarja.decide(CLEAN))


class TestDecisionIsHonestInAnIf(unittest.TestCase):
    """[DEC-BOOL] the object is meant to be used inside `if not decide(text)`. If __bool__ lies, every
    caller silently stops gating while every attribute assertion keeps passing.
    """

    @guarantees("G-DECIDE-FALSY-WHEN-BLOCKED")
    def test_blocked_is_falsy_and_allowed_is_truthy(self):
        blocked, allowed = tarja.decide(VALID_CPF), tarja.decide(CLEAN)
        self.assertFalse(bool(blocked))
        self.assertTrue(bool(allowed))
        # written as the caller writes it, not as an attribute read
        taken = []
        for text in (VALID_CPF, CLEAN):
            if not tarja.decide(text):
                taken.append(text)
        self.assertEqual(taken, [VALID_CPF])

    def test_the_reason_never_carries_the_value(self):
        d = tarja.decide(VALID_CPF)
        for shown in (d.reason(), repr(d), str(d)):
            with self.subTest(shown=shown[:30]):
                self.assertNotIn("529.982.247-25", shown)
                self.assertNotIn("52998224725", shown)
        self.assertIn("BR_CPF", d.reason())

    def test_decision_is_immutable_and_has_no_dict(self):
        d = tarja.decide(CLEAN)
        with self.assertRaises(AttributeError):
            d.allowed = True
        with self.assertRaises(TypeError):
            vars(d)


class TestRequireClean(unittest.TestCase):
    """[DEC-RAISE] same engine, exception ergonomics, for code that would rather not branch."""

    def test_it_raises_with_the_decision_attached(self):
        with self.assertRaises(tarja.BlockedError) as ctx:
            tarja.require_clean(VALID_CPF)
        self.assertIsInstance(ctx.exception.decision, Decision)
        self.assertFalse(ctx.exception.decision.allowed)
        self.assertNotIn("529.982.247-25", str(ctx.exception))

    def test_it_is_silent_on_clean_text(self):
        self.assertIsNone(tarja.require_clean(CLEAN))

    def test_it_honours_the_same_policy_as_decide(self):
        # one engine, so a divergence here means two policies to keep in sync, which is the bug
        self.assertIsNone(tarja.require_clean(BAD_DV_CPF, on_suspect="allow"))
        with self.assertRaises(tarja.BlockedError):
            tarja.require_clean(BAD_DV_CPF)


class TestScanKeepsItsOwnPolicy(unittest.TestCase):
    """[DEC-COHERENCE] the two differ on purpose. This test exists so that a future change which quietly
    aligns them fails loudly, in either direction.
    """

    def test_the_two_policies_are_different_and_that_is_the_documented_state(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest import mock

        from tarja.cli import main

        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(BAD_DV_CPF + "\n")), redirect_stdout(out), redirect_stderr(err):
            code = main(["scan", "-"])
        self.assertEqual(code, 0, "scan keeps exiting 0 on a suspect, see docs/decisions.md")
        self.assertFalse(tarja.decide(BAD_DV_CPF), "decide blocks it")
        # and the warning says the consequence, not just the count
        warning = err.getvalue()
        self.assertIn("93%", warning)
        self.assertIn("--fail-on-suspect", warning)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
