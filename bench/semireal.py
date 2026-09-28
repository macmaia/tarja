# bench/semireal.py
# [BENCH-SEMIREAL] E4.3, semi-real subset. Takes REAL public texts that carry no personal data (laws, decrees,
#   public notices...), cuts them into paragraphs and inserts generated identifiers with a context phrase at a
#   sentence boundary. Real Portuguese around, synthetic identifiers inside, so nobody's data is exposed.
#   Input: a folder of .txt files + a sources.json saying where each came from and its licence.
#   Brazilian laws and official acts are NOT protected by copyright (Lei 9.610/1998, art. 8, IV).
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
from bench.ids import generate, render

# [BENCH-SEMIREAL-PHRASES] EN: insertion phrases, {} = the identifier. Several per entity ON PURPOSE: with one
#   canonical wording per type the subset only ever measures detection under that wording, and the context
#   window is then always the same distance from the value. Variants differ in the context word, in case, in
#   punctuation, and in whether the identifier sits in a short sentence of its own or inside a longer clause.
#   PT: varias por entidade DE PROPOSITO. C/ uma redacao canonica por tipo, o subconjunto so mede deteccao
#   naquela redacao, e a janela de contexto fica sempre a mesma distancia do valor. As variantes mudam a
#   palavra de contexto, a caixa, a pontuacao e se o identificador fica em oracao curta ou dentro de outra.
PHRASES = {
    "BR_CPF": (
        "Interessado inscrito no CPF {}.",
        "cpf {} do requerente",
        "O interessado, portador do CPF n {}, apresentou a documentacao exigida.",
        "Fica intimado o titular do C.P.F. {} a manifestar-se.",
    ),
    "BR_CNPJ": (
        "Requerente: empresa inscrita no CNPJ {}.",
        "pessoa juridica de CNPJ {}",
        "A contratada, inscrita no CNPJ sob o n {}, apresentou proposta.",
        "cnpj: {}",
    ),
    "BR_CNS": (
        "Usuario do SUS, cartao nacional de saude {}.",
        "cns {}",
        "O paciente, cujo cartao nacional de saude e {}, foi encaminhado.",
    ),
    "BR_NIS": (
        "Beneficiario com NIS {}.",
        "nis: {}",
        "O beneficiario identificado pelo NIS {} consta do cadastro.",
    ),
    "BR_CNJ": (
        "Referente ao processo {}.",
        "autos n {}",
        "Nos autos do processo judicial n {}, determinou-se a intimacao.",
        "processo: {}",
    ),
    "BR_CNM": (
        "Imovel de CNM {}.",
        "cnm {}",
        "O imovel, de codigo nacional de matricula {}, foi objeto de averbacao.",
    ),
    "BR_CIB": (
        "Cadastro imobiliario brasileiro {}.",
        "cib {}",
        "O imovel rural de CIB {} consta do cadastro.",
    ),
    "BR_TITULO_ELEITOR": (
        "Titulo de eleitor {}.",
        "inscricao eleitoral {}",
        "O eleitor, de titulo n {}, requereu a transferencia de domicilio.",
    ),
    "BR_CNH": (
        "Condutor com CNH {}.",
        "cnh: {}",
        "Ao condutor habilitado sob o registro {} foi aplicada a penalidade.",
    ),
    "BR_RENAVAM": (
        "Veiculo de renavam {}.",
        "renavam {}",
        "O veiculo, de codigo RENAVAM {}, encontra-se regularizado.",
    ),
    "BR_PLACA": (
        "Veiculo de placa {}.",
        "placa {}",
        "O veiculo de placa {} foi removido ao deposito.",
    ),
    "BR_PIX_EVP": (
        "Pagamento pela chave pix {}.",
        "chave pix: {}",
        "O recolhimento devera ser feito pela chave pix {}.",
    ),
    "BR_TELEFONE": (
        "Contato pelo telefone {}.",
        "tel {}",
        "Fica o interessado ciente de que o contato sera feito pelo telefone {}.",
    ),
    "BR_CEP": (
        "Endereco no CEP {}.",
        "cep {}",
        "A correspondencia sera remetida ao endereco de CEP {}.",
    ),
    "BR_IPTU": (
        "Inscricao do IPTU {}.",
        "iptu {}",
        "O imovel, de inscricao imobiliaria {}, esta em debito.",
    ),
    "BR_MATRICULA_IMOVEL": (
        "Matricula do imovel {} no registro de imoveis.",
        "matricula {} do registro de imoveis",
        "Conforme a matricula n {} do registro de imoveis competente, procede-se a averbacao.",
    ),
    "BR_CARTAO": (
        "Pagamento no cartao de credito {}.",
        "cartao de credito {}",
        "O pagamento foi lancado no cartao de credito n {}.",
    ),
}

