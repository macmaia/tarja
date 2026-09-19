# tests/test_normalise.py
# [TEST-NORMALISE] tests for the offset-preserving normaliser

import unittest

from tarja.normalise import fold, normalise_text


class TestNormalise(unittest.TestCase):
    def test_ascii_untouched(self):
        # [TEST-NORMALISE] plain ASCII comes back identical
        t = "CPF 529.982.247-25"
        self.assertIs(normalise_text(t), t)

    def test_lookalikes(self):
        # [TEST-NORMALISE] fullwidth digits, en dash, NBSP, fullwidth letters and slash
        t = "５２９.982.247–25 ＡＢ／"
        self.assertEqual(normalise_text(t), "529.982.247-25 AB/")

    def test_length_always_kept(self):
        # [TEST-NORMALISE] output length == input length, char by char
        t = "a—b−c　d١٢eéİ"
        self.assertEqual(len(normalise_text(t)), len(t))
        self.assertEqual(len(fold(t)), len(t))

    def test_arabic_indic_digits(self):
        # [TEST-NORMALISE] other Unicode digit systems -> ASCII
        self.assertEqual(normalise_text("١٢٣"), "123")

    def test_fold(self):
        # [TEST-NORMALISE] lowercase, no accents
        self.assertEqual(fold("Cartão Nacional de SAÚDE"), "cartao nacional de saude")


if __name__ == "__main__":
    unittest.main()
