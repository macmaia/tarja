# tests/test_evasao.py
# EN: evasion by normalisation. One character a reader cannot see, inserted inside a valid identifier, used
#   to make find() return nothing at all, not even a suspect. Ten characters across five classes were
#   measured on 01/10/2026. This file is the property that closes the class, not a list of ten examples:
#   every character, in every position of a valid identifier, for every entity that has a check digit.
# PT: evasao por normalizacao. 1 caractere q o leitor nao ve, dentro de um identificador valido, fazia o
#   find() nao devolver nada, nem suspeito. Este arquivo fixa a propriedade, nao dez exemplos.
#
# [EVA] file anchor.

from __future__ import annotations

import unittest

from _guarantees import Swept, guarantees

from tarja import find, mask
from tarja.normalise import has_invisible_near_digit, is_invisible, strip_invisible

# [EVA-CONST] the measured set, one per class, by codepoint so the source stays greppable.
INVISIBLES = {
    "ZWSP U+200B": "​",
    "ZWNJ U+200C": "‌",
    "WORD JOINER U+2060": "⁠",
    "SOFT HYPHEN U+00AD": "­",
    "BIDI RLO U+202E": "‮",
    "VARIATION SELECTOR U+FE00": "︀",
    "COMBINING ACUTE U+0301": "́",
    "TAG DIGIT U+E0035": "\U000e0035",
    "HANGUL FILLER U+3164": "ㅤ",
}

# EN: one valid identifier per tier-N1 entity, generated, never real.
VALID = {
    "BR_CPF": "529.982.247-25",
    "BR_CNPJ": "11.222.333/0001-81",
    "BR_CNS": "898 0000 0004 3208",
}

CONTEXT = {"BR_CPF": "CPF", "BR_CNPJ": "CNPJ", "BR_CNS": "cartao SUS"}


class TestInvisibleSetIsCoherent(unittest.TestCase):
    def test_every_measured_character_is_recognised_as_invisible(self):
        # [EVA-SET] the strip and the trigger read one constant, so a character the set does not know is a
        #   character neither of them handles. This test is what makes that constant the real boundary.
        for name, ch in INVISIBLES.items():
            with self.subTest(char=name):
                self.assertTrue(is_invisible(ch), f"{name} is not in the invisible set")

    def test_stripping_keeps_an_offset_map_that_points_back(self):
        # [EVA-MAP] the whole fix rests on this: a position in the stripped text must translate to the
        #   position of the same character in the original, or mask() cuts in the wrong place.
        for name, ch in INVISIBLES.items():
            with self.subTest(char=name):
                original = f"CPF 529.982{ch}.247-25"
                stripped, index_map = strip_invisible(original)
                self.assertEqual(len(stripped), len(index_map))
                self.assertNotIn(ch, stripped)
                for i, c in enumerate(stripped):
                    self.assertEqual(original[index_map[i]], c, "index map points at the wrong character")

    def test_the_trigger_ignores_ordinary_accented_prose(self):
        # [EVA-TRIGGER] Portuguese decomposed to NFD carries a combining mark on nearly every accented word.
        #   A trigger that only asked "does this text contain a combining mark" would fire on any Brazilian
        #   document and double the cost of the common path for nothing.
        import unicodedata

        prose = unicodedata.normalize("NFD", "Jose da Silva, residente a rua Sao Joao, nesta cidade.")
        self.assertFalse(has_invisible_near_digit(prose))


