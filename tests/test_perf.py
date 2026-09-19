# tests/test_perf.py
# [TEST-PERF] EN: E2.8 performance budget. Fails if find() takes more than 50 ms per 100 tokens
#             (Presidio's bar is 100 ms). Prints the measured number so CI logs keep a history.
# [TEST-PERF] PT: orcamento de desempenho do E2.8. Falha se o find() passar de 50 ms por 100 tokens
#             (a regua do Presidio e 100 ms). Imprime o valor medido p/ o log da CI guardar historico.

import os
import time
import unittest

import tarja

# EN: budget, can be tightened via env var in CI / PT: orcamento, da p/ apertar via variavel de ambiente na CI
BUDGET_MS = float(os.environ.get("TARJA_PERF_BUDGET_MS", "50"))

# EN: realistic ~70-token paragraph with a mix of identifiers and noise
# PT: paragrafo realista de ~70 tokens c/ mistura de identificadores e ruido
SAMPLE = (
    "Contrato de prestacao de servicos entre Fulano de Tal, CPF 529.982.247-25, residente na rua X, CEP 22290-140, "
    "telefone (21) 98765-4321, e a empresa Exemplo Ltda, CNPJ 12.ABC.345/01DE-35, com sede no Rio de Janeiro. "
    "Referente ao processo 0000001-83.2017.8.26.0100. Pagamento via chave pix 123e4567-e89b-42d3-a456-426614174000. "
    "Cartao SUS 729 1417 7763 1701, PIS 120.37567.08-3, titulo de eleitor 1023 4567 0388, veiculo placa ABC1D23, "
    "renavam 00639724361, CNH 12345678900. Pedido 2024-00017, nota 000123456, valor R$ 1.234,56, protocolo 98765432."
)


class TestPerf(unittest.TestCase):
    def test_budget(self):
        # [TEST-PERF] EN: warm up, then best of 5 runs of 20 calls / PT: aquece, dps melhor de 5 rodadas de 20 chamadas
        tokens = len(SAMPLE.split())
        tarja.find(SAMPLE)
        best = min(self._run(20) for _ in range(5))
        per_100 = best / tokens * 100
        print(f"\n[TEST-PERF] {per_100:.2f} ms per 100 tokens (budget {BUDGET_MS} ms, {tokens} tokens)")
        self.assertLess(per_100, BUDGET_MS)

    def test_sample_finds_everything(self):
        # [TEST-PERF] EN: the sample really exercises all 12 entities / PT: o exemplo exercita as 12 entidades mesmo
        self.assertEqual({m.entity for m in tarja.find(SAMPLE)}, set(tarja.ENTITIES))

    @staticmethod
    def _run(n):
        # EN: average ms per call over n calls / PT: media em ms por chamada em n chamadas
        start = time.perf_counter()
        for _ in range(n):
            tarja.find(SAMPLE)
        return (time.perf_counter() - start) / n * 1000


if __name__ == "__main__":
    unittest.main()
