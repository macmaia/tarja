# bench/runners/presidio_runner.py
# [BENCH-RUNNER-PRESIDIO] EN: Presidio out of the box (English defaults, the "foreign tool" baseline) and
#   Presidio + presidio-br. Needs: pip install presidio-analyzer (+ packages/presidio-br).
# [BENCH-RUNNER-PRESIDIO] PT: Presidio padrao (defaults em ingles, a linha de base "ferramenta gringa") e
#   Presidio + presidio-br. Precisa: pip install presidio-analyzer (+ packages/presidio-br).

from __future__ import annotations

from bench.runners.base import Runner, span

# [BENCH-RUNNER-PRESIDIO-MAP] EN: Presidio default entities that can overlap ours / PT: entidades padrao q podem casar
DEFAULT_MAP = {"PHONE_NUMBER": "BR_TELEFONE"}


class PresidioDefaultRunner(Runner):
    name = "presidio-default"

    def __init__(self, score_threshold: float = 0.0):
        import presidio_analyzer
        from presidio_analyzer import AnalyzerEngine

        # EN: default English engine, as a foreign company would install it / PT: motor padrao em ingles
        self.engine = AnalyzerEngine()
        self.th = score_threshold
        self.info = {"presidio_version": getattr(presidio_analyzer, "__version__", "?"), "language": "en"}

    def predict_one(self, text: str) -> list[dict]:
        res = self.engine.analyze(text=text, language="en", score_threshold=self.th)
        return [span(r.start, r.end, DEFAULT_MAP.get(r.entity_type, "OTHER"), r.score) for r in res]


class PresidioBrRunner(Runner):
    name = "presidio-br"

    def __init__(self, score_threshold: float = 0.4):
        import presidio_br
        from presidio_analyzer import RecognizerRegistry

        self.registry = RecognizerRegistry(supported_languages=["pt"])
        presidio_br.register(self.registry)
        self.th = score_threshold
        self.info = {"presidio_br_version": presidio_br.__version__, "score_threshold": score_threshold}

    def predict_one(self, text: str) -> list[dict]:
        # EN: pattern recognizers only, no NLP model needed / PT: so reconhecedores de padrao, sem modelo NLP
        out = []
        for rec in self.registry.recognizers:
            for r in rec.analyze(text, rec.supported_entities):
                if r.score >= self.th:
                    out.append(span(r.start, r.end, r.entity_type, r.score))
        return out
