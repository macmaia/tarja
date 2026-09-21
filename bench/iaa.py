# bench/iaa.py
# [BENCH-IAA] E4.4 support. Inter-annotator agreement between two annotation files (same doc ids):
#   - span F1 between annotators (exact and partial), the usual number in NER papers
#   - Cohen's kappa at character level (label of each char: entity id or "O")
#
# usage

from __future__ import annotations

import argparse
import json
from collections import Counter

from bench.metrics import evaluate
from bench.run import load


def char_labels(doc: dict) -> list[str]:
    """EN: One label per character. PT: 1 rotulo por caractere."""
    # [BENCH-IAA-CHARS]
    lab = ["O"] * len(doc["text"])
    for s in doc["spans"]:
        for i in range(s["start"], s["end"]):
            lab[i] = s["entity"]
    return lab


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """EN: Cohen's kappa for two label sequences. PT: kappa de Cohen p/ 2 sequencias de rotulos."""
    # [BENCH-IAA-KAPPA]
    n = len(a)
    if n == 0:
        return 1.0
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def agreement(docs_a: list[dict], docs_b: list[dict]) -> dict:
    """EN: Span F1 (A as reference) + char-level kappa. PT: F1 de span (A como referencia) + kappa por caractere."""
    # [BENCH-IAA-AGREEMENT]
    b_by_id = {d["id"]: d for d in docs_b}
    common = [d for d in docs_a if d["id"] in b_by_id]
    preds = {d["id"]: b_by_id[d["id"]]["spans"] for d in common}
    la, lb = [], []
    for d in common:
        la += char_labels(d)
        lb += char_labels(b_by_id[d["id"]])
    return {
        "docs": len(common),
        "span_f1_exact": evaluate(common, preds, "exact", n_boot=0)["overall"]["f1"],
        "span_f1_partial": evaluate(common, preds, "partial", n_boot=0)["overall"]["f1"],
        "char_kappa": cohen_kappa(la, lb),
    }


def main(argv=None) -> int:
    # [BENCH-IAA-CLI]
    p = argparse.ArgumentParser(description="Inter-annotator agreement / Concordancia entre anotadores")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    a = p.parse_args(argv)
    print(json.dumps(agreement(load(a.a), load(a.b)), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
