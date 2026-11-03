from flask import jsonify, request

from .. import uploads, validate as v
from ..auth import admin_required, current_user
from ..db import execute, mongo
from ..errors import ApiError
from ..models import activity, category, product, review


def _admin_id():
    return current_user()["user_id"]


def list_categories():
    return jsonify(category.list_all())


@admin_required
def create_category():
    data = v.body()
    cid = category.create(v.text(data, "name", "a category name", 80),
                          v.text(data, "description", "a description", required=False) or None)
    return jsonify(category.get(cid)), 201


@admin_required
def update_category(category_id):
    data = v.body()
    if category.get(category_id) is None:
        raise ApiError("That category does not exist.", 404)
    category.update(category_id, v.text(data, "name", "a category name", 80),
                    v.text(data, "description", "a description", required=False) or None)
    return jsonify(category.get(category_id))


@admin_required
def delete_category(category_id):
    category.delete(category_id)
    return "", 204


def list_products():
    user = current_user()
    status = request.args.get("status", "active")
    if status != "active" and not (user and user["role"] == "admin"):
        status = "active"
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 12, type=int), 1), 100)
    rows, total = product.search(request.args.get("q", "").strip() or None,
                                 request.args.get("category", type=int), status,
                                 request.args.get("sort", "newest"), page, per_page)
    ratings = review.stats([p["product_id"] for p in rows])
    for p in rows:
        p["rating"] = ratings.get(p["product_id"])
    return jsonify({"items": rows, "total": total, "page": page, "per_page": per_page})


def get_product(product_id):
    row = product.get(product_id)
    if row is None:
        raise ApiError("That shirt is not in the catalogue.", 404)
    row["rating"] = review.stats([product_id]).get(product_id)
    if current_user():
        activity.log(current_user()["user_id"], "product_viewed",
                     {"productId": product_id, "title": row["title"]})
    return jsonify(row)


def _form():
    data = v.body()
    fields = {"category_id": v.integer(data, "category_id", "the category", 1),
              "title": v.text(data, "title", "a title", 160),
              "club": v.text(data, "club", "the club", 100),
              "season": v.text(data, "season", "the season", 9),
              "description": v.text(data, "description", "a description", 2000, required=False),
              "price": v.money(data, "price", "the price"),
              "stock_quantity": v.integer(data, "stock_quantity", "the stock", 0, 100000)}
    if "status" in data:
        if data["status"] not in ("active", "archived"):
            raise ApiError("Choose a valid status.", 422)
        fields["status"] = data["status"]
    file = request.files.get("image")
    if file and file.filename:
        fields["image_path"] = uploads.save_image(file, "products")
    return fields


@admin_required
def create_product():
    pid = product.create(_form())
    activity.log(_admin_id(), "product_created", {"productId": pid})
    return jsonify(product.get(pid)), 201


@admin_required
def update_product(product_id):
    current = product.get(product_id)
    if current is None:
        raise ApiError("That shirt is not in the catalogue.", 404)
    fields = _form()
    product.update(product_id, fields)
    if "image_path" in fields:
        uploads.remove_image(current["image_path"])
    activity.log(_admin_id(), "product_updated", {"productId": product_id})
    return jsonify(product.get(product_id))


@admin_required
def adjust_stock(product_id):
    """Relative change, so it cannot overwrite a sale that happened meanwhile."""
    delta = v.integer(v.body(), "delta", "the stock change", -100000, 100000)
    current = product.get(product_id)
    if current is None:
        raise ApiError("That shirt is not in the catalogue.", 404)
    execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id=%s",
            (delta, product_id))
    activity.log(_admin_id(), "stock_adjusted", {"productId": product_id, "delta": delta})
    return jsonify(product.get(product_id))


@admin_required
def delete_product(product_id):
    current = product.get(product_id)
    if current is None:
        raise ApiError("That shirt is not in the catalogue.", 404)
    if product.has_orders(product_id):
        raise ApiError("This shirt appears in past orders. Archive it instead.", 409,
                       code="has_orders")
    product.delete(product_id)
    review.delete_for_product(product_id)
    mongo().shopping_carts.update_many({"items.productId": product_id},
                                       {"$pull": {"items": {"productId": product_id}},
                                        "$inc": {"version": 1}})
    uploads.remove_image(current["image_path"])
    activity.log(_admin_id(), "product_deleted", {"productId": product_id, "title": current["title"]})
    return "", 204
