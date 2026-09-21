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

    def test_weak_salt_raises(self):
        # [TEST-MASK-SALT] refused, not warned about: placeholder word, too short, too few distinct bytes
        # short, weak word, long placeholder, 13 random-looking bytes, 16 bytes of one value, 2 distinct
        for bad in ("short", "SECRET", "changeme_please_12345", "0123456789abc", "x" * 16, b"ab" * 8):
            with self.assertRaises(ValueError, msg=bad):
                tarja.mask(T, strategy="pseudonym_stable", salt=bad)

    def test_good_salt_is_silent(self):
        # [TEST-MASK-SALT] a real key passes with no warning
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            tarja.mask(T, strategy="pseudonym_stable", salt="7f3b9a1c5d2e8046")

    def test_old_hash_name_still_works_and_warns(self):
        # [TEST-MASK-ALIAS] "hash" is the pre-0.5 name, kept until 0.6
        with self.assertWarns(DeprecationWarning):
            out = tarja.mask(T, strategy="hash", salt="7f3b9a1c5d2e8046")
        self.assertEqual(out, tarja.mask(T, strategy="pseudonym_stable", salt="7f3b9a1c5d2e8046"))

    def test_pseudonym_stable_needs_salt_and_is_stable(self):
        # [TEST-MASK] no salt -> error, same key -> same output, other key -> different
        with self.assertRaises(ValueError):
            tarja.mask(T, strategy="pseudonym_stable")
        a = tarja.mask(T, strategy="pseudonym_stable", salt="7f3b9a1c5d2e8046")
        self.assertEqual(a, tarja.mask(T, strategy="pseudonym_stable", salt=b"7f3b9a1c5d2e8046"))
        self.assertNotEqual(a, tarja.mask(T, strategy="pseudonym_stable", salt="c04e8d2a6b915f37"))
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
