# bench/runners/presidio_runner.py
# [BENCH-RUNNER-PRESIDIO] Presidio out of the box (English defaults, the "foreign tool" baseline) and
#   Presidio + tarja-presidio. Needs: pip install presidio-analyzer (+ packages/tarja-presidio).

from __future__ import annotations

from bench.runners.base import Runner, span

# [BENCH-RUNNER-PRESIDIO-MAP] Presidio default entities that can overlap ours
DEFAULT_MAP = {"PHONE_NUMBER": "BR_TELEFONE"}


class PresidioDefaultRunner(Runner):
    name = "presidio-default"

    def __init__(self, score_threshold: float = 0.0):
        import presidio_analyzer
        from presidio_analyzer import AnalyzerEngine

        # default English engine, as a foreign company would install it
        self.engine = AnalyzerEngine()
        self.th = score_threshold
        self.info = {"presidio_version": getattr(presidio_analyzer, "__version__", "?"), "language": "en"}

    def predict_one(self, text: str) -> list[dict]:
        res = self.engine.analyze(text=text, language="en", score_threshold=self.th)
        return [span(r.start, r.end, DEFAULT_MAP.get(r.entity_type, "OTHER"), r.score) for r in res]


class PresidioBrRunner(Runner):
    name = "tarja-presidio"

    def __init__(self, score_threshold: float = 0.4):
        import tarja_presidio
        from presidio_analyzer import RecognizerRegistry

        self.registry = RecognizerRegistry(supported_languages=["pt"])
        tarja_presidio.register(self.registry)
        self.th = score_threshold
        self.info = {"tarja_presidio_version": tarja_presidio.__version__, "score_threshold": score_threshold}

    def predict_one(self, text: str) -> list[dict]:
        # pattern recognizers only, no NLP model needed
        out = []
        for rec in self.registry.recognizers:
            for r in rec.analyze(text, rec.supported_entities):
                if r.score >= self.th:
                    out.append(span(r.start, r.end, r.entity_type, r.score))
        return out
