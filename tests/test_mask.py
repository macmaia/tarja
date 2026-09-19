# tests/test_mask.py
# [TEST-MASK] EN: tests for mask() / PT: testes do mask()

import unittest

import tarja

T = "cpf 529.982.247-25 e de novo cpf 52998224725, cnpj 12.ABC.345/01DE-35"


class TestMask(unittest.TestCase):
    def test_redact(self):
        # [TEST-MASK] EN: default strategy / PT: estrategia padrao
        self.assertEqual(tarja.mask(T), "cpf <BR_CPF> e de novo cpf <BR_CPF>, cnpj <BR_CNPJ>")

    def test_pseudonym_consistent(self):
        # [TEST-MASK] EN: same CPF written 2 ways -> same label / PT: mesmo CPF escrito de 2 jeitos -> mesmo rotulo
        out = tarja.mask(T, strategy="pseudonym")
        self.assertEqual(out, "cpf <BR_CPF_1> e de novo cpf <BR_CPF_1>, cnpj <BR_CNPJ_1>")

    def test_hash_needs_salt_and_is_stable(self):
        # [TEST-MASK] EN: no salt -> error, same salt -> same output, other salt -> different
        # [TEST-MASK] PT: sem salt -> erro, mesmo salt -> mesmo output, outro salt -> diferente
        with self.assertRaises(ValueError):
            tarja.mask(T, strategy="hash")
        a = tarja.mask(T, strategy="hash", salt="s1")
        self.assertEqual(a, tarja.mask(T, strategy="hash", salt=b"s1"))
        self.assertNotEqual(a, tarja.mask(T, strategy="hash", salt="s2"))
        self.assertNotIn("529", a)
        # EN: both CPF spellings hash the same / PT: as 2 grafias do CPF dao o mesmo hash
        tags = [w for w in a.split() if w.startswith("<BR_CPF:")]
        self.assertEqual(len({t.rstrip(",") for t in tags}), 1)

    def test_bad_strategy(self):
        # [TEST-MASK] EN: unknown strategy raises / PT: estrategia desconhecida da erro
        with self.assertRaises(ValueError):
            tarja.mask(T, strategy="blur")

    def test_reuse_matches_and_find_kwargs(self):
        # [TEST-MASK] EN: pass matches from find(), or find() kwargs / PT: passa matches do find() ou kwargs do find()
        found = tarja.find(T, entities=["BR_CNPJ"])
        self.assertEqual(tarja.mask(T, matches=found).count("<BR_CNPJ>"), 1)
        self.assertNotIn("<BR_CPF>", tarja.mask(T, entities=["BR_CNPJ"]))


if __name__ == "__main__":
    unittest.main()
