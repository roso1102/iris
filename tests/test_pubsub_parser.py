"""Tier 0 unit tests — Pub/Sub envelope parsing (FIX-005).

Loads the production decoder from `services/ingestion-worker/app.py` (via
importlib — the directory name contains a hyphen, so it cannot be imported as a
normal package). Verifies that the base64-encoded `message.data` JSON payload is
decoded correctly and that envelope/root attributes are merged, so `doc_id` /
`gcs_uri` / `page_number` survive a real GCP push delivery.

Zero external deps: the decoder only uses stdlib `base64`/`json`.
"""

import base64
import importlib.util
import json
import sys
import unittest
from pathlib import Path

_APP_PY = Path(__file__).resolve().parents[1] / "services" / "ingestion-worker" / "app.py"


def _load_app_module():
    spec = importlib.util.spec_from_file_location("ingestion_worker_app", _APP_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


app = _load_app_module()
_decode_pubsub_payload = app._decode_pubsub_payload
_first_present = app._first_present


def _envelope(payload: dict, attrs: dict | None = None) -> dict:
    """Build a realistic GCP Pub/Sub push envelope."""
    message = {"data": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")}
    if attrs:
        message["attributes"] = attrs
    return {"message": message, "subscription": "projects/p/subscriptions/s"}


class TestPubsubParser(unittest.TestCase):

    def test_decodes_base64_payload(self):
        """doc_id/gcs_uri come from the base64-encoded message.data, not the envelope root."""
        env = _envelope({"gcs_uri": "gs://b/f.pdf", "tenant_id": "t1", "doc_id": "d1"})
        data, attrs = _decode_pubsub_payload(env)
        self.assertEqual(data["gcs_uri"], "gs://b/f.pdf")
        self.assertEqual(data["tenant_id"], "t1")
        self.assertEqual(data["doc_id"], "d1")

    def test_page_numbers_preserved(self):
        """page_number/total_pages from payload survive as strings (as Pub/Sub sends them)."""
        env = _envelope({"doc_id": "d1", "page_number": "3", "total_pages": "34"})
        data, _ = _decode_pubsub_payload(env)
        self.assertEqual(data["page_number"], "3")
        self.assertEqual(data["total_pages"], "34")

    def test_first_present_prefers_payload_over_attributes(self):
        data = {"doc_id": "from-payload"}
        attrs = {"doc_id": "from-attrs"}
        self.assertEqual(_first_present(data, attrs, "doc_id"), "from-payload")

    def test_first_present_falls_back_to_attributes(self):
        """When payload lacks a field, the attribute value is used."""
        data = {"gcs_uri": "gs://b/f.pdf"}
        attrs = {"doc_id": "from-attrs", "tenant_id": "t1"}
        self.assertEqual(_first_present(data, attrs, "doc_id"), "from-attrs")
        self.assertEqual(_first_present(data, attrs, "tenant_id"), "t1")

    def test_first_present_missing_everywhere(self):
        self.assertEqual(_first_present({}, {}, "gcs_uri"), "")

    def test_attributes_merged_from_root(self):
        """Eventarc can put attributes at the envelope root; they must be merged."""
        env = {
            "message": {"data": base64.b64encode(json.dumps({"doc_id": "d1"}).encode()).decode()},
            "attributes": {"tenant_id": "root-tenant"},
        }
        data, attrs = _decode_pubsub_payload(env)
        self.assertEqual(attrs["tenant_id"], "root-tenant")
        self.assertEqual(data["doc_id"], "d1")

    def test_malformed_base64_returns_empty_payload(self):
        """Corrupt data must not crash the handler — empty payload, no exception."""
        env = {"message": {"data": "!!!not-base64!!!"}}
        data, attrs = _decode_pubsub_payload(env)
        self.assertEqual(data, {})

    def test_empty_envelope(self):
        data, attrs = _decode_pubsub_payload({})
        self.assertEqual(data, {})
        self.assertEqual(attrs, {})

    def test_no_message_key_uses_envelope_root(self):
        """Some deliveries put message fields at the root; decoder must tolerate that."""
        env = {"data": base64.b64encode(json.dumps({"doc_id": "d1"}).encode()).decode()}
        data, _ = _decode_pubsub_payload(env)
        self.assertEqual(data["doc_id"], "d1")


if __name__ == "__main__":
    unittest.main()
