from flask import jsonify

from .. import validate as v
from ..auth import admin_required, current_user, login_required
from ..errors import ApiError
from ..models import activity, cart, order, product
from ..services import orders as service


def _uid():
    return current_user()["user_id"]


def _cart_payload(user_id):
    doc = cart.get(user_id)
    live = {p["product_id"]: p for p in product.get_many([i["productId"] for i in doc["items"]])}
    lines = []
    for item in doc["items"]:
        p = live.get(item["productId"], {})
        lines.append({"product_id": item["productId"], "quantity": item["quantity"],
                      "price": p.get("price", item["price"]), "title": item.get("title"),
                      "club": p.get("club"), "season": p.get("season"),
                      "image_path": p.get("image_path"), "stock": p.get("stock_quantity", 0),
                      "price_changed": p.get("price") is not None
                      and float(p["price"]) != float(item["price"])})
    return {"items": lines, "version": doc["version"], "updatedAt": doc.get("updatedAt"),
            "total": sum(float(l["price"]) * l["quantity"] for l in lines)}


@login_required
def get_cart():
    return jsonify(_cart_payload(_uid()))


def _check_stock(p, quantity):
    if p is None or p["status"] != "active":
        raise ApiError("That shirt is no longer on sale.", 404)
    if quantity > p["stock_quantity"]:
        raise ApiError(f"Only {p['stock_quantity']} left of {p['title']}.", 409,
                       code="insufficient_stock")


@login_required
def add_to_cart():
    data, uid = v.body(), _uid()
    pid = v.integer(data, "product_id", "the product", 1)
    quantity = v.integer(data, "quantity", "the quantity", 1, 99)
    p = product.get(pid)
    held = next((i["quantity"] for i in cart.get(uid)["items"] if i["productId"] == pid), 0)
    _check_stock(p, held + quantity)
    cart.add_item(uid, pid, quantity, float(p["price"]), p["title"])
    activity.log(uid, "cart_item_added", {"productId": pid, "quantity": quantity})
    return jsonify(_cart_payload(uid)), 201


@login_required
def update_cart_item(product_id):
    uid = _uid()
    quantity = v.integer(v.body(), "quantity", "the quantity", 1, 99)
    _check_stock(product.get(product_id), quantity)
    if not cart.set_quantity(uid, product_id, quantity):
        raise ApiError("That shirt is not in your cart.", 404)
    activity.log(uid, "cart_item_updated", {"productId": product_id, "quantity": quantity})
    return jsonify(_cart_payload(uid))


@login_required
def remove_cart_item(product_id):
    uid = _uid()
    cart.remove_item(uid, product_id)
    activity.log(uid, "cart_item_removed", {"productId": product_id})
    return jsonify(_cart_payload(uid))


@login_required
def clear_cart():
    cart.clear(_uid())
    activity.log(_uid(), "cart_cleared")
    return "", 204


@login_required
def checkout():
    uid = _uid()
    address = v.text(v.body(), "shipping_address", "a delivery address", 255)
    try:
        result = service.place_order(uid, address)
    except ApiError as err:
        activity.log(uid, "checkout_failed", {"reason": err.message})
        raise
    return jsonify(result), 201


def _visible(order_id):
    row = order.get(order_id)
    user = current_user()
    if row is None or (user["role"] != "admin" and row["user_id"] != user["user_id"]):
        raise ApiError("That order does not exist.", 404)
    return row


@login_required
def list_orders():
    return jsonify(order.history(_uid()))


@admin_required
def list_all_orders():
    return jsonify(order.history())


@login_required
def get_order(order_id):
    return jsonify({**_visible(order_id), "items": order.items(order_id)})


@login_required
def update_order_address(order_id):
    row = _visible(order_id)
    if row["order_status"] != "pending":
        raise ApiError("This order has left the warehouse, so the address is fixed.", 409)
    order.update_address(order_id, v.text(v.body(), "shipping_address", "a delivery address", 255))
    return jsonify(order.get(order_id))


@admin_required
def update_order_status(order_id):
    status = v.body().get("status")
    if status not in ("shipped", "delivered", "cancelled"):
        raise ApiError("Choose a valid status.", 422)
    service.change_status(order_id, status)
    return jsonify(order.get(order_id))


@login_required
def cancel_order(order_id):
    _visible(order_id)
    service.cancel_order(order_id)
    return jsonify(order.get(order_id))


@admin_required
def delete_order(order_id):
    row = order.get(order_id)
    if row is None:
        raise ApiError("That order does not exist.", 404)
    if row["order_status"] != "cancelled":
        raise ApiError("Only cancelled orders can be deleted.", 409)
    order.delete(order_id)  # order_items and sync_outbox go with it (ON DELETE CASCADE)
    activity.log(_uid(), "order_deleted", {"orderId": order_id})
    return "", 204


@admin_required
def add_order_item(order_id):
    data = v.body()
    service.add_line(order_id, v.integer(data, "product_id", "the product", 1),
                     v.integer(data, "quantity", "the quantity", 1, 99))
    return get_order(order_id), 201


@admin_required
def update_order_item(order_id, item_id):
    service.set_line_quantity(order_id, item_id, v.integer(v.body(), "quantity", "the quantity", 1, 99))
    return get_order(order_id)


@login_required
def delete_order_item(order_id, item_id):
    _visible(order_id)
    service.delete_line(order_id, item_id)
    return get_order(order_id)


