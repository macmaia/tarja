# tests/test_validators_e2.py
# [TEST-E2-VALID] EN: tests for the E2.3 validators: CNS, NIS/PIS, CNJ case number
# [TEST-E2-VALID] PT: testes dos validadores do E2.3: CNS, NIS/PIS, processo CNJ

import random
import unittest

from tarja.validators import cnj, cns, nis


class TestNIS(unittest.TestCase):
    def test_valid(self):
        # [TEST-NIS] EN: formatted and compact / PT: formatado e compacto
        for v in ["120.37567.08-3", "12037567083"]:
            self.assertTrue(nis.is_valid(v), v)

    def test_invalid(self):
        # [TEST-NIS] EN: wrong digit, repeated, short, wrong type / PT: DV errado, repetido, curto, tipo errado
        for v in ["120.37567.08-4", "11111111111", "1203756708", "", None, 12037567083]:
            self.assertFalse(nis.is_valid(v), v)

    def test_ten_or_eleven_becomes_zero(self):
        # [TEST-NIS] EN: find bases where 11 - remainder is 10 or 11, digit must be 0
        # [TEST-NIS] PT: acha bases onde 11 - resto da 10 ou 11, o DV tem q ser 0
        rng = random.Random(3)
        weights = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        hits = 0
        for _ in range(2000):
            b = "".join(rng.choice("0123456789") for _ in range(10))
            if 11 - sum(int(d) * w for d, w in zip(b, weights, strict=True)) % 11 >= 10:
                self.assertEqual(nis.compute_check_digit(b), "0")
                hits += 1
        self.assertGreater(hits, 0)

    def test_compute_and_format(self):
        # [TEST-NIS] EN: bad base raises, format round-trip / PT: base ruim da erro, format ida e volta
        with self.assertRaises(ValueError):
            nis.compute_check_digit("123")
        self.assertEqual(nis.format("12037567083"), "120.37567.08-3")
        with self.assertRaises(ValueError):
            nis.format("12037567084")


class TestCNS(unittest.TestCase):
    def test_valid(self):
        # [TEST-CNS] EN: provisional (7, 8) and definitive (1) prefixes, spaced and compact
        # [TEST-CNS] PT: prefixo provisorio (7, 8) e definitivo (1), c/ espaco e compacto
        for v in ["729141777631701", "866 9074 3915 0002", "898 0000 0004 3208", "180636083770008"]:
            self.assertTrue(cns.is_valid(v), v)

    def test_invalid(self):
        # [TEST-CNS] EN: wrong digit, bad prefix (3), short, wrong type / PT: DV errado, prefixo ruim (3), curto, tipo
        for v in ["729141777631702", "329141777631701", "72914177763170", "180636083778351", "", None, 1]:
            self.assertFalse(cns.is_valid(v), v)

    def test_official_example(self):
        # [TEST-CNS] EN: example printed in the Anvisa/MS doc / PT: exemplo impresso no doc da Anvisa/MS
        self.assertTrue(cns.is_valid("898 0000 0004 3208"))

    def test_definitive_structure(self):
        # [TEST-CNS] EN: 1/2 cards are pis + 000|001 + dv, a mod-11-only number with other middle digits fails
        # [TEST-CNS] PT: cartao 1/2 e pis + 000|001 + dv, numero q so passa no mod 11 c/ outro meio falha
        rng = random.Random(5)
        branches = set()
        for _ in range(3000):
            pis = rng.choice("12") + "".join(rng.choice("0123456789") for _ in range(10))
            full = cns.definitive_from_pis(pis)
            branches.add(full[11:14])
            self.assertEqual(len(full), 15)
            self.assertTrue(cns.is_valid(full))
            self.assertFalse(cns.is_valid(full[:14] + str((int(full[14]) + 1) % 10)))
        self.assertEqual(branches, {"000", "001"})
        with self.assertRaises(ValueError):
            cns.definitive_from_pis("3" * 11)

    def test_provisional_property(self):
        # [TEST-CNS] EN: provisional 7/8/9, any change in the last digit fails / PT: provisorio, trocar o ultimo falha
        rng = random.Random(6)
        made = 0
        while made < 500:
            base = rng.choice("789") + "".join(rng.choice("0123456789") for _ in range(13))
            ok = [d for d in "0123456789" if cns.weighted_sum(base + d) % 11 == 0]
            if not ok:
                continue
            self.assertTrue(cns.is_valid(base + ok[0]))
            for d in "0123456789":
                if d != ok[0]:
                    self.assertFalse(cns.is_valid(base + d))
            made += 1

    def test_format(self):
        # [TEST-CNS] EN: format and error / PT: formata e erro
        self.assertEqual(cns.format("729141777631701"), "729 1417 7763 1701")
        with self.assertRaises(ValueError):
            cns.format("729141777631702")


class TestCNJ(unittest.TestCase):
    def test_valid(self):
        # [TEST-CNJ] EN: formatted and compact / PT: formatado e compacto
        for v in ["0000001-83.2017.8.26.0100", "00000018320178260100"]:
            self.assertTrue(cnj.is_valid(v), v)

    def test_iso7064_property(self):
        # [TEST-CNJ] EN: the ISO 7064 identity int(N AAAA J TR OOOO DD) % 97 == 1 must hold for generated numbers
        # [TEST-CNJ] PT: a identidade ISO 7064 int(N AAAA J TR OOOO DD) % 97 == 1 vale p/ numeros gerados
        rng = random.Random(9)
        for _ in range(3000):
            seq = "".join(rng.choice("0123456789") for _ in range(7))
            rest = f"{rng.randint(1990, 2026)}{rng.randint(1, 9)}{rng.randint(1, 99):02d}{rng.randint(0, 9999):04d}"
            dd = cnj.compute_check_digits(seq, rest)
            self.assertEqual(int(seq + rest + dd) % 97, 1)
            self.assertTrue(cnj.is_valid(seq + dd + rest))
            wrong = f"{(int(dd) + 1) % 100:02d}"
            self.assertFalse(cnj.is_valid(seq + wrong + rest))

    def test_invalid(self):
        # [TEST-CNJ] EN: wrong DD, J = 0, short, wrong type / PT: DD errado, J = 0, curto, tipo errado
        for v in ["0000001-84.2017.8.26.0100", "0000001-83.2017.0.26.0100", "0000001-83.2017.8.26.010", None, 1]:
            self.assertFalse(cnj.is_valid(v), v)

    def test_compute_and_format(self):
        # [TEST-CNJ] EN: bad input raises, format / PT: entrada ruim da erro, formata
        with self.assertRaises(ValueError):
            cnj.compute_check_digits("123", "20178260100")
        self.assertEqual(cnj.format("00000018320178260100"), "0000001-83.2017.8.26.0100")
        with self.assertRaises(ValueError):
            cnj.format("00000018420178260100")


if __name__ == "__main__":
    unittest.main()
