# bench/report.py
# [BENCH-REPORT] collect every *.scores.json in a results folder, write paper tables (CSV + LaTeX) and figures.
#
# usage
#   python -m bench.report --results bench/results --out bench/paper
#
# systems missing from the folder are simply left out, so the same command works before and after
#   the Presidio / spaCy / cloud / LLM runs.

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

# [BENCH-REPORT-ORDER] fixed order = fixed colour per system, never by rank
SYSTEM_ORDER = ["tarja", "presidio-br", "presidio-default", "spacy", "azure", "google-sdp", "macie", "purview", "llm"]
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MODES = ("exact", "partial", "untyped")


def _key(name: str) -> tuple[int, str]:
    """EN: Sort key following SYSTEM_ORDER. PT: Chave de ordenacao seguindo SYSTEM_ORDER."""
    base = name.split("-claude")[0].split("-gpt")[0]
    return (SYSTEM_ORDER.index(base) if base in SYSTEM_ORDER else len(SYSTEM_ORDER), name)


def collect(results: Path) -> dict[str, dict[str, dict]]:
    """EN: {dataset: {system: report}}. PT: {dataset: {sistema: relatorio}}."""
    # [BENCH-REPORT-COLLECT]
    out: dict[str, dict[str, dict]] = {}
    for f in sorted(results.glob("*.scores.json")):
        system, dataset = f.name.removesuffix(".scores.json").split("__", 1)
        out.setdefault(dataset, {})[system] = json.loads(f.read_text(encoding="utf-8"))
    return out


def overall_rows(data: dict[str, dict[str, dict]]) -> list[dict]:
    """EN: One row per dataset x system x mode. PT: Uma linha por dataset x sistema x modo."""
    # [BENCH-REPORT-OVERALL]
    rows = []
    for ds, systems in data.items():
        for s in sorted(systems, key=_key):
            rep = systems[s]
            for m in MODES:
                o = rep["results"][m]["overall"]
                rows.append({
                    "dataset": ds, "system": s, "mode": m, "precision": round(o["precision"], 4),
                    "recall": round(o["recall"], 4), "f1": round(o["f1"], 4),
                    "f1_ci_low": round(o["f1_ci95"][0], 4), "f1_ci_high": round(o["f1_ci95"][1], 4),
                    "latency_ms_median": rep.get("latency_ms_median"),
                })  # fmt: skip
    return rows


