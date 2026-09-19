# tarja/__init__.py
# EN: Public API: find() (search text), mask() (replace), validate() (check one value).
# PT: API publica: find() (busca no texto), mask() (substitui), validate() (confere 1 valor).
# author/autoria: https://github.com/macmaia

# EN: import the validator modules (one file per document type in validators/)
# PT: importa os modulos de validacao (1 arquivo por doc em validators/)
from tarja.detect import Match, find, resolve_overlaps
from tarja.entities import ENTITIES
from tarja.mask import mask
from tarja.validators import cnj, cnpj, cns, cpf, nis

# EN: what "from tarja import *" exposes / PT: o q sai no "from tarja import *"
__all__ = [
    "ENTITIES",
    "Match",
    "cnj",
    "cnpj",
    "cns",
    "cpf",
    "find",
    "mask",
    "nis",
    "resolve_overlaps",
    "validate",
]

# EN: version read by hatch at build time (see pyproject.toml, [tool.hatch.version])
# PT: versao lida pelo hatch no build (ver pyproject.toml, [tool.hatch.version])
__version__ = "0.2.0.dev0"


def validate(entity: str, value: str) -> bool:
    """EN: Check value against the entity's rule. E.g. validate("BR_CPF", "529.982.247-25").
    PT: Valida value pela regra da entidade. Ex: validate("BR_CPF", "529.982.247-25").
    """
    # [VALIDATE] EN: look the entity up in the registry (tarja/entities.py)
    # [VALIDATE] PT: busca a entidade no registro (tarja/entities.py)
    spec = ENTITIES.get(entity)
    if spec is None:
        # EN: unknown entity -> explicit error, better than a silent False
        # PT: entidade nao cadastrada -> erro explicito, melhor q False calado
        raise ValueError(f"unknown entity / entidade desconhecida: {entity!r}")
    # EN: entities without a check digit can't be validated alone / PT: entidade sem DV nao da p/ validar sozinha
    if spec.validator is None:
        raise ValueError(f"{entity} has no check digit / {entity} nao tem DV")
    return spec.validator(value)