class TestOneInvisibleCharacterCannotHideAnIdentifier(unittest.TestCase):
    """EN: the property. PT: a propriedade."""

    @guarantees("G-NORMALISE-INVISIBLE")
    def test_every_invisible_in_every_position_is_still_detected(self):
        # [EVA-PROPERTY] EN: this is the test that would have caught the defect. It fails on every version
        #   before 01/10/2026, for every entity, every character and every position.
        missed = []
        # [EVA-SWEPT] 3 entities x 9 characters x the interior positions of each identifier. If the product
        #   ever collapses, every case below stops running and the test still reports success.
        cases = Swept(
            ((e, v, n, ch, pos) for e, v in VALID.items() for n, ch in INVISIBLES.items()
             for pos in range(1, len(v))),
            "entity x invisible x position", minimum=300,
        )  # fmt: skip
        for entity, value, name, ch, pos in cases:
            # every gap between two characters of the identifier, borders excluded: an invisible on the
            # border sits outside the identifier and is a different question
            text = f"{CONTEXT[entity]} {value[:pos]}{ch}{value[pos:]}"
            hits = [m for m in find(text) if m.entity == entity]
            if not hits:
                missed.append(f"{entity} {name} at offset {pos}")
            elif text[hits[0].start : hits[0].end] != hits[0].value:
                missed.append(f"{entity} {name} at offset {pos}: offsets do not slice the value")
        cases.check(self)
        self.assertEqual(missed, [], f"{len(missed)} evaded detection:\n  " + "\n  ".join(missed[:20]))

    @guarantees("G-NORMALISE-INVISIBLE")
    def test_an_evaded_identifier_is_masked_out_of_the_document(self):
        # [EVA-MASK] detecting it is half. The document that leaves must not carry the digits.
        for name, ch in INVISIBLES.items():
            with self.subTest(char=name):
                text = f"Contrato de CPF 529.982.247{ch}-25 assinado hoje."
                out = mask(text)
                self.assertIn("<BR_CPF>", out)
                leftovers = out.replace("<BR_CPF>", "")
                self.assertFalse(any(c.isdigit() for c in leftovers), f"digits survived masking: {out!r}")

    @guarantees("G-LABEL-CANONICAL")
    def test_the_stable_label_does_not_depend_on_the_spelling(self):
        # [EVA-CANON] the same person must get the same label whether or not the document carries an
        #   invisible character or a circled digit, otherwise joining records across files silently breaks.
        key = "7f3b9a1c5d2e8046aa11bb22cc33dd44"
        circled = "529.982.247-25".translate({ord(d): 0x245F + int(d) for d in "123456789"} | {ord("0"): 0x24EA})
        spellings = ["529.982.247-25", "52998224725", "529.982.247​-25", circled]
        labels = {mask(f"CPF {s}", strategy="pseudonym_stable", salt=key).split("CPF ")[1] for s in spellings}
        self.assertEqual(len(labels), 1, f"one identifier produced {len(labels)} different labels: {labels}")


class TestEvasionDoesNotInventFindings(unittest.TestCase):
    @guarantees("G-NORMALISE-INVISIBLE")
    def test_joining_across_a_removed_character_needs_a_check_digit_or_context(self):
        # [EVA-BAR] EN: removing a soft hyphen where a line break was joins two number groups that were
        #   never one number. A tier with a check digit survives that on its own, because a wrong join
        #   closes the digit about one time in a hundred. A tier without one has nothing to fall back on,
        #   so the evaded candidate is only accepted with a context word nearby.
        #
        #   The first version of this test looped over the entities, skipped the N1 ones and then asserted
        #   the remaining tier was not N1. A tautology: it could not fail. The mutation run caught it, which
        #   is the only reason it is written properly now. Verified against the mutant: with the bar removed,
        #   the first case below invents a BR_TELEFONE with has_context False.
        #   PT: tirar um hifen opcional numa quebra de linha junta dois grupos q nunca foram um numero. A 1a
        #   versao deste teste era tautologia e nao podia falhar. Quem pegou foi a rodada de mutacao.
        forged = "itens 119876\u00ad54321 do estoque"
        self.assertEqual(
            [m for m in find(forged) if m.entity == "BR_TELEFONE"],
            [],
            "a number group joined across a removed character, with no context word and no check digit, "
            "must not be reported: that is an invented finding, not a detection",
        )

        with_context = "telefone 119876\u00ad54321 do cliente"
        hits = [m for m in find(with_context) if m.entity == "BR_TELEFONE"]
        self.assertEqual(len(hits), 1, "the same digits WITH a context word are a real detection")
        self.assertTrue(hits[0].has_context)

    @guarantees("G-NORMALISE-INVISIBLE")
    def test_a_check_digit_carries_an_evaded_match_without_any_context_word(self):
        # [EVA-BAR-N1] the other half of the bar: a tier that validates a check digit does not need a
        #   context word, because the digit is the evidence. Without this, raising the bar for everyone
        #   would have quietly undone the fix for the case it exists for.
        hits = [m for m in find("segue o numero 529.982.247\u200b-25 para cadastro") if m.entity == "BR_CPF"]
        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0].has_context, "no context word in that sentence, the check digit carried it")

    def test_the_benchmark_corpus_is_untouched_by_the_extra_pass(self):
        # [EVA-NEUTRAL] the published F1 figures were measured before this pass existed. If the pass changed
        #   any result on the published data, the numbers would have to be re-measured and republished.
        #   Checked over all 10,000 benchmark documents on 01/10/2026: the trigger fired on none of them and
        #   find() returned identical results with the pass on and off. This test keeps a sample of that
        #   proof cheap enough to run every time.
        clean = [
            "Processo 0002907-25.2015.8.26.0100 distribuido nesta data.",
            "O CPF 529.982.247-25 consta do cadastro, assim como o CNPJ 11.222.333/0001-81.",
            "Art. 5 Todos sao iguais perante a lei, sem distincao de qualquer natureza.",
        ]
        for text in clean:
            with self.subTest(text=text[:40]):
                self.assertFalse(has_invisible_near_digit(text), "trigger fired on clean text")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
