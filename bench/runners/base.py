# bench/runners/base.py
# [BENCH-RUNNER-BASE] common base: timing + span helpers.

from __future__ import annotations

import time


class Runner:
    """EN: Subclasses implement predict_one(text). PT: Subclasses implementam predict_one(text)."""

    name = "base"
    # filled in by subclasses, recorded in the results for reproducibility
    info: dict = {}

    def predict_one(self, text: str) -> list[dict]:  # pragma: no cover
        raise NotImplementedError

    def predict(self, texts: list[str]) -> tuple[list[list[dict]], list[float]]:
        """EN: Predictions + latency in ms per doc. PT: Previsoes + latencia em ms por doc."""
        # [BENCH-RUNNER-TIMING]
        preds, lat = [], []
        for t in texts:
            t0 = time.perf_counter()
            preds.append(self.predict_one(t))
            lat.append((time.perf_counter() - t0) * 1000)
        return preds, lat


def span(start: int, end: int, entity: str, score: float = 1.0) -> dict:
    """EN: One prediction in the common format. PT: 1 previsao no formato comum."""
    return {"start": int(start), "end": int(end), "entity": entity, "score": float(score)}


def locate(text: str, needle: str, used: set[int]) -> int | None:
    """EN: First occurrence of needle not already used (for systems that return text, not offsets).
    PT: 1a ocorrencia de needle ainda nao usada (p/ sistema q devolve texto, nao offset).
    """
    # [BENCH-RUNNER-LOCATE]
    start = 0
    while True:
        i = text.find(needle, start)
        if i < 0:
            return None
        if i not in used:
            used.add(i)
            return i
        start = i + 1
