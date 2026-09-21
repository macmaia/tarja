# examples/rag_pipeline.py
# [RAG] RAG with no identifiers in the LLM payload. Four points where tarja runs:
#   1. ingestion  -> tokenise chunks BEFORE embedding/indexing (the index never holds a CPF)
#   2. query      -> tokenise the user question with the SAME key, so the token matches the index
#   3. pre-flight -> residual() on the final prompt, fail closed if anything leaked
#   4. answer     -> reveal() only for the authorised user, residual() before logging
#
# Run: python examples/rag_pipeline.py

from __future__ import annotations

import os
import sqlite3

import tarja
from tarja.vault import Vault

# [RAG-KEY] one long-lived key for the corpus. HMAC is deterministic, so the same CPF yields the same
#   token in every chunk AND in the query. That is what keeps retrieval working after masking.
#   In production: KMS/HSM, never an env var in the repo. Rotating the key means re-indexing.
CORPUS_KEY = bytes.fromhex(os.environ.get("TARJA_CORPUS_KEY", "00" * 32))


class PersistedVault(Vault):
    """EN/PT: Vault + sqlite. The open-source Vault keeps the map in memory for one process, which dies
    between the ingestion job and the serving process. RAG needs the map to survive, so persist it.
    ATENCAO: esta tabela E o dado pessoal. Criptografia em repouso, ACL propria, retencao definida.
    """

    def __init__(self, db_path: str, key: bytes):
        super().__init__(key=key)
        self._db = sqlite3.connect(db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS vault (token TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def protect(self, text: str, **kw) -> str:
        out = super().protect(text, **kw)
        self._db.executemany("INSERT OR IGNORE INTO vault (token, value) VALUES (?, ?)", list(self._map.items()))
        self._db.commit()
        return out

    def reveal(self, text: str) -> str:
        # [RAG-REVEAL] load from sqlite what this process did not tokenise itself
        for row in self._db.execute("SELECT token, value FROM vault"):
            self._map.setdefault(row[0], row[1])
        return super().reveal(text)


# ---------------------------------------------------------------- 1. ingestion
def ingest(chunks: list[str], vault: PersistedVault, index: dict) -> None:
    for i, chunk in enumerate(chunks):
        safe = vault.protect(chunk)
        # [RAG-FAILCLOSED] nothing goes into the index before residual() says it is clean
        leftover = tarja.residual(safe, min_score=0.5)
        if leftover:
            raise ValueError(f"chunk {i}: identificador nao mascarado {[m.entity for m in leftover]}")
        index[i] = safe  # here: embed(safe) -> vector DB. The embedding API never sees the CPF.


# ---------------------------------------------------------------- 2. query
def retrieve(question: str, vault: PersistedVault, index: dict, k: int = 2) -> tuple[str, list[str]]:
    safe_q = vault.protect(question)
    # toy lexical match. In production: embed(safe_q) -> ANN search.
    terms = {t.strip(".,?").lower() for t in safe_q.split()}
    scored = [(len(terms & {w.strip(".,").lower() for w in c.split()}), c) for c in index.values()]
    scored.sort(key=lambda s: -s[0])
    return safe_q, [c for score, c in scored[:k] if score]


# ---------------------------------------------------------------- 3. pre-flight
def build_prompt(safe_q: str, docs: list[str]) -> str:
    prompt = "Contexto:\n" + "\n".join(f"- {d}" for d in docs) + f"\n\nPergunta: {safe_q}"
    leftover = tarja.residual(prompt, min_score=0.5)
    if leftover:
        # [RAG-GATE] fail closed. Never "log and continue": the log becomes the leak.
        raise ValueError(f"prompt bloqueado, {len(leftover)} identificador(es) em claro")
    return prompt


def fake_llm(prompt: str) -> str:
    # o LLM so ve tokens e devolve tokens
    tok = [w.strip(".,") for w in prompt.split() if w.startswith("<BR_")]
    return f"O titular {tok[0]} esta com a fatura em aberto desde marco."


# ---------------------------------------------------------------- 4. answer
def answer(question: str, vault: PersistedVault, index: dict, authorised: bool) -> str:
    safe_q, docs = retrieve(question, vault, index)
    prompt = build_prompt(safe_q, docs)
    raw = fake_llm(prompt)
    print("  [payload que saiu do seu processo]", prompt.replace("\n", " | "))
    print("  [resposta crua do LLM]           ", raw)
    # [RAG-LOG] log the tokenised version, always. reveal() only at the last millimetre.
    return vault.reveal(raw) if authorised else raw


if __name__ == "__main__":
    db = ":memory:"
    vault = PersistedVault(db, CORPUS_KEY)
    index: dict[int, str] = {}

    ingest(
        [
            "Cliente Joao Souza, CPF 529.982.247-25, fatura vencida desde marco de 2026.",
            "Contrato da empresa CNPJ 11.222.333/0001-81, reajuste anual em julho.",
            "Atendimento no SUS, cartao 729 1417 7763 1701, retorno em 30 dias.",
        ],
        vault,
        index,
    )
    print("indice (o que foi embeddado):")
    for c in index.values():
        print("  ", c)

    print("\npergunta do usuario: qual a situacao do CPF 529.982.247-25?")
    out = answer("qual a situacao do CPF 529.982.247-25?", vault, index, authorised=True)
    print("  [entregue ao usuario autorizado] ", out)

    print("\nmesma pergunta, usuario NAO autorizado:")
    print("  ", answer("qual a situacao do CPF 529.982.247-25?", vault, index, authorised=False))
