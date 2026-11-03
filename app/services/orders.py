"""Multi-table order workflows. Each one is a single atomic SQL transaction."""
from flask import has_request_context, request

from ..db import transaction
from ..errors import ApiError
from ..models import cart as cart_model
from ..models import outbox
from . import sync

TRANSITIONS = {"pending": {"shipped"}, "shipped": {"delivered"}}
FAILURE_POINTS = {"after_deduct", "after_order", "mid_items", "mongo_sync"}


class Trace:
    """Records what the transaction did, for the Transaction Lab screen."""

    def __init__(self):
        self.steps = []

    def add(self, name, ok=True, detail=""):
        self.steps.append({"step": name, "ok": ok, "detail": detail})


def _crash(point, fail_at, trace):
    if fail_at == point:
        trace.add("Simulated failure", False, f"Exception raised at '{point}'")
        raise ApiError(f"Simulated failure at '{point}'. The transaction was rolled back.",
                       500, code="simulated_failure")


def _client_ip():
    return request.remote_addr if has_request_context() else None


def place_order(user_id, address, fail_at=None, trace=None):
    """Steps 1-4 of the spec plus the outbox row, all-or-nothing; then the MongoDB sync."""
    trace = trace or Trace()
    sync.process_pending()  # a sync left over from an earlier order must not re-order its cart

    cart = cart_model.get(user_id)
    if not cart["items"]:
        raise ApiError("Your cart is empty.", 400)
    # Ascending product order: two concurrent checkouts lock rows in the same
    # order, which rules out the classic A-waits-B / B-waits-A deadlock.
    lines = sorted(cart["items"], key=lambda i: i["productId"])
    ids = [i["productId"] for i in lines]
    trace.add("Read cart from MongoDB", True, f"{len(lines)} line(s), version {cart['version']}")

    try:
        with transaction() as cur:
            trace.add("BEGIN", True, "SQL transaction opened")

            marks = ",".join(["%s"] * len(ids))
            cur.execute(f"""SELECT product_id, title, price, stock_quantity, status FROM products
                            WHERE product_id IN ({marks}) ORDER BY product_id FOR UPDATE""", ids)
            products = {p["product_id"]: p for p in cur.fetchall()}

            shortages = []
            for line in lines:
                p = products.get(line["productId"])
                if p is None or p["status"] != "active":
                    shortages.append({"product_id": line["productId"], "title": line.get("title"),
                                      "requested": line["quantity"], "available": 0})
                elif p["stock_quantity"] < line["quantity"]:
                    shortages.append({"product_id": p["product_id"], "title": p["title"],
                                      "requested": line["quantity"],
                                      "available": p["stock_quantity"]})
            if shortages:
                names = ", ".join(f"{s['title']} ({s['available']} left)" for s in shortages)
                trace.add("Verify stock (rows locked FOR UPDATE)", False, names)
                raise ApiError(f"Not enough stock: {names}.", 409, code="insufficient_stock",
                               shortages=shortages)
            trace.add("Verify stock (rows locked FOR UPDATE)", True, "All lines available")

            for line in lines:
                cur.execute("UPDATE products SET stock_quantity = stock_quantity - %s "
                            "WHERE product_id=%s", (line["quantity"], line["productId"]))
            trace.add("Deduct stock", True, f"{len(lines)} product(s) updated")
            _crash("after_deduct", fail_at, trace)

            # Prices always come from SQL; the cart's copy is only for display.
            total = sum(products[l["productId"]]["price"] * l["quantity"] for l in lines)
            cur.execute("INSERT INTO orders (user_id, total_amount, shipping_address) "
                        "VALUES (%s,%s,%s)", (user_id, total, address))
            order_id = cur.lastrowid
            trace.add("Insert order", True, f"orders row #{order_id}, total ฿{total}")
            _crash("after_order", fail_at, trace)

            for n, line in enumerate(lines):
                cur.execute("INSERT INTO order_items (order_id, product_id, unit_price, quantity) "
                            "VALUES (%s,%s,%s,%s)", (order_id, line["productId"],
                                                     products[line["productId"]]["price"],
                                                     line["quantity"]))
                if n == 0:
                    _crash("mid_items", fail_at, trace)
            trace.add("Insert order items", True, f"{len(lines)} order_items row(s)")

            outbox_id = outbox.add(cur, order_id, "order_placed", {
                "user_id": user_id, "total": str(total), "cart_version": cart["version"],
                "items": [{"productId": l["productId"], "quantity": l["quantity"]} for l in lines],
                "ip": _client_ip()})
            trace.add("Insert outbox event", True, f"sync_outbox row #{outbox_id}")
    except ApiError:
        trace.add("ROLLBACK", False, "Every change above was undone")
        raise
    except Exception as exc:
        trace.add("ROLLBACK", False, f"Unexpected error: {exc}")
        raise
    trace.add("COMMIT", True, f"Order #{order_id} is durable")

    synced = sync.process(outbox_id, fail=fail_at == "mongo_sync")
    trace.add("MongoDB sync (cart, log, notification)", synced,
              "Committed" if synced else "Aborted, nothing written. Event stays pending for replay")
    return {"order_id": order_id, "total": total, "synced": synced, "outbox_id": outbox_id}


