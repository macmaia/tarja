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


class TestFreeze(unittest.TestCase):
    # [TEST-REGISTRY-FREEZE] the registry is module-level state that find() reads on every call, so the
    #   supported shape is: register at start-up, freeze, then serve. These check the window really shuts.
    def setUp(self):
        tarja.unfreeze()
        # addCleanup runs in reverse, so register the removal FIRST and the unfreeze SECOND: the unfreeze then
        # happens before the removal, which would otherwise hit a frozen registry
        self.addCleanup(tarja.unregister_entity, "FREEZE_TEST_ID")
        self.addCleanup(tarja.unfreeze)

    def test_registration_works_before_freezing(self):
        tarja.register_entity("FREEZE_TEST_ID", [("t", r"\bFZ-\d{4}\b", 0.3)], context_words=["freeze"])
        self.assertIn("FREEZE_TEST_ID", tarja.ENTITIES)

    def test_register_after_freeze_raises(self):
        tarja.freeze()
        with self.assertRaises(tarja.RegistryFrozenError):
            tarja.register_entity("FREEZE_TEST_ID", [("t", r"\bFZ-\d{4}\b", 0.3)], context_words=["freeze"])

    def test_unregister_after_freeze_raises(self):
        tarja.register_entity("FREEZE_TEST_ID", [("t", r"\bFZ-\d{4}\b", 0.3)], context_words=["freeze"])
        tarja.freeze()
        with self.assertRaises(tarja.RegistryFrozenError):
            tarja.unregister_entity("FREEZE_TEST_ID")

    def test_freeze_is_idempotent_and_reversible(self):
        tarja.freeze()
        tarja.freeze()
        self.assertTrue(tarja.is_frozen())
        tarja.unfreeze()
        self.assertFalse(tarja.is_frozen())

    def test_freezing_does_not_stop_detection(self):
        tarja.freeze()
        self.assertEqual([m.entity for m in tarja.find("cpf 529.982.247-25")], ["BR_CPF"])

    def test_concurrent_registration_does_not_interleave(self):
        # [TEST-REGISTRY-LOCK] not a proof of thread safety, just that the lock serialises writers and that
        #   every registration either happened completely or raised
        import threading

        errors = []

        def worker(i):
            try:
                tarja.register_entity(f"FZ_CONC_{i}", [("t", rf"\bFZ{i}-\d{{4}}\b", 0.3)], context_words=["fz"])
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        try:
            self.assertEqual(errors, [])
            for i in range(12):
                self.assertIn(f"FZ_CONC_{i}", tarja.ENTITIES)
                self.assertEqual(tarja.ENTITIES[f"FZ_CONC_{i}"].id, f"FZ_CONC_{i}")
        finally:
            for i in range(12):
                tarja.unregister_entity(f"FZ_CONC_{i}")
