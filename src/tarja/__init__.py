# tarja/__init__.py
# EN: Public API. For now there's only validate(), find() lands in 0.2.
# PT: API publica. Por enqto so tem validate(), o find() entra na 0.2.
# author/autoria: https://github.com/macmaia

# EN: import the validator modules (one file per document type in validators/)
# PT: importa os modulos de validacao (1 arquivo por doc em validators/)
from tarja.validators import cnpj, cpf

# EN: what "from tarja import *" exposes
# PT: o q sai no "from tarja import *"
__all__ = ["cpf", "cnpj", "validate"]

# EN: version read by hatch at build time (see pyproject.toml, [tool.hatch.version])
# PT: versao lida pelo hatch no build (ver pyproject.toml, [tool.hatch.version])
__version__ = "0.1.0.dev0"

# [REGISTRY] EN: entity -> validator map. New entity? write the validator, add a line here and a yaml in spec/
# [REGISTRY] PT: mapa entidade -> validador. Entidade nova? cria o validador, poe a linha aqui e o yaml em spec/
_VALIDATORS = {
    "BR_CPF": cpf.is_valid,
    "BR_CNPJ": cnpj.is_valid,
}


def validate(entity: str, value: str) -> bool:
    """EN: Check value against the entity's rule. E.g. validate("BR_CPF", "529.982.247-25").
    PT: Valida value pela regra da entidade. Ex: validate("BR_CPF", "529.982.247-25").
    """
    # [VALIDATE] EN: look the function up in the registry
    # [VALIDATE] PT: busca a funcao no registro
    try:
        fn = _VALIDATORS[entity]
    except KeyError as exc:
        # EN: unknown entity -> explicit error, better than a silent False
        # PT: entidade nao cadastrada -> erro explicito, melhor q False calado
        raise ValueError(f"unknown entity / entidade desconhecida: {entity!r}") from exc
    # EN: run the validator, return True/False
    # PT: roda o validador e devolve True/False
    return fn(value)
