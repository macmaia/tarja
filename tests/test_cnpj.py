# tests/test_cnpj.py
# [TEST-CNPJ] tests for the CNPJ validator (numeric + alphanumeric)

import random
import string
import unittest

from tarja.validators import cnpj

# alphabet allowed in the first 12 positions
ALNUM = string.digits + string.ascii_uppercase


class TestCNPJ(unittest.TestCase):
    def test_official_example(self):
        # [TEST-CNPJ] Receita Federal's official example
        self.assertEqual(cnpj.compute_check_digits("12ABC34501DE"), "35")
        self.assertTrue(cnpj.is_valid("12.ABC.345/01DE-35"))

    def test_valid(self):
        # [TEST-CNPJ] compact, lowercase, numeric formatted, numeric compact
        for v in ["12ABC34501DE35", "12.abc.345/01de-35", "11.222.333/0001-81", "11222333000181"]:
            self.assertTrue(cnpj.is_valid(v), v)

    def test_wrong_check_digit(self):
        # [TEST-CNPJ] changed or swapped check digits
        for v in ["12.ABC.345/01DE-36", "12.ABC.345/01DE-53", "11.222.333/0001-80"]:
            self.assertFalse(cnpj.is_valid(v), v)

    def test_letter_check_digit(self):
        # [TEST-CNPJ] check digits are never letters
        self.assertFalse(cnpj.is_valid("12ABC34501DE3A"))

    def test_repeated_digits(self):
        # [TEST-CNPJ] 000... to 999... are never valid
        for d in "0123456789":
            self.assertFalse(cnpj.is_valid(d * 14))

    def test_bad_format(self):
        # [TEST-CNPJ] short, long, symbol, accent, None, int
        cases = ["", "11.222.333/0001-8", "12ABC34501DE355", "12ABC-34501DE35!", "12ÁBC34501DE35"]
        for v in [*cases, None, 11222333000181]:
            self.assertFalse(cnpj.is_valid(v), v)

    def test_is_alphanumeric(self):
        # [TEST-CNPJ] new vs old format
        self.assertTrue(cnpj.is_alphanumeric("12.ABC.345/01DE-35"))
        self.assertFalse(cnpj.is_alphanumeric("11.222.333/0001-81"))

    def test_matches_legacy_algorithm(self):
        # [TEST-CNPJ] for digit-only CNPJs ord(c)-48 == int(c), so results must match the classic calc (3k cases)
        rng = random.Random(7)
        w1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        w2 = (6,) + w1

        def legacy(b):
            # old digit-only calculation
            def check_digit(s, w):
                r = sum(int(c) * p for c, p in zip(s, w, strict=True)) % 11
                return 0 if r < 2 else 11 - r

            d1 = check_digit(b, w1)
            return f"{d1}{check_digit(b + str(d1), w2)}"

        for _ in range(3000):
            b = "".join(rng.choice(string.digits) for _ in range(12))
            self.assertEqual(cnpj.compute_check_digits(b), legacy(b))

    def test_compute_bad_base(self):
        # [TEST-CNPJ] short, long or symbol base raises
        for b in ["12ABC34501D", "12ABC34501DE3", "12ABC34501D!"]:
            with self.assertRaises(ValueError):
                cnpj.compute_check_digits(b)

    def test_format(self):
        # [TEST-CNPJ] formats (and uppercases), raises on invalid
        self.assertEqual(cnpj.format("12abc34501de35"), "12.ABC.345/01DE-35")
        with self.assertRaises(ValueError):
            cnpj.format("12ABC34501DE36")

    def test_property(self):
        # [TEST-CNPJ] generate 5k alphanumeric CNPJs, all validate, then change one check digit -> must fail
        rng = random.Random(11)
        for _ in range(5000):
            base = "".join(rng.choice(ALNUM) for _ in range(12))
            full = base + cnpj.compute_check_digits(base)
            if len(set(full)) == 1:
                continue
            self.assertTrue(cnpj.is_valid(full))
            i = rng.choice([12, 13])
            d = str((int(full[i]) + rng.randrange(1, 10)) % 10)
            self.assertFalse(cnpj.is_valid(full[:i] + d + full[i + 1 :]))


if __name__ == "__main__":
    unittest.main()
