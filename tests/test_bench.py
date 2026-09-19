# tests/test_bench.py
# [TEST-BENCH] EN: tests for tarja-bench (E4): generator, gold correctness, metrics, runners, IAA.
# [TEST-BENCH] PT: testes do tarja-bench (E4): gerador, gold correto, metricas, runners, concordancia.

import json
import pathlib
import random
import tempfile
import types
import unittest

import tarja
from bench import generate as gen
from bench import iaa, ids, metrics, semireal
from bench.runners import base, cloud, ner_llm
from bench.runners.tarja_runner import TarjaRunner
from bench.templates import FILLER, TEMPLATES

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestIds(unittest.TestCase):
    def test_every_entity_generates_valid_values(self):
        # [TEST-BENCH-IDS] EN: 200 values per entity, all valid in every rendering / PT: 200 por entidade, todos validos
        rng = random.Random(1)
        for ent in tarja.ENTITIES:
            for _ in range(200):
                v = ids.generate(ent, rng)
                for style in ("formatted", "compact", "spaced"):
                    s = ids.render(ent, v, style)
                    if tarja.ENTITIES[ent].validator:
                        self.assertTrue(tarja.ENTITIES[ent].validator(s), (ent, style, s))

    def test_invalid_lookalikes_are_invalid_for_all(self):
        # [TEST-BENCH-IDS] EN: D3 distractors must not be valid for ANY entity / PT: distrator D3 invalido p/ TODAS
        rng = random.Random(2)
        for ent in ("BR_CPF", "BR_CNPJ", "BR_CNS", "BR_NIS", "BR_CNJ", "BR_TITULO_ELEITOR", "BR_CIB"):
            for _ in range(50):
                bad = ids.invalid_lookalike(ent, rng)
                self.assertIsNotNone(bad)
                self.assertFalse(any(tarja.ENTITIES[e].validator(bad) for e in ids.DV_ENTITIES), bad)
        self.assertIsNone(ids.invalid_lookalike("BR_CEP", rng))

    def test_render_bad_style(self):
        with self.assertRaises(ValueError):
            ids.render("BR_CPF", "52998224725", "weird")


