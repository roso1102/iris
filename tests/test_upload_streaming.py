"""Upload streaming path — temp-file lifecycle, partial cleanup, native timeout.

Exercises ``_stream_upload_to_gcs`` directly (not through the HTTP layer) so the
temporary-file lifecycle and the GCS upload arguments are observable.
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("MODEL_BACKEND", "mock")

from services.common.cloud import GCS_TIMEOUT_SECONDS
from services.common.errors import BadUpstreamResponse, InvalidInput
from services.common.reliability import TransientError
import services.retrieval_api.app as app_module
from services.retrieval_api.app import _stream_upload_to_gcs


class _FakeUpload:
    """Minimal async UploadFile stub."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self, size: int) -> bytes:
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk


def _recording_tempfile(created: list):
    """Wrap the real NamedTemporaryFile, recording every path it creates."""
    real = tempfile.NamedTemporaryFile  # captured before the patch is applied

    def _factory(*args, **kwargs):
        handle = real(*args, **kwargs)
        created.append(handle.name)
        return handle

    return _factory


class _GcsPatcher:
    """Patch the GCS client so the blob is a MagicMock we can assert on."""

    def __init__(self):
        self.blob = MagicMock()
        self.client = MagicMock()
        self.client.bucket.return_value.blob.return_value = self.blob

    def __enter__(self):
        self._patcher = patch(
            "services.retrieval_api.app._get_gcs_client", return_value=self.client
        )
        self._patcher.start()
        return self.blob

    def __exit__(self, *exc):
        self._patcher.stop()
        return False


class TestStreamUploadTempFileLifecycle(unittest.TestCase):

    def test_temp_file_removed_after_success(self):
        created = []
        with _GcsPatcher() as blob, patch(
            "services.retrieval_api.app.tempfile.NamedTemporaryFile",
            _recording_tempfile(created),
        ):
            total = asyncio.run(
                _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b"x" * 32))
            )
        self.assertEqual(total, 32)
        self.assertTrue(created)
        for path in created:
            self.assertFalse(Path(path).exists(), f"temp residue: {path}")
        blob.upload_from_filename.assert_called_once()

    def test_temp_file_removed_after_gcs_failure(self):
        created = []
        with _GcsPatcher() as blob, patch(
            "services.retrieval_api.app.tempfile.NamedTemporaryFile",
            _recording_tempfile(created),
        ):
            blob.upload_from_filename.side_effect = TransientError("reset")
            with self.assertRaises(BadUpstreamResponse):
                asyncio.run(
                    _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b"x" * 32))
                )
        for path in created:
            self.assertFalse(Path(path).exists(), f"temp residue: {path}")

    def test_temp_file_removed_after_oversize_rejection(self):
        created = []
        with _GcsPatcher() as blob, patch(
            "services.retrieval_api.app.tempfile.NamedTemporaryFile",
            _recording_tempfile(created),
        ), patch.object(app_module, "_UPLOAD_MAX_BYTES", 8):
            with self.assertRaises(InvalidInput):
                asyncio.run(
                    _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b"x" * 64))
                )
        for path in created:
            self.assertFalse(Path(path).exists(), f"temp residue: {path}")
        blob.upload_from_filename.assert_not_called()

    def test_partial_blob_delete_attempted_on_failure(self):
        with _GcsPatcher() as blob:
            blob.upload_from_filename.side_effect = TransientError("reset")
            with self.assertRaises(BadUpstreamResponse):
                asyncio.run(
                    _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b"x" * 32))
                )
        blob.delete.assert_called()  # _safe_delete_blob → gcs_delete(blob)

    def test_zero_byte_file_rejected_without_uploading(self):
        with _GcsPatcher() as blob:
            with self.assertRaises(InvalidInput):
                asyncio.run(
                    _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b""))
                )
        blob.upload_from_filename.assert_not_called()

    def test_upload_uses_pdf_content_type_and_native_timeout(self):
        with _GcsPatcher() as blob:
            asyncio.run(
                _stream_upload_to_gcs("tenant-a", "doc_x", _FakeUpload(b"%PDF-1.4"))
            )
        kwargs = blob.upload_from_filename.call_args.kwargs
        self.assertEqual(kwargs["content_type"], "application/pdf")
        self.assertEqual(kwargs["timeout"], GCS_TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
