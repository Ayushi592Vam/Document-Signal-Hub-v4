"""
modules/audit.py
Append-only audit log helpers.
"""

import json
from config.settings import AUDIT_LOG_PATH


def _load_audit_log() -> list:
    try:
        with open(AUDIT_LOG_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def _save_audit_log(log: list) -> None:
    with open(AUDIT_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def _append_audit(entry: dict) -> None:
    log = _load_audit_log()
    log.append(entry)
    _save_audit_log(log)
