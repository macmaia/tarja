# tarja-presidio

**EN** · Brazilian identifiers for [Presidio](https://github.com/data-privacy-stack/presidio), powered by [tarja](https://github.com/macmaia/tarja). One `PatternRecognizer` per tarja entity (CPF, alphanumeric CNPJ, CNS, CNJ, CNM, CIB...), with check-digit validation and Portuguese context words.

**PT** · Identificadores brasileiros p/ o Presidio, via tarja. 1 `PatternRecognizer` por entidade do tarja, c/ validação de DV e palavras de contexto em pt-BR.

EN: until tarja is on PyPI, install both from the repo root / PT: ate o tarja estar no PyPI, instale os 2 da raiz do repo:

```bash
pip install -e . -e packages/tarja-presidio
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

EN: scores: valid check digit -> 1.0; wrong check digit -> dropped; entities that need context in tarja (CEP, CNH, RENAVAM, PIX key, CIB, IPTU, matricula) start at 0.1 and rely on Presidio's context enhancer, so use `score_threshold`. Full walkthrough: `docs/presidio.md`.
PT: scores: DV certo -> 1.0; DV errado -> descartado; entidades q exigem contexto no tarja começam em 0.1 e dependem do enhancer de contexto do Presidio, entao use `score_threshold`. Passo a passo: `docs/presidio.md`.
