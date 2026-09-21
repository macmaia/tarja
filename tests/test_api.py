# tests/test_api.py
# [TEST-API] tests for tarja.validate()

import unittest

import tarja


class TestAPI(unittest.TestCase):
    def test_validate(self):
        # [TEST-API] CPF ok, alphanumeric CNPJ ok, CNPJ with wrong digit
        self.assertTrue(tarja.validate("BR_CPF", "529.982.247-25"))
        self.assertTrue(tarja.validate("BR_CNPJ", "12.ABC.345/01DE-35"))
        self.assertFalse(tarja.validate("BR_CNPJ", "12.ABC.345/01DE-36"))

    def test_unknown_entity(self):
        # [TEST-API] entity not in the registry raises
        with self.assertRaises(ValueError):
            tarja.validate("BR_XYZ", "1")


if __name__ == "__main__":
    unittest.main()
