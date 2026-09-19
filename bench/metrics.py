# bench/metrics.py
# [BENCH-METRICS] E4.8. Precision / recall / F1 at span level, three matching modes, per entity and per
#   difficulty, with 95% bootstrap confidence intervals (resampling documents).
#     exact   = same start, end AND entity
#     partial = spans overlap AND same entity
#     untyped = spans overlap, entity ignored (fair to NER/LLMs that find the number but name it differently)

from __future__ import annotations

import random
from collections import defaultdict

MODES = ("exact", "partial", "untyped")


def _match(g: dict, p: dict, mode: str) -> bool:
    # [BENCH-METRICS-MATCH]
    if mode == "exact":
        return (g["start"], g["end"], g["entity"]) == (p["start"], p["end"], p["entity"])
    overlap = g["start"] < p["end"] and p["start"] < g["end"]
    return overlap and (mode == "untyped" or g["entity"] == p["entity"])


def doc_counts(gold: list[dict], pred: list[dict], mode: str) -> dict[str, list[int]]:
    """EN: {entity: [tp, fp, fn]} for one document, greedy one-to-one matching.
    PT: {entidade: [tp, fp, fn]} p/ 1 documento, casamento guloso 1 p/ 1.
    """
    # [BENCH-METRICS-DOC]
    c: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    used = set()
    for g in gold:
        hit = next((i for i, p in enumerate(pred) if i not in used and _match(g, p, mode)), None)
        if hit is None:
            c[g["entity"]][2] += 1
        else:
            used.add(hit)
            c[g["entity"]][0] += 1
    for i, p in enumerate(pred):
        if i not in used:
            c[p["entity"]][1] += 1
    return c


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """EN: precision, recall, F1 (0 when undefined). PT: precisao, revocacao, F1 (0 qdo indefinido)."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f, "tp": tp, "fp": fp, "fn": fn}


def _sum(per_doc: list[dict[str, list[int]]], keep=lambda e: True) -> list[int]:
    tot = [0, 0, 0]
    for c in per_doc:
        for e, (tp, fp, fn) in c.items():
            if keep(e):
                tot[0] += tp
                tot[1] += fp
                tot[2] += fn
    return tot


def evaluate(gold_docs: list[dict], pred_by_id: dict[str, list[dict]], mode: str = "partial",
             n_boot: int = 1000, seed: int = 0) -> dict:  # fmt: skip
    """EN: Full report for one mode: overall (micro) + CI, per entity, per difficulty.
    PT: Relatorio completo p/ 1 modo: geral (micro) + IC, por entidade, por dificuldade.
    """
    # [BENCH-METRICS-EVAL]
    per_doc = [doc_counts(d["spans"], pred_by_id.get(d["id"], []), mode) for d in gold_docs]
    overall = prf(*_sum(per_doc))
    # [BENCH-METRICS-BOOT] resample documents with replacement
    rng = random.Random(seed)
    boot = []
    for _ in range(n_boot):
        sample = [per_doc[rng.randrange(len(per_doc))] for _ in per_doc]
        boot.append(prf(*_sum(sample))["f1"])
    boot.sort()
    overall["f1_ci95"] = [boot[int(0.025 * n_boot)], boot[int(0.975 * n_boot) - 1]] if boot else [overall["f1"]] * 2
    entities = sorted({e for c in per_doc for e in c})
    by_entity = {e: prf(*_sum(per_doc, lambda x, e=e: x == e)) for e in entities}
    by_level: dict[str, dict] = {}
    for lv in sorted({d["difficulty"] for d in gold_docs}):
        idx = [i for i, d in enumerate(gold_docs) if d["difficulty"] == lv]
        by_level[lv] = prf(*_sum([per_doc[i] for i in idx]))
    return {"mode": mode, "docs": len(gold_docs), "overall": overall, "by_entity": by_entity, "by_difficulty": by_level}