_SENT_END = re.compile(r"(?<=[.;:])\s+")


def paragraphs(folder: Path, min_len: int = 200, max_len: int = 1200, drop_flagged: bool = True):
    """EN: Yield (file_name, paragraph) from every .txt. PT: Gera (arquivo, paragrafo) de cada .txt."""
    # [BENCH-SEMIREAL-PARAS] EN: drop_flagged=True skips paragraphs tarja already flags, which keeps the gold
    #   clean but also removes, USING TARJA ITSELF, every background false positive before anything is
    #   measured. Precision on such a corpus is near 1 by construction and is not an estimate of precision on
    #   real text. drop_flagged=False keeps those paragraphs: the source texts are laws and decrees carrying
    #   no personal data, so any tarja hit outside an inserted span is a false positive by construction.
    #   PT: drop_flagged=True descarta paragrafo q o tarja ja sinaliza, o q mantem o gold limpo mas tambem
    #   remove, USANDO O PROPRIO TARJA, todo falso positivo de fundo antes de qq medicao. A precisao fica
    #   perto de 1 por construcao e nao estima precisao em texto real. Com False, como a fonte e lei e decreto
    #   sem dado pessoal, todo achado fora de span inserido e falso positivo por construcao.
    for f in sorted(folder.glob("*.txt")):
        for p in re.split(r"\n\s*\n", f.read_text(encoding="utf-8")):
            p = " ".join(p.split())
            if not (min_len <= len(p) <= max_len):
                continue
            if drop_flagged and tarja.find(p):
                continue
            yield f.name, p


def insert(paragraph: str, rng: random.Random, k: int) -> tuple[str, list[dict]]:
    """EN: Insert k identifiers at random sentence boundaries. PT: Insere k identificadores em fronteiras de frase."""
    # [BENCH-SEMIREAL-INSERT]
    sents = _SENT_END.split(paragraph)
    spans = []
    for _ in range(k):
        ent = rng.choice(sorted(PHRASES))
        value = render(ent, generate(ent, rng), rng.choice(["formatted", "formatted", "compact"]))
        phrase = rng.choice(PHRASES[ent])
        sents.insert(rng.randint(0, len(sents)), phrase.format(value))
        # remember which phrase, spans are computed after joining
        spans.append((phrase.format(value), phrase.index("{}"), len(value), ent))
    text = " ".join(sents)
    out, cursor = [], 0
    for full, off, n, ent in sorted(spans, key=lambda s: text.index(s[0])):
        at = text.index(full, cursor) + off
        out.append({"start": at, "end": at + n, "entity": ent})
        cursor = at + n
    return text, out


def build(src: Path, n: int, seed: int, drop_flagged: bool = True) -> list[dict]:
    """EN: n semi-real docs. PT: n docs semi-reais."""
    # [BENCH-SEMIREAL-BUILD]
    rng = random.Random(seed)
    pool = list(paragraphs(src, drop_flagged=drop_flagged))
    if not pool:
        raise SystemExit(f"no usable paragraphs in / sem paragrafo util em {src}")
    sources = json.loads((src / "sources.json").read_text(encoding="utf-8")) if (src / "sources.json").exists() else {}
    docs = []
    for i in range(n):
        fname, para = pool[i % len(pool)]
        text, spans = insert(para, rng, rng.choice([1, 2, 3]))
        docs.append({"id": f"semireal-{i:05d}", "domain": "semireal", "difficulty": "D0", "text": text,
                     "spans": spans, "source": {"file": fname, **sources.get(fname, {})},
                     "background_filtered": drop_flagged})  # fmt: skip
    return docs


