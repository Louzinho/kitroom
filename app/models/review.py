from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from ..db import mongo
from ..errors import ApiError


def _reviews():
    return mongo().product_reviews


def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise ApiError("That id is not valid.", 404)


def for_product(product_id):
    return list(_reviews().find({"productId": product_id}).sort("createdAt", -1))


def by_user(user_id):
    return list(_reviews().find({"userId": user_id}).sort("createdAt", -1))


def stats(product_ids):
    """Average rating per product, computed with an aggregation pipeline."""
    pipeline = [{"$match": {"productId": {"$in": list(product_ids)}}},
                {"$group": {"_id": "$productId", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
    return {r["_id"]: {"avg": round(r["avg"], 1), "count": r["count"]}
            for r in _reviews().aggregate(pipeline)}


def get(review_id):
    return _reviews().find_one({"_id": oid(review_id)})


def create(doc):
    doc.update(likedBy=[], likes=0, createdAt=datetime.now(timezone.utc))
    return _reviews().insert_one(doc).inserted_id


def update(review_id, fields):
    fields["editedAt"] = datetime.now(timezone.utc)
    _reviews().update_one({"_id": oid(review_id)}, {"$set": fields})


def toggle_like(review_id, user_id):
    review = get(review_id)
    if not review:
        raise ApiError("That review no longer exists.", 404)
    op = "$pull" if user_id in review.get("likedBy", []) else "$addToSet"
    _reviews().update_one({"_id": review["_id"]}, {op: {"likedBy": user_id}})
    # Keep the counter derived from the array so the two cannot drift.
    _reviews().update_one({"_id": review["_id"]}, [{"$set": {"likes": {"$size": "$likedBy"}}}])


def delete(review_id):
    return _reviews().delete_one({"_id": oid(review_id)}).deleted_count


def delete_for_product(product_id):
    _reviews().delete_many({"productId": product_id})


def delete_for_user(user_id):
    _reviews().delete_many({"userId": user_id})
