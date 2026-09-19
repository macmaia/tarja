# tests/test_validators_e29.py
# [TEST-E29] EN: tests for the E2.9 validators and how they behave inside find()
# [TEST-E29] PT: testes dos validadores do E2.9 e de como se comportam dentro do find()

import random
import unittest

import tarja
from tarja.validators import cep, cnh, pix, placa, renavam, telefone, titulo


class TestTitulo(unittest.TestCase):
    def test_valid_invalid(self):
        # [TEST-TITULO] EN: SP, RJ, spaced / PT: SP, RJ, c/ espaco
        for v in ["102345670183", "1023 4567 0388", "100000010116"]:
            self.assertTrue(titulo.is_valid(v), v)
        # EN: wrong digit, bad state 29, short, repeated, type / PT: DV errado, UF 29, curto, repetido, tipo
        for v in ["102345670184", "102345672999", "10234567018", "111111111111", None]:
            self.assertFalse(titulo.is_valid(v), v)

    def test_sp_mg_zero_becomes_one(self):
        # [TEST-TITULO] EN: remainder 0 -> 1 only for SP/MG / PT: resto 0 -> 1 so p/ SP/MG
        seq = "10000001"  # EN: weighted sum % 11 == 0 / PT: soma ponderada % 11 == 0
        self.assertEqual(titulo.compute_check_digits(seq, "01")[0], "1")
        self.assertEqual(titulo.compute_check_digits(seq, "03")[0], "0")

    def test_property_and_state(self):
        # [TEST-TITULO] EN: generated numbers validate and report their state / PT: gerados validam e dizem a UF
        rng = random.Random(4)
        for _ in range(2000):
            seq = "".join(rng.choice("0123456789") for _ in range(8))
            uf = rng.choice(sorted(titulo.STATES))
            full = seq + uf + titulo.compute_check_digits(seq, uf)
            if len(set(full)) == 1:
                continue
            self.assertTrue(titulo.is_valid(full))
            self.assertEqual(titulo.state(full), titulo.STATES[uf])
        self.assertIsNone(titulo.state("102345670184"))
        with self.assertRaises(ValueError):
            titulo.compute_check_digits("1234", "01")


class TestCNH(unittest.TestCase):
    def test_valid_invalid(self):
        # [TEST-CNH] EN: normal and "discount" branch / PT: caso normal e ramo do "desconto"
        for v in ["12345678900", "10000000100"]:
            self.assertTrue(cnh.is_valid(v), v)
        for v in ["12345678901", "11111111111", "1234567890", None]:
            self.assertFalse(cnh.is_valid(v), v)
        with self.assertRaises(ValueError):
            cnh.compute_check_digits("12")

    def test_discount_branch_exact(self):
        # [TEST-CNH] EN: DV1 >= 10 triggers the "discount 2" on DV2. Hand-computed vector:
        #   base 100000044: DV1 = (1*9 + 4*2 + 4*1) % 11 = 21 % 11 = 10 -> 0, discount 2
        #   DV2 = (1*1 + 4*8 + 4*9) % 11 = 69 % 11 = 3 -> 3 - 2 = 1. Result "01".
        # [TEST-CNH] PT: DV1 >= 10 ativa o "desconto 2" no DV2. Vetor calculado a mao (acima). Resultado "01".
        self.assertEqual(cnh.compute_check_digits("100000044"), "01")

    def test_property(self):
        # [TEST-CNH] EN: generate, validate, break DV2 / PT: gera, valida, quebra o DV2
        rng = random.Random(6)
        for _ in range(3000):
            b = "".join(rng.choice("0123456789") for _ in range(9))
            full = b + cnh.compute_check_digits(b)
            if len(set(full)) == 1:
                continue
            self.assertTrue(cnh.is_valid(full))
            self.assertFalse(cnh.is_valid(full[:10] + str((int(full[10]) + 1) % 10)))


class TestRenavam(unittest.TestCase):
    def test_valid_invalid(self):
        # [TEST-RENAVAM] EN: 11 digits and old 9-digit form / PT: 11 digitos e o formato antigo de 9
        for v in ["00639724361", "639724361"]:
            self.assertTrue(renavam.is_valid(v), v)
        for v in ["00639724362", "11111111111", "6397243", None]:
            self.assertFalse(renavam.is_valid(v), v)
        with self.assertRaises(ValueError):
            renavam.compute_check_digit("1")


