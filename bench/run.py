# bench/run.py
# [BENCH-RUN] run one system over one JSONL file, write predictions + latency + system info.
#
# usage
#   python -m bench.run --system tarja --data bench/data/v0.2/synthetic_adversarial.test.jsonl --out bench/results/
#   python -m bench.run --system llm --provider anthropic --model <model-id> --data ... --out ...

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from bench.runners import get_runner


def load(path: str) -> list[dict]:
    """EN: Read a JSONL file. PT: Le um JSONL."""
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def run(system: str, docs: list[dict], **kwargs) -> dict:
    """EN: Predictions for every doc. PT: Previsoes p/ todo doc."""
    # [BENCH-RUN-SYSTEM]
    runner = get_runner(system, **kwargs)
    if hasattr(runner, "predict_doc"):
        # import-based runners (Macie, Purview) work by doc id
        preds, lat = [runner.predict_doc(d["id"]) for d in docs], []
    else:
        preds, lat = runner.predict([d["text"] for d in docs])
    return {
        "system": system,
        "info": runner.info,
        "latency_ms_median": statistics.median(lat) if lat else None,
        "predictions": {d["id"]: p for d, p in zip(docs, preds, strict=True)},
    }


def main(argv=None) -> int:
    # [BENCH-RUN-CLI]
    p = argparse.ArgumentParser(description="Run a system on tarja-bench / Roda um sistema no tarja-bench")
    p.add_argument("--system", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", default="bench/results")
    p.add_argument("--provider")
    p.add_argument("--model")
    a = p.parse_args(argv)
    kwargs = {k: v for k, v in {"provider": a.provider, "model": a.model}.items() if v}
    res = run(a.system, load(a.data), **kwargs)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"{a.system}{'-' + a.model if a.model else ''}__{Path(a.data).stem}.json"
    (out / name).write_text(json.dumps(res, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out / name)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
