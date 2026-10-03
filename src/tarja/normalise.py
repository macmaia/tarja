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


# [NORMALISE-INVISIBLE] EN: the single source of truth for "character a reader cannot see inside an
#   identifier". detect.py reads this for both its trigger and its strip, so the two cannot drift apart.
#
#   Two mechanisms on purpose, because neither alone is enough. The CATEGORIES catch the whole families and
#   keep catching characters Unicode adds later: Cf (format: zero-width, soft hyphen, bidi controls, tag
#   characters) and Mn (nonspacing marks: combining accents, variation selectors). The EXTRAS list catches
#   what sits outside those categories and was measured to evade anyway: the Hangul fillers are category Lo
#   and even answer True to isalnum(), so no category rule finds them.
#
#   What is deliberately NOT here: U+00A0 and the other Zs spaces, because removing a space joins words and
#   numbers that were never together, and the circled digits (No), which are real digits and belong in the
#   digit mapping below instead. Both were measured on 01/10/2026 and each is a different problem.
#   PT: fonte unica do q e "caractere q o leitor nao ve dentro de um identificador". Duas regras de
#   proposito: categoria p/ as familias inteiras, lista explicita p/ o q escapa de categoria.
_INVISIBLE_CATEGORIES = frozenset({"Cf", "Mn"})

_INVISIBLE_EXTRAS = frozenset(
    {
        "\u3164",  # Hangul filler, category Lo, isalnum() is True
        "\u115f",  # Hangul choseong filler
        "\u1160",  # Hangul jungseong filler
        "\uffa0",  # halfwidth Hangul filler
    }
)


def is_invisible(ch: str) -> bool:
    """EN: True for a character a reader cannot see but that breaks a pattern. PT: caractere invisivel."""
    # [NORMALISE-INVISIBLE-TEST]
    return ch in _INVISIBLE_EXTRAS or unicodedata.category(ch) in _INVISIBLE_CATEGORIES


def strip_invisible(text: str) -> tuple[str, list[int]]:
    """EN: Return (text without invisible characters, index map). index_map[i] is the position IN THE
    ORIGINAL of character i of the stripped text, so an offset found in the stripped text translates back.
    PT: Devolve (texto sem invisivel, mapa de indices). index_map[i] e a posicao no ORIGINAL.
    """
    # [NORMALISE-STRIP] the one place that removes them, so the trigger and the strip see the same set
    out: list[str] = []
    index_map: list[int] = []
    for i, ch in enumerate(text):
        if is_invisible(ch):
            continue
        out.append(ch)
        index_map.append(i)
    return "".join(out), index_map


def has_invisible_near_digit(text: str, window: int = 2) -> bool:
    """EN: True when an invisible character sits within `window` characters of a digit. This is the trigger
    for the extra detection pass, and it is narrow on purpose: Portuguese text decomposed to NFD carries a
    combining mark on nearly every accented word, so a bare "contains Mn" test would fire on ordinary
    documents and double the cost of the common path for nothing.
    PT: True qdo um invisivel esta a `window` caracteres de um digito. Gatilho estreito de proposito: texto
    em NFD tem marca combinante em quase toda palavra acentuada.
    """
    # [NORMALISE-TRIGGER]
    n = len(text)
    for i, ch in enumerate(text):
        if not is_invisible(ch):
            continue
        lo, hi = max(0, i - window), min(n, i + window + 1)
        if any(text[j].isdigit() for j in range(lo, hi) if j != i):
            return True
    return False


def _swap(ch: str) -> str:
    # [NORMALISE-CHAR] map one char, always returning exactly one char
    if ch in _MAP:
        return _MAP[ch]
    # [NORMALISE-DIGIT] any Unicode digit -> ASCII. isdigit(), not isdecimal(): the circled digits
    #   (U+2460 and friends) are category No, so isdecimal() is False for them and they slipped through,
    #   which made "CPF ①②⑨..." invisible to every pattern. unicodedata.digit() resolves all of them to a
    #   single ASCII character, so the 1-for-1 length rule still holds. Measured 01/10/2026.
    #   PT: isdigit() e nao isdecimal(): o digito cercado e categoria No, entao escapava.
    if not ch.isascii() and ch.isdigit():
        return str(unicodedata.digit(ch))
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
