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


# [GUAR-INTERNAL] EN: spec/guarantees.yaml is published, and the published file carries promises to the
#   USER only. A rule about the test bench itself is not one of those, and G-SWEEP-NONEMPTY was in there by
#   mistake: it says a sweep that examined nothing must fail, which no user of the library can observe.
#   It moved to spec/guarantees-internal.yaml, which is gitignored, and that creates a trap: a published
#   test claiming an id that lives in an untracked file is an orphan in any fresh clone, so CI would fail
#   on a checkout that is perfectly correct. Hence a separate marker with a GI- prefix and its own
#   attribute. The id stays visible on the test, which is the whole point (a test nobody can trace back to
#   a reason gets deleted in two years as dead weight), and it is never counted as a public claim.
#   PT: o guarantees.yaml e publico e carrega promessa ao USUARIO. Regra sobre a propria bancada de teste
#   nao e promessa ao usuario, e a G-SWEEP-NONEMPTY estava lah por engano. Foi p/ o arquivo interno, q e
#   gitignored, e teste publico reivindicando id de arquivo nao versionado quebraria o CI num clone limpo.
#   Dai um marcador separado, prefixo GI-, atributo proprio. O id continua visivel no teste, q e o ponto.
ATTRIBUTE_INTERNAL = "tarja_guarantees_internal"


def internal_guarantee(*ids: str) -> Callable:
    """EN: Mark a test as the check for an INTERNAL rule, described in spec/guarantees-internal.yaml.
    PT: Marca o teste q confere regra INTERNA, descrita no spec/guarantees-internal.yaml.
    """
    if not ids:
        raise ValueError("internal_guarantee() needs at least one id / precisa de pelo menos 1 id")
    for i in ids:
        if not i.startswith("GI-"):
            raise ValueError(f"internal ids start with GI-: {i!r} / id interno comeca com GI-")

    def wrap(fn: Callable) -> Callable:
        setattr(fn, ATTRIBUTE_INTERNAL, tuple(ids))
        return fn

    return wrap


# [GUAR-SWEPT] EN: a sweep that examined nothing passes. Three tests in this project did exactly that: a
#   regex that matched no count, an exemption that emptied the set, a filter placed before the assertion.
#   Each one passed in the precise case it had been written to catch, and each looked like a working test.
#
#   The fix is not care, it is arithmetic: a sweep has to say how many items it looked at, and that number
#   has to clear a floor. Wrap the iterable and the test cannot pass vacuously any more.
#   PT: varredura q nao examinou nada passa. Tres testes aqui fizeram exatamente isso. O conserto nao e
#   cuidado, e aritmetica: a varredura diz quantos itens olhou e esse numero tem de passar de um piso.


class Swept:
    """EN: Counts what a sweep actually looked at. PT: Conta o que a varredura de fato olhou."""

    __slots__ = ("_items", "_label", "_minimum", "count")

    def __init__(self, items, label: str, minimum: int = 1) -> None:
        if minimum < 1:
            raise ValueError("a sweep that may examine nothing is not a sweep / piso tem de ser >= 1")
        self._items = items
        self._label = label
        self._minimum = minimum
        self.count = 0

    def __iter__(self):
        for item in self._items:
            self.count += 1
            yield item

    def check(self, test) -> None:
        """EN: Call at the end of the test. PT: Chame no fim do teste."""
        test.assertGreaterEqual(
            self.count,
            self._minimum,
            f"the sweep over {self._label} examined {self.count} item(s), the floor is {self._minimum}. "
            f"A test that examines nothing reports success without checking anything, which is how three "
            f"guards in this repository passed in the exact case they existed to catch.",
        )
