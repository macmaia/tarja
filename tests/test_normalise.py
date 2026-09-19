# tests/test_normalise.py
# [TEST-NORMALISE] EN: tests for the offset-preserving normaliser / PT: testes do normalizador q preserva offset

import unittest

from tarja.normalise import fold, normalise_text


class TestNormalise(unittest.TestCase):
    def test_ascii_untouched(self):
        # [TEST-NORMALISE] EN: plain ASCII comes back identical / PT: ASCII puro volta igual
        t = "CPF 529.982.247-25"
        self.assertIs(normalise_text(t), t)

    def test_lookalikes(self):
        # [TEST-NORMALISE] EN: fullwidth digits, en dash, NBSP, fullwidth letters and slash
        # [TEST-NORMALISE] PT: digito fullwidth, meia-risca, NBSP, letra e barra fullwidth
        t = "５２９.982.247–25 ＡＢ／"
        self.assertEqual(normalise_text(t), "529.982.247-25 AB/")

    def test_length_always_kept(self):
        # [TEST-NORMALISE] EN: output length == input length, char by char / PT: tamanho igual, char a char
        t = "a—b−c　d١٢eéİ"
        self.assertEqual(len(normalise_text(t)), len(t))
        self.assertEqual(len(fold(t)), len(t))

    def test_arabic_indic_digits(self):
        # [TEST-NORMALISE] EN: other Unicode digit systems -> ASCII / PT: outros sistemas de digito -> ASCII
        self.assertEqual(normalise_text("١٢٣"), "123")

    def test_fold(self):
        # [TEST-NORMALISE] EN: lowercase, no accents / PT: minusculo, sem acento
        self.assertEqual(fold("Cartão Nacional de SAÚDE"), "cartao nacional de saude")


if __name__ == "__main__":
    unittest.main()
