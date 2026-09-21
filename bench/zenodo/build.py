# bench/zenodo/build.py
# [BENCH-ZENODO] E4.9. Builds the zip to upload to Zenodo. Checks synthetic files against manifest.json first,
#   so a stale or edited file never gets a DOI. Writes SHA256SUMS for every file in the zip.
#
# usage
# then upload the zip on zenodo.org and paste .zenodo.json fields in the form.

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
BENCH = HERE.parent

LICENCE = """Creative Commons Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/legalcode

Copyright 2026 Maria Alice Maia. Data in this package is licensed under CC BY 4.0.
Law texts in the semi-real subset are public domain in Brazil (Lei 9.610/1998, art. 8, IV).
"""


def sha256(path: Path) -> str:
    """EN: File hash. PT: Hash do arquivo."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(data: Path) -> dict:
    """EN: Fail if a synthetic file is missing or differs from the manifest. PT: Falha se sintetico faltar ou divergir."""
    # [BENCH-ZENODO-CHECK]
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    for name, meta in manifest["files"].items():
        f = data / name
        if not f.exists():
            raise SystemExit(f"missing / faltando: {f}  (python -m bench.generate --seed {manifest['seed']})")
        if sha256(f) != meta["sha256"]:
            raise SystemExit(f"sha256 mismatch / divergente: {f}")
    return manifest


def build(data: Path, out: Path) -> Path:
    """EN: Write the zip. PT: Grava o zip."""
    # [BENCH-ZENODO-BUILD]
    manifest = check(data)
    files = {p.name: p for p in sorted(data.glob("*.jsonl"))}
    files["manifest.json"] = data / "manifest.json"
    files["DATASHEET.md"] = BENCH / "DATASHEET.md"
    for extra in ("README.md", "CITATION.cff", ".zenodo.json"):
        files[extra] = HERE / extra
    out.mkdir(parents=True, exist_ok=True)
    zpath = out / f"tarja-bench-v{manifest['bench_version']}.zip"
    sums = []
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for arc, src in files.items():
            z.write(src, arc)
            sums.append(f"{sha256(src)}  {arc}")
        z.writestr("LICENSE-DATA.txt", LICENCE)
        z.writestr("SHA256SUMS", "\n".join(sums) + "\n")
    if not any(n.startswith("semireal") for n in files):
        # allowed, but say so
        print("warning / aviso: no semireal files, run bench.semireal first / sem semireal, rode o bench.semireal antes")
    print(f"{zpath}  ({len(files) + 2} files)")
    return zpath


def main(argv=None) -> int:
    # [BENCH-ZENODO-CLI]
    p = argparse.ArgumentParser(description="Build the Zenodo zip / Monta o zip do Zenodo")
    p.add_argument("--data", default="bench/data/v0.2")
    p.add_argument("--out", default="dist")
    a = p.parse_args(argv)
    build(Path(a.data), Path(a.out))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
