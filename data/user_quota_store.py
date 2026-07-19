"""Persistent per-principal request quotas for cost-controlled chat access."""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.paths import data_path


DB_PATH = data_path("outputs", "auth", "usage.sqlite3")
USER_DAILY_LIMIT = int(os.getenv("BAA_USER_DAILY_MESSAGE_LIMIT", "30"))
GUEST_DAILY_LIMIT = int(os.getenv("BAA_GUEST_DAILY_MESSAGE_LIMIT", "5"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("BAA_USER_MAX_CONCURRENCY", "1"))
FAILURE_LIMIT = int(os.getenv("BAA_USER_FAILURE_LIMIT", "5"))
BLOCK_SECONDS = int(os.getenv("BAA_USER_BLOCK_SECONDS", "1800"))
LEASE_SECONDS = int(os.getenv("BAA_USER_REQUEST_LEASE_SECONDS", "900"))


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    code: str = ""
    message: str = ""
    used: int = 0
    remaining: int = 0
    daily_limit: int = USER_DAILY_LIMIT
    retry_after_seconds: int = 0


def _now() -> int:
    return int(time.time())


def _day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


class UserQuotaStore:
    def initialize(self) -> None:
        with closing(_connect()) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS quota_daily (
                    principal TEXT NOT NULL,
                    day TEXT NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(principal, day)
                );
                CREATE TABLE IF NOT EXISTS quota_runtime (
                    principal TEXT PRIMARY KEY,
                    active_count INTEGER NOT NULL DEFAULT 0,
                    active_expires_at INTEGER NOT NULL DEFAULT 0,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    blocked_until INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS guest_quota_claims (
                    guest_principal TEXT NOT NULL,
                    user_principal TEXT NOT NULL,
                    day TEXT NOT NULL,
                    PRIMARY KEY(guest_principal, user_principal, day)
                );
                CREATE INDEX IF NOT EXISTS idx_quota_daily_day ON quota_daily(day);
            """)

    def status(self, principal: str, *, daily_limit: int) -> dict:
        self.initialize()
        now, day = _now(), _day()
        with closing(_connect()) as conn:
            daily = conn.execute(
                "SELECT request_count FROM quota_daily WHERE principal = ? AND day = ?",
                (principal, day),
            ).fetchone()
            runtime = conn.execute(
                "SELECT active_count, active_expires_at, blocked_until FROM quota_runtime WHERE principal = ?",
                (principal,),
            ).fetchone()
        used = int(daily["request_count"]) if daily else 0
        active = int(runtime["active_count"]) if runtime and int(runtime["active_expires_at"]) > now else 0
        blocked_until = int(runtime["blocked_until"]) if runtime else 0
        return {
            "used": used,
            "remaining": max(0, daily_limit - used),
            "daily_limit": daily_limit,
            "active_requests": active,
            "blocked_until": blocked_until if blocked_until > now else None,
        }

    def claim_guest_usage(self, guest_principal: str, user_principal: str) -> dict:
        """Transfer today's guest usage once when the browser signs in."""
        if not guest_principal or not user_principal:
            return self.status(user_principal, daily_limit=USER_DAILY_LIMIT)
        self.initialize()
        day = _day()
        with closing(_connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                claimed = conn.execute(
                    "SELECT 1 FROM guest_quota_claims WHERE guest_principal = ? AND user_principal = ? AND day = ?",
                    (guest_principal, user_principal, day),
                ).fetchone()
                if not claimed:
                    guest = conn.execute(
                        "SELECT request_count FROM quota_daily WHERE principal = ? AND day = ?",
                        (guest_principal, day),
                    ).fetchone()
                    amount = int(guest["request_count"]) if guest else 0
                    if amount:
                        conn.execute(
                            "INSERT INTO quota_daily(principal, day, request_count) VALUES(?, ?, ?) "
                            "ON CONFLICT(principal, day) DO UPDATE SET request_count = request_count + excluded.request_count",
                            (user_principal, day, amount),
                        )
                    conn.execute(
                        "INSERT INTO guest_quota_claims(guest_principal, user_principal, day) VALUES(?, ?, ?)",
                        (guest_principal, user_principal, day),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return self.status(user_principal, daily_limit=USER_DAILY_LIMIT)

    def acquire(self, principal: str, *, daily_limit: int, guest: bool = False) -> QuotaDecision:
        self.initialize()
        now, day = _now(), _day()
        with closing(_connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                runtime = conn.execute(
                    "SELECT * FROM quota_runtime WHERE principal = ?", (principal,)
                ).fetchone()
                active = int(runtime["active_count"]) if runtime else 0
                expires_at = int(runtime["active_expires_at"]) if runtime else 0
                blocked_until = int(runtime["blocked_until"]) if runtime else 0
                failures = int(runtime["consecutive_failures"]) if runtime else 0
                if expires_at <= now:
                    active = 0
                if blocked_until > now:
                    conn.execute("COMMIT")
                    wait = blocked_until - now
                    return QuotaDecision(
                        False, "temporarily_blocked",
                        f"请求暂时受限，请在 {max(1, (wait + 59) // 60)} 分钟后再试。",
                        daily_limit=daily_limit, retry_after_seconds=wait,
                    )
                if active >= MAX_CONCURRENT_REQUESTS:
                    conn.execute("COMMIT")
                    return QuotaDecision(
                        False, "concurrency_limit",
                        "当前账号已有分析正在进行，请等待完成后再发送下一条。",
                        daily_limit=daily_limit, retry_after_seconds=15,
                    )
                daily = conn.execute(
                    "SELECT request_count FROM quota_daily WHERE principal = ? AND day = ?",
                    (principal, day),
                ).fetchone()
                used = int(daily["request_count"]) if daily else 0
                if used >= daily_limit:
                    conn.execute("COMMIT")
                    message = (
                        "本次体验额度已用完，请登录后继续使用。"
                        if guest else "今日分析额度已用完，请明天再试。"
                    )
                    return QuotaDecision(False, "daily_quota_exceeded", message, used, 0, daily_limit)

                next_used = used + 1
                conn.execute(
                    "INSERT INTO quota_daily(principal, day, request_count) VALUES(?, ?, 1) "
                    "ON CONFLICT(principal, day) DO UPDATE SET request_count = request_count + 1",
                    (principal, day),
                )
                conn.execute(
                    "INSERT INTO quota_runtime(principal, active_count, active_expires_at, consecutive_failures, blocked_until) "
                    "VALUES(?, 1, ?, ?, 0) "
                    "ON CONFLICT(principal) DO UPDATE SET active_count = 1, active_expires_at = excluded.active_expires_at",
                    (principal, now + LEASE_SECONDS, failures),
                )
                conn.execute("COMMIT")
                return QuotaDecision(True, used=next_used, remaining=max(0, daily_limit - next_used), daily_limit=daily_limit)
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def release(self, principal: str, *, success: bool) -> None:
        self.initialize()
        now = _now()
        with closing(_connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT active_count, consecutive_failures FROM quota_runtime WHERE principal = ?", (principal,)
                ).fetchone()
                active = max(0, int(row["active_count"]) - 1) if row else 0
                failures = 0 if success else (int(row["consecutive_failures"]) + 1 if row else 1)
                blocked_until = now + BLOCK_SECONDS if failures >= FAILURE_LIMIT else 0
                if blocked_until:
                    failures = 0
                conn.execute(
                    "INSERT INTO quota_runtime(principal, active_count, active_expires_at, consecutive_failures, blocked_until) "
                    "VALUES(?, ?, 0, ?, ?) "
                    "ON CONFLICT(principal) DO UPDATE SET active_count = excluded.active_count, "
                    "active_expires_at = 0, consecutive_failures = excluded.consecutive_failures, blocked_until = excluded.blocked_until",
                    (principal, active, failures, blocked_until),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def cancel(self, principal: str) -> None:
        """Release an admission that failed before any model work started."""
        self.release(principal, success=True)
        day = _day()
        with closing(_connect()) as conn:
            conn.execute(
                "UPDATE quota_daily SET request_count = MAX(0, request_count - 1) WHERE principal = ? AND day = ?",
                (principal, day),
            )


quota_store = UserQuotaStore()
