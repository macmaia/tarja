"""EN: Tests for E9 (suspect format, card, vault, residual check).
PT: Testes do E9 (formato suspeito, cartao, cofre, verificacao residual).
"""

import io
import json
import unittest
from contextlib import redirect_stdout

import tarja
from tarja import Vault, cartao, residual
from tarja.cli import main

VALID_CPF = "529.982.247-25"
BAD_CPF = "529.982.247-24"


class TestSuspect(unittest.TestCase):
    # [TEST-E9-SUSPECT]
    def test_off_by_default(self):
        # EN: default output is unchanged / PT: saida padrao nao muda
        self.assertEqual(tarja.find(f"cpf {BAD_CPF}"), [])

    def test_reports_wrong_dv(self):
        found = tarja.find(f"cpf {BAD_CPF}", report_invalid=True)
        self.assertEqual(len(found), 1)
        m = found[0]
        self.assertEqual((m.entity, m.value, m.score, m.valid_dv), ("BR_CPF", BAD_CPF, 0.0, False))
        self.assertFalse(m.to_dict()["valid_dv"])

    def test_valid_and_suspect_together(self):
        found = tarja.find(f"cpf {BAD_CPF} e {VALID_CPF}", report_invalid=True)
        self.assertEqual([m.valid_dv for m in found], [False, True])

    def test_suspect_loses_to_valid_overlap(self):
        # EN: a valid match on the same span wins / PT: match valido no mesmo trecho ganha
        found = tarja.find(f"cpf {VALID_CPF}", report_invalid=True)
        self.assertTrue(all(m.valid_dv for m in found))

    def test_cli_flag(self):
        buf = io.StringIO()
        path = self._tmp(f"cpf {BAD_CPF}\n")
        with redirect_stdout(buf):
            code = main(["scan", path, "--suspect"])
        self.assertEqual(code, 1)
        row = json.loads(buf.getvalue().splitlines()[0])
        self.assertFalse(row["valid_dv"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(["scan", path]), 0)

    def _tmp(self, text):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(__import__("os").unlink, f.name)
        return f.name


class TestCartao(unittest.TestCase):
    # [TEST-E9-CARTAO] EN: public test PANs / PT: numeros de teste publicos
    def test_valid(self):
        for v in ("4111 1111 1111 1111", "5555555555554444", "3782 822463 10005", "4012888888881881"):
            self.assertTrue(cartao.is_valid(v), v)

    def test_invalid(self):
        for v in ("4111 1111 1111 1112", "0000000000000000", "411111111111", "4" * 20, ""):
            self.assertFalse(cartao.is_valid(v), v)

    def test_check_digit(self):
        self.assertEqual(cartao.luhn_check_digit("411111111111111"), "1")
        self.assertEqual(cartao.luhn_check_digit("7992739871"), "3")

    def test_detect(self):
        found = tarja.find("pago no cartao de credito 4111 1111 1111 1111")
        self.assertEqual([(m.entity, m.score) for m in found], [("BR_CARTAO", 0.95)])
        self.assertEqual(tarja.find("numero 4111 1111 1111 1112"), [])


class TestVault(unittest.TestCase):
    # [TEST-E9-VAULT]
    def test_round_trip(self):
        v = Vault(key=b"k" * 32)
        text = f"cpf {VALID_CPF} e cartao 4111 1111 1111 1111"
        prot = v.protect(text)
        self.assertNotIn(VALID_CPF, prot)
        self.assertNotIn("4111", prot)
        self.assertEqual(v.reveal(prot), text)
        self.assertEqual(len(v), 2)

    def test_deterministic_per_key(self):
        a, b = Vault(key=b"a" * 32), Vault(key=b"b" * 32)
        self.assertEqual(a.token("BR_CPF", VALID_CPF), a.token("BR_CPF", "52998224725"))
        self.assertNotEqual(a.token("BR_CPF", VALID_CPF), b.token("BR_CPF", VALID_CPF))

    def test_skips_suspects(self):
        v = Vault()
        text = f"cpf {BAD_CPF}"
        self.assertEqual(v.protect(text, report_invalid=True), text)

    def test_unknown_token_left_alone(self):
        v = Vault()
        self.assertEqual(v.reveal("x <BR_CPF:000000000000> y"), "x <BR_CPF:000000000000> y")


class TestResidual(unittest.TestCase):
    # [TEST-E9-RESIDUAL]
    def test_clean_after_protect(self):
        v = Vault()
        self.assertEqual(residual(v.protect(f"cpf {VALID_CPF}")), [])

    def test_clean_after_mask(self):
        self.assertEqual(residual(tarja.mask(f"cpf {VALID_CPF}")), [])

    def test_leak_found(self):
        self.assertEqual([m.entity for m in residual(f"cpf {VALID_CPF}")], ["BR_CPF"])


if __name__ == "__main__":
    unittest.main()
