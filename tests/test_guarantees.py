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

ROOT = Path(__file__).resolve().parent.parent
GUARANTEES = ROOT / "spec" / "guarantees.yaml"
TESTS = ROOT / "tests"

# [GUAR-CONST] everything tunable at the top, so no literal hides in the body below.

# EN: where a test may claim a guarantee. A plain mention anywhere in the file counts, which keeps the
#   mechanism cheap: writing the id in the comment above the assertion is the whole ritual.
CLAIM_SUFFIXES = (".py",)

# EN: the id shape. Deliberately narrow so a typo does not silently count as a claim.
ID_RE = re.compile(r"^G-[A-Z0-9]+(?:-[A-Z0-9]+)*$")

# EN: files that define or check the guarantees themselves, so they cannot claim one.
NOT_A_CLAIM = ("test_guarantees.py",)

# EN: the acknowledged gaps, pinned. Each was found by attacking the stated promise, not the code, and each
#   is measured rather than suspected. Changing this list is a decision, which is the point of pinning it.
EXPECTED_OPEN = {
    # scan on a file whose only finding has a failing check digit exits 0, so `scan f.txt && send.sh`
    # sends it. There is a stderr warning, and a warning does not stop &&.
    "G-SUSPECT-EXIT",
    # dataclasses.asdict(match) and vars(match) return the value. repr() and to_dict() do not.
    # Structured logging libraries serialise with asdict, not repr.
    "G-SERIALISE-HIDES",
    # one U+200B, U+200C, U+2060, U+00AD or U+00A0 inside a valid CPF gives zero findings and no suspect.
    "G-NORMALISE-INVISIBLE",
}


def _load() -> list[dict]:
    with GUARANTEES.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["guarantees"]


def _claims() -> set[str]:
    # [GUAR-CLAIM] one pass over the suite, collecting every guarantee id any test names
    found: set[str] = set()
    for path in TESTS.rglob("*"):
        if path.suffix not in CLAIM_SUFFIXES or path.name in NOT_A_CLAIM:
            continue
        found.update(re.findall(r"\bG-[A-Z0-9][A-Z0-9-]*\b", path.read_text(encoding="utf-8", errors="replace")))
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

    def test_blocks_is_written_as_something_to_prevent(self):
        # [GUAR-VOICE] the file is useful only if each line says what must NOT happen. A sentence that
        #   describes what the code does instead of what it forbids is how this file would rot into a
        #   restatement of the implementation, which is the thing it exists to avoid.
        for g in _load():
            with self.subTest(guarantee=g["id"]):
                self.assertRegex(
                    g["blocks"].lower(),
                    r"\bmust not\b|\bmust never\b|\bmust be refused\b|\bmust refuse\b",
                    f"{g['id']}: `blocks` has to state a prohibition, got {g['blocks']!r}",
                )


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
