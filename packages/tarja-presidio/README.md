# tarja-presidio

**EN** · Brazilian identifiers for [Presidio](https://github.com/data-privacy-stack/presidio), powered by [tarja](https://github.com/macmaia/tarja). One `PatternRecognizer` per tarja entity (CPF, alphanumeric CNPJ, CNS, CNJ, CNM, CIB...), with check-digit validation and Portuguese context words.

**PT** · Identificadores brasileiros p/ o Presidio, via tarja. 1 `PatternRecognizer` por entidade do tarja, c/ validação de DV e palavras de contexto em pt-BR.

EN: install / PT: instalar:

```bash
pip install tarja-presidio
```

EN: from a clone, for development / PT: a partir de um clone, p/ desenvolver:

```bash
pip install -e . -e "packages/tarja-presidio[dev]"
```

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
import tarja_presidio

registry = RecognizerRegistry(supported_languages=["pt"])
registry.load_predefined_recognizers(languages=["pt"])  # EN: optional / PT: opcional
tarja_presidio.register(registry)  # EN: all tarja entities / PT: todas as entidades do tarja

engine = AnalyzerEngine(registry=registry, supported_languages=["pt"])  # EN: needs a pt NLP config / PT: precisa de config NLP pt
engine.analyze("Paciente CPF 529.982.247-25, cartao SUS 898 0000 0004 3208", language="pt")
```

EN: scores, from 0.1.1 on. A **verified check digit** reaches Presidio at 1.0, which is the 8 tier-N1
entities that need no context word. A wrong check digit is dropped. Everything else keeps a base score and
relies on Presidio's context enhancer, so filter with `score_threshold`: the entities that need context in
tarja (CEP, CNH, RENAVAM, PIX key, CIB, IPTU, matricula) start at 0.1, and the two that are format-only
without context (plate, phone) start at 0.5. Until 0.1.0 those two arrived at 1.0, which told Presidio a
format match had been verified. Full walkthrough: https://macmaia.github.io/tarja/presidio.html
PT: scores, da 0.1.1 em diante. DV conferido chega com 1.0, q são as 8 entidades N1 sem contexto. DV errado é
descartado. O resto mantém score base e depende do enhancer de contexto, então filtre c/ `score_threshold`.
Até a 0.1.0 placa e telefone chegavam com 1.0, dizendo ao Presidio q formato tinha sido verificado.
