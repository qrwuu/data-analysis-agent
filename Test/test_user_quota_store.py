import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data.user_quota_store as quota_module
from api import create_app
from data.user_quota_store import QuotaDecision


class TestUserQuotaStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "usage.sqlite3"
        self.db_patch = patch.object(quota_module, "DB_PATH", self.db_path)
        self.db_patch.start()
        self.store = quota_module.UserQuotaStore()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_guest_limit_persists_for_the_same_browser_identity(self):
        principal = "guest:browser-a"
        for _ in range(5):
            decision = self.store.acquire(principal, daily_limit=5, guest=True)
            self.assertTrue(decision.allowed)
            self.store.release(principal, success=True)
        denied = self.store.acquire(principal, daily_limit=5, guest=True)
        self.assertEqual(denied.code, "daily_quota_exceeded")
        self.assertIn("登录", denied.message)

    def test_guest_usage_is_transferred_once_after_login(self):
        guest, user = "guest:browser-a", "user:42"
        for _ in range(5):
            self.assertTrue(self.store.acquire(guest, daily_limit=5, guest=True).allowed)
            self.store.release(guest, success=True)
        first = self.store.claim_guest_usage(guest, user)
        self.assertEqual(first["used"], 5)
        self.assertEqual(first["remaining"], 25)
        second = self.store.claim_guest_usage(guest, user)
        self.assertEqual(second["used"], 5)

    def test_concurrency_and_failure_block_are_enforced(self):
        principal = "user:42"
        self.assertTrue(self.store.acquire(principal, daily_limit=30).allowed)
        self.assertEqual(
            self.store.acquire(principal, daily_limit=30).code, "concurrency_limit"
        )
        self.store.release(principal, success=True)
        for _ in range(5):
            self.assertTrue(self.store.acquire(principal, daily_limit=30).allowed)
            self.store.release(principal, success=False)
        self.assertEqual(
            self.store.acquire(principal, daily_limit=30).code, "temporarily_blocked"
        )


class TestChatQuotaGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = create_app().test_client()

    def test_chat_rejects_before_starting_analysis_when_quota_is_exhausted(self):
        denied = QuotaDecision(
            False,
            "daily_quota_exceeded",
            "quota exhausted",
            used=5,
            remaining=0,
            daily_limit=5,
        )
        with patch("api.chat.quota_store.acquire", return_value=denied) as acquire:
            response = self.client.post(
                "/api/session/quota-admission-test/chat",
                json={"message": "analyze this data"},
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["code"], "daily_quota_exceeded")
        acquire.assert_called_once()


if __name__ == "__main__":
    unittest.main()
