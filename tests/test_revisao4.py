# tests/test_revisao4.py
# [R4] 4th code review, 29/09/2026. A key-provider proposal and a canary proposal were both rejected, and
#   these defects turned up while reviewing them. Every test here is a regression test for one.

import io
import pathlib
import secrets
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import tarja
from tarja.cli import main
from tarja.mask import check_salt
from tarja.vault import Vault

REAL_KEY = bytes.fromhex("11223344556677889900aabbccddeeff") * 2
CEP = "Endereco: CEP 22250-040, Rio de Janeiro.\n"
BAD_CPF_TEXT = "CPF 111.222.333-44 do cliente.\n"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(argv, stdin=""):
    # [B4-RUN] run main() capturing stdout/stderr
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def run_exit(argv, stdin=""):
    # [B4-RUN] run main() expecting argparse to exit, returning (code, stdout + stderr). argparse writes
    #   errors to stderr and --help to stdout, so both are returned joined.
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
        try:
            main(argv)
        except SystemExit as exc:
            return (exc.code or 0), out.getvalue() + err.getvalue()
    raise AssertionError(f"expected SystemExit for {argv}")


class TestVaultChecksItsKey(unittest.TestCase):
    """[B4-VAULT-KEY] Vault(key=...) has to refuse exactly what mask(salt=...) refuses. The reversible path
    carries the higher consequence, so it cannot be the path without the guard.
    """

    def test_refuses_low_entropy_key(self):
        with self.assertRaises(ValueError) as cm:
            Vault(key=b"\x00" * 32)
        self.assertIn("distinct bytes", str(cm.exception))

    def test_refuses_placeholder_key_in_portuguese(self):
        # guarantee: G-SALT-WEAK
        for weak in (b"senha", "chave-secreta-de-teste", "minha-senha-do-cofre-123456"):
            with self.subTest(weak=weak), self.assertRaises(ValueError) as cm:
                Vault(key=weak)
            self.assertIn("placeholder", str(cm.exception))

    def test_refuses_short_key(self):
        with self.assertRaises(ValueError) as cm:
            Vault(key=b"1f2e3d4c")
        self.assertIn("16 bytes", str(cm.exception))

    def test_refuses_empty_key_instead_of_generating_one(self):
        # [B4-EMPTY] b"" used to be falsy and silently became os.urandom(32), so a caller who lost their key
        #   got working tokens that joined with nothing. Fail loudly instead.
        for empty in (b"", ""):
            with self.subTest(empty=empty), self.assertRaises(ValueError):
                Vault(key=empty)

    def test_key_none_still_generates_and_is_not_validated(self):
        a, b = Vault(), Vault()
        self.assertNotEqual(a.key_id, b.key_id)
        self.assertRegex(a.key_id, r"^[0-9a-f]{4}$")

    def test_str_key_is_accepted_like_mask(self):
        key = secrets.token_hex(32)
        self.assertEqual(Vault(key=key).key_id, Vault(key=key.encode()).key_id)

    def test_same_guard_as_mask(self):
        # [B4-PARITY] the two entry points must agree, value by value, or a caller learns the wrong rule
        for candidate in (b"\x00" * 32, b"senha", b"x", REAL_KEY, secrets.token_bytes(32)):
            with self.subTest(candidate=candidate[:8]):
                try:
                    check_salt(candidate)
                except ValueError:
                    with self.assertRaises(ValueError):
                        Vault(key=candidate)
                else:
                    Vault(key=candidate)


class TestGateIsNotOpenedByTheReportFilter(unittest.TestCase):
    """[B4-GATE] a report filter must not decide the exit code. Until 0.8.0 --min-score 0.9 hid a BR_CEP
    scoring 0.50 AND turned exit 1 into exit 0, so `tarja scan f.txt && send.sh` sent the file.
    """

    def test_threshold_does_not_open_the_gate(self):
        # guarantee: G-EXIT-THRESHOLD
        code, out, _ = run(["scan", "-"], stdin=CEP)
        self.assertEqual(code, 1)
        self.assertIn("BR_CEP", out)
        code, out, _ = run(["scan", "-", "--report-min-score", "0.9"], stdin=CEP)
        self.assertEqual(code, 1, "raising the report threshold must not open the gate")
        self.assertEqual(out, "", "the finding is below the threshold, so it is not reported")

    def test_gate_still_zero_when_really_clean(self):
        code, out, _ = run(["scan", "-", "--report-min-score", "0.9"], stdin="nada aqui, sem numero\n")
        self.assertEqual((code, out), (0, ""))

    def test_suspect_survives_the_threshold_in_report_and_gate(self):
        # [B4-GATE] a suspect always scores 0 and is never filtered out by a threshold
        code, out, _ = run(["scan", "-", "--suspect", "--report-min-score", "1.0"], stdin=BAD_CPF_TEXT)
        self.assertEqual(code, 1)
        self.assertIn("BR_CPF", out)

    def test_old_name_warns_on_stderr_and_still_gates(self):
        code, out, err = run(["scan", "-", "--min-score", "0.9"], stdin=CEP)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("--min-score was renamed", err)
        self.assertIn("1.0.0", err)

    def test_both_names_at_once_is_an_error(self):
        code, _, err = run(["scan", "-", "--min-score", "0.9", "--report-min-score", "0.5"], stdin=CEP)
        self.assertEqual(code, 2)
        self.assertIn("not both", err)

    def test_abbreviations_still_resolve(self):
        # [B4-PREFIX] --report-min-score shares no prefix with --min-score, so no abbreviation moved target
        self.assertEqual(run(["scan", "-", "--min", "0.9"], stdin=CEP)[0], 1)
        self.assertEqual(run(["scan", "-", "--report", "0.9"], stdin=CEP)[0], 1)


