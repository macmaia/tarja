#!/usr/bin/env python3
# tools/check_test_floor.py
# EN: refuse a suite that shrank. See spec/test_floor.yaml for why this exists at all.
#   It lives in tools/ and reads spec/, so deleting tests/ does not delete the guard that notices.
# PT: recusa suite que encolheu. Mora em tools/ e le o spec/, entao apagar tests/ nao apaga a guarda.
#
# [FLOOR-CHECK] file anchor. Run: python tools/check_test_floor.py

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOOR = ROOT / "spec" / "test_floor.yaml"
PATTERN = "tests/test_*.py"


def collected() -> int:
    # [FLOOR-COLLECT] run the discovery the project actually uses, and read the count it prints
    run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT,
        env={"PYTHONPATH": "src:.", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    m = re.search(r"^Ran (\d+) tests?", run.stderr, re.M)
    if not m:
        raise SystemExit(f"could not read the test count from the runner:\n{run.stderr[-800:]}")
    return int(m.group(1))


def tracked() -> int | None:
    # [FLOOR-TRACKED] EN: this is the number the disk cannot tell you. A rename staged with `git add -u`
    #   leaves the new files untracked, so the disk count stays put and only this one falls.
    #   Returns None outside a git checkout (an installed wheel, a mutation tempdir), where it means nothing.
    try:
        run = subprocess.run(["git", "ls-files", PATTERN], cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if run.returncode != 0:
        return None
    return len([line for line in run.stdout.splitlines() if line.strip()])


def main() -> int:
    floor = yaml.safe_load(FLOOR.read_text(encoding="utf-8"))
    problems = []

    found = collected()
    if found < floor["collected"]:
        problems.append(
            f"the suite collects {found} tests, the floor is {floor['collected']}. "
            f"Tests were removed. If that was deliberate, lower the floor in {FLOOR.name} and say why."
        )

    files = tracked()
    if files is None:
        print("note: not a git checkout, the tracked-file floor was not checked")
    elif files < floor["tracked_files"]:
        problems.append(
            f"git is tracking {files} test files, the floor is {floor['tracked_files']}. "
            f"A test file was deleted or a rename was staged without its new side, which is the failure "
            f"this check exists for: the suite can stay green while the repository loses the tests."
        )

    for p in problems:
        print("FAIL:", p)
    if not problems:
        print(f"ok: {found} tests collected (floor {floor['collected']}), "
              f"{files} test files tracked (floor {floor['tracked_files']})")  # fmt: skip
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
