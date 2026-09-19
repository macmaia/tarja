# tarja/entities.py
# [ENTITIES] EN: runtime copy of spec/entities/*.yaml. The core has zero deps, so it can't read yaml at runtime.
#            tests/test_spec.py fails if this file and the yaml files drift apart. Edit both together.
# [ENTITIES] PT: copia em runtime dos spec/entities/*.yaml. O core nao tem dependencia, entao nao le yaml em runtime.
#            tests/test_spec.py quebra se este arquivo e os yaml divergirem. Editar os 2 juntos.

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from tarja.validators import cnj, cnpj, cns, cpf, nis

# [ENTITIES-TIERS] EN: tier order, lower = stronger evidence. Used to break overlaps.
# [ENTITIES-TIERS] PT: ordem dos niveis, menor = evidencia mais forte. Usado p/ resolver sobreposicao.
TIER_RANK = {"N1": 1, "N2": 2, "N3": 3, "N4": 4}


@dataclass(frozen=True)
class Pattern:
    """EN: One candidate regex. PT: Uma regex de candidato."""

    name: str
    regex: re.Pattern[str]
    score: float


@dataclass(frozen=True)
class EntitySpec:
    """EN: Everything the engine needs to know about one entity. Mirrors the yaml fields.
    PT: Tudo q o motor precisa saber de 1 entidade. Espelha os campos do yaml.
    """

    id: str
    tier: str
    patterns: tuple[Pattern, ...]
    validator: Callable[[str], bool] | None
    context_words: tuple[str, ...]
    context_window: int
    context_required: bool
    score_with_context: float
    score_without_context: float


def _p(name: str, regex: str, score: float) -> Pattern:
    # [ENTITIES-PATTERN] EN: helper, compiles once at import / PT: helper, compila 1x no import
    return Pattern(name, re.compile(regex), score)


# [ENTITIES-REGISTRY] EN: the registry. Order matters only as the last tie-breaker in overlaps.
# [ENTITIES-REGISTRY] PT: o registro. A ordem so importa como ultimo desempate na sobreposicao.
ENTITIES: dict[str, EntitySpec] = {
    # [ENTITIES-CPF]
    "BR_CPF": EntitySpec(
        id="BR_CPF",
        tier="N1",
        patterns=(
            _p("cpf_formatted", r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", 0.5),
            _p("cpf_compact", r"\b\d{11}\b", 0.1),
            _p("cpf_irregular_punctuation", r"\b\d{3}[\s.]?\d{3}[\s.]?\d{3}[\s\-./]?\d{2}\b", 0.3),
        ),
        validator=cpf.is_valid,
        context_words=(
            "cpf",
            "cadastro de pessoa fisica",
            "cadastro de pessoas fisicas",
            "inscrito no cpf",
            "portador do cpf",
            "contribuinte",
        ),
        context_window=50,
        context_required=False,
        score_with_context=0.95,
        score_without_context=0.85,
    ),
    # [ENTITIES-CNPJ]
    "BR_CNPJ": EntitySpec(
        id="BR_CNPJ",
        tier="N1",
        patterns=(
            _p("cnpj_formatted", r"\b[0-9A-Za-z]{2}\.[0-9A-Za-z]{3}\.[0-9A-Za-z]{3}/[0-9A-Za-z]{4}-\d{2}\b", 0.5),
            _p("cnpj_compact", r"\b[0-9A-Za-z]{12}\d{2}\b", 0.1),
        ),
        validator=cnpj.is_valid,
        context_words=(
            "cnpj",
            "cadastro nacional da pessoa juridica",
            "inscrita no cnpj",
            "inscrita sob o",
            "pessoa juridica",
            "empresa",
        ),
        context_window=50,
        context_required=False,
        score_with_context=0.95,
        score_without_context=0.85,
    ),
    # [ENTITIES-CNS]
    "BR_CNS": EntitySpec(
        id="BR_CNS",
        tier="N1",
        patterns=(
            _p("cns_formatted", r"\b[12789]\d{2}[\s.]\d{4}[\s.]\d{4}[\s.]\d{4}\b", 0.5),
            _p("cns_compact", r"\b[12789]\d{14}\b", 0.2),
        ),
        validator=cns.is_valid,
        context_words=("cns", "cartao sus", "cartao do sus", "cartao nacional de saude", "sus"),
        context_window=50,
        context_required=False,
        score_with_context=0.95,
        score_without_context=0.85,
    ),
    # [ENTITIES-NIS]
    "BR_NIS": EntitySpec(
        id="BR_NIS",
        tier="N1",
        patterns=(
            _p("nis_formatted", r"\b\d{3}\.\d{5}\.\d{2}-\d\b", 0.5),
            _p("nis_compact", r"\b\d{11}\b", 0.1),
        ),
        validator=nis.is_valid,
        context_words=("nis", "pis", "pasep", "nit", "pis/pasep", "numero de identificacao social"),
        context_window=50,
        context_required=False,
        # EN: a bit lower than CPF without context, since 11 bare digits are more often a CPF
        # PT: um pouco abaixo do CPF sem contexto, pq 11 digitos soltos costumam ser CPF
        score_with_context=0.95,
        score_without_context=0.80,
    ),
    # [ENTITIES-CNJ]
    "BR_CNJ": EntitySpec(
        id="BR_CNJ",
        tier="N1",
        patterns=(
            _p("cnj_formatted", r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", 0.6),
            _p("cnj_compact", r"\b\d{20}\b", 0.1),
        ),
        validator=cnj.is_valid,
        context_words=("processo", "autos", "proc.", "numero do processo", "acao", "recurso"),
        context_window=60,
        context_required=False,
        score_with_context=0.95,
        score_without_context=0.9,
    ),
}
