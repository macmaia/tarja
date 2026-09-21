# bench/generate.py
# [BENCH-GEN] builds the synthetic benchmark (E4.1 + E4.2). Deterministic: same seed -> byte-identical files.
#   Each document = 1 to 3 templates (+ filler), ONE difficulty level applied to all its slots:
#     D0 canonical layout | D1 no punctuation / spaces instead of separators | D2 line break inside, glued to text,
#     table cell | D3 invalid look-alikes added as distractors (NOT annotated) | D4 OCR noise (O for 0, l for 1),
#     still annotated | D5 misleading context (word says CPF, number is really a NIS...), gold = real entity
#   Offsets are computed while the text is assembled, so gold spans are exact by construction.
#
# usage

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path

import tarja
from bench import BENCH_VERSION
from bench.ids import generate, invalid_lookalike, render
from bench.templates import CONFUSABLE, FILLER, TEMPLATES

SLOT = re.compile(r"\{(BR_[A-Z_]+)\}")
LEVELS = ("D0", "D1", "D2", "D3", "D4", "D5")


def _value_for_level(entity: str, level: str, rng: random.Random) -> str:
    # [BENCH-GEN-VALUE] how the identifier itself is written at each level
    v = generate(entity, rng)
    if level == "D1":
        return render(entity, v, rng.choice(["compact", "spaced"]))
    s = render(entity, v, "formatted")
    # PIX keys are UUIDs, a line break inside makes them another string, so they're skipped here
    if level == "D2" and entity != "BR_PIX_EVP" and rng.random() < 0.5:
        # line break replacing one separator
        seps = [i for i, c in enumerate(s) if c in ".-/ "]
        if seps:
            i = rng.choice(seps)
            s = s[:i] + "\n" + s[i + 1 :]
    if level == "D4":
        # 1-2 OCR swaps
        idx = [i for i, c in enumerate(s) if c in "01"]
        for i in rng.sample(idx, min(len(idx), rng.choice([1, 2]))):
            s = s[:i] + {"0": "O", "1": "l"}[s[i]] + s[i + 1 :]
    return s


def _fill(template: str, level: str, rng: random.Random) -> tuple[str, list[dict]]:
    # [BENCH-GEN-FILL] fill one template, return text + spans relative to it
    out, spans, pos = [], [], 0
    for m in SLOT.finditer(template):
        prefix = template[pos : m.start()]
        entity = m.group(1)
        real = entity
        if level == "D5" and entity in CONFUSABLE:
            real = rng.choice(CONFUSABLE[entity])
        value = _value_for_level(real, level, rng)
        if level == "D5" and real != entity:
            # the swapped value must NOT also be valid as the entity the word announces
            for _ in range(20):
                if not tarja.ENTITIES[entity].validator(value):
                    break
                value = _value_for_level(real, level, rng)
        if level == "D2" and rng.random() < 0.3:
            # glue to the previous word ("CPF:529...")
            prefix = prefix.rstrip() + ":"
        out.append(prefix)
        start = sum(len(x) for x in out)
        if level == "D2" and rng.random() < 0.2:
            # table cell
            out.append("| ")
            start += 2
            out.append(value)
            out.append(" |")
        else:
            out.append(value)
        spans.append({"start": start, "end": start + len(value), "entity": real})
        pos = m.end()
    out.append(template[pos:])
    return "".join(out), spans


def make_doc(doc_id: str, domain: str, level: str, rng: random.Random) -> dict:
    """EN: One benchmark document. PT: 1 documento do benchmark."""
    # [BENCH-GEN-DOC]
    parts, spans, text = [], [], ""
    pieces = rng.sample(TEMPLATES[domain], rng.choice([1, 2, 3]))
    if rng.random() < 0.5:
        pieces.append(rng.choice(FILLER))
    rng.shuffle(pieces)
    for p in pieces:
        t, sp = _fill(p, level, rng)
        base = len(text) + (1 if text else 0)
        text = (text + " " + t) if text else t
        spans += [{**s, "start": s["start"] + base, "end": s["end"] + base} for s in sp]
        parts.append(p)
    if level == "D3":
        # [BENCH-GEN-D3] add 1-2 invalid look-alikes with a context word
        for _ in range(rng.choice([1, 2])):
            ent = rng.choice(["BR_CPF", "BR_CNPJ", "BR_CNS", "BR_NIS", "BR_CNJ", "BR_TITULO_ELEITOR"])
            bad = invalid_lookalike(ent, rng)
            if bad:
                word = tarja.ENTITIES[ent].context_words[0].upper()
                text += f" Conferir {word} {bad}, digitado com erro."
    return {"id": doc_id, "domain": domain, "difficulty": level, "text": text, "spans": spans}


def _doc_rng(seed: int, subset: str, index: int) -> random.Random:
    """EN: One independent random stream per document. PT: Um fluxo aleatorio independente por documento."""
    # [BENCH-GEN-SEED] derived from (seed, subset, index) instead of drawing from one shared stream. With a
    #   single stream, changing a validator shifts every draw after the first difference, so the whole corpus
    #   changes and the committed hashes stop matching. Per document, a validator change moves only the
    #   documents that use that entity, and the rest stay byte-identical.
    h = hashlib.sha256(f"{seed}|{subset}|{index}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def build(seed: int, n_controlled: int, n_adversarial: int, dev_share: float = 0.3) -> dict[str, list[dict]]:
    """EN: All subsets and splits. PT: Todos os subconjuntos e splits."""
    # [BENCH-GEN-BUILD] controlled = D0/D1, adversarial = D2..D5
    domains = sorted(TEMPLATES)
    out: dict[str, list[dict]] = {}
    for name, n, levels, weights in (
        ("synthetic_controlled", n_controlled, ["D0", "D1"], [0.6, 0.4]),
        ("synthetic_adversarial", n_adversarial, ["D2", "D3", "D4", "D5"], [0.25] * 4),
    ):
        docs = []
        for i in range(n):
            r = _doc_rng(seed, name, i)
            docs.append(make_doc(f"{name}-{i:05d}", domains[i % len(domains)], r.choices(levels, weights)[0], r))
        cut = int(n * dev_share)
        out[f"{name}.dev"], out[f"{name}.test"] = docs[:cut], docs[cut:]
    return out


def write(out_dir: Path, data: dict[str, list[dict]], seed: int) -> dict:
    """EN: Write JSONL files + manifest with sha256. PT: Grava JSONL + manifest c/ sha256."""
    # [BENCH-GEN-WRITE]
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, docs in data.items():
        path = out_dir / f"{name}.jsonl"
        body = "".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in docs)
        path.write_text(body, encoding="utf-8")
        files[path.name] = {"docs": len(docs), "spans": sum(len(d["spans"]) for d in docs),
                            "sha256": hashlib.sha256(body.encode()).hexdigest()}  # fmt: skip
    manifest = {"bench_version": BENCH_VERSION, "tarja_version": tarja.__version__, "seed": seed, "files": files}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    # [BENCH-GEN-CLI]
    p = argparse.ArgumentParser(description="Generate tarja-bench / Gera o tarja-bench")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--controlled", type=int, default=5000)
    p.add_argument("--adversarial", type=int, default=3000)
    p.add_argument("--out", default="bench/data/v0.2")
    a = p.parse_args(argv)
    m = write(Path(a.out), build(a.seed, a.controlled, a.adversarial), a.seed)
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
