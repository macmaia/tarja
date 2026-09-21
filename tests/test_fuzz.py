"""EN: Fuzz tests for find(): never crashes, offsets always point at the original text, no overlaps, bounded time.
PT: Testes de fuzz do find(): nunca quebra, offsets sempre apontam p/ o texto original, sem sobreposicao, tempo limitado.
"""

import os
import random
import time
import unittest

import tarja

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover
    given = None

# [TEST-FUZZ-NOSKIP] in CI a missing hypothesis is an error, never a silent skip
if os.environ.get("TARJA_NO_SKIP") == "1" and given is None:
    raise RuntimeError("TARJA_NO_SKIP=1 but hypothesis missing")

# characters that stress the normaliser: digits, separators, accents, fullwidth and Arabic-Indic digits,
# zero-width and combining marks, surrogate-free emoji, RTL mark, NBSP
ALPHABET = "0123456789.-/ \n\t|:ABCXYZabcçãéíõº°ª０１２３٠١٢٣​́‏ 🙂CPFcnpjCNSprocesso"


def check_invariants(testcase: unittest.TestCase, text: str, **kw) -> None:
    # [TEST-FUZZ-INVARIANTS]
    found = tarja.find(text, **kw)
    last_end = -1
    for m in sorted(found, key=lambda m: m.start):
        testcase.assertIn(m.entity, tarja.ENTITIES)
        testcase.assertTrue(0 <= m.start < m.end <= len(text), (m, len(text)))
        testcase.assertEqual(text[m.start : m.end], m.value)
        testcase.assertTrue(0.0 <= m.score <= 1.0)
        if kw.get("resolve", True) and not kw.get("report_invalid"):
            testcase.assertGreaterEqual(m.start, last_end, "overlap after resolve")
            last_end = m.end


def noisy(rng: random.Random, n: int) -> str:
    # random noise with real identifiers spliced in, so the fuzz also walks the match paths
    parts = []
    while sum(map(len, parts)) < n:
        if rng.random() < 0.15:
            parts.append(
                rng.choice(["529.982.247-25", "12.ABC.345/01DE-35", "0000001-83.2017.8.26.0100", "4111 1111 1111 1111"])
            )
        else:
            parts.append("".join(rng.choice(ALPHABET) for _ in range(rng.randint(1, 30))))
    return "".join(parts)


class TestFuzzSeeded(unittest.TestCase):
    # [TEST-FUZZ-SEEDED] runs everywhere, no extra dependency
    def test_random_text(self):
        rng = random.Random(2026)
        for _ in range(300):
            text = noisy(rng, rng.randint(0, 400))
            check_invariants(self, text)
            check_invariants(self, text, report_invalid=True)
            check_invariants(self, text, resolve=False)

    def test_large_input_is_linear(self):
        # [TEST-FUZZ-SCALE] 10x the input must not cost much more than ~10x the time (catches quadratic paths)
        rng = random.Random(7)
        small, big = noisy(rng, 20_000), noisy(rng, 200_000)
        t0 = time.perf_counter()
        tarja.find(small)
        t1 = time.perf_counter()
        tarja.find(big)
        t2 = time.perf_counter()
        self.assertLess(t2 - t1, max(0.5, 30 * (t1 - t0)))


if given is not None:

    class TestFuzzHypothesis(unittest.TestCase):
        # [TEST-FUZZ-HYPOTHESIS] shrinking fuzz over arbitrary Unicode and over the stress alphabet
        @settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
        @given(st.text(max_size=300))
        def test_any_unicode(self, text):
            check_invariants(self, text)

        @settings(max_examples=300, deadline=None)
        @given(st.text(alphabet=ALPHABET, max_size=300))
        def test_stress_alphabet(self, text):
            check_invariants(self, text)
            check_invariants(self, text, report_invalid=True)


if __name__ == "__main__":
    unittest.main()
