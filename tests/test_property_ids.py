# tests/test_property_ids.py
# [TEST-PROPERTY] EN: tests for the property IDs: CNM, CIB, IPTU, matricula
# [TEST-PROPERTY] PT: testes dos identificadores de imovel: CNM, CIB, IPTU, matricula

import random
import unittest

import tarja
from tarja.validators import cib, cnm, iptu, matricula


class TestCNM(unittest.TestCase):
    def test_valid_invalid(self):
        # [TEST-CNM] EN: formatted, compact / PT: formatado, compacto
        for v in ["123456.2.1234567-44", "1234562123456744"]:
            self.assertTrue(cnm.is_valid(v), v)
        # EN: wrong DV, book 4, short, type / PT: DV errado, livro 4, curto, tipo
        for v in ["123456.2.1234567-45", "123456.4.1234567-44", "12345621234567", None]:
            self.assertFalse(cnm.is_valid(v), v)

    def test_iso7064_property(self):
        # [TEST-CNM] EN: int(all 16 digits) % 97 == 1 for generated numbers / PT: int(16 digitos) % 97 == 1 nos gerados
        rng = random.Random(8)
        for _ in range(3000):
            base = "".join(rng.choice("0123456789") for _ in range(6)) + rng.choice("23")
            base += "".join(rng.choice("0123456789") for _ in range(7))
            full = base + cnm.compute_check_digits(base)
            self.assertEqual(int(full) % 97, 1)
            self.assertTrue(cnm.is_valid(full))

    def test_format_and_errors(self):
        # [TEST-CNM] EN: format, bad input / PT: formata, entrada ruim
        self.assertEqual(cnm.format("1234562123456744"), "123456.2.1234567-44")
        with self.assertRaises(ValueError):
            cnm.format("1234562123456745")
        with self.assertRaises(ValueError):
            cnm.compute_check_digits("1")


class TestLoose(unittest.TestCase):
    def test_cib(self):
        # [TEST-CIB] EN: needs a letter and a digit in the first 7 / PT: precisa de letra e digito nos 7 primeiros
        for v in ["ABC1234-5", "abc12345"]:
            self.assertTrue(cib.is_valid(v), v)
        for v in ["ABCDEFG-5", "1234567-5", "ABC1234-X", None]:
            self.assertFalse(cib.is_valid(v), v)

    def test_iptu(self):
        # [TEST-IPTU] EN: 6-20 digits, not all equal / PT: 6-20 digitos, nao todos iguais
        for v in ["012.345.6789-0", "1.234.567-8"]:
            self.assertTrue(iptu.is_valid(v), v)
        for v in ["12345", "000.000.0000-0", "abc", None]:
            self.assertFalse(iptu.is_valid(v), v)

    def test_matricula(self):
        # [TEST-MATRICULA] EN: 1-7 digits, not zero / PT: 1-7 digitos, nao zero
        for v in ["12.345", "12345", "7"]:
            self.assertTrue(matricula.is_valid(v), v)
        for v in ["0", "12345678", "abc", None]:
            self.assertFalse(matricula.is_valid(v), v)


class TestInFind(unittest.TestCase):
    def ents(self, text):
        return [(m.entity, m.value) for m in tarja.find(text)]

    def test_property_ids_with_context(self):
        # [TEST-PROPERTY-FIND] EN: each one shows up with its context word / PT: cada um aparece c/ a palavra de contexto
        self.assertEqual(self.ents("CNM 123456.2.1234567-44"), [("BR_CNM", "123456.2.1234567-44")])
        self.assertEqual(self.ents("CIB ABC1234-5"), [("BR_CIB", "ABC1234-5")])
        self.assertEqual(self.ents("IPTU 012.345.6789-0"), [("BR_IPTU", "012.345.6789-0")])
        self.assertEqual(self.ents("matricula n 12.345"), [("BR_MATRICULA_IMOVEL", "12.345")])

    def test_loose_ones_need_context(self):
        # [TEST-PROPERTY-FIND] EN: without context, IPTU/matricula/CIB never fire / PT: sem contexto, nunca aparecem
        self.assertEqual(self.ents("pedido 012.345.6789-0 e nota 12.345"), [])
        self.assertEqual(self.ents("codigo ABC1234-5"), [("BR_PLACA", "ABC1234")])

    def test_student_matricula_is_not_property(self):
        # [TEST-PROPERTY-FIND] EN: bare "matricula" (student) is not enough / PT: "matricula" solta (aluno) nao basta
        self.assertEqual(self.ents("matricula do aluno 2024123"), [])

    def test_cpf_wins_over_iptu(self):
        # [TEST-PROPERTY-FIND] EN: a valid CPF near "iptu" stays a CPF (N1 > N3) / PT: CPF perto de "iptu" continua CPF
        self.assertEqual(self.ents("iptu do titular cpf 529.982.247-25")[0][0], "BR_CPF")


if __name__ == "__main__":
    unittest.main()
