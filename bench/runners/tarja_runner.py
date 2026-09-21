# bench/runners/tarja_runner.py
# [BENCH-RUNNER-TARJA] tarja itself, pinned version recorded.

from __future__ import annotations

import tarja
from bench.runners.base import Runner, span


class TarjaRunner(Runner):
    name = "tarja"

    def __init__(self, min_score: float = 0.0):
        self.min_score = min_score
        self.info = {"tarja_version": tarja.__version__, "min_score": min_score}

    def predict_one(self, text: str) -> list[dict]:
        # [BENCH-RUNNER-TARJA-PREDICT]
        return [span(m.start, m.end, m.entity, m.score) for m in tarja.find(text, min_score=self.min_score)]
