from flask import jsonify, request

from .. import uploads, validate as v
from ..auth import admin_required, current_user, login_required
from ..db import query_one
from ..errors import ApiError
from ..models import activity, notification, product, review
from ..models import user as users


def _uid():
    return current_user()["user_id"]


def _review_fields(data):
    fields = {"rating": v.integer(data, "rating", "the rating", 1, 5),
              "comment": v.text(data, "comment", "a comment", 2000)}
    # Optional attribute: only stored when given, which a document model allows.
    if data.get("sizeFeedback") in ("small", "true", "large"):
        fields["sizeFeedback"] = data["sizeFeedback"]
    return fields


def list_reviews(product_id):
    return jsonify({"items": review.for_product(product_id),
                    "stats": review.stats([product_id]).get(product_id)})


@login_required
def my_reviews():
    return jsonify(review.by_user(_uid()))


@login_required
def create_review(product_id):
    p = product.get(product_id)
    if p is None:
        raise ApiError("That shirt is not in the catalogue.", 404)
    uid = _uid()
    doc = {**_review_fields(v.body()), "productId": product_id, "userId": uid,
           "userName": current_user()["full_name"], "productTitle": p["title"],
           "verifiedPurchase": query_one(
               """SELECT 1 AS x FROM order_items i JOIN orders o ON o.order_id = i.order_id
                  WHERE o.user_id=%s AND i.product_id=%s AND o.order_status <> 'cancelled' LIMIT 1""",
               (uid, product_id)) is not None}
    photo = request.files.get("photo")
    if photo and photo.filename:
        doc["photo"] = uploads.save_image(photo, "reviews")
    rid = review.create(doc)
    activity.log(uid, "review_posted", {"productId": product_id, "rating": doc["rating"]})
    return jsonify(review.get(rid)), 201


def _own_review(review_id, allow_admin=False):
    row = review.get(review_id)
    if row is None:
        raise ApiError("That review no longer exists.", 404)
    user = current_user()
    if row["userId"] != user["user_id"] and not (allow_admin and user["role"] == "admin"):
        raise ApiError("You can only change your own reviews.", 403)
    return row


@login_required
def update_review(review_id):
    _own_review(review_id)
    review.update(review_id, _review_fields(v.body()))
    return jsonify(review.get(review_id))


@login_required
def like_review(review_id):
    review.toggle_like(review_id, _uid())
    return jsonify(review.get(review_id))


@login_required
def delete_review(review_id):
    row = _own_review(review_id, allow_admin=True)
    review.delete(review_id)
    uploads.remove_image(row.get("photo"))
    activity.log(_uid(), "review_deleted", {"productId": row["productId"]})
    return "", 204


@login_required
def list_notifications():
    return jsonify(notification.for_user(_uid()))


def _own_note(note_id):
    row = notification.get(note_id)
    if row is None or row["userId"] != _uid():
        raise ApiError("That notification no longer exists.", 404)


@login_required
def read_notification(note_id):
    _own_note(note_id)
    notification.update(note_id, {"isRead": bool(v.body().get("isRead", True))})
    return jsonify(notification.get(note_id))


@login_required
def read_all_notifications():
    notification.mark_all_read(_uid())
    return "", 204


@login_required
def delete_notification(note_id):
    _own_note(note_id)
    notification.delete(note_id)
    return "", 204


@admin_required
def admin_list_notifications():
    return jsonify(notification.list_all())


@admin_required
def admin_send_notification():
    data = v.body()
    title = v.text(data, "title", "a title", 120)
    message = v.text(data, "message", "a message", 1000)
    if data.get("user_id"):
        targets = [v.integer(data, "user_id", "the user", 1)]
        if users.get(targets[0]) is None:
            raise ApiError("That user does not exist.", 404)
    else:
        targets = [u["user_id"] for u in users.list_all()]
    for uid in targets:
        notification.create(uid, title, message, "broadcast" if len(targets) > 1 else "info")
    activity.log(_uid(), "notification_sent", {"recipients": len(targets), "title": title})
    return jsonify({"sent": len(targets)}), 201


@admin_required
def admin_update_notification(note_id):
    data = v.body()
    if not notification.update(note_id, {"title": v.text(data, "title", "a title", 120),
                                         "message": v.text(data, "message", "a message", 1000)}):
        raise ApiError("That notification no longer exists.", 404)
    return jsonify(notification.get(note_id))


@admin_required
def admin_delete_notification(note_id):
    if not notification.delete(note_id):
        raise ApiError("That notification no longer exists.", 404)
    return "", 204


@admin_required
def list_logs():
    return jsonify({"items": activity.search(request.args.get("user", type=int),
                                             request.args.get("action") or None),
                    "actions": activity.action_types()})


@admin_required
def create_log():
    data = v.body()
    activity.log(_uid(), v.text(data, "action_type", "an action name", 60),
                 {"note": v.text(data, "note", "a note", 500, required=False)}, source="manual")
    return "", 201


@admin_required
def update_log(log_id):
    if not activity.annotate(log_id, v.text(v.body(), "adminNote", "a note", 500, required=False)):
        raise ApiError("That log entry no longer exists.", 404)
    return "", 204


@admin_required
def delete_log(log_id):
    if not activity.delete(log_id):
        raise ApiError("That log entry no longer exists.", 404)
    return "", 204
