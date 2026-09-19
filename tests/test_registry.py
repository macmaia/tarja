"""EN: Tests for register_entity / unregister_entity. PT: Testes do registro de entidades proprias."""

import unittest

import tarja
from tarja import Vault, register_entity, residual, unregister_entity


def ie_sp_ok(value: str) -> bool:
    # toy validator for the test: last digit = sum of the others mod 10
    d = [int(c) for c in value if c.isdigit()]
    return len(d) == 12 and sum(d[:-1]) % 10 == d[-1]


class TestRegistry(unittest.TestCase):
    # [TEST-REGISTRY]
    def tearDown(self):
        for eid in ("X_IE_SP", "ACME_ID"):
            unregister_entity(eid)

    def test_custom_entity_flows_everywhere(self):
        register_entity(
            "X_IE_SP",
            [("ie_sp", r"\b\d{3}\.\d{3}\.\d{3}\.\d{3}\b", 0.5)],
            tier="N1",
            validator=ie_sp_ok,
            context_words=["inscricao estadual"],
        )
        text = "inscrição estadual 110.042.490.113 da empresa"
        found = tarja.find(text)
        self.assertEqual([(m.entity, m.value) for m in found], [("X_IE_SP", "110.042.490.113")])
        self.assertEqual(tarja.mask(text), "inscrição estadual <X_IE_SP> da empresa")
        v = Vault()
        prot = v.protect(text)
        self.assertEqual(v.reveal(prot), text)
        self.assertEqual(residual(prot), [])
        self.assertEqual(residual(tarja.mask(text)), [])
        self.assertTrue(tarja.validate("X_IE_SP", "110.042.490.113"))

    def test_n3_needs_context_by_default(self):
        register_entity("ACME_ID", [("acme", r"\bAC-\d{6}\b", 0.3)], context_words=["matricula acme"])
        self.assertEqual(tarja.find("codigo AC-123456"), [])
        self.assertEqual([m.entity for m in tarja.find("matrícula ACME AC-123456")], ["ACME_ID"])

    def test_guards(self):
        with self.assertRaises(ValueError):
            register_entity("BR_CPF", [("x", r"\d", 0.1)])  # built-in, no replace
        with self.assertRaises(ValueError):
            register_entity("bad id", [("x", r"\d", 0.1)])
        with self.assertRaises(ValueError):
            register_entity("ACME_ID", [("x", r"\d", 0.1)], tier="N1")  # N1 without validator
        with self.assertRaises(ValueError):
            register_entity("ACME_ID", [])
        with self.assertRaises(ValueError):
            register_entity("ACME_ID", [("x", r"\d", 0.1)])  # N3 without context words
        with self.assertRaises(ValueError):
            unregister_entity("BR_CPF")
        self.assertNotIn("ACME_ID", tarja.ENTITIES)


if __name__ == "__main__":
    unittest.main()
