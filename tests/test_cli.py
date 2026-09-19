# tests/test_cli.py
# [TEST-CLI] EN: tests for the command line / PT: testes da linha de comando

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
    # [TEST-CLI] EN: run main() capturing stdout/stderr / PT: roda o main() capturando stdout/stderr
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestCLI(unittest.TestCase):
    def setUp(self):
        # EN: temp file with sample text / PT: arquivo temporario c/ texto de exemplo
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(T)

    def tearDown(self):
        os.remove(self.path)

    def test_scan_jsonl_hides_values(self):
        # [TEST-CLI] EN: default output has no raw value, exit 1 when found / PT: padrao sem valor cru, exit 1 qdo acha
        code, out, _ = run(["scan", self.path])
        rows = [json.loads(line) for line in out.splitlines()]
        self.assertEqual(code, 1)
        self.assertEqual([r["entity"] for r in rows], ["BR_CPF", "BR_CNPJ"])
        self.assertTrue(all("value" not in r for r in rows))

    def test_scan_show_values_and_table(self):
        # [TEST-CLI] EN: --show-values and --format table / PT: --show-values e --format table
        _, out, _ = run(["scan", self.path, "--show-values"])
        self.assertIn("529.982.247-25", out)
        _, out, _ = run(["scan", self.path, "--format", "table"])
        self.assertIn("**************", out)
        self.assertNotIn("529.982.247-25", out)
        _, out, _ = run(["scan", self.path, "--format", "table", "--show-values"])
        self.assertIn("529.982.247-25", out)

    def test_scan_stdin_filters_and_nothing_found(self):
        # [TEST-CLI] EN: stdin, --entities, --min-score, exit 0 when clean
        # [TEST-CLI] PT: stdin, --entities, --min-score, exit 0 qdo limpo
        code, out, _ = run(["scan", "-", "--entities", "br_cnpj"], stdin=T)
        self.assertEqual([json.loads(line)["entity"] for line in out.splitlines()], ["BR_CNPJ"])
        code, out, _ = run(["scan", "-"], stdin="nada aqui")
        self.assertEqual((code, out), (0, ""))

    def test_mask(self):
        # [TEST-CLI] EN: redact default, hash with salt / PT: redact padrao, hash c/ salt
        code, out, _ = run(["mask", self.path])
        self.assertEqual((code, out), (0, "cpf <BR_CPF> e cnpj <BR_CNPJ>\n"))
        _, out, _ = run(["mask", self.path, "--strategy", "hash", "--salt", "x"])
        self.assertIn("<BR_CPF:", out)

    def test_errors(self):
        # [TEST-CLI] EN: missing file, hash without salt, unknown entity -> exit 2 + message
        # [TEST-CLI] PT: arquivo inexistente, hash sem salt, entidade desconhecida -> exit 2 + msg
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TARJA_SALT", None)
            for argv in (
                ["scan", "/nao/existe.txt"],
                ["mask", self.path, "--strategy", "hash"],
                ["scan", self.path, "--entities", "BR_XYZ"],
            ):
                code, _, err = run(argv)
                self.assertEqual(code, 2, argv)
                self.assertTrue(err.startswith("tarja:"))


if __name__ == "__main__":
    unittest.main()