def _lock_order(cur, order_id):
    cur.execute("SELECT * FROM orders WHERE order_id=%s FOR UPDATE", (order_id,))
    order = cur.fetchone()
    if order is None:
        raise ApiError("That order does not exist.", 404)
    return order


def _require_pending(order):
    if order["order_status"] != "pending":
        raise ApiError(f"This order is {order['order_status']}, so it can no longer be changed.", 409)


def _restock_and_cancel(cur, order):
    order_id = order["order_id"]
    cur.execute("SELECT product_id, quantity FROM order_items WHERE order_id=%s "
                "ORDER BY product_id", (order_id,))
    for line in cur.fetchall():
        cur.execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id=%s",
                    (line["quantity"], line["product_id"]))
    cur.execute("UPDATE orders SET order_status='cancelled' WHERE order_id=%s", (order_id,))
    return outbox.add(cur, order_id, "order_cancelled", {"user_id": order["user_id"], "ip": _client_ip()})


def cancel_order(order_id):
    with transaction() as cur:
        order = _lock_order(cur, order_id)
        _require_pending(order)
        outbox_id = _restock_and_cancel(cur, order)
    sync.process(outbox_id)


def change_status(order_id, new_status):
    if new_status == "cancelled":
        return cancel_order(order_id)
    with transaction() as cur:
        order = _lock_order(cur, order_id)
        if new_status not in TRANSITIONS.get(order["order_status"], set()):
            raise ApiError(f"An order cannot go from {order['order_status']} to {new_status}.", 409)
        cur.execute("UPDATE orders SET order_status=%s WHERE order_id=%s", (new_status, order_id))
        outbox_id = outbox.add(cur, order_id, "order_status_changed", {
            "user_id": order["user_id"], "status": new_status, "ip": _client_ip()})
    sync.process(outbox_id)


def _recalculate(cur, order_id):
    cur.execute("""UPDATE orders SET total_amount =
                   (SELECT COALESCE(SUM(unit_price * quantity), 0) FROM order_items WHERE order_id=%s)
                   WHERE order_id=%s""", (order_id, order_id))


def _take_stock(cur, product_id, quantity):
    """quantity > 0 removes stock, quantity < 0 returns it."""
    cur.execute("SELECT title, stock_quantity, status, price FROM products "
                "WHERE product_id=%s FOR UPDATE", (product_id,))
    product = cur.fetchone()
    if product is None:
        raise ApiError("That product does not exist.", 404)
    if quantity > product["stock_quantity"]:
        raise ApiError(f"Not enough stock: {product['title']} "
                       f"({product['stock_quantity']} left).", 409, code="insufficient_stock")
    cur.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id=%s",
                (quantity, product_id))
    return product


def add_line(order_id, product_id, quantity):
    with transaction() as cur:
        _require_pending(_lock_order(cur, order_id))
        product = _take_stock(cur, product_id, quantity)
        if product["status"] != "active":
            raise ApiError("That product is archived.", 409)
        cur.execute("""INSERT INTO order_items (order_id, product_id, unit_price, quantity)
                       VALUES (%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)""",
                    (order_id, product_id, product["price"], quantity))
        _recalculate(cur, order_id)


def _find_line(cur, order_id, item_id):
    cur.execute("SELECT * FROM order_items WHERE item_id=%s AND order_id=%s", (item_id, order_id))
    line = cur.fetchone()
    if line is None:
        raise ApiError("That order line does not exist.", 404)
    return line


def set_line_quantity(order_id, item_id, quantity):
    with transaction() as cur:
        _require_pending(_lock_order(cur, order_id))
        line = _find_line(cur, order_id, item_id)
        _take_stock(cur, line["product_id"], quantity - line["quantity"])
        cur.execute("UPDATE order_items SET quantity=%s WHERE item_id=%s", (quantity, item_id))
        _recalculate(cur, order_id)


def delete_line(order_id, item_id):
    """Removes one line and restocks it. Removing the last line cancels the order."""
    outbox_id = None
    with transaction() as cur:
        order = _lock_order(cur, order_id)
        _require_pending(order)
        line = _find_line(cur, order_id, item_id)
        cur.execute("SELECT COUNT(*) AS n FROM order_items WHERE order_id=%s", (order_id,))
        if cur.fetchone()["n"] == 1:
            outbox_id = _restock_and_cancel(cur, order)
        else:
            _take_stock(cur, line["product_id"], -line["quantity"])
            cur.execute("DELETE FROM order_items WHERE item_id=%s", (item_id,))
            _recalculate(cur, order_id)
    if outbox_id:
        sync.process(outbox_id)
