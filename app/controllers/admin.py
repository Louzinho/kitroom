from flask import jsonify

from .. import validate as v
from ..auth import admin_required, current_user
from ..db import mongo, mongo_client, query, query_one
from ..errors import ApiError
from ..models import activity, cart, outbox, product
from ..services import orders as service
from ..services import sync


def health():
    state = {"mysql": False, "mongodb": False, "replica_set": False}
    try:
        state["mysql"] = query_one("SELECT 1 AS ok")["ok"] == 1
    except Exception:  # noqa: BLE001
        pass
    try:
        hello = mongo_client().admin.command("hello")
        state["mongodb"], state["replica_set"] = True, bool(hello.get("setName"))
    except Exception:  # noqa: BLE001
        pass
    ok = state["mysql"] and state["mongodb"]
    return jsonify(state), 200 if ok else 503


@admin_required
def dashboard():
    return jsonify({
        "revenue": query_one("""SELECT COALESCE(SUM(total_amount),0) AS v, COUNT(*) AS n
                                FROM orders WHERE order_status <> 'cancelled'"""),
        "low_stock": query("""SELECT product_id, title, stock_quantity FROM products
                              WHERE status='active' AND stock_quantity <= 3
                              ORDER BY stock_quantity, title LIMIT 8"""),
        "top_sellers": query("""SELECT p.product_id, p.title, SUM(i.quantity) AS sold,
                                       SUM(i.quantity * i.unit_price) AS revenue
                                FROM order_items i
                                JOIN orders o ON o.order_id = i.order_id
                                JOIN products p ON p.product_id = i.product_id
                                WHERE o.order_status <> 'cancelled'
                                GROUP BY p.product_id, p.title
                                HAVING sold > 0 ORDER BY sold DESC LIMIT 5"""),
        "pending_sync": len(outbox.pending_ids()),
        "active_carts": mongo().shopping_carts.count_documents({"items.0": {"$exists": True}}),
        "reviews": mongo().product_reviews.estimated_document_count(),
    })


@admin_required
def list_outbox():
    return jsonify(outbox.list_all())


@admin_required
def retry_outbox(outbox_id):
    if outbox.get(outbox_id) is None:
        raise ApiError("That event does not exist.", 404)
    return jsonify({"synced": sync.process(outbox_id), "event": outbox.get(outbox_id)})


@admin_required
def retry_all_outbox():
    return jsonify(sync.process_pending())


@admin_required
def delete_outbox(outbox_id):
    event = outbox.get(outbox_id)
    if event is None:
        raise ApiError("That event does not exist.", 404)
    if event["status"] == "pending":
        raise ApiError("Replay this event first. Deleting it would lose the sync.", 409)
    outbox.delete(outbox_id)
    return "", 204


SCENARIOS = {
    "success": {"fail_at": None},
    "insufficient_stock": {"fail_at": None, "short": True},
    "after_deduct": {"fail_at": "after_deduct"},
    "after_order": {"fail_at": "after_order"},
    "mid_items": {"fail_at": "mid_items"},
    "mongo_sync": {"fail_at": "mongo_sync"},
}


def _snapshot(user_id, product_ids):
    db = mongo()
    return {
        "stock": {str(p["product_id"]): p["stock_quantity"] for p in product.get_many(product_ids)},
        "orders": query_one("SELECT COUNT(*) AS n FROM orders")["n"],
        "order_items": query_one("SELECT COUNT(*) AS n FROM order_items")["n"],
        "outbox_pending": len(outbox.pending_ids()),
        "cart_lines": len(cart.get(user_id)["items"]),
        "order_logs": db.user_activity_logs.count_documents(
            {"userId": user_id, "action_type": "order_placed"}),
        "order_notifications": db.user_notifications.count_documents(
            {"userId": user_id, "kind": "order"}),
    }


@admin_required
def run_lab():
    """Runs the real checkout with a chosen failure and reports before/after state."""
    data = v.body()
    scenario = SCENARIOS.get(data.get("scenario"))
    if scenario is None:
        raise ApiError("Choose a scenario.", 422)
    first = product.get(v.integer(data, "product_a", "the first shirt", 1))
    second = product.get(v.integer(data, "product_b", "the second shirt", 1))
    if not first or not second or first["product_id"] == second["product_id"]:
        raise ApiError("Choose two different shirts.", 422)
    if first["stock_quantity"] < 1 or second["stock_quantity"] < 1:
        raise ApiError("Both shirts need stock for this test. Restock them first.", 409)

    uid = current_user()["user_id"]
    sync.process_pending()  # start from a clean state so the run shows only its own effect
    cart.clear(uid)
    cart.add_item(uid, first["product_id"], 1, float(first["price"]), first["title"])
    quantity = second["stock_quantity"] + 1 if scenario.get("short") else 1
    cart.add_item(uid, second["product_id"], quantity, float(second["price"]), second["title"])

    ids = [first["product_id"], second["product_id"]]
    before = _snapshot(uid, ids)
    trace, error, result = service.Trace(), None, None
    try:
        result = service.place_order(uid, "Transaction Lab, Kasetsart University, Bangkok",
                                     scenario["fail_at"], trace)
    except ApiError as err:
        error = err.message
    after = _snapshot(uid, ids)
    activity.log(uid, "lab_run", {"scenario": data["scenario"], "error": error})
    return jsonify({"scenario": data["scenario"], "trace": trace.steps, "before": before,
                    "after": after, "error": error, "result": result,
                    "titles": {str(first["product_id"]): first["title"],
                               str(second["product_id"]): second["title"]}})


