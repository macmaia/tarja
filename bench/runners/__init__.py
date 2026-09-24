# bench/runners/__init__.py
# [BENCH-RUNNERS] one adapter per system under test. All return the SAME format:
#   list (one per doc) of lists of {"start", "end", "entity", "score"}, entity in tarja's ids (BR_CPF...).
#   Systems that label something tarja doesn't know return entity "OTHER" (counts only in "untyped" mode).

from __future__ import annotations

import importlib

# [BENCH-RUNNERS-REGISTRY] name -> "module:Class", imported lazily (cloud SDKs are optional)
RUNNERS = {
    "tarja": "bench.runners.tarja_runner:TarjaRunner",
    "presidio-default": "bench.runners.presidio_runner:PresidioDefaultRunner",
    "tarja-presidio": "bench.runners.presidio_runner:PresidioBrRunner",
    "azure": "bench.runners.cloud:AzureRunner",
    "google-sdp": "bench.runners.cloud:GoogleSdpRunner",
    "macie": "bench.runners.cloud:MacieRunner",
    "purview": "bench.runners.cloud:PurviewImportRunner",
    "spacy": "bench.runners.ner_llm:SpacyRunner",
    "llm": "bench.runners.ner_llm:LlmRunner",
}


def get_runner(name: str, **kwargs):
    """EN: Instantiate a runner by name. PT: Instancia um runner pelo nome."""
    mod, cls = RUNNERS[name].split(":")
    return getattr(importlib.import_module(mod), cls)(**kwargs)
