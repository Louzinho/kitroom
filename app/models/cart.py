"""shopping_carts: one document per user, items embedded (they are always read together)."""
from datetime import datetime, timezone

from ..db import mongo


def _carts():
    return mongo().shopping_carts


def _now():
    return datetime.now(timezone.utc)


def get(user_id):
    return _carts().find_one({"userId": user_id}) or {"userId": user_id, "items": [], "version": 0}


def add_item(user_id, product_id, quantity, price, title):
    # Positional update if the line already exists, $push otherwise.
    done = _carts().update_one(
        {"userId": user_id, "items.productId": product_id},
        {"$inc": {"items.$.quantity": quantity, "version": 1},
         "$set": {"items.$.price": price, "updatedAt": _now()}})
    if not done.matched_count:
        _carts().update_one(
            {"userId": user_id},
            {"$push": {"items": {"productId": product_id, "quantity": quantity,
                                 "price": price, "title": title, "addedAt": _now()}},
             "$inc": {"version": 1}, "$set": {"updatedAt": _now()}},
            upsert=True)


def set_quantity(user_id, product_id, quantity):
    return _carts().update_one(
        {"userId": user_id, "items.productId": product_id},
        {"$set": {"items.$.quantity": quantity, "updatedAt": _now()}, "$inc": {"version": 1}}
    ).matched_count


def remove_item(user_id, product_id):
    return _carts().update_one(
        {"userId": user_id},
        {"$pull": {"items": {"productId": product_id}},
         "$set": {"updatedAt": _now()}, "$inc": {"version": 1}}).modified_count


def clear(user_id):
    _carts().delete_one({"userId": user_id})
