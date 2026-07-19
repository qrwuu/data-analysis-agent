"""Authenticated, per-user analysis history endpoints."""
from flask import Blueprint, jsonify, request

from .auth import current_user, login_required
from .state import session_manager
from data import user_history_store as store

bp = Blueprint("user_history", __name__)


@bp.get("/api/history/sessions")
@login_required
def list_history():
    return jsonify({"sessions": store.list_sessions(int(current_user()["id"]))})


@bp.get("/api/history/sessions/<history_id>")
@login_required
def get_history(history_id: str):
    session, messages = store.get_session(int(current_user()["id"]), history_id)
    if not session:
        return jsonify({"error": "历史分析不存在或无权访问"}), 404
    return jsonify({"session": session, "messages": messages})


@bp.post("/api/history/sessions/<history_id>/restore/<sid>")
@login_required
def restore_history_to_runtime(history_id: str, sid: str):
    session, messages = store.get_session(int(current_user()["id"]), history_id)
    if not session:
        return jsonify({"error": "历史分析不存在或无权访问"}), 404
    runtime = session_manager.get_or_create(sid)
    runtime.history = [
        {key: item[key] for key in ("role", "content", "reasoning", "chart_ids") if item.get(key) is not None}
        for item in messages
    ]
    return jsonify({"ok": True, "session": session, "messages": runtime.history})


@bp.patch("/api/history/sessions/<history_id>")
@login_required
def rename_history(history_id: str):
    title = str((request.get_json(silent=True) or {}).get("title") or "").strip()
    if not title:
        return jsonify({"error": "请输入分析标题"}), 400
    if not store.rename_session(int(current_user()["id"]), history_id, title):
        return jsonify({"error": "历史分析不存在或无权访问"}), 404
    return jsonify({"ok": True})


@bp.delete("/api/history/sessions/<history_id>")
@login_required
def delete_history(history_id: str):
    if not store.delete_session(int(current_user()["id"]), history_id):
        return jsonify({"error": "历史分析不存在或无权访问"}), 404
    return jsonify({"ok": True})


@bp.post("/api/history/import-session/<sid>")
@login_required
def import_temporary_session(sid: str):
    session = session_manager.get(sid)
    if not session or not session.history:
        return jsonify({"error": "当前临时分析为空，无需保存"}), 400
    history_id = store.import_runtime_session(int(current_user()["id"]), sid, session)
    title = str((request.get_json(silent=True) or {}).get("title") or "").strip()
    if title:
        store.rename_session(int(current_user()["id"]), history_id, title)
    saved_session, _ = store.get_session(int(current_user()["id"]), history_id)
    return jsonify({"ok": True, "session_id": history_id, "session": saved_session})