class TestGenerator(unittest.TestCase):
    def test_deterministic(self):
        # [TEST-BENCH-GEN] EN: same seed -> identical, other seed -> different / PT: mesma seed -> igual, outra -> diferente
        a, b, c = gen.build(3, 40, 40), gen.build(3, 40, 40), gen.build(4, 40, 40)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_gold_spans_are_correct(self):
        # [TEST-BENCH-GEN] EN: every gold span holds a value valid for its entity (except D4, OCR noise on purpose)
        # [TEST-BENCH-GEN] PT: todo span gold tem valor valido p/ a entidade (exceto D4, ruido de OCR de proposito)
        data = gen.build(11, 300, 300)
        n = 0
        for docs in data.values():
            for d in docs:
                for s in d["spans"]:
                    val = d["text"][s["start"] : s["end"]]
                    self.assertEqual(val, val.strip("| "), d["id"])
                    v = tarja.ENTITIES[s["entity"]].validator
                    if v and d["difficulty"] != "D4":
                        self.assertTrue(v(val), (d["id"], s, val))
                        n += 1
        self.assertGreater(n, 500)

    def test_levels_and_splits(self):
        # [TEST-BENCH-GEN] EN: controlled = D0/D1, adversarial = D2..D5, dev/test split / PT: idem
        data = gen.build(5, 100, 100)
        self.assertEqual({d["difficulty"] for d in data["synthetic_controlled.test"]}, {"D0", "D1"})
        self.assertEqual({d["difficulty"] for d in data["synthetic_adversarial.test"]}, {"D2", "D3", "D4", "D5"})
        self.assertEqual(len(data["synthetic_controlled.dev"]), 30)

    def test_d5_label_is_the_real_entity(self):
        # [TEST-BENCH-GEN] EN: in D5 the value is NOT valid for the entity the context word announces
        # [TEST-BENCH-GEN] PT: no D5 o valor NAO e valido p/ a entidade q a palavra anuncia
        rng = random.Random(8)
        swapped = 0
        for i in range(200):
            d = gen.make_doc(f"x{i}", "administrativo", "D5", rng)
            for s in d["spans"]:
                before = d["text"][max(0, s["start"] - 12) : s["start"]].upper()
                if "CPF" in before and s["entity"] != "BR_CPF":
                    swapped += 1
                    self.assertFalse(tarja.cpf.is_valid(d["text"][s["start"] : s["end"]]))
        self.assertGreater(swapped, 0)

    def test_fixed_text_has_no_identifiers(self):
        # [TEST-BENCH-GEN] EN: templates without slots and fillers trigger nothing in tarja
        # [TEST-BENCH-GEN] PT: modelos sem slot e enchimentos nao disparam nada no tarja
        for tpls in TEMPLATES.values():
            for t in tpls:
                self.assertEqual(tarja.find(gen.SLOT.sub("", t)), [], t)
        for f in FILLER:
            self.assertEqual(tarja.find(f), [], f)

    def test_committed_manifest_is_reproducible(self):
        # [TEST-BENCH-GEN] EN: regenerating v0.1 gives the sha256 recorded in the committed manifest
        # [TEST-BENCH-GEN] PT: gerar a v0.1 de novo da o sha256 gravado no manifest commitado
        manifest = json.loads((ROOT / "bench/data/v0.1/manifest.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            m = gen.write(pathlib.Path(tmp), gen.build(manifest["seed"], 5000, 3000), manifest["seed"])
        self.assertEqual({k: v["sha256"] for k, v in m["files"].items()},
                         {k: v["sha256"] for k, v in manifest["files"].items()})  # fmt: skip


class TestMetrics(unittest.TestCase):
    G = [{"id": "a", "difficulty": "D0", "spans": [{"start": 0, "end": 5, "entity": "BR_CPF"},
                                                   {"start": 10, "end": 15, "entity": "BR_CEP"}]}]  # fmt: skip

    def test_modes(self):
        # [TEST-BENCH-METRICS] EN: exact vs partial vs untyped on a hand case / PT: exato x parcial x sem tipo, caso a mao
        pred = {"a": [{"start": 0, "end": 4, "entity": "BR_CPF"}, {"start": 10, "end": 15, "entity": "OTHER"}]}
        ex = metrics.evaluate(self.G, pred, "exact", n_boot=0)["overall"]
        pa = metrics.evaluate(self.G, pred, "partial", n_boot=0)["overall"]
        un = metrics.evaluate(self.G, pred, "untyped", n_boot=0)["overall"]
        self.assertEqual((ex["tp"], ex["fp"], ex["fn"]), (0, 2, 2))
        self.assertEqual((pa["tp"], pa["fp"], pa["fn"]), (1, 1, 1))
        self.assertEqual((un["tp"], un["fp"], un["fn"]), (2, 0, 0))

    def test_one_to_one(self):
        # [TEST-BENCH-METRICS] EN: one prediction can't match two gold spans / PT: 1 previsao nao casa c/ 2 golds
        g = [{"id": "a", "difficulty": "D0", "spans": [{"start": 0, "end": 5, "entity": "X"},
                                                        {"start": 3, "end": 8, "entity": "X"}]}]  # fmt: skip
        r = metrics.evaluate(g, {"a": [{"start": 0, "end": 8, "entity": "X"}]}, "partial", n_boot=0)["overall"]
        self.assertEqual((r["tp"], r["fn"]), (1, 1))

    def test_bootstrap_ci_contains_point(self):
        # [TEST-BENCH-METRICS] EN: CI brackets the point estimate / PT: IC contem a estimativa pontual
        data = gen.build(9, 150, 0)["synthetic_controlled.test"]
        preds = dict(zip([d["id"] for d in data], TarjaRunner().predict([d["text"] for d in data])[0], strict=True))
        o = metrics.evaluate(data, preds, "partial", n_boot=200)["overall"]
        self.assertLessEqual(o["f1_ci95"][0], o["f1"])
        self.assertGreaterEqual(o["f1_ci95"][1], o["f1"])
        self.assertEqual(metrics.prf(0, 0, 0)["f1"], 0.0)


class TestRunners(unittest.TestCase):
    def test_tarja_d0_perfect(self):
        # [TEST-BENCH-RUNNER] EN: sanity: tarja on D0 is perfect, so gold and tarja agree on the basics
        # [TEST-BENCH-RUNNER] PT: sanidade: tarja no D0 e perfeito, gold e tarja concordam no basico
        docs = [d for d in gen.build(21, 200, 0)["synthetic_controlled.test"] if d["difficulty"] == "D0"]
        preds = dict(zip([d["id"] for d in docs], TarjaRunner().predict([d["text"] for d in docs])[0], strict=True))
        self.assertEqual(metrics.evaluate(docs, preds, "exact", n_boot=0)["overall"]["f1"], 1.0)

    def test_llm_runner_parse_locate_cache(self):
        # [TEST-BENCH-RUNNER] EN: fake model: good span, hallucinated span, wrong type; cache avoids 2nd call
        # [TEST-BENCH-RUNNER] PT: modelo falso: span bom, span alucinado, tipo errado; cache evita 2a chamada
        calls = []

        def fake(prompt):
            calls.append(prompt)
            return 'ok ```{"entities": [{"type": "BR_CPF", "text": "529.982.247-25"},' \
                   '{"type": "BR_CPF", "text": "000"}, {"type": "XX", "text": "CEP"}]}```'  # fmt: skip

        with tempfile.TemporaryDirectory() as tmp:
            r = ner_llm.LlmRunner(provider="fake", model="m", cache_dir=tmp, call=fake)
            text = "cpf 529.982.247-25 CEP"
            out = r.predict_one(text)
            self.assertEqual([(s["entity"], text[s["start"] : s["end"]]) for s in out],
                             [("BR_CPF", "529.982.247-25"), ("OTHER", "CEP")])  # fmt: skip
            r2 = ner_llm.LlmRunner(provider="fake", model="m", cache_dir=tmp, call=fake)
            r2.predict_one(text)
            self.assertEqual(len(calls), 1)
        self.assertEqual(ner_llm.parse_llm_json("no json"), [])
        self.assertEqual(ner_llm.parse_llm_json("{bad json}"), [])

    def test_locate_repeats(self):
        # [TEST-BENCH-RUNNER] EN: same text twice -> two different offsets / PT: mesmo texto 2x -> 2 offsets
        used = set()
        self.assertEqual([base.locate("ab ab", "ab", used) for _ in range(3)], [0, 3, None])

    def test_spacy_runner_all_other(self):
        # [TEST-BENCH-RUNNER] EN: NER labels become OTHER / PT: rotulo de NER vira OTHER
        ent = types.SimpleNamespace(start_char=0, end_char=5, label_="PER")
        r = ner_llm.SpacyRunner(nlp=lambda t: types.SimpleNamespace(ents=[ent]))
        self.assertEqual(r.predict_one("Maria x")[0]["entity"], "OTHER")

    def test_azure_google_mapping(self):
        # [TEST-BENCH-RUNNER] EN: fake SDK clients, check mapping and offsets / PT: clientes falsos, confere mapa e offsets
        e = types.SimpleNamespace(offset=4, length=14, category="BRCPFNumber", confidence_score=0.9)
        az = types.SimpleNamespace(recognize_pii_entities=lambda docs, language: [types.SimpleNamespace(entities=[e])])
        self.assertEqual(cloud.AzureRunner(client=az).predict_one("cpf 529.982.247-25")[0]["entity"], "BR_CPF")
        text = "ção 529.982.247-25"
        start_b = len("ção ".encode())
        rng_b = types.SimpleNamespace(start=start_b, end=start_b + 14)
        f = types.SimpleNamespace(
            location=types.SimpleNamespace(byte_range=rng_b), info_type=types.SimpleNamespace(name="BRAZIL_CPF_NUMBER")
        )
        gc = types.SimpleNamespace(
            inspect_content=lambda request: types.SimpleNamespace(result=types.SimpleNamespace(findings=[f]))
        )
        [s] = cloud.GoogleSdpRunner(client=gc, project="p").predict_one(text)
        self.assertEqual(text[s["start"] : s["end"]], "529.982.247-25")

    def test_import_runners(self):
        # [TEST-BENCH-RUNNER] EN: Macie findings JSON and Purview CSV rows / PT: JSON do Macie e CSV do Purview
        occ = {"lineRanges": [{"startColumn": 5, "endColumn": 18}]}
        det = {"detections": [{"type": "BRAZIL_CPF_NUMBER", "occurrences": occ}]}
        finding = {
            "resourcesAffected": {"s3Object": {"key": "bench/doc-1.txt"}},
            "classificationDetails": {"result": {"sensitiveData": [det]}},
        }
        m = cloud.MacieRunner(findings=[finding])
        self.assertEqual(m.predict_doc("doc-1"), [base.span(4, 18, "BR_CPF")])
        p = cloud.PurviewImportRunner(rows=[{"doc_id": "d", "sit_name": "Brazil CPF Number", "start": "1", "end": "3"}])
        self.assertEqual(p.predict_doc("d")[0]["entity"], "BR_CPF")
        self.assertEqual(p.predict_doc("zz"), [])


class TestSemiRealAndIaa(unittest.TestCase):
    def test_semireal_insert(self):
        # [TEST-BENCH-SEMIREAL] EN: inserted spans point at valid values / PT: spans inseridos apontam p/ valor valido
        rng = random.Random(3)
        para = "Art. 1o Esta Lei dispoe sobre a organizacao. Paragrafo unico. O disposto aplica-se a todos."
        for _ in range(50):
            text, spans = semireal.insert(para, rng, 3)
            for s in spans:
                v = tarja.ENTITIES[s["entity"]].validator
                if v:
                    self.assertTrue(v(text[s["start"] : s["end"]]), (text, s))

    def test_semireal_build_from_folder(self):
        # [TEST-BENCH-SEMIREAL] EN: end to end on a temp folder / PT: ponta a ponta numa pasta temporaria
        with tempfile.TemporaryDirectory() as tmp:
            para = "Texto publico de exemplo sem dados pessoais. " * 8
            pathlib.Path(tmp, "lei.txt").write_text(para + "\n\n" + para, encoding="utf-8")
            pathlib.Path(tmp, "sources.json").write_text('{"lei.txt": {"licence": "public domain"}}', encoding="utf-8")
            docs = semireal.build(pathlib.Path(tmp), 5, 1)
            self.assertEqual(len(docs), 5)
            self.assertEqual(docs[0]["source"]["licence"], "public domain")

    def test_iaa(self):
        # [TEST-BENCH-IAA] EN: identical -> 1.0, one missing span lowers both numbers / PT: identico -> 1.0
        a = [{"id": "1", "difficulty": "D0", "text": "cpf 529.982.247-25 x",
              "spans": [{"start": 4, "end": 18, "entity": "BR_CPF"}]}]  # fmt: skip
        b = [{**a[0], "spans": []}]
        self.assertEqual(iaa.agreement(a, a)["char_kappa"], 1.0)
        r = iaa.agreement(a, b)
        self.assertLess(r["char_kappa"], 1.0)
        self.assertEqual(r["span_f1_exact"], 0.0)
        self.assertEqual(iaa.cohen_kappa([], []), 1.0)


if __name__ == "__main__":
    unittest.main()
