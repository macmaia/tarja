# tests/test_mask.py
# [TEST-MASK] tests for mask()

import unittest

import tarja

T = "cpf 529.982.247-25 e de novo cpf 52998224725, cnpj 12.ABC.345/01DE-35"


class TestMask(unittest.TestCase):
    def test_redact(self):
        # [TEST-MASK] default strategy
        self.assertEqual(tarja.mask(T), "cpf <BR_CPF> e de novo cpf <BR_CPF>, cnpj <BR_CNPJ>")

    def test_pseudonym_consistent(self):
        # [TEST-MASK] same CPF written 2 ways -> same label
        out = tarja.mask(T, strategy="pseudonym")
        self.assertEqual(out, "cpf <BR_CPF_1> e de novo cpf <BR_CPF_1>, cnpj <BR_CNPJ_1>")

    def test_short_salt_warns(self):
        # [TEST-MASK-SALT] under 16 bytes -> warning, 16+ -> silent
        with self.assertWarns(UserWarning):
            tarja.mask(T, strategy="hash", salt="short")
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            tarja.mask(T, strategy="hash", salt="x" * 16)

    def test_hash_needs_salt_and_is_stable(self):
        # [TEST-MASK] no salt -> error, same salt -> same output, other salt -> different
        with self.assertRaises(ValueError):
            tarja.mask(T, strategy="hash")
        a = tarja.mask(T, strategy="hash", salt="s1" * 8)
        self.assertEqual(a, tarja.mask(T, strategy="hash", salt=b"s1" * 8))
        self.assertNotEqual(a, tarja.mask(T, strategy="hash", salt="s2" * 8))
        self.assertNotIn("529", a)
        # both CPF spellings hash the same
        tags = [w for w in a.split() if w.startswith("<BR_CPF:")]
        self.assertEqual(len({t.rstrip(",") for t in tags}), 1)

    def test_bad_strategy(self):
        # [TEST-MASK] unknown strategy raises
        with self.assertRaises(ValueError):
            tarja.mask(T, strategy="blur")

    def test_reuse_matches_and_find_kwargs(self):
        # [TEST-MASK] pass matches from find(), or find() kwargs
        found = tarja.find(T, entities=["BR_CNPJ"])
        self.assertEqual(tarja.mask(T, matches=found).count("<BR_CNPJ>"), 1)
        self.assertNotIn("<BR_CPF>", tarja.mask(T, entities=["BR_CNPJ"]))


if __name__ == "__main__":
    unittest.main()
