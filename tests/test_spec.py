# tests/test_spec.py
# [TEST-SPEC] checks spec/entities/*.yaml against the schema and against the code.
#             Needs pyyaml (and jsonschema for one test), skipped otherwise.

import importlib
import json
import os
import pathlib
import re
import unittest

# repo root and spec/ folder
ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"

# optional deps (in the [dev] extra)
try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None
try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

# [TEST-SPEC-NOSKIP] in CI (TARJA_NO_SKIP=1) a missing dependency is an ERROR, never a silent skip
if os.environ.get("TARJA_NO_SKIP") == "1" and (yaml is None or jsonschema is None):
    raise RuntimeError("TARJA_NO_SKIP=1 but pyyaml/jsonschema missing / faltando pyyaml/jsonschema")


def load_specs():
    # [TEST-SPEC] load every yaml -> list of (file_name, dict)
    files = sorted((SPEC / "entities").glob("*.yaml"))
    return [(p.name, yaml.safe_load(p.read_text(encoding="utf-8"))) for p in files]


@unittest.skipIf(yaml is None, "pyyaml missing / sem pyyaml")
class TestSpec(unittest.TestCase):
    def test_schema_is_json(self):
        # [TEST-SPEC] schema.json parses
        json.loads((SPEC / "schema.json").read_text(encoding="utf-8"))

    @unittest.skipIf(jsonschema is None, "jsonschema missing / sem jsonschema")
    def test_specs_match_schema(self):
        # [TEST-SPEC] every yaml passes the schema
        schema = json.loads((SPEC / "schema.json").read_text(encoding="utf-8"))
        for name, spec in load_specs():
            with self.subTest(spec=name):
                jsonschema.validate(spec, schema)

    def test_file_name_matches_id(self):
        # [TEST-SPEC] br_cpf.yaml must have id BR_CPF
        for name, spec in load_specs():
            self.assertEqual(name, spec["id"].lower() + ".yaml")

    def test_regex_compiles(self):
        # [TEST-SPEC] every regex compiles
        for _name, spec in load_specs():
            for p in spec["patterns"]:
                re.compile(p["regex"])

    def test_examples_vs_validator(self):
        # [TEST-SPEC] yaml examples agree with the real validator
        for name, spec in load_specs():
            mod, fn = spec["validator"]["function"].rsplit(".", 1)
            f = getattr(importlib.import_module(mod), fn)
            for v in spec["examples"]["valid"]:
                self.assertTrue(f(v), (name, v))
            for v in spec["examples"]["invalid"]:
                self.assertFalse(f(v), (name, v))

    def test_examples_vs_regex(self):
        # [TEST-SPEC] every valid example matches at least one regex
        for name, spec in load_specs():
            pats = [re.compile(p["regex"]) for p in spec["patterns"]]
            for v in spec["examples"]["valid"]:
                self.assertTrue(any(p.search(v) for p in pats), (name, v))

    def test_registry_matches_yaml(self):
        # [TEST-SPEC] tarja/entities.py (runtime) must mirror the yaml (source of truth)
        from tarja.entities import ENTITIES

        specs = {spec["id"]: spec for _name, spec in load_specs()}
        self.assertEqual(set(specs), set(ENTITIES))
        for eid, spec in specs.items():
            with self.subTest(entity=eid):
                rt = ENTITIES[eid]
                self.assertEqual(rt.tier, spec["tier"])
                self.assertEqual(
                    [(p.name, p.regex.pattern, p.score) for p in rt.patterns],
                    [(p["name"], p["regex"], p["score"]) for p in spec["patterns"]],
                )
                self.assertEqual(list(rt.context_words), spec["context"]["words"])
                self.assertEqual(rt.context_window, spec["context"]["window"])
                self.assertEqual(rt.context_required, spec["context"]["required"])
                self.assertEqual(rt.score_with_context, spec["score"]["valid_with_context"])
                self.assertEqual(rt.score_without_context, spec["score"]["valid_without_context"])
                fn = spec["validator"]["function"].rsplit(".", 1)[1]
                self.assertEqual(rt.validator.__name__, fn)
                self.assertEqual(rt.validator.__module__, spec["validator"]["function"].rsplit(".", 1)[0])


if __name__ == "__main__":
    unittest.main()
