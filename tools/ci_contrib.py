# tools/ci_contrib.py
# [CI-CONTRIB] keeps contrib/presidio-pr honest until the upstream PR merges. Installs the kit's recognizers
#   into the presidio-analyzer that is pip-installed in this environment, then runs the kit's own tests with a
#   small shim for the two helpers they borrow from Presidio's test suite (assert_result_within_score_range and
#   the max_score fixture). Delete this file and the CI job once the PR is merged upstream.
#
# usage (CI):  pip install presidio-analyzer pytest && python tools/ci_contrib.py

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "contrib" / "presidio-pr" / "presidio-analyzer"
IMPORT_LINE = (
    "from presidio_analyzer.predefined_recognizers.country_specific.brazil import BrCnpjRecognizer, BrCpfRecognizer\n"
)

SHIM_INIT = """
import pytest


def assert_result_within_score_range(result, expected_entity_type, expected_start, expected_end,
                                     expected_score_min, expected_score_max):
    # mirrors Presidio's tests/assertions.py helper
    assert result.entity_type == expected_entity_type
    assert result.start == expected_start
    assert result.end == expected_end
    assert expected_score_min - 1e-9 <= result.score <= expected_score_max + 1e-9
"""

SHIM_CONFTEST = """
import pytest
from presidio_analyzer import EntityRecognizer


@pytest.fixture(scope="session")
def max_score():
    return EntityRecognizer.MAX_SCORE
"""


def main() -> int:
    # [CI-CONTRIB-INSTALL] copy br/ into the installed package and expose the classes
    import presidio_analyzer

    pkg = Path(presidio_analyzer.__file__).parent / "predefined_recognizers"
    dest = pkg / "country_specific" / "brazil"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(KIT / "presidio_analyzer" / "predefined_recognizers" / "country_specific" / "brazil", dest)
    init = pkg / "__init__.py"
    if IMPORT_LINE not in init.read_text(encoding="utf-8"):
        with init.open("a", encoding="utf-8") as fh:
            fh.write("\n" + IMPORT_LINE)
    # [CI-CONTRIB-RUN] kit tests + shim in a clean folder
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / "tests"
        t.mkdir()
        (t / "__init__.py").write_text(SHIM_INIT, encoding="utf-8")
        (Path(tmp) / "conftest.py").write_text(SHIM_CONFTEST, encoding="utf-8")
        for f in (KIT / "tests").glob("test_br_*.py"):
            shutil.copy(f, t / f.name)
        return subprocess.call([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(t)], cwd=tmp)


if __name__ == "__main__":
    raise SystemExit(main())
