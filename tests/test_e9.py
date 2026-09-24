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
        # default output is unchanged
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

    def test_compact_digit_runs_never_suspect(self):
        # [TEST-E9-SUSPECT-MIN] only formatted layouts raise suspects, bare digit runs would flood the report
        self.assertEqual(tarja.find("pedido 12345678901 e nota 98765432109", report_invalid=True), [])

    def test_suspect_loses_to_valid_overlap(self):
        # a valid match on the same span wins
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
    # [TEST-E9-CARTAO] public test PANs
    def test_valid(self):
        for v in ("4111 1111 1111 1111", "5555555555554444", "3782 822463 10005", "4012888888881881"):
            self.assertTrue(cartao.is_valid(v), v)

    def test_invalid(self):
        for v in ("4111 1111 1111 1112", "0000000000000000", "411111111111", "4" * 20, ""):
            self.assertFalse(cartao.is_valid(v), v)

    def test_check_digit(self):
        self.assertEqual(cartao.luhn_check_digit("411111111111111"), "1")
        self.assertEqual(cartao.luhn_check_digit("7992739871"), "3")

    def test_every_network_is_recognised(self):
        # [TEST-CARTAO-BRAND] public test numbers, one per network the IIN table claims to cover
        for value, expected in (
            ("4111 1111 1111 1111", "visa"),
            ("5555555555554444", "mastercard"),
            ("2223003122003222", "mastercard"),
            ("3782 822463 10005", "amex"),
            ("6011111111111117", "discover"),
            ("3056 9309 0259 04", "diners"),
            ("3530111333300000", "jcb"),
            ("6062 8288 8866 6688", "hipercard"),
        ):
            self.assertEqual(cartao.brand(value), expected, value)
            self.assertTrue(cartao.is_valid(value), value)

    def test_luhn_alone_is_not_enough(self):
        # [TEST-CARTAO-FP] these pass Luhn and are NOT cards: no registered issuer prefix. This is the noise
        #   that made 29 false positives appear in a corpus of real administrative documents.
        for v in ("1002003004005005", "9000123456789016", "7000000000000013", "1234567890123452"):
            self.assertTrue(cartao.luhn_ok(cartao.normalise(v)), v)
            self.assertIsNone(cartao.brand(v), v)
            self.assertFalse(cartao.is_valid(v), v)
            # the old behaviour is still reachable, explicitly
            self.assertTrue(cartao.is_valid(v, require_brand=False), v)

    def test_length_must_match_the_brand(self):
        # 15-digit Amex prefix on a 16-digit number is not an Amex
        self.assertIsNone(cartao.brand("3782822463100051"))

    def test_detector_drops_the_luhn_only_numbers(self):
        self.assertEqual(tarja.find("protocolo 1002003004005005"), [])

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
        text = "x <BR_CPF:000000000000> y"
        self.assertEqual(v.reveal(text, any_token=True), text)


class TestVaultHardening(unittest.TestCase):
    # [TEST-VAULT-HARDENING]
    def test_token_is_96_bits(self):
        tok = Vault().token("BR_CPF", VALID_CPF)
        self.assertRegex(tok, r"^<BR_CPF:[0-9a-f]{4}:[0-9a-f]{24}>$")

    def test_token_carries_the_key_generation(self):
        # [TEST-VAULT-KEY-ID] a stable token is only stable under one key. Without the generation marker,
        #   rotating the key breaks a join between an old document and a new one with no visible sign.
        from tarja.vault import key_id

        a, b = Vault(key=b"a" * 32), Vault(key=b"b" * 32)
        self.assertEqual(a.key_id, key_id(b"a" * 32))
        self.assertNotEqual(a.key_id, b.key_id)
        self.assertTrue(a.token("BR_CPF", VALID_CPF).startswith(f"<BR_CPF:{a.key_id}:"))
        # same key, same id, across instances
        self.assertEqual(Vault(key=b"a" * 32).key_id, a.key_id)

    def test_key_id_is_short_deterministic_and_sensitive(self):
        from tarja.vault import KEY_ID_HEX, key_id

        self.assertEqual(len(key_id(b"k" * 32)), KEY_ID_HEX)
        self.assertEqual(key_id(b"k" * 32), key_id(b"k" * 32))
        # one bit of difference in the key must change the marker, otherwise it cannot tell generations apart
        self.assertNotEqual(key_id(b"k" * 32), key_id(b"k" * 31 + b"j"))

    def test_alphanumeric_cnpj_is_stable_across_spellings(self):
        # [TEST-VAULT-CNPJ-ALNUM] the letters carry meaning here, and _canonical upper-cases. If that ever
        #   stops holding, the deterministic join silently splits one company into two.
        v = Vault(key=b"k" * 32)
        spellings = ["12.ABC.345/01DE-35", "12abc34501de35", "12 ABC 345 01DE 35", "12.abc.345/01DE-35"]
        tokens = {v.token("BR_CNPJ", x) for x in spellings}
        self.assertEqual(len(tokens), 1, tokens)

    def test_alphanumeric_cnpj_is_stable_in_mask_too(self):
        salt = "7f3b9a1c5d2e8046"
        a = tarja.mask("cnpj 12.ABC.345/01DE-35", strategy="pseudonym_stable", salt=salt)
        b = tarja.mask("cnpj 12abc34501de35", strategy="pseudonym_stable", salt=salt)
        self.assertEqual(a.split("cnpj ")[1], b.split("cnpj ")[1])

    def test_collision_raises(self):
        from tarja.vault import VaultCollisionError

        v = Vault()
        v.token = lambda entity, value: "<BR_CPF:" + "0" * 24 + ">"  # force every value onto one token
        v.protect(f"cpf {VALID_CPF}")
        with self.assertRaises(VaultCollisionError):
            v.protect("cpf 111.444.777-35")

    def test_same_value_other_layout_is_not_collision(self):
        v = Vault()
        v.protect(f"cpf {VALID_CPF}")
        self.assertIn("<BR_CPF:", v.protect("cpf 52998224725"))
        self.assertEqual(len(v), 1)

    def test_overlapping_matches_skipped(self):
        v = Vault()
        text = f"cpf {VALID_CPF}"
        ms = tarja.find(text)
        both = ms + [tarja.Match("BR_CPF", ms[0].start + 2, ms[0].end, ms[0].value[2:], 0.9, ms[0].tier, "x", True)]
        self.assertEqual(v.reveal(v.protect(text, matches=both)), text)

    def test_residual_blanks_mask_hash_tokens(self):
        self.assertEqual(residual(tarja.mask(f"cpf {VALID_CPF}", strategy="pseudonym_stable", salt="7f3b9a1c5d2e8046")), [])


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
