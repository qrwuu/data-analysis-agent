"""SQLite storage for local user accounts and private analysis history."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt

from infrastructure.paths import data_path

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DB_PATH = data_path("outputs", "auth", "users.sqlite3")
SECRET_PATH = data_path("outputs", "auth", "token_secret")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                nickname TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                runtime_session_id TEXT,
                title TEXT NOT NULL,
                data_source_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user_updated
                ON analysis_sessions(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS analysis_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                result_type TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_analysis_messages_session
                ON analysis_messages(session_id, created_at ASC);
        """)


def _secret() -> bytes:
    configured = os.getenv("BAA_AUTH_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_PATH.exists():
        SECRET_PATH.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return SECRET_PATH.read_text(encoding="utf-8").strip().encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_token(user: dict[str, Any]) -> str:
    payload = {"uid": int(user["id"]), "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64(hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def user_from_token(token: str) -> dict[str, Any] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(encoded))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return get_user(int(payload["uid"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    return {"id": int(row["id"]), "email": row["email"], "nickname": row["nickname"] or row["email"].split("@")[0]}


def get_user(user_id: int) -> dict[str, Any] | None:
    initialize()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def register(email: str, password: str, nickname: str = "") -> tuple[dict[str, Any] | None, str | None]:
    initialize()
    email = email.strip().lower()
    nickname = nickname.strip()[:80]
    if not EMAIL_RE.fullmatch(email):
        return None, "请输入有效的邮箱地址"
    if len(password) < 8:
        return None, "密码至少需要 8 位"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = _now()
    try:
        with _connect() as conn:
            cursor = conn.execute(
                "INSERT INTO users(email, password_hash, nickname, created_at, updated_at) VALUES(?, ?, ?, ?, ?)",
                (email, password_hash, nickname or None, now, now),
            )
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        return None, "该邮箱已注册，请直接登录"
    return get_user(user_id), None


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    initialize()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if not row:
        return None
    try:
        valid = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
    except ValueError:
        valid = False
    return dict(row) if valid else None


def update_nickname(user_id: int, nickname: str) -> dict[str, Any] | None:
    """Update only the profile field exposed by the lightweight account UI."""
    initialize()
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET nickname = ?, updated_at = ? WHERE id = ?",
            (nickname.strip()[:80] or None, _now(), user_id),
        )
    return get_user(user_id)


_GREETING_TITLES = {"你好", "您好", "嗨", "hi", "hello", "开始", "开始分析"}
_GENERIC_TITLE_MARKERS = ("未命名", "数据分析", "新分析", "新会话")


def _source_stem(source_name: str) -> str:
    first_name = str(source_name or "").split("、", 1)[0].strip()
    return re.sub(r"\.(?:xlsx|xls|csv)$", "", first_name, flags=re.IGNORECASE).strip()


def _title_from_question(question: str, source_name: str = "") -> str:
    """Prefer a useful analysis subject over greetings or generic requests."""
    text = " ".join(str(question or "").split()).strip().strip("。！？!?，,；;")
    lowered = text.lower()
    generic_request = not text or lowered in _GREETING_TITLES or lowered in {
        "分析这个数据", "分析数据", "帮我分析", "帮我分析这个数据", "看看这个数据",
    }
    if generic_request:
        source = _source_stem(source_name)
        return f"{source} 数据分析" if source else "数据分析"
    return f"{text[:32]}…" if len(text) > 32 else text


def _is_generic_title(title: str) -> bool:
    value = str(title or "").strip()
    return not value or value.lower() in _GREETING_TITLES or value in _GENERIC_TITLE_MARKERS or "未命名" in value


def _source_name(session) -> str:
    sources = session.list_sources() if hasattr(session, "list_sources") else []
    return "、".join(str(item.get("name") or "") for item in sources[:5] if item.get("name"))


def _ensure_session(conn: sqlite3.Connection, user_id: int, runtime_session_id: str, question: str, source_name: str) -> str:
    row = conn.execute(
        "SELECT id, title FROM analysis_sessions WHERE user_id = ? AND runtime_session_id = ? ORDER BY updated_at DESC LIMIT 1",
        (user_id, runtime_session_id),
    ).fetchone()
    now = _now()
    if row:
        candidate_title = _title_from_question(question, source_name)
        current_title = str(row["title"] or "")
        next_title = candidate_title if _is_generic_title(current_title) and not _is_generic_title(candidate_title) else current_title
        conn.execute(
            "UPDATE analysis_sessions SET updated_at = ?, data_source_name = ?, title = ? WHERE id = ?",
            (now, source_name, next_title, row["id"]),
        )
        return str(row["id"])
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO analysis_sessions(id, user_id, runtime_session_id, title, data_source_name, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
        (session_id, user_id, runtime_session_id, _title_from_question(question, source_name), source_name, now, now),
    )
    return session_id


def record_user_message(user_id: int, runtime_session_id: str, session, question: str) -> str:
    """Persist a submitted question before analysis begins so it cannot be lost."""
    initialize()
    # If this runtime conversation began as a guest (for example before the
    # browser restored its auth token), claim its already-visible messages for
    # the current authenticated user before adding the new question.
    if getattr(session, "history", None):
        import_runtime_session(user_id, runtime_session_id, session)
    with _connect() as conn:
        history_id = _ensure_session(conn, user_id, runtime_session_id, question, _source_name(session))
        conn.execute(
            "INSERT INTO analysis_messages(id, session_id, user_id, role, content, result_type, metadata_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), history_id, user_id, "user", question, "question", None, _now()),
        )
    return history_id


def record_assistant_message(user_id: int, history_id: str, answer: str, reasoning: str, chart_ids: list[str]) -> bool:
    """Append a completed AI reply to the already-persisted user question."""
    if not str(answer or "").strip():
        return False
    initialize()
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM analysis_sessions WHERE id = ? AND user_id = ?", (history_id, user_id)
        ).fetchone()
        if not exists:
            return False
        now = _now()
        conn.execute(
            "INSERT INTO analysis_messages(id, session_id, user_id, role, content, result_type, metadata_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), history_id, user_id, "assistant", answer, "analysis", json.dumps({"reasoning": reasoning, "chart_ids": chart_ids}, ensure_ascii=False), now),
        )
        conn.execute("UPDATE analysis_sessions SET updated_at = ? WHERE id = ?", (now, history_id))
    return True


