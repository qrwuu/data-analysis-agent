"""Email/password authentication for private analysis history."""
from functools import wraps

from flask import Blueprint, g, jsonify, request

from data import user_history_store as store
from data import user_preference_store as preference_store
from data.user_quota_store import USER_DAILY_LIMIT, quota_store

bp = Blueprint("auth", __name__)


def _quota_for_user(user: dict) -> dict:
    guest_id = str(request.cookies.get("baa_guest_id") or "").strip()
    principal = f"user:{user['id']}"
    if guest_id:
        return quota_store.claim_guest_usage(f"guest:{guest_id}", principal)
    return quota_store.status(principal, daily_limit=USER_DAILY_LIMIT)


def current_user():
    if hasattr(g, "baa_current_user"):
        return g.baa_current_user
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    g.baa_current_user = store.user_from_token(token) if token else None
    return g.baa_current_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "请先登录后再查看历史分析", "code": "auth_required"}), 401
        return view(*args, **kwargs)
    return wrapped


@bp.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    user, error = store.register(str(data.get("email") or ""), str(data.get("password") or ""), str(data.get("nickname") or ""))
    if error:
        return jsonify({"error": error}), 400
    quota = _quota_for_user(user)
    return jsonify({"token": store.issue_token(user), "user": store.public_user(user), "quota": quota}), 201


@bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = store.authenticate(str(data.get("email") or ""), str(data.get("password") or ""))
    if not user:
        return jsonify({"error": "邮箱或密码不正确，请重试"}), 401
    quota = _quota_for_user(user)
    return jsonify({"token": store.issue_token(user), "user": store.public_user(user), "quota": quota})


@bp.get("/api/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "登录状态已失效", "code": "auth_required"}), 401
    return jsonify({
        "user": store.public_user(user),
        "quota": _quota_for_user(user),
    })


@bp.patch("/api/auth/me")
@login_required
def update_me():
    data = request.get_json(silent=True) or {}
    user = store.update_nickname(int(current_user()["id"]), str(data.get("nickname") or ""))
    return jsonify({"user": store.public_user(user)})


@bp.get("/api/preferences")
@login_required
def list_preferences():
    return jsonify({"preferences": preference_store.list_preferences(current_user()["id"])})


@bp.post("/api/preferences")
@login_required
def add_preference():
    data = request.get_json(silent=True) or {}
    preference, error = preference_store.add_preference(
        current_user()["id"], str(data.get("content") or ""), source="manual",
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"preference": preference}), 201


@bp.delete("/api/preferences/<preference_id>")
@login_required
def delete_preference(preference_id: str):
    deleted = preference_store.delete_preference(current_user()["id"], preference_id)
    if not deleted:
        return jsonify({"error": "未找到该偏好记忆。"}), 404
    return jsonify({"ok": True})


@bp.post("/api/auth/logout")
def logout():
    return jsonify({"ok": True})
