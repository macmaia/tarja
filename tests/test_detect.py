# tests/test_detect.py
# [TEST-DETECT] tests for find() and overlap resolution

import unittest

import tarja
from tarja.detect import Match, resolve_overlaps


class TestFind(unittest.TestCase):
    def test_all_entities_in_one_text(self):
        # [TEST-DETECT] one of each, all with context
        t = (
            "Paciente cartao SUS 729 1417 7763 1701, CPF 529.982.247-25, empresa CNPJ 12.ABC.345/01DE-35, "
            "PIS 120.37567.08-3, processo 0000001-83.2017.8.26.0100."
        )
        got = {(m.entity, m.value) for m in tarja.find(t)}
        self.assertEqual(
            got,
            {
                ("BR_CNS", "729 1417 7763 1701"),
                ("BR_CPF", "529.982.247-25"),
                ("BR_CNPJ", "12.ABC.345/01DE-35"),
                ("BR_NIS", "120.37567.08-3"),
                ("BR_CNJ", "0000001-83.2017.8.26.0100"),
            },
        )
        self.assertTrue(all(m.score == 0.95 and m.has_context for m in tarja.find(t)))

    def test_offsets_point_to_original(self):
        # [TEST-DETECT] offsets slice the ORIGINAL text, even with Unicode look-alikes
        t = "cpf: ５２９.982.247–25 fim"
        [m] = tarja.find(t)
        self.assertEqual(t[m.start : m.end], m.value)
        self.assertEqual(m.value, "５２９.982.247–25")

    def test_wrong_check_digit_dropped(self):
        # [TEST-DETECT] right shape, wrong digit -> nothing
        self.assertEqual(tarja.find("CPF 529.982.247-24"), [])

    def test_context_changes_score(self):
        # [TEST-DETECT] same number with/without context word
        [a] = tarja.find("cpf 529.982.247-25", entities=["BR_CPF"])
        [b] = tarja.find("xyz 529.982.247-25", entities=["BR_CPF"])
        self.assertEqual((a.score, a.has_context), (0.95, True))
        self.assertEqual((b.score, b.has_context), (0.85, False))

    def test_context_whole_word_only(self):
        # [TEST-DETECT] "sus" inside "suspenso" is not context
        [m] = tarja.find("pagamento suspenso 729141777631701", entities=["BR_CNS"])
        self.assertFalse(m.has_context)

    def test_line_break_inside_cpf(self):
        # [TEST-DETECT] irregular pattern catches a CPF split by a newline
        [m] = tarja.find("CPF 529.982.247\n25", entities=["BR_CPF"])
        self.assertEqual(m.pattern, "cpf_irregular_punctuation")

    def test_cpf_vs_nis_same_digits(self):
        # [TEST-DETECT] 11 bare digits valid as both -> CPF wins without context, NIS wins with "pis"
        # 56012309864 is a valid CPF AND a valid NIS (found by search)
        both = "56012309864"
        self.assertTrue(tarja.cpf.is_valid(both) and tarja.nis.is_valid(both))
        self.assertEqual(tarja.find(f"num {both}")[0].entity, "BR_CPF")
        self.assertEqual(tarja.find(f"pis {both}")[0].entity, "BR_NIS")

    def test_filters(self):
        # [TEST-DETECT] entities subset, min_score, unknown id, wrong type
        t = "cpf 529.982.247-25 e xyz 12.ABC.345/01DE-35"
        self.assertEqual([m.entity for m in tarja.find(t, entities=["BR_CNPJ"])], ["BR_CNPJ"])
        self.assertEqual([m.entity for m in tarja.find(t, min_score=0.9)], ["BR_CPF"])
        with self.assertRaises(ValueError):
            tarja.find(t, entities=["BR_XYZ"])
        with self.assertRaises(TypeError):
            tarja.find(123)

    def test_no_resolve_keeps_both(self):
        # [TEST-DETECT] resolve=False returns overlapping hits too
        both = "52998224725"
        ents = {m.entity for m in tarja.find(both, resolve=False)}
        self.assertIn("BR_CPF", ents)

    def test_to_dict(self):
        # [TEST-DETECT] value hidden when asked
        [m] = tarja.find("cpf 529.982.247-25")
        self.assertIn("value", m.to_dict())
        self.assertNotIn("value", m.to_dict(include_value=False))


class TestOverlap(unittest.TestCase):
    def _m(self, entity, start, end, score, tier="N1"):
        return Match(entity, start, end, "x" * (end - start), score, tier, "p", False)

    def test_priority_order(self):
        # [TEST-OVERLAP] tier beats score, score beats length, length beats registry order
        a = self._m("BR_CPF", 0, 10, 0.5, "N2")
        b = self._m("BR_CNPJ", 5, 12, 0.4, "N1")
        self.assertEqual(resolve_overlaps([a, b]), [b])
        c = self._m("BR_CPF", 0, 10, 0.9)
        d = self._m("BR_NIS", 0, 12, 0.8)
        self.assertEqual(resolve_overlaps([c, d]), [c])
        e = self._m("BR_CPF", 0, 10, 0.8)
        f = self._m("BR_NIS", 0, 12, 0.8)
        self.assertEqual(resolve_overlaps([e, f]), [f])

    def test_touching_spans_both_kept(self):
        # [TEST-OVERLAP] end == start is not an overlap
        a = self._m("BR_CPF", 0, 5, 0.9)
        b = self._m("BR_CPF", 5, 9, 0.9)
        self.assertEqual(resolve_overlaps([b, a]), [a, b])


class TestValidateAPI(unittest.TestCase):
    def test_validate_all(self):
        # [TEST-API] validate() works for every registered entity
        self.assertTrue(tarja.validate("BR_CNS", "729141777631701"))
        self.assertTrue(tarja.validate("BR_NIS", "12037567083"))
        self.assertTrue(tarja.validate("BR_CNJ", "0000001-83.2017.8.26.0100"))

    def test_entity_without_validator(self):
        # [TEST-API] entity with validator=None raises
        from dataclasses import replace

        from tarja.entities import ENTITIES

        original = ENTITIES["BR_CPF"]
        ENTITIES["BR_TMP"] = replace(original, id="BR_TMP", validator=None)
        try:
            with self.assertRaises(ValueError):
                tarja.validate("BR_TMP", "1")
        finally:
            del ENTITIES["BR_TMP"]


if __name__ == "__main__":
    unittest.main()
