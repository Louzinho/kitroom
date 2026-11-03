from datetime import datetime, timezone

from ..db import mongo
from .review import oid


def _notes():
    return mongo().user_notifications


def create(user_id, title, message, kind="info", **extra):
    return _notes().insert_one({"userId": user_id, "title": title, "message": message,
                                "kind": kind, "isRead": False,
                                "sentAt": datetime.now(timezone.utc), **extra}).inserted_id


def for_user(user_id):
    return list(_notes().find({"userId": user_id}).sort("sentAt", -1).limit(100))


def list_all():
    return list(_notes().find().sort("sentAt", -1).limit(200))


def unread_count(user_id):
    return _notes().count_documents({"userId": user_id, "isRead": False})


def get(note_id):
    return _notes().find_one({"_id": oid(note_id)})


def update(note_id, fields):
    return _notes().update_one({"_id": oid(note_id)}, {"$set": fields}).matched_count


def mark_all_read(user_id):
    _notes().update_many({"userId": user_id, "isRead": False}, {"$set": {"isRead": True}})


def delete(note_id):
    return _notes().delete_one({"_id": oid(note_id)}).deleted_count


def delete_for_user(user_id):
    _notes().delete_many({"userId": user_id})
