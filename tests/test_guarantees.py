# tests/test_guarantees.py
# EN: the linkage between spec/guarantees.yaml and the suite. A guarantee marked `enforced` must be named by
#   at least one test, and the set marked `open` is pinned, so an acknowledged gap can only be added or
#   removed on purpose. This is the layer coverage and mutation testing cannot provide: both of those start
#   from code that exists, and a requirement nobody implemented has no code to start from.
#   PT: a ligacao entre o spec/guarantees.yaml e a suite. Garantia `enforced` precisa de pelo menos 1 teste
#   citando o id dela, e o conjunto `open` e fixado, entao lacuna reconhecida so entra ou sai de proposito.
#
# [GUAR-TEST] file anchor.

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml
from _guarantees import ATTRIBUTE

ROOT = Path(__file__).resolve().parent.parent
GUARANTEES = ROOT / "spec" / "guarantees.yaml"
TESTS = ROOT / "tests"

# [GUAR-CONST] everything tunable at the top, so no literal hides in the body below.

# EN: the guarantee ids a test claims live on the function, put there by the @guarantees decorator in
#   tests/_guarantees.py. The previous version scanned the test files with a regex over comments, which
#   counted an id anywhere it appeared, including inside a docstring, inside commented-out code and inside a
#   test that was skipped. A skipped test claiming a guarantee is false assurance that nothing reports.
TEST_PATTERN = "test_*.py"

# EN: the id shape. Deliberately narrow so a typo does not silently count as a claim.
ID_RE = re.compile(r"^G-[A-Z0-9]+(?:-[A-Z0-9]+)*$")

# EN: files that define or check the guarantees themselves, so they cannot claim one.
NOT_A_CLAIM = ("test_guarantees.py",)

# EN: the acknowledged gaps, pinned. Each was found by attacking the stated promise, not the code, and each
#   is measured rather than suspected. Changing this list is a decision, which is the point of pinning it.
# EN: empty since 03/10/2026. G-SUSPECT-EXIT was the last one, and it closed when --fail-on-suspect gave
#   the idiom a way to block on a suspect. The DEFAULT exit code did not change and remains the accepted
#   risk in docs/decisions.md: the guarantee was never about the default, it was about the idiom being
#   achievable at all, and before the flag it was not achievable by any combination of options.
#   An empty set is not a claim that nothing is open. It means nothing is open AND KNOWN, which is a much
#   smaller statement, and the blind attack round exists because the gap between the two is where the
#   defects live.
#   PT: vazio desde 03/10/2026. Conjunto vazio nao afirma q nada esta aberto, afirma q nada esta aberto E
#   CONHECIDO, q e afirmacao bem menor.
EXPECTED_OPEN: set[str] = set()


def _load() -> list[dict]:
    with GUARANTEES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["guarantees"]


def _claims() -> set[str]:
    # [GUAR-CLAIM] EN: load every test module and read the attribute off every test function. This is a real
    #   link: the id is on the object the runner executes, so it cannot be claimed by a comment, by dead code
    #   or by a docstring. Works under pytest and under `python -m unittest discover -s tests` alike, because
    #   it depends on neither.
    loader = unittest.TestLoader()
    found: set[str] = set()

    def walk(suite) -> None:
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                walk(item)
                continue
            if isinstance(item, unittest.TestCase):
                method = getattr(type(item), item._testMethodName, None)
                found.update(getattr(method, ATTRIBUTE, ()) or ())

    for path in sorted(TESTS.glob(TEST_PATTERN)):
        if path.name in NOT_A_CLAIM:
            continue
        walk(loader.discover(start_dir=str(TESTS), pattern=path.name, top_level_dir=str(TESTS)))
    if not found:  # pragma: no cover
        raise AssertionError("no test claimed any guarantee, the collector itself is broken")
    return found


class TestGuaranteesFile(unittest.TestCase):
    def test_every_entry_is_well_formed(self):
        # [GUAR-SHAPE] a malformed entry would quietly drop out of the linkage check below
        seen = set()
        for g in _load():
            with self.subTest(guarantee=g.get("id")):
                for field in ("id", "blocks", "violated", "status"):
                    self.assertIn(field, g, f"missing {field}")
                    self.assertTrue(str(g[field]).strip(), f"empty {field}")
                self.assertRegex(g["id"], ID_RE, "id shape")
                self.assertIn(g["status"], ("enforced", "open"))
                self.assertNotIn(g["id"], seen, "duplicate id")
                seen.add(g["id"])


class TestGuaranteesPointAtRealCode(unittest.TestCase):
    def test_every_implemented_in_resolves_by_import(self):
        # [GUAR-IMPL] EN: checking that a FILE exists would be useless, a file survives the deletion of the
        #   function inside it. Import the module and look the symbol up, so a guarantee pointing at code
        #   that no longer exists fails here instead of sitting `enforced` forever on a test that still
        #   passes for an unrelated reason.
        import importlib

        broken = []
        for g in _load():
            target = g.get("implemented_in")
            if not target:
                continue
            module, _, symbol = target.partition(":")
            if not symbol:
                broken.append(f"{g['id']}: {target!r} is not module:symbol")
                continue
            try:
                if not hasattr(importlib.import_module(module), symbol):
                    broken.append(f"{g['id']}: {module} has no {symbol}")
            except ImportError as exc:
                broken.append(f"{g['id']}: cannot import {module} ({exc})")
        self.assertEqual(broken, [], "implemented_in points at code that is not there:\n  " + "\n  ".join(broken))

    def test_only_the_guarantees_about_published_text_may_skip_it(self):
        # [GUAR-IMPL-NULL] EN: null is pinned, so "no symbol" stays a decision instead of becoming the easy
        #   way out of the check above.
        without = sorted(g["id"] for g in _load() if not g.get("implemented_in"))
        self.assertEqual(without, ["G-DOC-COUNT", "G-DOC-INTERNAL", "G-PRESIDIO-TIER"])


class TestGuaranteesAreCovered(unittest.TestCase):
    def test_every_enforced_guarantee_is_named_by_a_test(self):
        # [GUAR-LINK] this is the whole point of the file
        claimed = _claims()
        missing = [g["id"] for g in _load() if g["status"] == "enforced" and g["id"] not in claimed]
        self.assertEqual(
            missing,
            [],
            "guarantee marked enforced but no test names its id:\n  "
            + "\n  ".join(missing)
            + "\n\nName the id in a comment above the assertion that checks it, or set status: open.",
        )

    def test_the_open_gaps_are_the_expected_ones(self):
        # [GUAR-OPEN] an acknowledged gap must be a decision, not a drift
        actual = {g["id"] for g in _load() if g["status"] == "open"}
        self.assertEqual(
            actual,
            EXPECTED_OPEN,
            "the set of acknowledged gaps changed. Closing one: set status to enforced and name the id in a "
            "test. Opening one: say why here, with a measurement.",
        )

    def test_no_test_names_a_guarantee_that_does_not_exist(self):
        # [GUAR-ORPHAN] a renamed id would leave a test claiming nothing, and the claim would still look
        #   like coverage to a reader
        known = {g["id"] for g in _load()}
        orphans = sorted(_claims() - known)
        self.assertEqual(orphans, [], f"test names a guarantee not in {GUARANTEES.name}: {orphans}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
