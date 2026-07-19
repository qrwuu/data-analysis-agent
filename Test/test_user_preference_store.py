import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import data.user_preference_store as preference_module


class TestUserPreferenceStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "users.sqlite3"
        self.db_patch = patch.object(preference_module, "DB_PATH", self.db_path)
        self.db_patch.start()
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
            conn.executemany("INSERT INTO users(id) VALUES(?)", [(1,), (2,)])
            conn.commit()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_preferences_are_private_and_deletable(self):
        first, error = preference_module.add_preference(1, "Default to GMV for sales analysis")
        self.assertIsNone(error)
        self.assertEqual(len(preference_module.list_preferences(1)), 1)
        self.assertEqual(preference_module.list_preferences(2), [])
        self.assertFalse(preference_module.delete_preference(2, first["id"]))
        self.assertTrue(preference_module.delete_preference(1, first["id"]))
        self.assertEqual(preference_module.list_preferences(1), [])

    def test_explicit_chat_capture_does_not_store_normal_questions(self):
        self.assertEqual(
            preference_module.extract_explicit_preference("\u8bb0\u4f4f\uff1a\u56fe\u8868\u4f18\u5148\u4f7f\u7528\u67f1\u72b6\u56fe"),
            "\u56fe\u8868\u4f18\u5148\u4f7f\u7528\u67f1\u72b6\u56fe",
        )
        self.assertEqual(
            preference_module.extract_explicit_preference("\u9ed8\u8ba4\uff1a\u4f7f\u7528 GMV"),
            "\u4f7f\u7528 GMV",
        )
        self.assertIsNone(
            preference_module.extract_explicit_preference("Which product had the highest GMV?"),
        )


if __name__ == "__main__":
    unittest.main()