class TestMaskTakesNoThreshold(unittest.TestCase):
    """[B4-MASK] `mask --min-score 0.9` used to leave a 0.50 BR_CEP unmasked in the output file, exit 0. The
    threshold flags now live on the scan subparser only, so mask does not advertise them in --help and
    argparse refuses them before any masking happens.
    """

    def test_mask_has_no_threshold_flag_at_all(self):
        # guarantee: G-MASK-NO-THRESHOLD
        for flag in ("--min-score", "--report-min-score"):
            for value in ("0", "0.9"):
                with self.subTest(flag=flag, value=value):
                    code, err = run_exit(["mask", "-", flag, value], stdin=CEP)
                    self.assertEqual(code, 2)
                    self.assertIn("unrecognized arguments", err)

    def test_mask_help_does_not_advertise_a_threshold(self):
        code, out = run_exit(["mask", "--help"])
        self.assertEqual(code, 0)
        self.assertNotIn("min-score", out)

    def test_scan_help_does_advertise_it(self):
        code, out = run_exit(["scan", "--help"])
        self.assertEqual(code, 0)
        self.assertIn("--report-min-score", out)

    def test_mask_without_a_threshold_masks(self):
        code, out, err = run(["mask", "-"], stdin=CEP)
        self.assertEqual(code, 0)
        self.assertIn("<BR_CEP>", out)
        self.assertEqual(err, "")


class TestMaskDoesNotLeakSuspectsSilently(unittest.TestCase):
    """[B4-SUSPECT] mask forced report_invalid=False, so a CPF with a wrong check digit left mask in
    cleartext, with exit 0, and residual() called the file clean: a green light over personal data.
    """

    def test_mask_warns_about_unmasked_suspects(self):
        # guarantee: G-SUSPECT-VISIBLE
        code, out, err = run(["mask", "-"], stdin=BAD_CPF_TEXT)
        self.assertEqual(code, 0)
        self.assertEqual(out, BAD_CPF_TEXT, "a suspect is not masked by default")
        self.assertIn("tarja: warning:", err)
        self.assertIn("1 ID-shaped value", err)

    def test_mask_suspect_masks_them_and_says_nothing(self):
        code, out, err = run(["mask", "-", "--suspect"], stdin=BAD_CPF_TEXT)
        self.assertEqual((code, out), (0, "CPF <BR_CPF> do cliente.\n"))
        self.assertEqual(err, "")

    def test_no_false_alarm_on_ordinary_text(self):
        code, _, err = run(["mask", "-"], stdin="cpf 529.982.247-25 e nada mais\n")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_residual_can_see_suspects(self):
        # guarantee: G-RESIDUAL-SEES-SUSPECT
        text = "CPF 111.222.333-44 do cliente."
        self.assertEqual(tarja.residual(text), [])
        found = tarja.residual(text, report_invalid=True)
        self.assertEqual([(m.entity, m.valid_dv) for m in found], [("BR_CPF", False)])

    def test_residual_keeps_valid_dv_on_the_rebuilt_match(self):
        # [B4-RESIDUAL-DV] residual() rebuilds every Match to restore the original offsets, and dropped
        #   valid_dv while doing it, which relabelled a suspect as valid
        found = tarja.residual("CPF 111.222.333-44", report_invalid=True)
        self.assertFalse(found[0].valid_dv)


