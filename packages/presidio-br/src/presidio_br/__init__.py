# presidio_br/__init__.py
# [PRESIDIO-BR] EN: builds one Presidio PatternRecognizer per tarja entity, straight from tarja's registry,
#   so regex, context words and check digits never drift from the core library.
# [PRESIDIO-BR] PT: monta 1 PatternRecognizer do Presidio por entidade do tarja, direto do registro do tarja,
#   entao regex, palavras de contexto e DV nunca divergem da biblioteca principal.
#
# EN: How scores map to Presidio's model (validate_result):
#   - check digit wrong             -> False  (Presidio drops the result)
#   - check digit ok                -> True   (Presidio sets score to 1.0, like its own credit-card recognizer)
#   - entity needs context in tarja -> None   (keeps the LOW base score; Presidio's context enhancer raises it
#                                              when a context word is near. Filter with score_threshold.)
#   - entity with no check digit    -> None   (base score = tarja's "without context" score)
# PT: Como os scores viram o modelo do Presidio (validate_result):
#   - DV errado                        -> False (Presidio descarta)
#   - DV certo                         -> True  (Presidio poe score 1.0, igual o reconhecedor de cartao dele)
#   - entidade q exige contexto        -> None  (fica o score base BAIXO; o enhancer de contexto do Presidio
#                                               sobe qdo tem palavra perto. Filtrar c/ score_threshold.)
#   - entidade sem DV                  -> None  (score base = score "sem contexto" do tarja)
# author/autoria: https://github.com/macmaia

from __future__ import annotations

from collections.abc import Iterable

from presidio_analyzer import Pattern, PatternRecognizer

from tarja.entities import ENTITIES, EntitySpec

__all__ = ["TarjaRecognizer", "get_recognizers", "register"]
__version__ = "0.1.0.dev0"

# [PRESIDIO-BR-SCORE] EN: base score for entities that require context in tarja / PT: score base p/ quem exige contexto
REQUIRED_CONTEXT_BASE_SCORE = 0.1


def _class_name(entity_id: str) -> str:
    # [PRESIDIO-BR-NAME] EN: BR_TITULO_ELEITOR -> BrTituloEleitorRecognizer / PT: idem
    return "".join(part.capitalize() for part in entity_id.lower().split("_")) + "Recognizer"


class TarjaRecognizer(PatternRecognizer):
    """EN: Presidio recognizer for one tarja entity. PT: Reconhecedor do Presidio p/ 1 entidade do tarja."""

    # [PRESIDIO-BR-COUNTRY] EN: same convention as Presidio's country_specific recognizers
    # [PRESIDIO-BR-COUNTRY] PT: mesma convencao dos reconhecedores country_specific do Presidio
    COUNTRY_CODE = "br"

    def __init__(self, entity_id: str, supported_language: str = "pt") -> None:
        # [PRESIDIO-BR-INIT] EN: unknown id -> KeyError with a clear message / PT: id desconhecido -> erro claro
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
        # [PRESIDIO-BR-VALIDATE]
        spec = self._spec
        if spec.validator is None:
            return None
        if not spec.validator(pattern_text):
            return False
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