class TestFormatOnly(unittest.TestCase):
    def test_placa(self):
        # [TEST-PLACA] EN: old, dashed, Mercosur, conversion / PT: antiga, c/ traco, Mercosul, conversao
        for v in ["ABC1234", "abc-1234", "ABC1D23"]:
            self.assertTrue(placa.is_valid(v), v)
        for v in ["AB1234", "ABC12345", "ABCD123", None]:
            self.assertFalse(placa.is_valid(v), v)
        self.assertEqual(placa.to_mercosur("ABC-1234"), "ABC1C34")
        self.assertEqual(placa.to_mercosur("ABC1D23"), "ABC1D23")
        self.assertTrue(placa.is_mercosur("ABC1D23"))
        with self.assertRaises(ValueError):
            placa.to_mercosur("XYZ")

    def test_pix(self):
        # [TEST-PIX] EN: v4 UUID ok, bad version / garbage not / PT: UUID v4 ok, versao ruim / lixo nao
        self.assertTrue(pix.is_valid("123E4567-E89B-42D3-A456-426614174000"))
        for v in ["123e4567-e89b-02d3-a456-426614174000", "not-a-uuid", None]:
            self.assertFalse(pix.is_valid(v), v)

    def test_telefone(self):
        # [TEST-TELEFONE] EN: mobile, landline, +55, bad DDD, bad first digit, length
        # [TEST-TELEFONE] PT: celular, fixo, +55, DDD ruim, 1o digito ruim, tamanho
        for v in ["(21) 98765-4321", "+55 21 2345-6789", "5511987654321"]:
            self.assertTrue(telefone.is_valid(v), v)
        for v in ["(20) 98765-4321", "(21) 18765-4321", "(21) 8765-4321", "123", None]:
            self.assertFalse(telefone.is_valid(v), v)

    def test_cep(self):
        # [TEST-CEP] EN: range and format / PT: faixa e formato
        self.assertTrue(cep.is_valid("22290-140"))
        for v in ["00000-000", "00999-999", "2229-014", None]:
            self.assertFalse(cep.is_valid(v), v)


class TestInFind(unittest.TestCase):
    def ents(self, text):
        return [(m.entity, m.value) for m in tarja.find(text)]

    def test_context_required_entities(self):
        # [TEST-E29-FIND] EN: CEP, CNH, RENAVAM, PIX only show up with their context word
        # [TEST-E29-FIND] PT: CEP, CNH, RENAVAM, PIX so aparecem c/ a palavra de contexto
        self.assertIn(("BR_CEP", "22290-140"), self.ents("CEP 22290-140"))
        self.assertNotIn("BR_CEP", [e for e, _ in self.ents("codigo 22290-140")])
        uuid = "123e4567-e89b-42d3-a456-426614174000"
        self.assertIn(("BR_PIX_EVP", uuid), self.ents(f"chave pix {uuid}"))
        self.assertEqual(self.ents(f"trace id {uuid}"), [])
        self.assertIn(("BR_CNH", "12345678900"), self.ents("CNH 12345678900"))
        self.assertIn(("BR_RENAVAM", "00639724361"), self.ents("renavam 00639724361"))

    def test_renavam_beats_nis_with_context(self):
        # [TEST-E29-FIND] EN: RENAVAM and NIS share the digit rule, context decides
        # [TEST-E29-FIND] PT: RENAVAM e NIS tem a mesma regra de DV, o contexto decide
        self.assertTrue(tarja.nis.is_valid("00639724361"))
        self.assertEqual(self.ents("renavam 00639724361"), [("BR_RENAVAM", "00639724361")])

    def test_phone_plate_titulo(self):
        # [TEST-E29-FIND] EN: N2 phone and plate, N1 voter ID / PT: telefone e placa N2, titulo N1
        got = self.ents("whatsapp (21) 98765-4321, placa ABC1D23, titulo de eleitor 1023 4567 0388")
        self.assertEqual(
            got,
            [("BR_TELEFONE", "(21) 98765-4321"), ("BR_PLACA", "ABC1D23"), ("BR_TITULO_ELEITOR", "1023 4567 0388")],
        )

    def test_valid_cpf_beats_phone(self):
        # [TEST-E29-FIND] EN: 11 digits that are a valid CPF AND phone-shaped -> CPF (N1 > N2)
        # [TEST-E29-FIND] PT: 11 digitos q sao CPF valido E parecem telefone -> CPF (N1 > N2)
        base = "219876543"
        full = base + tarja.cpf.compute_check_digits(base)
        self.assertTrue(telefone.is_valid(full))
        self.assertEqual(tarja.find(full)[0].entity, "BR_CPF")


if __name__ == "__main__":
    unittest.main()
