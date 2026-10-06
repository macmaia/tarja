# tests/test_revisao5.py
# [R5] 5th code review, 02 and 03/10/2026. The round started from the stated promises alone, with no access
#   to the code, and three of the defects below had survived 97.97% line coverage and 71 killed mutants. The
#   reason they survived is the same every time: coverage asks whether a line ran, mutation asks whether a
#   test would notice it changing, and neither asks what the promise actually was.

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _guarantees import guarantees

import tarja
from tarja.cli import main

VALID_CPF = "529.982.247-25"
VALID_CPF_DIGITS = "52998224725"
BAD_DV_CPF = "111.444.777-36"


def run(argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    with unittest.mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestMaskLeavesNothingBehind(unittest.TestCase):
    """[R5-MASK-SUSPECT] mask() defaulted to report_invalid=False, so a value with a failing check digit
    stayed in the returned text WHILE THE CALL SUCCEEDED. The caller had no way to know, because the only
    signal was a warning on stderr from the CLI, and stderr is not what a pipeline keeps.
    """

    @guarantees("G-MASK-NO-SUSPECT-LEFT")
    def test_no_identifier_shaped_value_survives_mask(self):
        text = f"CPF {BAD_DV_CPF} e CPF {VALID_CPF}"
        out = tarja.mask(text)
        for digits in (BAD_DV_CPF, VALID_CPF, "111444777", "529982247"):
            with self.subTest(digits=digits):
                self.assertNotIn(digits, out)

    def test_the_old_behaviour_is_still_reachable_on_purpose(self):
        # [R5-MASK-ESCAPE] the escape hatch is explicit and typed. A caller who wants a suspect left alone
        #   says so in the call, which is a different thing from a default nobody reads.
        self.assertIn(BAD_DV_CPF, tarja.mask(f"CPF {BAD_DV_CPF}", report_invalid=False))

    def test_masking_twice_changes_nothing(self):
        once = tarja.mask(f"CPF {BAD_DV_CPF} e CPF {VALID_CPF}")
        self.assertEqual(tarja.mask(once), once)


class TestBuiltInEntitiesCannotBeSwapped(unittest.TestCase):
    """[R5-REPLACE] unregister_entity refused to remove a built-in, which made the promise look kept, while
    register_entity(..., replace=True) walked in through the next door and kept the BR_CPF id with a
    validator of the caller's choosing. A guarantee enforced on one of two doors is not enforced.
    """

    @guarantees("G-BUILTIN-NOT-REPLACEABLE")
    def test_a_builtin_cannot_be_replaced(self):
        for eid in ("BR_CPF", "BR_CNPJ", "BR_CARTAO"):
            with self.subTest(entity=eid):
                with self.assertRaises(ValueError) as ctx:
                    tarja.register_entity(
                        eid, [("x", r"\b\d{11}\b", 0.9)], tier="N1", validator=lambda v: True, replace=True
                    )
                self.assertIn("built in", str(ctx.exception))
        # the real validator is still the one deciding
        self.assertEqual([m.valid_dv for m in tarja.find(f"CPF {BAD_DV_CPF}", report_invalid=True)], [False])

    def test_a_custom_entity_can_still_be_replaced(self):
        # the guarantee is about built-ins, and it must not take the caller's own ids with it
        tarja.register_entity("R5_CODIGO", [("a", r"\b\d{9}\b", 0.5)], context_words=["codigo r5"])
        try:
            tarja.register_entity("R5_CODIGO", [("b", r"\b\d{8}\b", 0.5)], context_words=["codigo r5"],
                                  replace=True)  # fmt: skip
            self.assertEqual([p.name for p in tarja.ENTITIES["R5_CODIGO"].patterns], ["b"])
        finally:
            tarja.unregister_entity("R5_CODIGO")


class TestIdentifierGluedToOtherDigits(unittest.TestCase):
    """[R5-EMBEDDED] every pattern is anchored with a word boundary, so a valid CPF with a digit stuck to it
    returned NOTHING, not even a suspect, and `scan` called the file clean. In a database dump or a
    concatenated log that is the ordinary shape of the data, not an exotic one.
    """

    @guarantees("G-EMBEDDED-LABELLED-RUN")
    def test_a_labelled_run_is_found(self):
        for text in (
            f"cpf 00{VALID_CPF_DIGITS}",
            f"cpf {VALID_CPF_DIGITS}00",
            f"cpf,nome\n00{VALID_CPF_DIGITS},Ana",
        ):
            with self.subTest(text=text):
                found = [(m.entity, m.value) for m in tarja.find(text)]
                self.assertIn(("BR_CPF", VALID_CPF_DIGITS), found)
        # and it is actually removed, not merely reported
        self.assertNotIn(VALID_CPF_DIGITS, tarja.mask(f"cpf 00{VALID_CPF_DIGITS}"))

    def test_an_unlabelled_run_stays_a_documented_limit(self):
        # [R5-EMBEDDED-LIMIT] without the context word the window keeps only the check digit as a filter,
        #   and that is not enough: 90.1% of random 24-digit runs produced a false finding, measured
        #   03/10/2026 over 2000 draws per length. So the unlabelled run is NOT detected, on purpose, and
        #   this test pins the trade-off rather than leaving it to be rediscovered as a bug.
        self.assertEqual(tarja.find(f"registro interno 00{VALID_CPF_DIGITS} fim"), [])

    def test_a_long_number_that_is_not_an_identifier_is_left_alone(self):
        for text in ("protocolo 1002003004005005", "trace id 123e4567-e89b-42d3-a456-426614174000"):
            with self.subTest(text=text):
                self.assertEqual([m.entity for m in tarja.find(text)], [])

    def test_the_window_does_not_dig_inside_another_valid_identifier(self):
        # a PIX key is a UUID, and its tail `426614174000` carries a valid NIS. The NIS used to win the
        # overlap and ERASE the PIX key, which trades a false negative of one entity for a false positive
        # of another, the worst of the two outcomes.
        uuid = "123e4567-e89b-42d3-a456-426614174000"
        self.assertEqual([m.entity for m in tarja.find(f"chave pix {uuid}")], ["BR_PIX_EVP"])


class TestTheConservativeGateExists(unittest.TestCase):
    """[R5-FAIL-ON-SUSPECT] the documented `tarja scan f.txt && send.sh` idiom could not be made to block on
    a value whose check digit fails. The default exit code stays as decided (accepted risk, see
    docs/decisions.md). What was missing was any way at all to opt out of that risk.
    """

    @guarantees("G-SUSPECT-EXIT")
    def test_fail_on_suspect_blocks_the_send(self):
        text = f"CPF {BAD_DV_CPF} apenas\n"
        self.assertEqual(run(["scan", "-"], stdin=text)[0], 0, "the default is unchanged")
        self.assertEqual(run(["scan", "-", "--fail-on-suspect"], stdin=text)[0], 1)

    def test_the_flag_changes_the_exit_code_and_not_the_report(self):
        text = f"CPF {BAD_DV_CPF} apenas\n"
        plain = run(["scan", "-"], stdin=text)[1]
        gated = run(["scan", "-", "--fail-on-suspect"], stdin=text)[1]
        self.assertEqual(plain, gated, "a gate must not change what is displayed")

    def test_the_flag_does_not_invent_a_failure_on_clean_text(self):
        self.assertEqual(run(["scan", "-", "--fail-on-suspect"], stdin="nada aqui\n")[0], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
