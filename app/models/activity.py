from datetime import datetime, timezone

from flask import has_request_context, request

from ..db import mongo
from .review import oid


def _logs():
    return mongo().user_activity_logs


def log(user_id, action_type, metadata=None, **extra):
    """Best-effort telemetry: a logging failure must never break the user's action."""
    try:
        doc = {"userId": user_id, "action_type": action_type, "metadata": metadata or {},
               "ip_address": request.remote_addr if has_request_context() else None,
               "timestamp": datetime.now(timezone.utc), **extra}
        _logs().insert_one(doc)
    except Exception:  # noqa: BLE001
        pass


def search(user_id=None, action_type=None, limit=100):
    f = {}
    if user_id:
        f["userId"] = user_id
    if action_type:
        f["action_type"] = action_type
    return list(_logs().find(f).sort("timestamp", -1).limit(limit))


def action_types():
    return sorted(_logs().distinct("action_type"))


def annotate(log_id, note):
    return _logs().update_one({"_id": oid(log_id)}, {"$set": {"adminNote": note}}).matched_count


def delete(log_id):
    return _logs().delete_one({"_id": oid(log_id)}).deleted_count
