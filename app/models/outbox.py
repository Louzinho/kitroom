import json

from ..db import execute, query, query_one


def add(cur, order_id, event_type, payload):
    cur.execute("INSERT INTO sync_outbox (order_id, event_type, payload) VALUES (%s,%s,%s)",
                (order_id, event_type, json.dumps(payload, default=str)))
    return cur.lastrowid


def get(outbox_id):
    return query_one("SELECT * FROM sync_outbox WHERE outbox_id=%s", (outbox_id,))


def list_all(status=None):
    if status:
        return query("SELECT * FROM sync_outbox WHERE status=%s ORDER BY outbox_id DESC", (status,))
    return query("SELECT * FROM sync_outbox ORDER BY outbox_id DESC LIMIT 200")


def pending_ids():
    return [r["outbox_id"] for r in
            query("SELECT outbox_id FROM sync_outbox WHERE status='pending' ORDER BY outbox_id")]


def mark_done(outbox_id):
    execute("""UPDATE sync_outbox SET status='done', processed_at=CURRENT_TIMESTAMP,
               attempts=attempts+1, last_error=NULL WHERE outbox_id=%s""", (outbox_id,))


def mark_failed(outbox_id, error):
    execute("UPDATE sync_outbox SET attempts=attempts+1, last_error=%s WHERE outbox_id=%s",
            (str(error)[:500], outbox_id))


def delete(outbox_id):
    execute("DELETE FROM sync_outbox WHERE outbox_id=%s", (outbox_id,))
