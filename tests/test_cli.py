# tests/test_cli.py
# [TEST-CLI] tests for the command line

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from tarja.cli import main

T = "cpf 529.982.247-25 e cnpj 12.ABC.345/01DE-35\n"


def run(argv, stdin=""):
    # [TEST-CLI] run main() capturing stdout/stderr
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestCLI(unittest.TestCase):
    def setUp(self):
        # temp file with sample text
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(T)

    def tearDown(self):
        os.remove(self.path)

    def test_scan_jsonl_hides_values(self):
        # [TEST-CLI] default output has no raw value, exit 1 when found
        code, out, _ = run(["scan", self.path])
        rows = [json.loads(line) for line in out.splitlines()]
        self.assertEqual(code, 1)
        self.assertEqual([r["entity"] for r in rows], ["BR_CPF", "BR_CNPJ"])
        self.assertTrue(all("value" not in r for r in rows))

    def test_scan_show_values_and_table(self):
        # [TEST-CLI] --show-values and --format table
        _, out, _ = run(["scan", self.path, "--show-values"])
        self.assertIn("529.982.247-25", out)
        _, out, _ = run(["scan", self.path, "--format", "table"])
        self.assertIn("**************", out)
        self.assertNotIn("529.982.247-25", out)
        _, out, _ = run(["scan", self.path, "--format", "table", "--show-values"])
        self.assertIn("529.982.247-25", out)

    def test_scan_stdin_filters_and_nothing_found(self):
        # [TEST-CLI] stdin, --entities, --min-score, exit 0 when clean
        code, out, _ = run(["scan", "-", "--entities", "br_cnpj"], stdin=T)
        self.assertEqual([json.loads(line)["entity"] for line in out.splitlines()], ["BR_CNPJ"])
        code, out, _ = run(["scan", "-"], stdin="nada aqui")
        self.assertEqual((code, out), (0, ""))

    def test_mask(self):
        # [TEST-CLI] redact default, pseudonym_stable with a key
        code, out, _ = run(["mask", self.path])
        self.assertEqual((code, out), (0, "cpf <BR_CPF> e cnpj <BR_CNPJ>\n"))
        _, out, _ = run(["mask", self.path, "--strategy", "pseudonym_stable", "--salt", "7f3b9a1c5d2e8046"])
        self.assertIn("<BR_CPF:", out)

    def test_errors(self):
        # [TEST-CLI] missing file, no key, weak key, unknown entity -> exit 2 + message
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TARJA_SALT", None)
            for argv in (
                ["scan", "/nao/existe.txt"],
                ["mask", self.path, "--strategy", "pseudonym_stable"],
                ["mask", self.path, "--strategy", "pseudonym_stable", "--salt", "changeme"],
                ["scan", self.path, "--entities", "BR_XYZ"],
            ):
                code, _, err = run(argv)
                self.assertEqual(code, 2, argv)
                self.assertTrue(err.startswith("tarja:"))


class TestCLILimit(unittest.TestCase):
    # [TEST-CLI-LIMIT] input over --max-mb is refused with exit 2, under it works
    def test_over_limit(self):
        code, out, err = run(["scan", "-", "--max-mb", "0.00001"], stdin="x" * 100)
        self.assertEqual(code, 2)
        self.assertIn("larger than", err)
        self.assertEqual(out, "")

    def test_under_limit(self):
        code, _, _ = run(["scan", "-", "--max-mb", "1"], stdin=T)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
