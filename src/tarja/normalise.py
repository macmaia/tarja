# tarja/normalise.py
# [NORMALISE] EN: text normaliser that keeps offsets. Every char is swapped 1-for-1, so position i in the
#             normalised text is position i in the original. Matches can be sliced from the original as-is.
# [NORMALISE] PT: normalizador q preserva offset. Cada caractere e trocado 1 por 1, entao a posicao i no
#             texto normalizado e a posicao i no original. Da p/ recortar o match direto do original.
#
# EN: What it fixes (common in PDFs, Word, WhatsApp, OCR output):
#   - fullwidth / other Unicode digits -> ASCII 0-9
#   - Unicode dashes and minus signs -> "-"
#   - non-breaking / thin / zero-width-ish spaces -> " "
#   - Unicode slashes and full stops -> "/" and "."
# PT: O q corrige (comum em PDF, Word, WhatsApp, saida de OCR):
#   - digitos fullwidth / outros digitos Unicode -> ASCII 0-9
#   - tracos e sinais de menos Unicode -> "-"
#   - espaco nao quebravel / fino -> " "
#   - barras e pontos Unicode -> "/" e "."
#
# EN: What it does NOT fix yet: OCR letter/digit confusion (O->0, l->1). Too risky without context, planned for later.
# PT: O q ainda NAO corrige: confusao letra/digito de OCR (O->0, l->1). Arriscado sem contexto, fica p/ dps.

from __future__ import annotations

import unicodedata

# [NORMALISE-MAP] EN: explicit 1-to-1 swaps. Written as escapes so the source stays ASCII and greppable.
# [NORMALISE-MAP] PT: trocas 1 p/ 1 explicitas. Em escape p/ o fonte ficar ASCII e facil de buscar.
_MAP = {
    # EN: dashes / PT: tracos
    "‐": "-",  # hyphen
    "‑": "-",  # non-breaking hyphen
    "‒": "-",  # figure dash
    "–": "-",  # en dash
    "—": "-",  # em dash
    "―": "-",  # horizontal bar
    "−": "-",  # minus sign
    "﹣": "-",  # small hyphen-minus
    "－": "-",  # fullwidth hyphen-minus
    # EN: spaces / PT: espacos
    " ": " ",  # no-break space
    " ": " ",  # figure space
    " ": " ",  # thin space
    " ": " ",  # narrow no-break space
    "　": " ",  # ideographic space
    # EN: slashes and dots / PT: barras e pontos
    "⁄": "/",  # fraction slash
    "∕": "/",  # division slash
    "／": "/",  # fullwidth solidus
    "．": ".",  # fullwidth full stop
    "․": ".",  # one dot leader
}


def _swap(ch: str) -> str:
    # [NORMALISE-CHAR] EN: map one char, always returning exactly one char
    # [NORMALISE-CHAR] PT: mapeia 1 caractere, sempre devolve exatamente 1
    if ch in _MAP:
        return _MAP[ch]
    # EN: any Unicode decimal digit (fullwidth, Arabic-Indic...) -> ASCII
    # PT: qq digito decimal Unicode (fullwidth, arabe...) -> ASCII
    if not ch.isascii() and ch.isdecimal():
        return str(unicodedata.decimal(ch))
    # EN: fullwidth Latin letters (U+FF21..FF5A) -> ASCII, matters for alphanumeric CNPJ
    # PT: letras fullwidth (U+FF21..FF5A) -> ASCII, importa p/ CNPJ alfanum
    code = ord(ch)
    if 0xFF21 <= code <= 0xFF5A:
        return chr(code - 0xFEE0)
    return ch


def normalise_text(text: str) -> str:
    """EN: Return text of the SAME length with look-alike chars swapped for ASCII. Offsets are preserved.
    PT: Devolve texto do MESMO tamanho c/ caracteres parecidos trocados por ASCII. Offsets preservados.
    """
    # [NORMALISE-TEXT] EN: fast path for plain ASCII / PT: atalho p/ texto ASCII puro
    if text.isascii():
        return text
    out = "".join(_swap(c) for c in text)
    # EN: safety net, the whole design depends on this / PT: rede de seguranca, o design todo depende disso
    assert len(out) == len(text)
    return out


def fold(text: str) -> str:
    """EN: Lowercase and strip accents, for context-word matching ("Número" -> "numero"). Keeps length.
    PT: Minuscula e sem acento, p/ casar palavra de contexto ("Número" -> "numero"). Mantem o tamanho.
    """
    # [NORMALISE-FOLD] EN: NFD splits letter + accent, keep only the base letter (1 char per input char)
    # [NORMALISE-FOLD] PT: NFD separa letra + acento, fica so a letra base (1 caractere por entrada)
    # EN: lower() per char, first char only, because a few chars grow when lowercased (e.g. U+0130)
    # PT: lower() por caractere, so o 1o, pq alguns caracteres crescem ao virar minuscula (ex: U+0130)
    return "".join(unicodedata.normalize("NFD", c.lower()[:1] or c)[0] for c in text)
