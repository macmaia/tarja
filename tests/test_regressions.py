"""EN: One test per detection failure found by the benchmark or the semi-real pilot.
PT: Um teste por falha de deteccao achada pelo benchmark ou pelo piloto semi-real.
"""

import random
import unittest

import tarja
from bench.ids import generate, render


class TestSpacedSeparators(unittest.TestCase):
    # [TEST-REG-SPACED] D1: PDF/OCR text with spaces where the separators should be (19/09/2026)
    CASES = {
        "BR_CNPJ": "inscrita no CNPJ {}",
        "BR_CNJ": "nos autos do processo {}",
        "BR_NIS": "beneficiario com NIS {}",
        "BR_CNM": "imovel com CNM {}",
        "BR_CIB": "cadastro imobiliario brasileiro {}",
    }

    def test_spaced_values_found(self):
        rng = random.Random(11)
        for entity, phrase in self.CASES.items():
            for _ in range(30):
                value = render(entity, generate(entity, rng), "spaced")
                found = [m for m in tarja.find(phrase.format(value)) if m.entity == entity]
                self.assertEqual([m.value for m in found], [value], (entity, value))

    def test_spaced_alphanumeric_cnpj(self):
        self.assertEqual([m.entity for m in tarja.find("CNPJ 12 ABC 345 01DE 35")], ["BR_CNPJ"])

    def test_spaced_wrong_dv_still_rejected(self):
        self.assertEqual(tarja.find("CNPJ 12 ABC 345 01DE 36"), [])


class TestMatriculaAdjacency(unittest.TestCase):
    # [TEST-REG-MATRICULA] semi-real pilot: numbers near "registro de imoveis" were taken as matricula
    def test_law_number_nearby_is_not_matricula(self):
        text = "Matricula do imovel 547.175 no registro de imoveis. 3 Nos procedimentos da Lei n. 13.465, de 2017."
        found = [m.value for m in tarja.find(text) if m.entity == "BR_MATRICULA_IMOVEL"]
        self.assertEqual(found, ["547.175"])

    def test_adjacent_forms(self):
        for text, value in (
            ("matrícula nº 12.345 do 2º Ofício", "12.345"),
            ("sob a matrícula 12.345", "12.345"),
            ("imóvel 12.345 no Registro de Imóveis de Niterói", "12.345"),
        ):
            found = [m.value for m in tarja.find(text) if m.entity == "BR_MATRICULA_IMOVEL"]
            self.assertEqual(found, [value], text)

    def test_far_context_ignored(self):
        text = "Registro de imoveis da comarca. Em 2019 foram 45 atos."
        self.assertEqual([m for m in tarja.find(text) if m.entity == "BR_MATRICULA_IMOVEL"], [])


if __name__ == "__main__":
    unittest.main()
