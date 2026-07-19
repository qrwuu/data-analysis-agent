"""Private, explicit long-term preference memory for signed-in users."""
from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

from infrastructure.paths import data_path


DB_PATH = data_path("outputs", "auth", "users.sqlite3")
MAX_PREFERENCES_PER_USER = 20
MAX_PREFERENCE_LENGTH = 300

_EXPLICIT_PATTERNS = (
    re.compile(r"^(?:请)?记住[：:\s]*(.+)$"),
    re.compile(r"^(?:以后|今后)(?:请|就)?(?:默认)?[：，,\s]*(.+)$"),
    re.compile(r"^默认[：，,\s]*(.+)$"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize() -> None:
    with closing(_connect()) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_user_preferences_user_updated
                ON user_preferences(user_id, updated_at DESC);
        """)


def list_preferences(user_id: int | str) -> list[dict[str, Any]]:
    initialize()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, content, source, created_at, updated_at FROM user_preferences "
            "WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
            (int(user_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def add_preference(user_id: int | str, content: str, *, source: str = "manual") -> tuple[dict[str, Any] | None, str | None]:
    clean = " ".join(str(content or "").split()).strip()
    if not clean:
        return None, "请输入想让 Agent 长期记住的偏好。"
    if len(clean) > MAX_PREFERENCE_LENGTH:
        return None, f"单条偏好不能超过 {MAX_PREFERENCE_LENGTH} 个字符。"

    initialize()
    now = _now()
    with closing(_connect()) as conn:
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE user_id = ? AND content = ?",
            (int(user_id), clean),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE user_preferences SET updated_at = ? WHERE id = ?",
                (now, existing["id"]),
            )
            row = conn.execute(
                "SELECT id, content, source, created_at, updated_at FROM user_preferences WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            return dict(row), None
        total = conn.execute(
            "SELECT COUNT(*) AS count FROM user_preferences WHERE user_id = ?", (int(user_id),)
        ).fetchone()["count"]
        if total >= MAX_PREFERENCES_PER_USER:
            return None, f"最多可保存 {MAX_PREFERENCES_PER_USER} 条偏好，请先删除不再需要的内容。"
        preference_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO user_preferences(id, user_id, content, source, created_at, updated_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (preference_id, int(user_id), clean, source[:20], now, now),
        )
        row = conn.execute(
            "SELECT id, content, source, created_at, updated_at FROM user_preferences WHERE id = ?",
            (preference_id,),
        ).fetchone()
    return dict(row), None


def delete_preference(user_id: int | str, preference_id: str) -> bool:
    initialize()
    with closing(_connect()) as conn:
        cursor = conn.execute(
            "DELETE FROM user_preferences WHERE id = ? AND user_id = ?",
            (str(preference_id), int(user_id)),
        )
    return cursor.rowcount > 0


def extract_explicit_preference(message: str) -> str | None:
    """Capture only an intentional memory instruction, never arbitrary chat text."""
    clean = " ".join(str(message or "").strip().split())
    if not clean or len(clean) > MAX_PREFERENCE_LENGTH + 24:
        return None
    for pattern in _EXPLICIT_PATTERNS:
        match = pattern.match(clean)
        if match:
            candidate = match.group(1).strip(" ：:，,。.!！")
            return candidate or None
    return None
