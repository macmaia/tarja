#!/usr/bin/env python3
# tools/claimants.py
# [CLAIM] EN: list the tests that claim a guarantee from spec/guarantees.yaml, one per line, so a loop can
#   ask tools/mutation_check.py --for-test what each one actually kills. The rule it feeds is: a test that
#   claims a guarantee must kill at least one mutant, otherwise it is a claim with nothing behind it.
#
#   Why a script in tools/ and not a flag on the package: a flag on a published CLI is a compatibility
#   commitment forever, and this is internal plumbing that the CI consumes. Measured need, 02/10/2026,
#   when four of the claiming tests turned out to kill nothing.
#
#   Why it reads the loader and not the files: the earlier idea was a regex over the test sources, which
#   counts an id anywhere it appears, including in a docstring, in commented-out code and in a skipped
#   test. The id has to be on the object the runner executes, which is what unittest discovery gives.
#   PT: lista os testes q reivindicam garantia, 1 por linha, p/ alimentar o laco q pergunta ao
#   mutation_check --for-test quantos mutantes cada um mata. Fica em tools/ e nao como flag do pacote:
#   flag em CLI publicada e compromisso de compatibilidade p/ sempre, e isto e encanamento interno.
#
# usage / uso:
#   python tools/claimants.py                 -> test_modulo.Classe.test_nome  (um por linha)
#   python tools/claimants.py --with-ids      -> acrescenta os ids reivindicados
#   python tools/claimants.py --internal      -> os de @internal_guarantee, q NAO entram na regra

from __future__ import annotations

import argparse
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
# [CLAIM-PATH] same three entries mutation_check uses, and for the same reason: tests/ has no __init__.py,
#   so the test modules only import with tests/ on the path.
for entry in ("src", ".", "tests"):
    sys.path.insert(0, str(ROOT / entry))

from _guarantees import ATTRIBUTE, ATTRIBUTE_INTERNAL  # noqa: E402

# [CLAIM-SKIP] the file that defines and checks the guarantees cannot claim one
NOT_A_CLAIM = ("test_guarantees.py",)


def walk(suite, attribute: str, out: list[tuple[str, tuple[str, ...]]]) -> None:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            walk(item, attribute, out)
            continue
        if not isinstance(item, unittest.TestCase):
            continue
        method = getattr(type(item), item._testMethodName, None)
        ids = getattr(method, attribute, ()) or ()
        if ids:
            out.append((f"{type(item).__module__}.{type(item).__name__}.{item._testMethodName}", tuple(ids)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tests that claim a guarantee / testes q reivindicam garantia")
    ap.add_argument("--with-ids", action="store_true", help="print the claimed ids too / mostra tb os ids")
    ap.add_argument("--internal", action="store_true", help="internal rules instead / regras internas")
    args = ap.parse_args(argv)

    attribute = ATTRIBUTE_INTERNAL if args.internal else ATTRIBUTE
    loader = unittest.TestLoader()
    rows: list[tuple[str, tuple[str, ...]]] = []
    for path in sorted(TESTS.glob("test_*.py")):
        if path.name in NOT_A_CLAIM:
            continue
        walk(loader.discover(start_dir=str(TESTS), pattern=path.name, top_level_dir=str(TESTS)), attribute, rows)

    if not rows:
        # [CLAIM-EMPTY] an empty list is almost certainly this script being broken, not a suite with no
        #   claims, and a silent empty list would make the CI loop pass over nothing.
        sys.stderr.write("claimants.py found no claiming test, which means this script is broken\n")
        return 1
    for name, ids in sorted(set(rows)):
        sys.stdout.write(f"{name} {' '.join(ids)}\n" if args.with_ids else f"{name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
