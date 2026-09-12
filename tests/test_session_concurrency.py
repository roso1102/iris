"""Phase 0.1 tests — transactional turn sequencing + optimistic concurrency.

Ordering is now allocated inside a Firestore transaction and guarded by the
``turn_seq`` version read before synthesis, so two independent API instances
cannot append out of order.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from services.common.errors import Conflict
from services.retrieval_api.app import _append_firestore_messages


def _fake_client(turn_seq: int = 0, exists: bool = True) -> MagicMock:
    fake = MagicMock()
    snapshot = MagicMock()
    snapshot.exists = exists
    snapshot.to_dict.return_value = {"turn_seq": turn_seq} if exists else {}
    fake.document.return_value.get.return_value = snapshot
    return fake


_TURN = [
    {"role": "user", "content": "question"},
    {"role": "assistant", "content": "answer"},
]


class TestOptimisticConcurrency(unittest.TestCase):

    def test_matching_version_appends_one_turn(self):
        fake = _fake_client(turn_seq=3)
        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake):
            new_version = _append_firestore_messages(
                "tenant-a", "s1", _TURN, expected_turn_seq=3
            )
        self.assertEqual(new_version, 4)
        txn = fake.transaction.return_value
        message_writes = [
            call.args[1] for call in txn.set.call_args_list
            if "turn_seq" in call.args[1] and "role" in call.args[1]
        ]
        self.assertEqual(len(message_writes), 2)
        self.assertEqual([w["message_index"] for w in message_writes], [0, 1])
        self.assertTrue(all(w["turn_seq"] == 4 for w in message_writes))
        # Session cursor advanced in the same transaction.
        self.assertIn({"turn_seq": 4}, [call.args[1] for call in txn.set.call_args_list])

    def test_stale_version_raises_conflict(self):
        # Instance B read history at turn_seq=3; instance A has since committed
        # turn 4, so B's append must be rejected rather than misordered.
        fake = _fake_client(turn_seq=4)
        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake):
            with self.assertRaises(Conflict):
                _append_firestore_messages(
                    "tenant-a", "s1", _TURN, expected_turn_seq=3
                )

    def test_second_instance_uses_committed_version(self):
        # Instance B re-reads after the conflict, sees turn_seq=4, and appends 5.
        fake = _fake_client(turn_seq=4)
        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake):
            new_version = _append_firestore_messages(
                "tenant-a", "s1", _TURN, expected_turn_seq=4
            )
        self.assertEqual(new_version, 5)

    def test_store_failure_maps_to_503(self):
        fake = _fake_client(turn_seq=0)
        fake.transaction.return_value._commit.side_effect = Exception("unavailable")
        with patch("services.retrieval_api.app._get_firestore_client", return_value=fake):
            with self.assertRaises(Exception) as ctx:
                _append_firestore_messages("tenant-a", "s1", _TURN, expected_turn_seq=0)
        self.assertEqual(getattr(ctx.exception, "status_code", None), 503)


if __name__ == "__main__":
    unittest.main()