def persist_turn(user_id: int, runtime_session_id: str, session, question: str, answer: str, reasoning: str, chart_ids: list[str]) -> str:
    history_id = record_user_message(user_id, runtime_session_id, session, question)
    record_assistant_message(user_id, history_id, answer, reasoning, chart_ids)
    return history_id


def import_runtime_session(user_id: int, runtime_session_id: str, session) -> str:
    initialize()
    history = list(getattr(session, "history", []) or [])
    first_question = next((item.get("content", "") for item in history if item.get("role") == "user"), "")
    with _connect() as conn:
        history_id = _ensure_session(conn, user_id, runtime_session_id, first_question, _source_name(session))
        exists = conn.execute("SELECT 1 FROM analysis_messages WHERE session_id = ? LIMIT 1", (history_id,)).fetchone()
        if exists:
            return history_id
        now = _now()
        for item in history:
            role = str(item.get("role") or "")
            if role not in {"user", "assistant"}:
                continue
            metadata = {key: item[key] for key in ("reasoning", "chart_ids") if item.get(key)}
            conn.execute(
                "INSERT INTO analysis_messages(id, session_id, user_id, role, content, result_type, metadata_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), history_id, user_id, role, str(item.get("content") or ""), "imported", json.dumps(metadata, ensure_ascii=False) if metadata else None, now),
            )
    return history_id


def list_sessions(user_id: int) -> list[dict[str, Any]]:
    initialize()
    with _connect() as conn:
        # Upgrade titles produced by the earlier "first message wins" rule.
        # A greeting should never remain the only way to identify an analysis.
        generic_sessions = conn.execute(
            "SELECT id, title, data_source_name FROM analysis_sessions WHERE user_id = ?", (user_id,)
        ).fetchall()
        for session_row in generic_sessions:
            if not _is_generic_title(session_row["title"]):
                continue
            questions = conn.execute(
                "SELECT content FROM analysis_messages WHERE session_id = ? AND user_id = ? AND role = 'user' ORDER BY created_at",
                (session_row["id"], user_id),
            ).fetchall()
            for question_row in questions:
                candidate = _title_from_question(question_row["content"], session_row["data_source_name"] or "")
                if not _is_generic_title(candidate):
                    conn.execute(
                        "UPDATE analysis_sessions SET title = ?, updated_at = ? WHERE id = ?",
                        (candidate, _now(), session_row["id"]),
                    )
                    break
        rows = conn.execute("""
            SELECT s.*, (
                SELECT content FROM analysis_messages m
                WHERE m.session_id = s.id AND m.user_id = s.user_id AND m.role = 'user'
                ORDER BY m.created_at DESC LIMIT 1
            ) AS last_question
            FROM analysis_sessions s WHERE s.user_id = ? ORDER BY s.updated_at DESC
        """, (user_id,)).fetchall()
    return [dict(row) for row in rows]


def get_session(user_id: int, history_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    initialize()
    with _connect() as conn:
        session_row = conn.execute("SELECT * FROM analysis_sessions WHERE id = ? AND user_id = ?", (history_id, user_id)).fetchone()
        if not session_row:
            return None, []
        messages = conn.execute("SELECT * FROM analysis_messages WHERE session_id = ? AND user_id = ? ORDER BY created_at", (history_id, user_id)).fetchall()
    result = []
    for row in messages:
        item = dict(row)
        metadata = json.loads(item.pop("metadata_json") or "{}")
        item.update(metadata)
        result.append(item)
    return dict(session_row), result


def rename_session(user_id: int, history_id: str, title: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("UPDATE analysis_sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?", (title[:80], _now(), history_id, user_id))
    return cursor.rowcount > 0


def delete_session(user_id: int, history_id: str) -> bool:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM analysis_sessions WHERE id = ? AND user_id = ?", (history_id, user_id))
    return cursor.rowcount > 0
