# bench/runners/ner_llm.py
# [BENCH-RUNNER-NER-LLM] E4.7. spaCy Portuguese NER (labels PER/LOC/ORG/MISC, not identifiers: expected to
#   score ~0 on typed metrics, which is itself a finding) and LLMs used as detectors.
#   LLM protocol: prompt file versioned in bench/prompts/, temperature 0, model + date recorded, every response
#   cached on disk (re-runs cost nothing and are reproducible).

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from bench.runners.base import Runner, locate, span

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
VALID_TYPES = {
    "BR_CPF", "BR_CNPJ", "BR_CNS", "BR_NIS", "BR_CNJ", "BR_CNM", "BR_CIB", "BR_TITULO_ELEITOR", "BR_CNH",
    "BR_RENAVAM", "BR_PLACA", "BR_PIX_EVP", "BR_TELEFONE", "BR_CEP", "BR_IPTU", "BR_MATRICULA_IMOVEL",
}  # fmt: skip


class SpacyRunner(Runner):
    name = "spacy"

    def __init__(self, model: str = "pt_core_news_lg", nlp=None):
        # [BENCH-RUNNER-SPACY] nlp injectable for tests
        if nlp is None:
            import spacy

            nlp = spacy.load(model)
        self.nlp = nlp
        self.info = {"model": model}

    def predict_one(self, text: str) -> list[dict]:
        # every NER entity becomes OTHER, only the "untyped" mode can credit it
        return [span(e.start_char, e.end_char, "OTHER") for e in self.nlp(text).ents]


def parse_llm_json(raw: str) -> list[dict]:
    """EN: Tolerant parse of the model's JSON answer. PT: Parse tolerante do JSON do modelo."""
    # [BENCH-RUNNER-LLM-PARSE] grab the outermost {...} even if the model added prose or code fences
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0)).get("entities", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("text"), str) and i.get("text")]


class LlmRunner(Runner):
    """EN: provider = anthropic | openai. call = injectable fn(prompt) -> str for tests.
    PT: provider = anthropic | openai. call = fn(prompt) -> str injetavel p/ teste.
    """

    name = "llm"

    def __init__(self, provider: str = "anthropic", model: str = "", prompt: str = "llm_v1.txt",
                 cache_dir: str = "bench/cache", call=None):  # fmt: skip
        # [BENCH-RUNNER-LLM-INIT]
        self.provider, self.model = provider, model
        self.template = (PROMPTS / prompt).read_text(encoding="utf-8")
        self.cache = Path(cache_dir) / f"{provider}-{model or 'default'}-{prompt}.jsonl"
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self._memo = {}
        if self.cache.exists():
            for line in self.cache.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self._memo[row["key"]] = row["raw"]
        self._call = call or self._default_call()
        self.info = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "temperature": 0,
            "date": dt.date.today().isoformat(),
        }

    def _default_call(self):
        # [BENCH-RUNNER-LLM-CALL] real API clients, keys from env
        if self.provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic()

            def call(prompt):
                msg = client.messages.create(model=self.model, max_tokens=2048, temperature=0,
                                             messages=[{"role": "user", "content": prompt}])  # fmt: skip
                return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

            return call
        if self.provider == "openai":
            import openai

            client = openai.OpenAI()

            def call(prompt):
                r = client.chat.completions.create(model=self.model, temperature=0,
                                                   messages=[{"role": "user", "content": prompt}])  # fmt: skip
                return r.choices[0].message.content or ""

            return call
        raise ValueError(f"unknown provider / provider desconhecido: {self.provider}")

    def predict_one(self, text: str) -> list[dict]:
        # [BENCH-RUNNER-LLM-PREDICT]
        prompt = self.template.replace("{TEXT}", text)
        key = hashlib.sha256(f"{self.provider}|{self.model}|{prompt}".encode()).hexdigest()
        if key not in self._memo:
            raw = self._call(prompt)
            self._memo[key] = raw
            with self.cache.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"key": key, "raw": raw}, ensure_ascii=False) + "\n")
        out, used = [], set()
        for item in parse_llm_json(self._memo[key]):
            at = locate(text, item["text"], used)
            if at is None:
                # text not found verbatim = hallucinated or reformatted span, counted as nothing
                continue
            ent = item.get("type") if item.get("type") in VALID_TYPES else "OTHER"
            out.append(span(at, at + len(item["text"]), ent, 1.0))
        return out
