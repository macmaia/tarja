# bench/evaluate.py
# [BENCH-EVAL] score a predictions file against gold, all 3 modes, print a table and write JSON.
#
# usage
#   python -m bench.evaluate --gold bench/data/v0.1/synthetic_adversarial.test.jsonl --pred bench/results/tarja__...json

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench.metrics import MODES, evaluate
from bench.run import load


def report(gold: list[dict], pred: dict, n_boot: int = 1000) -> dict:
    """EN: Scores for every mode. PT: Scores p/ todo modo."""
    # [BENCH-EVAL-REPORT]
    return {
        "system": pred["system"],
        "info": pred["info"],
        "latency_ms_median": pred.get("latency_ms_median"),
        "results": {m: evaluate(gold, pred["predictions"], m, n_boot=n_boot) for m in MODES},
    }


def table(rep: dict) -> str:
    """EN: Plain-text summary. PT: Resumo em texto."""
    # [BENCH-EVAL-TABLE]
    lines = [f"system: {rep['system']}  latency(ms, median): {rep['latency_ms_median']}"]
    for m, r in rep["results"].items():
        o = r["overall"]
        lo, hi = o["f1_ci95"]
        lines.append(f"  {m:8} P={o['precision']:.3f} R={o['recall']:.3f} F1={o['f1']:.3f} [{lo:.3f}, {hi:.3f}]")
    lines.append("  by difficulty (partial F1): " + ", ".join(
        f"{k}={v['f1']:.3f}" for k, v in rep["results"]["partial"]["by_difficulty"].items()))  # fmt: skip
    return "\n".join(lines)


def main(argv=None) -> int:
    # [BENCH-EVAL-CLI]
    p = argparse.ArgumentParser(description="Evaluate on tarja-bench / Avalia no tarja-bench")
    p.add_argument("--gold", required=True)
    p.add_argument("--pred", required=True)
    p.add_argument("--boot", type=int, default=1000)
    a = p.parse_args(argv)
    rep = report(load(a.gold), json.loads(Path(a.pred).read_text(encoding="utf-8")), a.boot)
    Path(a.pred).with_suffix(".scores.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(table(rep))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
