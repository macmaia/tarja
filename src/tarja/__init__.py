# tarja/__init__.py
# Public API: find() (search), mask() (replace), validate() (check one value), Vault (reversible
#     tokens), residual() (second-pass check), register_entity() (your own entities).
# author/autoria: https://github.com/macmaia

# import the validator modules (one file per document type in validators/)
from tarja.detect import Match, find, resolve_overlaps
from tarja.entities import ENTITIES
from tarja.mask import mask
from tarja.registry import (
    RegistryFrozenError,
    freeze,
    is_frozen,
    register_entity,
    unfreeze,
    unregister_entity,
)
from tarja.validators import cartao, cnj, cnpj, cns, cpf, nis
from tarja.vault import (
    ProtectedText,
    Vault,
    VaultCollisionError,
    VaultConsumedError,
    VaultError,
    VaultExpiredError,
    VaultScopeError,
    residual,
)

# what "from tarja import *" exposes
__all__ = [
    "ENTITIES",
    "Match",
    "ProtectedText",
    "RegistryFrozenError",
    "Vault",
    "VaultCollisionError",
    "VaultConsumedError",
    "VaultError",
    "VaultExpiredError",
    "VaultScopeError",
    "cartao",
    "cnj",
    "cnpj",
    "cns",
    "cpf",
    "find",
    "freeze",
    "is_frozen",
    "mask",
    "nis",
    "register_entity",
    "residual",
    "resolve_overlaps",
    "unfreeze",
    "unregister_entity",
    "validate",
]

# version read by hatch at build time (see pyproject.toml, [tool.hatch.version])
__version__ = "0.7.0"


def validate(entity: str, value: str) -> bool:
    """EN: Check value against the entity's rule. E.g. validate("BR_CPF", "529.982.247-25").
    PT: Valida value pela regra da entidade. Ex: validate("BR_CPF", "529.982.247-25").
    """
    # [VALIDATE] look the entity up in the registry (tarja/entities.py)
    spec = ENTITIES.get(entity)
    if spec is None:
        # unknown entity -> explicit error, better than a silent False
        raise ValueError(f"unknown entity / entidade desconhecida: {entity!r}")
    # entities without a check digit can't be validated alone
    if spec.validator is None:
        raise ValueError(f"{entity} has no check digit / {entity} nao tem DV")
    return spec.validator(value)
