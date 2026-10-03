# tests/_guarantees.py
# EN: the decorator a test uses to claim a guarantee from spec/guarantees.yaml.
#
#   Why not a pytest marker. The suite is unittest, and it runs under BOTH pytest and
#   `python -m unittest discover -s tests`, which is the path tools/mutation_check.py uses. A
#   `@pytest.mark.x` needs `import pytest` at module import time, which would make pytest a hard dependency
#   of the unittest path. If pytest were missing from a mutant's environment, every mutant would "die" on
#   ImportError and the mutation run would be measuring nothing at all while reporting a perfect score.
#   A plain attribute on the function needs no dependency, works in both runners, and is a real link rather
#   than a string someone wrote in a comment.
#
#   Why not the regex over comments it replaces. That scan counted the id anywhere it appeared: in a
#   docstring, in commented-out code, in a skipped test. A skipped test claiming a guarantee is false
#   assurance that nothing reports.
#   PT: decorator q um teste usa p/ reivindicar uma garantia. Nao e marcador do pytest pq a suite roda tb no
#   `unittest discover`, q e o caminho do mutation_check, e `import pytest` ali tornaria o pytest
#   dependencia dura: faltando ele, todo mutante morreria por ImportError e a medicao viraria nada.
#
# [GUAR-DECOR] file anchor.

from __future__ import annotations

from collections.abc import Callable

ATTRIBUTE = "tarja_guarantees"


def guarantees(*ids: str) -> Callable:
    """EN: Mark a test as the thing that checks these guarantees. PT: Marca o teste q confere estas."""
    if not ids:
        raise ValueError("guarantees() needs at least one id / precisa de pelo menos 1 id")
    for i in ids:
        if not i.startswith("G-"):
            raise ValueError(f"not a guarantee id: {i!r} / nao e id de garantia")

    def wrap(fn: Callable) -> Callable:
        setattr(fn, ATTRIBUTE, tuple(ids))
        return fn

    return wrap
