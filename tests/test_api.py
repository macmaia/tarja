# tests/test_api.py
# [TEST-API] EN: tests for tarja.validate() / PT: testes da funcao publica tarja.validate()

import unittest

import tarja


class TestAPI(unittest.TestCase):
    def test_validate(self):
        # [TEST-API] EN: CPF ok, alphanumeric CNPJ ok, CNPJ with wrong digit
        # [TEST-API] PT: CPF ok, CNPJ alfanum ok, CNPJ c/ DV errado
        self.assertTrue(tarja.validate("BR_CPF", "529.982.247-25"))
        self.assertTrue(tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35"))
        self.assertFalse(tarja.validate("BR_CNPJ", "12.ABC.345/01DE-36"))

    def test_unknown_entity(self):
        # [TEST-API] EN: entity not in the registry raises / PT: entidade fora do registro da erro
        with self.assertRaises(ValueError):
            tarja.validate("BR_XYZ", "1")


if __name__ == "__main__":
    unittest.main()
