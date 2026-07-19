"""Persistent storage for SQL / Google Sheets / HTTP API connection configs."""
import logging
log = logging.getLogger(__name__)

import json
import os
from pathlib import Path
from typing import Optional
from infrastructure.paths import runtime_config_path

_CONFIG_FILE = runtime_config_path(
    "datasource_config.json", "data/datasource_config.json"
)
_CONFIG_DIR = _CONFIG_FILE.parent

_SENSITIVE_KEYS = {
    "sql": "connection_string",
    "gsheets": "creds_json",
    "api": "auth_value",
}


class DataSourceConfigManager:
    def __init__(self):
        self._configs: dict = {}
        self._load()

    def _load(self):
        if _CONFIG_FILE.exists():
            try:
                self._configs = json.loads(_CONFIG_FILE.read_text("utf-8"))
            except Exception as e:
                log.warning("[datasource_config] failed to load config, using empty: %s", e)
                self._configs = {}

    def _save(self):
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(
            json.dumps(self._configs, indent=2, ensure_ascii=False), "utf-8"
        )

    @staticmethod
    def _user_key(user_id: int | str | None) -> str | None:
        """Return a stable storage key only for authenticated users.

        Connection strings and service-account credentials are sensitive.  A
        guest may connect for the current session, but must never create a
        reusable shared configuration.
        """
        return str(user_id) if user_id is not None and str(user_id).strip() else None

    def _user_configs(self, user_id: int | str | None, *, create: bool = False) -> dict:
        key = self._user_key(user_id)
        if not key:
            return {}
        users = self._configs.get("users")
        if not isinstance(users, dict):
            if not create:
                return {}
            users = {}
            self._configs = {"users": users}
        if create:
            return users.setdefault(key, {})
        value = users.get(key, {})
        return value if isinstance(value, dict) else {}

    def save(self, ds_type: str, config: dict, user_id: int | str | None = None):
        if not self._user_key(user_id):
            return
        scoped = self._user_configs(user_id, create=True)
        scoped[ds_type] = config
        self._save()

    def delete(self, ds_type: str, user_id: int | str | None = None):
        scoped = self._user_configs(user_id)
        if not scoped:
            return
        scoped.pop(ds_type, None)
        self._save()

    def get(self, ds_type: str, user_id: int | str | None = None) -> Optional[dict]:
        return self._user_configs(user_id).get(ds_type)

    def list_public(self, user_id: int | str | None = None) -> dict:
        """Return configs with sensitive fields replaced by has_* boolean flags."""
        result = {}
        for ds_type, cfg in self._user_configs(user_id).items():
            pub = dict(cfg)
            sensitive_key = _SENSITIVE_KEYS.get(ds_type)
            if sensitive_key and sensitive_key in pub:
                pub[f"has_{sensitive_key}"] = bool(pub.pop(sensitive_key))
            result[ds_type] = pub
        return result


_mgr: Optional[DataSourceConfigManager] = None


def get_datasource_config_manager() -> DataSourceConfigManager:
    global _mgr
    if _mgr is None:
        _mgr = DataSourceConfigManager()
    return _mgr