class TestScoreFlagValidation(unittest.TestCase):
    """[B4-SCORE] type=float accepted "nan", and NaN makes every comparison False, so --min-score nan
    silently dropped every finding and returned exit 0. A check a typo can disable is not a check.
    """

    def test_nan_inf_and_out_of_range_are_refused(self):
        # guarantee: G-SCORE-ARG
        for flag in ("--min-score", "--report-min-score"):
            for value in ("nan", "NaN", "inf", "1.5", "5", "abc"):
                with self.subTest(flag=flag, value=value):
                    code, err = run_exit(["scan", "-", flag, value], stdin=CEP)
                    self.assertEqual(code, 2)
                    self.assertIn("between 0.0 and 1.0", err)
            # [B4-SCORE-ARGPARSE] a leading minus and an empty string are refused by argparse before _score
            #   ever sees them, so only the exit code is asserted there
            for value in ("-1", "-inf", ""):
                with self.subTest(flag=flag, value=value):
                    self.assertEqual(run_exit(["scan", "-", flag, value], stdin=CEP)[0], 2)

    def test_valid_range_is_accepted(self):
        for value in ("0", "0.0", "0.5", "1", "1.0"):
            with self.subTest(value=value):
                self.assertEqual(run(["scan", "-", "--report-min-score", value], stdin=CEP)[0], 1)

    def test_max_mb_refuses_inf_nan_and_non_positive(self):
        # guarantee: G-SIZE-CAP
        # [B4-MAXMB] the score flags were hardened and --max-mb was left with a bare type=float. "inf" made
        #   int(inf * 1024 * 1024) raise OverflowError, which is not in main's except clause, so the user
        #   got a traceback and exit 1, indistinguishable from "personal data found". "-1" produced the
        #   message "input larger than -1 MB".
        for value in ("inf", "nan", "0", "abc", "2000"):
            with self.subTest(value=value):
                code, err = run_exit(["scan", "-", "--max-mb", value], stdin=CEP)
                self.assertEqual(code, 2)
                self.assertIn("positive number of megabytes", err)
        for value in ("-1", "-inf"):
            with self.subTest(value=value):
                self.assertEqual(run_exit(["scan", "-", "--max-mb", value], stdin=CEP)[0], 2)

    def test_max_mb_still_accepts_a_real_size(self):
        self.assertEqual(run(["scan", "-", "--max-mb", "0.5"], stdin=CEP)[0], 1)
        code, _, err = run(["scan", "-", "--max-mb", "0.000001"], stdin=CEP)
        self.assertEqual(code, 2, "a cap below the input size must still be enforced")
        self.assertIn("input larger than", err)


class TestThresholdOnlyRemoves(unittest.TestCase):
    """[B4-MONOTONE] the CLI now filters the report AFTER resolve_overlaps, which is only safe while raising
    the threshold can never REVEAL a match. It holds while the lowest N1 score (0.80) stays above the highest
    N2 score (0.70), so a tier winner never scores below an overlapping loser. Scope: the 17 built-in
    entities. An entity registered through register_entity() with an N1 score below an overlapping N2 score
    breaks the property and this test does NOT catch it. The real fix is a check inside register_entity().
    """

    TEXT = (
        "Oficio 123/2026. Contato: telefone (21) 3232-4545. Veiculo placa ABC1D23. "
        "Empresa CNPJ 45.997.418/0001-53. CEP 20031-170. Imovel matricula 167 no Registro de Imoveis. "
        "CPF 529.982.247-25."
    )

    def test_raising_the_threshold_never_adds_a_match(self):
        # guarantee: G-OVERLAP-ONE
        base = {(m.entity, m.start, m.end) for m in tarja.find(self.TEXT)}
        for threshold in (0.35, 0.45, 0.55, 0.60, 0.75, 0.90, 1.0):
            raised = {(m.entity, m.start, m.end) for m in tarja.find(self.TEXT, min_score=threshold)}
            self.assertTrue(raised <= base, f"min_score={threshold} added: {raised - base}")


class TestShippedExamplesAreNotTheAntiPattern(unittest.TestCase):
    """[B4-EXAMPLE] examples/rag_pipeline.py defaulted the corpus key to "00" * 32 and called
    residual(min_score=0.5) a fail-closed gate. It is the file people copy into a real ingestion job.
    """

    def _source(self):
        path = ROOT / "examples" / "rag_pipeline.py"
        if not path.exists():  # pragma: no cover
            self.skipTest("examples/ not present in this install")
        return path.read_text(encoding="utf-8")

    def test_example_has_no_default_corpus_key(self):
        source = self._source()
        self.assertNotIn("bytes.fromhex(os.environ.get(", source, "the example carries a default key again")
        self.assertIn("TARJA_CORPUS_KEY", source)
        self.assertIn("raise SystemExit", source)

    def test_example_gate_takes_no_threshold(self):
        source = self._source()
        self.assertNotIn("residual(safe, min_score", source, "the ingestion gate took a threshold again")
        self.assertNotIn("residual(prompt, min_score", source, "the prompt gate took a threshold again")

    def test_readme_does_not_teach_the_threshold_as_a_gate(self):
        # [B4-README] the first version of this test excused any line containing "&&", which is exactly the
        #   shape the CHANGELOG calls vulnerable, so it passed on the one case it existed to catch. Every
        #   `tarja scan` line is checked now, with no exception.
        readme = ROOT / "README.md"
        if not readme.exists():  # pragma: no cover
            self.skipTest("README.md not present in this install")
        checked = 0
        for line in readme.read_text(encoding="utf-8").splitlines():
            if "tarja scan" not in line:
                continue
            checked += 1
            self.assertNotIn("--min-score", line, f"README teaches a threshold on a scan: {line!r}")
        self.assertGreater(checked, 0, "no `tarja scan` line found, the test would pass vacuously")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
