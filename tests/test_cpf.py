# tests/test_cpf.py
# [TEST-CPF] EN: tests for the CPF validator / PT: testes do validador de CPF

import random
import unittest

from tarja.validators import cpf


class TestCPF(unittest.TestCase):
    def test_valid(self):
        # [TEST-CPF] EN: formatted, digits only, with spaces, another valid one
        # [TEST-CPF] PT: formatado, so digitos, c/ espaco e outro valido
        for v in ["529.982.247-25", "52998224725", " 529 982 247 25 ", "168.995.350-09"]:
            self.assertTrue(cpf.is_valid(v), v)

    def test_wrong_check_digit(self):
        # [TEST-CPF] EN: same number, check digit changed / PT: mesmo numero c/ DV trocado
        for v in ["529.982.247-24", "529.982.247-15", "168.995.350-08"]:
            self.assertFalse(cpf.is_valid(v), v)

    def test_repeated_digits(self):
        # [TEST-CPF] EN: 000... to 999... are never valid / PT: 000... ate 999... nao valem
        for d in "0123456789":
            self.assertFalse(cpf.is_valid(d * 11))

    def test_bad_format(self):
        # [TEST-CPF] EN: empty, short, letter, long, None, int / PT: vazio, curto, letra, longo, None, int
        for v in ["", "123", "529.982.247-2", "5299822472a", "529982247255", None, 52998224725]:
            self.assertFalse(cpf.is_valid(v), v)

    def test_zero_check_digit(self):
        # [TEST-CPF] EN: bases hitting the "remainder < 2 -> 0" branch / PT: bases q caem no ramo "resto < 2 -> 0"
        for base in ("100000001", "000000019"):
            self.assertTrue(cpf.is_valid(base + cpf.compute_check_digits(base)))

    def test_compute_bad_base(self):
        # [TEST-CPF] EN: 8-digit base raises / PT: base c/ 8 digitos da erro
        with self.assertRaises(ValueError):
            cpf.compute_check_digits("12345678")

    def test_format(self):
        # [TEST-CPF] EN: formats a valid one, raises on invalid / PT: formata o valido, erro no invalido
        self.assertEqual(cpf.format("52998224725"), "529.982.247-25")
        with self.assertRaises(ValueError):
            cpf.format("52998224724")

    def test_property(self):
        # [TEST-CPF] EN: generate 5k CPFs, all must validate, then change one check digit -> must fail.
        #            Only check digits are mutated because changing the base doesn't always fail (see cpf.py)
        # [TEST-CPF] PT: gera 5 mil CPFs, todos validam, dps muda 1 DV -> tem q falhar.
        #            So muta o DV pq mudar a base nem sempre invalida (ver cpf.py)
        rng = random.Random(42)
        for _ in range(5000):
            base = "".join(rng.choice("0123456789") for _ in range(9))
            if len(set(base)) == 1:
                continue
            full = base + cpf.compute_check_digits(base)
            self.assertTrue(cpf.is_valid(full))
            i = rng.choice([9, 10])
            d = str((int(full[i]) + rng.randrange(1, 10)) % 10)
            mutated = full[:i] + d + full[i + 1 :]
            if len(set(mutated)) > 1:
                self.assertFalse(cpf.is_valid(mutated), (full, mutated))


if __name__ == "__main__":
    unittest.main()
