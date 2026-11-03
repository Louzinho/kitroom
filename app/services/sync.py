"""Cross-database synchronisation: applies outbox events to MongoDB.

SQL and MongoDB cannot share one transaction, so the order is committed first with
an outbox row, then this step runs in its own MongoDB multi-document transaction.
If it fails, MongoDB aborts (nothing partial remains), the row stays 'pending' and
can be replayed. Every write is keyed by eventKey, so replaying is harmless.
"""
import json
from datetime import datetime, timezone

from ..db import mongo, mongo_client, mongo_supports_transactions
from ..models import outbox


class SimulatedSyncFailure(Exception):
    pass


def _upsert_event(collection, key, doc, session):
    collection.update_one({"eventKey": key}, {"$setOnInsert": {**doc, "eventKey": key}},
                          upsert=True, session=session)


def _apply(row, payload, session, fail):
    db = mongo()
    now = datetime.now(timezone.utc)
    user_id, order_id = payload["user_id"], row["order_id"]
    key = f"outbox:{row['outbox_id']}"
    event = row["event_type"]

    if event == "order_placed":
        # Only delete the cart the order was built from. If the customer has
        # changed it since (version moved on), a replay must leave it alone.
        db.shopping_carts.delete_one({"userId": user_id, "version": payload["cart_version"]},
                                     session=session)
        title, message, kind = (f"Order #{order_id} confirmed",
                                f"We have your order for ฿{payload['total']}.", "order")
    elif event == "order_cancelled":
        title, message, kind = (f"Order #{order_id} cancelled",
                                "Your order is cancelled and the items are back in stock.", "order")
    else:
        title, message, kind = (f"Order #{order_id} {payload['status']}",
                                f"Your order is now {payload['status']}.", "order")

    if fail:  # Lab scenario: crash after the cart delete, before the other writes.
        raise SimulatedSyncFailure("Simulated MongoDB failure in the sync transaction")

    _upsert_event(db.user_activity_logs, key, {
        "userId": user_id, "action_type": event, "ip_address": payload.get("ip"),
        "metadata": {"orderId": order_id, **{k: payload[k] for k in ("total", "status", "items")
                                             if k in payload}},
        "timestamp": now}, session)
    _upsert_event(db.user_notifications, key, {
        "userId": user_id, "title": title, "message": message, "kind": kind,
        "isRead": False, "sentAt": now, "orderId": order_id}, session)


def process(outbox_id, fail=False):
    """Applies one event. Returns True when MongoDB is in sync with SQL for it."""
    row = outbox.get(outbox_id)
    if row is None or row["status"] == "done":
        return row is not None
    payload = row["payload"]
    payload = json.loads(payload) if isinstance(payload, str) else payload
    try:
        if mongo_supports_transactions():
            with mongo_client().start_session() as session:
                session.with_transaction(lambda s: _apply(row, payload, s, fail))
        else:
            # Standalone mongod has no transactions; the writes are idempotent,
            # so a failed attempt is still repaired by a replay.
            _apply(row, payload, None, fail)
    except Exception as exc:  # noqa: BLE001 - any failure must leave the event pending
        outbox.mark_failed(outbox_id, exc)
        return False
    outbox.mark_done(outbox_id)
    return True


def process_pending():
    ids = outbox.pending_ids()
    return {"processed": len(ids), "synced": sum(process(i) for i in ids)}
