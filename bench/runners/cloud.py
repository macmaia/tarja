# bench/runners/cloud.py
# [BENCH-RUNNER-CLOUD] EN: E4.6, paid DLP services. Each needs an account + credentials (see bench/README.md).
#   Every call's cost and date must be logged in the results (info dict), per the paper protocol.
# [BENCH-RUNNER-CLOUD] PT: E4.6, DLPs pagos. Cada um precisa de conta + credencial (ver bench/README.md).
#   Custo e data de cada chamada vao p/ o resultado (dict info), pelo protocolo do artigo.

from __future__ import annotations

import csv
import datetime as dt
import os

from bench.runners.base import Runner, span

# [BENCH-RUNNER-CLOUD-MAPS] EN: vendor entity -> tarja id (documented types, checked 2026-09-18)
# [BENCH-RUNNER-CLOUD-MAPS] PT: entidade do fornecedor -> id do tarja (tipos documentados, conferidos 18/09/2026)
AZURE_MAP = {"BRCPFNumber": "BR_CPF", "BRLegalEntityNumber": "BR_CNPJ", "PhoneNumber": "BR_TELEFONE"}
GOOGLE_MAP = {"BRAZIL_CPF_NUMBER": "BR_CPF", "PHONE_NUMBER": "BR_TELEFONE"}
MACIE_MAP = {
    "BRAZIL_CPF_NUMBER": "BR_CPF",
    "BRAZIL_CNPJ_NUMBER": "BR_CNPJ",
    "BRAZIL_CEP_CODE": "BR_CEP",
    "BRAZIL_PHONE_NUMBER": "BR_TELEFONE",
}
PURVIEW_MAP = {"Brazil CPF Number": "BR_CPF", "Brazil Legal Entity Number (CNPJ)": "BR_CNPJ"}


def _today() -> str:
    return dt.date.today().isoformat()


class AzureRunner(Runner):
    """EN: Azure AI Language PII. Env: AZURE_LANGUAGE_ENDPOINT, AZURE_LANGUAGE_KEY. PT: idem."""

    name = "azure"

    def __init__(self, client=None, language: str = "pt-BR"):
        # [BENCH-RUNNER-AZURE] EN: client injectable for tests / PT: cliente injetavel p/ teste
        if client is None:
            from azure.ai.textanalytics import TextAnalyticsClient
            from azure.core.credentials import AzureKeyCredential

            client = TextAnalyticsClient(
                os.environ["AZURE_LANGUAGE_ENDPOINT"], AzureKeyCredential(os.environ["AZURE_LANGUAGE_KEY"])
            )
        self.client, self.language = client, language
        self.info = {"service": "Azure AI Language PII", "date": _today(), "language": language}

    def predict_one(self, text: str) -> list[dict]:
        [doc] = self.client.recognize_pii_entities([text], language=self.language)
        return [
            span(e.offset, e.offset + e.length, AZURE_MAP.get(e.category, "OTHER"), e.confidence_score) for e in doc.entities
        ]


class GoogleSdpRunner(Runner):
    """EN: Google Cloud Sensitive Data Protection inspect_content. Env: GOOGLE_CLOUD_PROJECT + ADC credentials.
    PT: Google Cloud SDP inspect_content. Env: GOOGLE_CLOUD_PROJECT + credencial ADC.
    """

    name = "google-sdp"
    INFO_TYPES = ["BRAZIL_CPF_NUMBER", "BRAZIL_RG_NUMBER", "PHONE_NUMBER"]

    def __init__(self, client=None, project: str | None = None):
        # [BENCH-RUNNER-GOOGLE]
        if client is None:
            from google.cloud import dlp_v2

            client = dlp_v2.DlpServiceClient()
        self.client = client
        self.parent = f"projects/{project or os.environ.get('GOOGLE_CLOUD_PROJECT', 'test')}/locations/global"
        self.info = {"service": "Google Cloud SDP", "date": _today(), "info_types": self.INFO_TYPES}

    def predict_one(self, text: str) -> list[dict]:
        req = {
            "parent": self.parent,
            "inspect_config": {"info_types": [{"name": n} for n in self.INFO_TYPES], "include_quote": True},
            "item": {"value": text},
        }
        resp = self.client.inspect_content(request=req)
        out = []
        for f in resp.result.findings:
            # EN: SDP returns UTF-8 byte offsets when the text isn't ASCII; convert to char offsets
            # PT: SDP devolve offset em bytes UTF-8 qdo o texto nao e ASCII; converte p/ offset de caractere
            b = f.location.byte_range
            start = len(text.encode("utf-8")[: b.start].decode("utf-8", "ignore"))
            end = len(text.encode("utf-8")[: b.end].decode("utf-8", "ignore"))
            out.append(span(start, end, GOOGLE_MAP.get(f.info_type.name, "OTHER"), 1.0))
        return out


