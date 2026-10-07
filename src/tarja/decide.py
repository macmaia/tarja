# tarja/decide.py
# [DECIDE] EN: the library primitive that answers "does this text get to leave". It exists because the
#   fail-closed behaviour only lived in the CLI, as an exit code, and `import tarja` had no way to ask the
#   question. A public talk promised "below a minimum confidence the call does not go out, fail closed, when
#   in doubt block", and until 0.12.0 that was true of `tarja scan` and of nothing else.
#   PT: a primitiva q responde "este texto pode sair". Existia so na linha de comando, como codigo de saida,
#   e quem usa `import tarja` nao tinha como perguntar.
#
# [DECIDE-POLICY] EN: this module blocks on a SUSPECT by default, and `tarja scan` does not. That difference
#   is deliberate and it is the whole reason this file carries a long comment.
#
#   A suspect is a value shaped like an identifier whose check digit does not close. Measured 01/10/2026: a
#   CPF with one corrupted digit reconstructs to exactly one valid CPF in 93% of 243 cases, search space
#   110. So a suspect usually re-identifies the same person, and treating it as noise is a choice with a
#   measured cost.
#
#   `scan` keeps exiting 0 on a suspect, by a decision recorded in docs/decisions.md, because an invoice or
#   protocol number in CPF shape is a suspect too and gating on it teaches people to write `|| true`, which
#   removes the gate for everything, valid CPFs included. That decision is about an exit code, which is a
#   one-byte channel with nowhere to put a reason. THIS function returns an object, so it can say what it
#   blocked and why, and the person reading the reason is the person who decides. Different channel,
#   different default, and the README carries the three-row table that states it.
#
#   PT: este modulo bloqueia SUSPEITO por padrao e o `tarja scan` nao. A diferenca e deliberada. Codigo de
#   saida e canal de um byte, sem lugar p/ motivo. Esta funcao devolve objeto e diz o q barrou e por que.

from __future__ import annotations

from collections.abc import Iterable

from tarja.detect import Match, find

# [DECIDE-SUSPECT-OPTS] the two words a caller may pass. "block" is the default on purpose, see
#   DECIDE-POLICY. Spelled out rather than a boolean so the call site reads as a policy and not as a flag.
ON_SUSPECT = ("block", "allow")


# [DECIDE-EXC-NAME] EN: BlockedError, not TarjaBlocked. Two reasons, and both are the project's own
#   convention rather than taste: every other exception here ends in Error (VaultError, UnsafeRegexError,
#   RegistryFrozenError), and ruff's N818 enforces it; and the module is already called tarja, so a Tarja
#   prefix reads as tarja.TarjaBlocked at the call site. Caught by the linter on 06/10/2026.
#   PT: BlockedError, nao TarjaBlocked. Toda excecao daqui termina em Error e o ruff cobra isso (N818), e o
#   modulo ja se chama tarja, entao o prefixo ficaria tarja.TarjaBlocked na chamada.
class BlockedError(Exception):
    """EN: raised by require_clean when the text must not leave. PT: o texto nao pode sair."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        n = len(decision.blocked_by)
        kinds = sorted({m.entity for m in decision.blocked_by})
        super().__init__(f"blocked by {n} finding(s) / barrado por {n} achado(s): {', '.join(kinds)}")


class Decision:
    """EN: the answer, with the reason attached. PT: a resposta, c/ o motivo junto."""

    # [DECIDE-SLOTS] same reason as Match: no __dict__, so the identifier does not leave through vars()
    __slots__ = ("allowed", "blocked_by", "checked_entities")

    allowed: bool
    blocked_by: tuple[Match, ...]
    checked_entities: tuple[str, ...]

    def __init__(self, allowed: bool, blocked_by: Iterable[Match], checked_entities: Iterable[str]) -> None:
        object.__setattr__(self, "allowed", bool(allowed))
        object.__setattr__(self, "blocked_by", tuple(blocked_by))
        object.__setattr__(self, "checked_entities", tuple(checked_entities))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"Decision is immutable / Decision e imutavel: {name!r}")

    def __bool__(self) -> bool:
        # [DECIDE-BOOL] EN: so `if not decide(text): refuse()` reads correctly. This is the one line whose
        #   sabotage passes every attribute test and fails only inside an `if`, which is why there is a
        #   mutant for exactly it.
        #   PT: p/ o `if not decide(texto)` ler certo. Sabotar esta linha passa em todo teste de atributo.
        return self.allowed

    def __repr__(self) -> str:
        # [DECIDE-REPR] never the values, same rule as Match
        kinds = sorted({m.entity for m in self.blocked_by})
        state = "allowed" if self.allowed else "blocked"
        return f"Decision({state}, {len(self.blocked_by)} finding(s): {kinds}, values hidden/valores ocultos)"

    def reason(self) -> str:
        """EN: one line for a log, with no identifier in it. PT: 1 linha p/ log, sem identificador."""
        if self.allowed:
            return "no finding / nenhum achado"
        parts = sorted({f"{m.entity}{'' if m.valid_dv else ' (suspect/suspeito)'}" for m in self.blocked_by})
        return "blocked by / barrado por: " + ", ".join(parts)


def decide(
    text: str,
    min_score: float = 0.0,
    on_suspect: str = "block",
    entities: Iterable[str] | None = None,
    **find_kwargs,
) -> Decision:
    """EN: Decide whether text may leave. Returns a Decision, which is falsy when blocked.
    on_suspect="block" (default) counts a value whose check digit fails. on_suspect="allow" ignores it,
    which matches what `tarja scan` does by default and is the less safe of the two.
    min_score drops VALID findings below the threshold from the decision. A suspect always scores 0 and is
    never filtered by min_score, so a threshold cannot quietly open the gate.

    PT: Decide se o texto pode sair. Devolve Decision, q e falso qdo barrado.
    on_suspect="block" (padrao) conta valor c/ DV errado. "allow" ignora, igual ao `tarja scan`, e e o menos
    seguro dos dois. O min_score descarta achado VALIDO abaixo do limiar. Suspeito pontua 0 e nunca e
    filtrado por limiar, entao limiar nao abre o portao em silencio.

    >>> bool(decide("nada de identificador aqui"))
    True
    """
    # [DECIDE-CHECK] fail loudly on a typo in the policy, instead of silently taking the default
    if on_suspect not in ON_SUSPECT:
        raise ValueError(f"on_suspect must be one of / tem de ser uma de: {ON_SUSPECT}")
    ids = list(entities) if entities is not None else None
    # [DECIDE-FIND] report_invalid is always True here: the decision needs to SEE the suspect in order to
    #   apply the policy to it. Which policy applies is the caller's choice, seeing it is not.
    found = find(text, entities=ids, min_score=0.0, report_invalid=True, **find_kwargs)
    blocks_suspect = on_suspect == "block"
    blocking = [m for m in found if (m.valid_dv and m.score >= min_score) or (not m.valid_dv and blocks_suspect)]
    checked = ids if ids is not None else sorted({m.entity for m in found})
    return Decision(not blocking, blocking, checked)


def require_clean(text: str, **kwargs) -> None:
    """EN: Same decision, as an exception, for code that would rather not branch. Raises BlockedError with
    the Decision on the `decision` attribute.
    PT: A mesma decisao, como excecao, p/ codigo q prefere nao ramificar. Levanta BlockedError c/ a Decision
    no atributo `decision`.
    """
    # [DECIDE-REQUIRE] two names, two ergonomics, one engine. Nothing is decided here that decide() does not
    #   decide, so there is no second policy to keep in sync.
    d = decide(text, **kwargs)
    if not d:
        raise BlockedError(d)
