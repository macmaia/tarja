# tarja/normalise.py
# [NORMALISE] text normaliser that keeps offsets. Every char is swapped 1-for-1, so position i in the
#             normalised text is position i in the original. Matches can be sliced from the original as-is.
#
# What it fixes (common in PDFs, Word, WhatsApp, OCR output):
#   - fullwidth / other Unicode digits -> ASCII 0-9
#   - Unicode dashes and minus signs -> "-"
#   - non-breaking / thin / zero-width-ish spaces -> " "
#   - Unicode slashes and full stops -> "/" and "."
#
# What it does NOT fix yet: OCR letter/digit confusion (O->0, l->1). Too risky without context, planned for later.

from __future__ import annotations

import unicodedata

# [NORMALISE-MAP] explicit 1-to-1 swaps. Written as escapes so the source stays ASCII and greppable.
_MAP = {
    # dashes
    "‐": "-",  # hyphen
    "‑": "-",  # non-breaking hyphen
    "‒": "-",  # figure dash
    "–": "-",  # en dash
    "—": "-",  # em dash
    "―": "-",  # horizontal bar
    "−": "-",  # minus sign
    "﹣": "-",  # small hyphen-minus
    "－": "-",  # fullwidth hyphen-minus
    # spaces
    " ": " ",  # no-break space
    " ": " ",  # figure space
    " ": " ",  # thin space
    " ": " ",  # narrow no-break space
    "　": " ",  # ideographic space
    # slashes and dots
    "⁄": "/",  # fraction slash
    "∕": "/",  # division slash
    "／": "/",  # fullwidth solidus
    "．": ".",  # fullwidth full stop
    "․": ".",  # one dot leader
}


def _swap(ch: str) -> str:
    # [NORMALISE-CHAR] map one char, always returning exactly one char
    if ch in _MAP:
        return _MAP[ch]
    # any Unicode decimal digit (fullwidth, Arabic-Indic...) -> ASCII
    if not ch.isascii() and ch.isdecimal():
        return str(unicodedata.decimal(ch))
    # fullwidth Latin letters (U+FF21..FF5A) -> ASCII, matters for alphanumeric CNPJ
    code = ord(ch)
    if 0xFF21 <= code <= 0xFF5A:
        return chr(code - 0xFEE0)
    return ch


def normalise_text(text: str) -> str:
    """EN: Return text of the SAME length with look-alike chars swapped for ASCII. Offsets are preserved.
    PT: Devolve texto do MESMO tamanho c/ caracteres parecidos trocados por ASCII. Offsets preservados.
    """
    # [NORMALISE-TEXT] fast path for plain ASCII
    if text.isascii():
        return text
    out = "".join(_swap(c) for c in text)
    # safety net, the whole design depends on this
    assert len(out) == len(text)
    return out


def fold(text: str) -> str:
    """EN: Lowercase and strip accents, for context-word matching ("Número" -> "numero"). Keeps length.
    PT: Minuscula e sem acento, p/ casar palavra de contexto ("Número" -> "numero"). Mantem o tamanho.
    """
    # [NORMALISE-FOLD] NFD splits letter + accent, keep only the base letter (1 char per input char)
    # lower() per char, first char only, because a few chars grow when lowercased (e.g. U+0130)
    return "".join(unicodedata.normalize("NFD", c.lower()[:1] or c)[0] for c in text)
