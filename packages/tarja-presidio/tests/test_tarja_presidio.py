# packages/tarja-presidio/tests/test_tarja_presidio.py
# [TEST-PRESIDIO-BR] runs against the REAL presidio-analyzer. Locally it's skipped if Presidio isn't installed,
#   but in CI TARJA_REQUIRE_PRESIDIO=1 turns a missing Presidio into a hard failure (no silent skip).

import os
import pathlib

import pytest

if os.environ.get("TARJA_REQUIRE_PRESIDIO") == "1":
    import presidio_analyzer  # noqa: F401  must import, or fail
else:
    pytest.importorskip("presidio_analyzer")

import tarja_presidio  # noqa: E402
import yaml  # noqa: E402

from tarja.entities import ENTITIES  # noqa: E402

# repo root, to read the yaml examples
ROOT = pathlib.Path(__file__).resolve().parents[3]


def _examples(entity_id):
    spec = yaml.safe_load((ROOT / "spec" / "entities" / f"{entity_id.lower()}.yaml").read_text(encoding="utf-8"))
    return spec["examples"]["valid"], spec["examples"]["invalid"]


def test_one_recognizer_per_entity():
    # [TEST-PRESIDIO-BR] all entities, right names and country
    recs = tarja_presidio.get_recognizers()
    assert [r.supported_entities[0] for r in recs] == list(ENTITIES)
    assert all(r.COUNTRY_CODE == "br" and r.supported_language == "pt" for r in recs)
    assert recs[0].name == "BrCpfRecognizer"


@pytest.mark.parametrize("entity_id", list(ENTITIES))
def test_examples_through_presidio(entity_id):
    # [TEST-PRESIDIO-BR] valid examples are found (with a context word), invalid ones are not
    rec = tarja_presidio.TarjaRecognizer(entity_id)
    word = ENTITIES[entity_id].context_words[0]
    valid, invalid = _examples(entity_id)
    for v in valid:
        res = rec.analyze(f"{word} {v}", [entity_id])
        assert any(r.entity_type == entity_id for r in res), (entity_id, v)
    for v in invalid:
        res = rec.analyze(f"{word} {v}", [entity_id])
        spans = [f"{word} {v}"[r.start : r.end] for r in res]
        # an invalid example may still contain a valid shorter match, but never itself
        assert v not in spans, (entity_id, v, spans)


def test_validate_result_mapping():
    # [TEST-PRESIDIO-BR] True for valid N1, False for wrong DV, None when context is required
    assert tarja_presidio.TarjaRecognizer("BR_CPF").validate_result("529.982.247-25") is True
    assert tarja_presidio.TarjaRecognizer("BR_CPF").validate_result("529.982.247-24") is False
    assert tarja_presidio.TarjaRecognizer("BR_CEP").validate_result("22290-140") is None


def test_register_and_analyzer_engine():
    # [TEST-PRESIDIO-BR] end to end with AnalyzerEngine, no NLP model needed for pattern recognizers
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

    registry = RecognizerRegistry(supported_languages=["pt"])
    tarja_presidio.register(registry, ["BR_CPF", "BR_CNPJ"])
    engine = AnalyzerEngine(registry=registry, supported_languages=["pt"], nlp_engine=_NoNlp())
    res = engine.analyze("cpf 529.982.247-25 e cnpj 12.ABC.345/01DE-35", language="pt")
    assert sorted(r.entity_type for r in res) == ["BR_CNPJ", "BR_CPF"]


def test_unknown_entity():
    # [TEST-PRESIDIO-BR] clear error
    with pytest.raises(KeyError):
        tarja_presidio.TarjaRecognizer("BR_XYZ")


class _NoNlp:
    """EN: minimal NLP engine stub so the test doesn't download a spaCy model.
    PT: stub minimo de NLP p/ o teste nao baixar modelo do spaCy.
    """

    def process_text(self, text, language):
        from presidio_analyzer.nlp_engine import NlpArtifacts

        return NlpArtifacts(entities=[], tokens=[], tokens_indices=[], lemmas=[], nlp_engine=self, language=language)

    def is_loaded(self):
        return True

    def get_supported_languages(self):
        return ["pt"]

    def get_supported_entities(self):
        return []

    def is_stopword(self, word, language):
        return False

    def is_punct(self, word, language):
        return False

    def process_batch(self, texts, language, batch_size=1, n_process=1, **kwargs):
        for t in texts:
            yield t, self.process_text(t, language)