def filter_report(src: Path) -> int:
    """EN: How much the drop_flagged filter removes, and what for. PT: Quanto o filtro remove, e por que."""
    # [BENCH-SEMIREAL-FILTER-REPORT] EN: run this before quoting any precision from the semi-real subset. Every
    #   paragraph counted here is a paragraph of law text where tarja fires with no personal data present, so
    #   it is a false positive that the filter hides. PT: rodar isto antes de citar qq precisao do semi-real.
    from collections import Counter

    kept = list(paragraphs(src, drop_flagged=True))
    allp = list(paragraphs(src, drop_flagged=False))
    dropped = len(allp) - len(kept)
    by_entity, hits = Counter(), 0
    keptset = {(f, p) for f, p in kept}
    for f, para in allp:
        if (f, para) in keptset:
            continue
        for m in tarja.find(para):
            by_entity[m.entity] += 1
            hits += 1
    print(f"paragraphs in length range / paragrafos na faixa : {len(allp)}")
    print(f"kept by the filter / mantidos pelo filtro        : {len(kept)}")
    print(
        f"dropped by the filter / descartados              : {dropped}  ({100 * dropped / len(allp):.1f}%)" if allp else ""
    )
    print(f"tarja findings inside the dropped ones / achados : {hits}")
    print("by entity / por entidade:")
    for ent, n in by_entity.most_common():
        print(f"  {ent:22} {n}")
    print()
    print("EN: every finding above is a false positive on text with no personal data in it.")
    print("PT: todo achado acima e falso positivo em texto sem dado pessoal nenhum.")
    return 0


def main(argv=None) -> int:
    # [BENCH-SEMIREAL-CLI]
    p = argparse.ArgumentParser(description="Semi-real subset / subconjunto semi-real")
    p.add_argument("--src", required=True)
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="bench/data/v0.3")
    # [BENCH-SEMIREAL-KEEPFLAGGED] see paragraphs(): this is what makes background false positives measurable
    p.add_argument(
        "--keep-flagged",
        action="store_true",
        help="EN: keep paragraphs tarja already flags / PT: manter paragrafo q o tarja sinaliza",
    )
    p.add_argument(
        "--filter-report",
        action="store_true",
        help="EN: report what the filter drops and exit / PT: relatar o q o filtro descarta e sair",
    )
    a = p.parse_args(argv)
    if a.filter_report:
        return filter_report(Path(a.src))
    docs = build(Path(a.src), a.n, a.seed, drop_flagged=not a.keep_flagged)
    cut = int(len(docs) * 0.3)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # [BENCH-SEMIREAL-MANIFEST] EN: the semi-real files carry the external-validity claim, so they belong in
    #   the manifest with a sha256 like every other split. generate.py writes the manifest first and this
    #   MERGES into it, so run generate.py before this, or this alone creates a manifest with only these two.
    #   PT: os arquivos semi-reais sustentam a alegacao de validade externa, entao entram no manifest c/
    #   sha256 como os outros. O generate.py escreve o manifest antes e aqui a gente FUNDE, entao rodar o
    #   generate.py primeiro, ou este sozinho cria manifest so c/ estes 2.
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    manifest.setdefault("bench_version", BENCH_VERSION)
    manifest.setdefault("tarja_version", tarja.__version__)
    manifest.setdefault("files", {})
    manifest["semireal"] = {"seed": a.seed, "n": a.n, "src": str(a.src),
                            "background_filtered": not a.keep_flagged}  # fmt: skip
    for name, part in (("semireal.dev", docs[:cut]), ("semireal.test", docs[cut:])):
        body = "".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in part)
        (out / f"{name}.jsonl").write_text(body, encoding="utf-8")
        manifest["files"][f"{name}.jsonl"] = {
            "docs": len(part), "spans": sum(len(d["spans"]) for d in part),
            "sha256": hashlib.sha256(body.encode()).hexdigest(),
        }  # fmt: skip
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(docs)} docs -> {out} (manifest updated / manifest atualizado)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
