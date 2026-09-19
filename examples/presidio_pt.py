# examples/presidio_pt.py
# [EXAMPLE-PRESIDIO] EN: E3.2, runs the docs/presidio.md example for real and CHECKS the result (exit 1 if wrong).
# [EXAMPLE-PRESIDIO] PT: E3.2, roda de verdade o exemplo do docs/presidio.md e CONFERE o resultado (exit 1 se errado).
#
# EN: setup once / PT: setup 1x:
#   pip install -e . -e packages/presidio-br presidio-analyzer spacy   (EN: in a venv / PT: num venv)
#   python -m spacy download pt_core_news_md
# EN: run / PT: rodar:  python examples/presidio_pt.py

import sys

import presidio_br
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

# [EXAMPLE-PRESIDIO-NLP] EN: Portuguese spaCy engine / PT: motor spaCy em portugues
nlp_engine = NlpEngineProvider(
    nlp_configuration={"nlp_engine_name": "spacy", "models": [{"lang_code": "pt", "model_name": "pt_core_news_md"}]}
).create_engine()

# [EXAMPLE-PRESIDIO-REGISTRY] EN: Presidio's own pt recognizers + all tarja entities / PT: os do Presidio + os do tarja
registry = RecognizerRegistry(supported_languages=["pt"])
registry.load_predefined_recognizers(languages=["pt"], nlp_engine=nlp_engine)
presidio_br.register(registry)
analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=["pt"])

text = "Paciente Maria, CPF 529.982.247-25, cartao SUS 898 0000 0004 3208, CEP 22290-140."
results = analyzer.analyze(text=text, language="pt", score_threshold=0.4)
for r in results:
    print(f"{r.entity_type:12} {text[r.start : r.end]!r:28} {r.score:.2f}")

# [EXAMPLE-PRESIDIO-CHECK] EN: CPF and CNS must be there with score 1.0 / PT: CPF e CNS tem q aparecer c/ score 1.0
found = {r.entity_type: r.score for r in results}
ok = found.get("BR_CPF") == 1.0 and found.get("BR_CNS") == 1.0
print("\nOK" if ok else "\nFAIL: expected BR_CPF and BR_CNS at 1.0 / esperado BR_CPF e BR_CNS c/ 1.0")
sys.exit(0 if ok else 1)