class MacieRunner(Runner):
    """EN: Amazon Macie only scans S3 objects through classification jobs, not raw text. This runner reads the
    findings of a job you ran on the bench docs uploaded one per object (key = doc id). See bench/README.md.
    PT: O Macie so varre objeto do S3 via job de classificacao, nao texto cru. Este runner le os findings de um
    job q vc rodou c/ os docs do bench, 1 por objeto (chave = id do doc). Ver bench/README.md.
    """

    name = "macie"

    def __init__(self, findings: list[dict] | None = None, findings_path: str | None = None):
        # [BENCH-RUNNER-MACIE] EN: findings = exported Macie findings JSON / PT: findings = JSON exportado do Macie
        import json

        if findings is None:
            with open(findings_path or os.environ["MACIE_FINDINGS_JSON"], encoding="utf-8") as fh:
                findings = json.load(fh)
        self.by_key: dict[str, list[dict]] = {}
        for f in findings:
            key = f["resourcesAffected"]["s3Object"]["key"].rsplit("/", 1)[-1].removesuffix(".txt")
            for det in f["classificationDetails"]["result"]["sensitiveData"]:
                for d in det["detections"]:
                    for occ in d.get("occurrences", {}).get("lineRanges", []):
                        self.by_key.setdefault(key, []).append(
                            {"type": d["type"], "start": occ["startColumn"] - 1, "end": occ["endColumn"]}
                        )
        self.info = {"service": "Amazon Macie", "date": _today()}
        self._current_id = None

    def predict_doc(self, doc_id: str) -> list[dict]:
        # EN: Macie findings are keyed by doc id, not by text / PT: findings do Macie vem por id, nao por texto
        return [span(x["start"], x["end"], MACIE_MAP.get(x["type"], "OTHER")) for x in self.by_key.get(doc_id, [])]

    def predict_one(self, text: str) -> list[dict]:  # pragma: no cover
        raise RuntimeError("Macie works by doc id, use predict_doc / Macie funciona por id, use predict_doc")


class PurviewImportRunner(Runner):
    """EN: Microsoft Purview has no text-in/text-out API. Run the docs through a DLP policy test / Content explorer
    and export a CSV with columns doc_id, sit_name, start, end. PT: O Purview nao tem API texto-entra/texto-sai.
    Passe os docs por um teste de politica DLP / Content explorer e exporte CSV c/ doc_id, sit_name, start, end.
    """

    name = "purview"

    def __init__(self, csv_path: str | None = None, rows: list[dict] | None = None):
        # [BENCH-RUNNER-PURVIEW]
        if rows is None:
            with open(csv_path or os.environ["PURVIEW_EXPORT_CSV"], encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        self.by_id: dict[str, list[dict]] = {}
        for r in rows:
            self.by_id.setdefault(r["doc_id"], []).append(
                span(int(r["start"]), int(r["end"]), PURVIEW_MAP.get(r["sit_name"], "OTHER"))
            )
        self.info = {"service": "Microsoft Purview (import)", "date": _today()}

    def predict_doc(self, doc_id: str) -> list[dict]:
        return self.by_id.get(doc_id, [])

    def predict_one(self, text: str) -> list[dict]:  # pragma: no cover
        raise RuntimeError("Purview works by doc id, use predict_doc / Purview funciona por id, use predict_doc")
