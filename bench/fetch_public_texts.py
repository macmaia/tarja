# bench/fetch_public_texts.py
# [BENCH-FETCH] E4.3 input. Downloads Brazilian federal laws from planalto.gov.br and saves plain text + sources.json
#   for bench/semireal.py. Laws carry no personal data and have no copyright (Lei 9.610/1998, art. 8, IV).
#   Stdlib only. Struck-out (revoked) text inside <strike>/<s>/<del> is dropped.
#
# usage
#   python -m bench.fetch_public_texts --out ../corpus_publico
#   python -m bench.semireal --src ../corpus_publico --n 2000 --out bench/data/v0.1

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://www.planalto.gov.br/ccivil_03/"
MAX_BYTES = 30 << 20  # 30 MB per page

# [BENCH-FETCH-LAWS] compiled versions, varied domains (health, tax, civil, admin, traffic, consumer, courts)
LAWS = {
    "constituicao_1988": "constituicao/constituicaocompilado.htm",
    "lei_13709_lgpd": "_ato2015-2018/2018/lei/l13709compilado.htm",
    "lei_8078_cdc": "leis/l8078compilado.htm",
    "lei_8080_sus": "leis/l8080.htm",
    "lei_8112_servidores": "leis/l8112compilado.htm",
    "lei_9784_processo_adm": "leis/l9784.htm",
    "lei_9503_ctb": "leis/l9503compilado.htm",
    "lei_14133_licitacoes": "_ato2019-2022/2021/lei/l14133.htm",
    "lei_6015_registros_publicos": "leis/l6015compilada.htm",
    "lei_13105_cpc": "_ato2015-2018/2015/lei/l13105.htm",
    "lei_5172_ctn": "leis/l5172compilado.htm",
    "lei_10406_codigo_civil": "leis/2002/l10406compilada.htm",
    "lei_12527_acesso_informacao": "_ato2011-2014/2011/lei/l12527.htm",
    "lei_8213_previdencia": "leis/l8213compilado.htm",
}  # fmt: skip


def read_capped(resp, cap: int) -> bytes:
    # [DOWNLOAD-CAP] stop at cap bytes, so a broken or hostile server can't fill the disk or the memory
    chunks, total = [], 0
    while chunk := resp.read(1 << 16):
        total += len(chunk)
        if total > cap:
            raise ValueError(f"response larger than {cap // (1 << 20)} MB, aborted")
        chunks.append(chunk)
    return b"".join(chunks)


class _Text(HTMLParser):
    """EN: HTML to text, one paragraph per block tag, skips struck text. PT: HTML p/ texto, pula texto riscado."""

    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table"}
    STRUCK = {"strike", "s", "del"}
    SKIP = {"script", "style", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.depth_struck = 0
        self.depth_skip = 0

    def handle_starttag(self, tag, attrs):
        # [BENCH-FETCH-PARSE]
        if tag in self.STRUCK:
            self.depth_struck += 1
        elif tag in self.SKIP:
            self.depth_skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.STRUCK and self.depth_struck:
            self.depth_struck -= 1
        elif tag in self.SKIP and self.depth_skip:
            self.depth_skip -= 1

    def handle_data(self, data):
        if not self.depth_struck and not self.depth_skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", raw)]
        return "\n\n".join(p for p in paras if p)


# [BENCH-FETCH-UA] planalto.gov.br resets the connection for clients that do not look like a browser (checked
#   20/09/2026: the same URL answers 200 with a browser UA and fails with "tarja-bench/..."). These are public
#   laws, fetched one at a time with a pause, so the only thing the UA changes is getting past that filter.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def fetch(url: str) -> str:
    """EN: GET and decode (planalto mixes cp1252 and utf-8). PT: GET e decodifica (planalto mistura cp1252 e utf-8)."""
    # [BENCH-FETCH-GET]
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = read_capped(r, MAX_BYTES)
        declared = r.headers.get_content_charset()
    for enc in filter(None, (declared, "utf-8", "cp1252")):
        try:
            return body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("latin-1")


def main(argv=None) -> int:
    # [BENCH-FETCH-CLI]
    p = argparse.ArgumentParser(description="Fetch public law texts / Baixa textos de lei")
    p.add_argument("--out", required=True)
    p.add_argument("--pause", type=float, default=2.0, help="seconds between requests / segundos entre requisicoes")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sources_path = out / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8")) if sources_path.exists() else {}
    for name, path in LAWS.items():
        url = BASE + path
        try:
            parser = _Text()
            parser.feed(fetch(url))
            text = parser.text()
        except OSError as exc:
            # a broken link must not stop the rest
            print(f"FAIL {name}: {exc}")
            continue
        (out / f"{name}.txt").write_text(text, encoding="utf-8")
        sources[f"{name}.txt"] = {
            "url": url,
            "retrieved": dt.date.today().isoformat(),
            "licence": "public domain, Lei 9.610/1998 art. 8 IV / dominio publico",
        }
        print(f"ok   {name}: {len(text):,} chars")
        time.sleep(a.pause)
    sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