def entity_rows(data: dict[str, dict[str, dict]], mode: str = "exact") -> list[dict]:
    """EN: Per-entity P/R/F1. PT: P/R/F1 por entidade."""
    # [BENCH-REPORT-ENTITY]
    rows = []
    for ds, systems in data.items():
        for s in sorted(systems, key=_key):
            for e, v in systems[s]["results"][mode]["by_entity"].items():
                rows.append(
                    {"dataset": ds, "system": s, "entity": e, **{k: round(v[k], 4) for k in ("precision", "recall", "f1")}}
                )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    """EN: Plain CSV. PT: CSV simples."""
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def latex_overall(rows: list[dict], dataset: str) -> str:
    """EN: booktabs table, P/R/F1 per mode, best F1 in bold. PT: tabela booktabs, melhor F1 em negrito."""
    # [BENCH-REPORT-LATEX]
    rs = [r for r in rows if r["dataset"] == dataset]
    systems = list(dict.fromkeys(r["system"] for r in rs))
    best = {m: max(r["f1"] for r in rs if r["mode"] == m) for m in MODES}
    lines = [
        r"\begin{tabular}{l" + "ccc" * len(MODES) + "}", r"\toprule",
        " & " + " & ".join(rf"\multicolumn{{3}}{{c}}{{{m}}}" for m in MODES) + r" \\",
        "System & " + " & ".join(["P & R & F1"] * len(MODES)) + r" \\", r"\midrule",
    ]  # fmt: skip
    for s in systems:
        cells = []
        for m in MODES:
            r = next(x for x in rs if x["system"] == s and x["mode"] == m)
            f1 = f"{r['f1']:.3f}"
            cells += [f"{r['precision']:.3f}", f"{r['recall']:.3f}", rf"\textbf{{{f1}}}" if r["f1"] == best[m] else f1]
        lines.append(f"{s} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def figures(data: dict[str, dict[str, dict]], out: Path) -> list[Path]:
    """EN: F1 by difficulty (grouped bars) and per-entity recall (dot plot). PT: F1 por dificuldade e recall por entidade."""
    # [BENCH-REPORT-FIG]
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#52514e",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e"})  # fmt: skip
    made = []
    for ds, systems in data.items():
        names = sorted(systems, key=_key)
        colour = {s: PALETTE[min(_key(s)[0], len(PALETTE) - 1)] for s in names}
        # F1 (partial) per difficulty level
        levels = sorted({lv for s in names for lv in systems[s]["results"]["partial"]["by_difficulty"]})
        fig, ax = plt.subplots(figsize=(3.3, 2.1))
        w = 0.8 / len(names)
        for i, s in enumerate(names):
            ys = [systems[s]["results"]["partial"]["by_difficulty"].get(lv, {}).get("f1", 0) for lv in levels]
            xs = [j + (i - (len(names) - 1) / 2) * w for j in range(len(levels))]
            ax.bar(xs, ys, width=w * 0.9, color=colour[s], label=s, edgecolor="white", linewidth=0.5)
        ax.set_xticks(range(len(levels)), levels)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("F1 (partial)")
        ax.grid(axis="y", color="#e6e5e0", linewidth=0.5)
        ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=7, ncol=min(len(names), 3), loc="lower left")
        fig.tight_layout()
        p = out / f"fig_f1_by_difficulty__{ds}.pdf"
        fig.savefig(p)
        fig.savefig(p.with_suffix(".png"), dpi=200)
        plt.close(fig)
        made.append(p)
        # exact-match recall per entity
        ents = sorted({e for s in names for e in systems[s]["results"]["exact"]["by_entity"]})
        fig, ax = plt.subplots(figsize=(3.3, 0.18 * len(ents) + 0.6))
        for s in names:
            be = systems[s]["results"]["exact"]["by_entity"]
            ax.scatter([be.get(e, {}).get("recall", 0) for e in ents], range(len(ents)), s=14, color=colour[s], label=s,
                       edgecolors="white", linewidths=0.8, zorder=3)  # fmt: skip
        ax.set_yticks(range(len(ents)), [e.removeprefix("BR_") for e in ents])
        ax.invert_yaxis()
        ax.set_xlim(-0.02, 1.02)
        ax.set_xlabel("Recall (exact)")
        ax.grid(axis="x", color="#e6e5e0", linewidth=0.5)
        ax.set_axisbelow(True)
        if len(names) > 1:
            ax.legend(frameon=False, fontsize=7, loc="lower left")
        fig.tight_layout()
        p = out / f"fig_recall_by_entity__{ds}.pdf"
        fig.savefig(p)
        fig.savefig(p.with_suffix(".png"), dpi=200)
        plt.close(fig)
        made.append(p)
    return made


def main(argv=None) -> int:
    # [BENCH-REPORT-CLI]
    p = argparse.ArgumentParser(description="Paper tables and figures / Tabelas e figuras do artigo")
    p.add_argument("--results", default="bench/results")
    p.add_argument("--out", default="bench/paper")
    p.add_argument("--no-figures", action="store_true")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = collect(Path(a.results))
    rows = overall_rows(data)
    write_csv(out / "overall.csv", rows)
    write_csv(out / "by_entity_exact.csv", entity_rows(data))
    for ds in data:
        (out / f"table_overall__{ds}.tex").write_text(latex_overall(rows, ds), encoding="utf-8")
    if not a.no_figures:
        figures(data, out)
    print(f"{len(data)} datasets, {len(rows)} rows -> {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
