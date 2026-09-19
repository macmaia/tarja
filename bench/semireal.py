# bench/semireal.py
# [BENCH-SEMIREAL] EN: E4.3, semi-real subset. Takes REAL public texts that carry no personal data (laws, decrees,
#   public notices...), cuts them into paragraphs and inserts generated identifiers with a context phrase at a
#   sentence boundary. Real Portuguese around, synthetic identifiers inside, so nobody's data is exposed.
#   Input: a folder of .txt files + a sources.json saying where each came from and its licence.
#   Brazilian laws and official acts are NOT protected by copyright (Lei 9.610/1998, art. 8, IV).
# [BENCH-SEMIREAL] PT: E4.3, subconjunto semi-real. Pega textos publicos REAIS sem dado pessoal (leis, decretos,
#   editais...), corta em paragrafos e insere identificadores gerados c/ frase de contexto numa fronteira de frase.
#   Portugues real em volta, identificador sintetico dentro, entao ninguem tem dado exposto.
#   Entrada: pasta de .txt + sources.json dizendo de onde veio cada um e a licenca.
#   Lei e ato oficial NAO tem direito autoral (Lei 9.610/1998, art. 8, IV).
#
# EN: usage / PT: uso:  python -m bench.semireal --src ../corpus_publico --n 2000 --out bench/data/v0.1

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import tarja
from bench.ids import generate, render

# [BENCH-SEMIREAL-PHRASES] EN: insertion phrases, {} = the identifier / PT: frases de insercao, {} = o identificador
PHRASES = {
    "BR_CPF": "Interessado inscrito no CPF {}.",
    "BR_CNPJ": "Requerente: empresa inscrita no CNPJ {}.",
    "BR_CNS": "Usuario do SUS, cartao nacional de saude {}.",
    "BR_NIS": "Beneficiario com NIS {}.",
    "BR_CNJ": "Referente ao processo {}.",
    "BR_CNM": "Imovel de CNM {}.",
    "BR_CIB": "Cadastro imobiliario brasileiro {}.",
    "BR_TITULO_ELEITOR": "Titulo de eleitor {}.",
    "BR_CNH": "Condutor com CNH {}.",
    "BR_RENAVAM": "Veiculo de renavam {}.",
    "BR_PLACA": "Veiculo de placa {}.",
    "BR_PIX_EVP": "Pagamento pela chave pix {}.",
    "BR_TELEFONE": "Contato pelo telefone {}.",
    "BR_CEP": "Endereco no CEP {}.",
    "BR_IPTU": "Inscricao do IPTU {}.",
    "BR_MATRICULA_IMOVEL": "Matricula do imovel {} no registro de imoveis.",
}
_SENT_END = re.compile(r"(?<=[.;:])\s+")


def paragraphs(folder: Path, min_len: int = 200, max_len: int = 1200):
    """EN: Yield (file_name, paragraph) from every .txt. PT: Gera (arquivo, paragrafo) de cada .txt."""
    # [BENCH-SEMIREAL-PARAS]
    for f in sorted(folder.glob("*.txt")):
        for p in re.split(r"\n\s*\n", f.read_text(encoding="utf-8")):
            p = " ".join(p.split())
            if min_len <= len(p) <= max_len and not tarja.find(p):
                # EN: skip paragraphs that already contain something tarja flags (keeps gold clean)
                # PT: pula paragrafo q ja tem algo q o tarja marca (mantem o gold limpo)
                yield f.name, p


def insert(paragraph: str, rng: random.Random, k: int) -> tuple[str, list[dict]]:
    """EN: Insert k identifiers at random sentence boundaries. PT: Insere k identificadores em fronteiras de frase."""
    # [BENCH-SEMIREAL-INSERT]
    sents = _SENT_END.split(paragraph)
    spans = []
    for _ in range(k):
        ent = rng.choice(sorted(PHRASES))
        value = render(ent, generate(ent, rng), rng.choice(["formatted", "formatted", "compact"]))
        phrase = PHRASES[ent]
        sents.insert(rng.randint(0, len(sents)), phrase.format(value))
        # EN: remember which phrase, spans are computed after joining / PT: guarda a frase, span calculado dps de juntar
        spans.append((phrase.format(value), phrase.index("{}"), len(value), ent))
    text = " ".join(sents)
    out, cursor = [], 0
    for full, off, n, ent in sorted(spans, key=lambda s: text.index(s[0])):
        at = text.index(full, cursor) + off
        out.append({"start": at, "end": at + n, "entity": ent})
        cursor = at + n
    return text, out


def build(src: Path, n: int, seed: int) -> list[dict]:
    """EN: n semi-real docs. PT: n docs semi-reais."""
    # [BENCH-SEMIREAL-BUILD]
    rng = random.Random(seed)
    pool = list(paragraphs(src))
    if not pool:
        raise SystemExit(f"no usable paragraphs in / sem paragrafo util em {src}")
    sources = json.loads((src / "sources.json").read_text(encoding="utf-8")) if (src / "sources.json").exists() else {}
    docs = []
    for i in range(n):
        fname, para = pool[i % len(pool)]
        text, spans = insert(para, rng, rng.choice([1, 2, 3]))
        docs.append({"id": f"semireal-{i:05d}", "domain": "semireal", "difficulty": "D0", "text": text,
                     "spans": spans, "source": {"file": fname, **sources.get(fname, {})}})  # fmt: skip
    return docs


def main(argv=None) -> int:
    # [BENCH-SEMIREAL-CLI]
    p = argparse.ArgumentParser(description="Semi-real subset / subconjunto semi-real")
    p.add_argument("--src", required=True)
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="bench/data/v0.1")
    a = p.parse_args(argv)
    docs = build(Path(a.src), a.n, a.seed)
    cut = int(len(docs) * 0.3)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, part in (("semireal.dev", docs[:cut]), ("semireal.test", docs[cut:])):
        (out / f"{name}.jsonl").write_text(
            "".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in part), encoding="utf-8"
        )
    print(f"{len(docs)} docs -> {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
