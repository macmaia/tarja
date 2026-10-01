# tarja_presidio/__init__.py
# [PRESIDIO-BR] builds one Presidio PatternRecognizer per tarja entity, straight from tarja's registry,
#   so regex, context words and check digits never drift from the core library.
#
# How scores map to Presidio's model (validate_result). Presidio has three answers and no way to express
# "0.85", so the mapping has to decide what counts as verified:
#   - validator says no                 -> False  (Presidio drops the result)
#   - tier N1 and no context needed     -> True   (score 1.0, like Presidio's own credit-card recognizer)
#   - tier N1 but context needed        -> None   (LOW base score; Presidio's context enhancer raises it when
#                                                  a context word is near. Filter with score_threshold.)
#   - tier N2 or N3                     -> None   (base score = tarja's "without context" score)
#   - no validator at all               -> None   (only reachable for a third-party register_entity() entity)
#
# [PRESIDIO-BR-TIER] EN: the tier is what decides True, not merely "the validator passed". Only N1 validates
#   a check digit. For N2 and N3 the validator checks a FORMAT or a RANGE, so returning True there told
#   Presidio "I verified this" about a seven-character plate. Until 0.1.1 that is what happened, and BR_PLACA
#   and BR_TELEFONE arrived at confidence 1.0, equal to a CPF whose check digit was actually verified, which
#   put them out of reach of the score_threshold this README tells people to filter with.
#   PT: o tier e quem decide o True, nao o "validator passou". So N1 confere digito verificador. Em N2 e N3 o
#   validator confere FORMATO, entao devolver True dizia ao Presidio "eu verifiquei" sobre uma placa.
# author/autoria: https://github.com/macmaia

from __future__ import annotations

from collections.abc import Iterable

from presidio_analyzer import Pattern, PatternRecognizer

from tarja.entities import ENTITIES, EntitySpec

__all__ = ["TarjaRecognizer", "get_recognizers", "register"]
__version__ = "0.1.1"

# [PRESIDIO-BR-SCORE] base score for entities that require context in tarja
REQUIRED_CONTEXT_BASE_SCORE = 0.1

# [PRESIDIO-BR-TIER-CONST] the one tarja tier whose validator checks a check digit. Everything else checks a
#   format or a range, which is not verification and must not reach Presidio as confidence 1.0.
CHECK_DIGIT_TIER = "N1"


def _class_name(entity_id: str) -> str:
    # [PRESIDIO-BR-NAME] BR_TITULO_ELEITOR -> BrTituloEleitorRecognizer
    return "".join(part.capitalize() for part in entity_id.lower().split("_")) + "Recognizer"


class TarjaRecognizer(PatternRecognizer):
    """EN: Presidio recognizer for one tarja entity. PT: Reconhecedor do Presidio p/ 1 entidade do tarja."""

    # [PRESIDIO-BR-COUNTRY] same convention as Presidio's country_specific recognizers
    COUNTRY_CODE = "br"

    def __init__(self, entity_id: str, supported_language: str = "pt") -> None:
        # [PRESIDIO-BR-INIT] unknown id -> KeyError with a clear message
        if entity_id not in ENTITIES:
            raise KeyError(f"unknown tarja entity / entidade desconhecida: {entity_id}")
        self._spec: EntitySpec = ENTITIES[entity_id]
        base = REQUIRED_CONTEXT_BASE_SCORE if self._spec.context_required else self._spec.score_without_context
        patterns = [Pattern(p.name, p.regex.pattern, base) for p in self._spec.patterns]
        super().__init__(
            supported_entity=entity_id,
            name=_class_name(entity_id),
            patterns=patterns,
            context=list(self._spec.context_words),
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str) -> bool | None:
        """EN: See the module header for the True/False/None mapping. PT: Ver o cabecalho p/ o mapa True/False/None."""
        # [PRESIDIO-BR-VALIDATE] see [PRESIDIO-BR-TIER] in the header for why the tier gates the True
        spec = self._spec
        if spec.validator is None:
            # a built-in always has one; an entity added through tarja's register_entity() may not
            return None
        if not spec.validator(pattern_text):
            return False
        if spec.tier != CHECK_DIGIT_TIER:
            # format or range checked, not a check digit: keep the base score and let the threshold work
            return None
        return None if spec.context_required else True


def get_recognizers(entities: Iterable[str] | None = None, supported_language: str = "pt") -> list[TarjaRecognizer]:
    """EN: One recognizer per entity (default: all tarja entities).
    PT: 1 reconhecedor por entidade (padrao: todas do tarja).
    """
    ids = list(entities) if entities is not None else list(ENTITIES)
    return [TarjaRecognizer(e, supported_language) for e in ids]


def register(registry, entities: Iterable[str] | None = None, supported_language: str = "pt") -> list[TarjaRecognizer]:
    """EN: Add the recognizers to a Presidio RecognizerRegistry and return them.
    PT: Adiciona os reconhecedores num RecognizerRegistry do Presidio e devolve eles.
    """
    # [PRESIDIO-BR-REGISTER]
    recs = get_recognizers(entities, supported_language)
    for r in recs:
        registry.add_recognizer(r)
    return recs
