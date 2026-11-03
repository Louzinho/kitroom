from flask import jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .. import uploads, validate as v
from ..auth import admin_required, current_user, login_required
from ..db import mongo
from ..errors import ApiError
from ..models import activity, cart, notification, order, review
from ..models import user as users


def _start_session(user_id):
    session.clear()
    session["user_id"] = user_id


def register():
    data = v.body()
    email, name = v.email(data), v.text(data, "full_name", "your name", 120)
    uid = users.create(email, generate_password_hash(v.password(data)), name)
    _start_session(uid)
    notification.create(uid, "Welcome to The Kit Room", "Your account is ready. Happy hunting.")
    activity.log(uid, "user_registered", {"email": email})
    return jsonify(users.get(uid)), 201


def login():
    data = v.body()
    row = users.get_auth(str(data.get("email") or "").strip().lower())
    if not row or not check_password_hash(row["password_hash"], str(data.get("password") or "")):
        activity.log(None, "login_failed", {"email": str(data.get("email") or "")[:190]})
        raise ApiError("That email and password do not match.", 401)
    _start_session(row["user_id"])
    activity.log(row["user_id"], "user_login")
    return jsonify(users.get(row["user_id"]))


@login_required
def logout():
    activity.log(current_user()["user_id"], "user_logout")
    session.clear()
    return "", 204


def me():
    user = current_user()
    if user is None:
        return jsonify(None)
    return jsonify({**user, "unread": notification.unread_count(user["user_id"]),
                    "cart_count": sum(i["quantity"] for i in cart.get(user["user_id"])["items"])})


def _apply_profile(user_id, data):
    fields = {}
    if "full_name" in data:
        fields["full_name"] = v.text(data, "full_name", "your name", 120)
    if "email" in data:
        fields["email"] = v.email(data)
    users.update(user_id, **fields)
    if "full_name" in fields:  # reviews carry a copy of the name (extended reference)
        mongo().product_reviews.update_many({"userId": user_id},
                                            {"$set": {"userName": fields["full_name"]}})


@login_required
def update_me():
    uid = current_user()["user_id"]
    _apply_profile(uid, v.body())
    activity.log(uid, "profile_updated")
    return jsonify(users.get(uid))


@login_required
def change_password():
    data, uid = v.body(), current_user()["user_id"]
    if not check_password_hash(users.get_hash(uid), str(data.get("current_password") or "")):
        raise ApiError("Your current password is not correct.", 403, field="current_password")
    users.update(uid, password_hash=generate_password_hash(v.password(data, "new_password")))
    activity.log(uid, "password_changed")
    return "", 204


@login_required
def upload_avatar():
    file = request.files.get("avatar")
    if not file:
        raise ApiError("Choose an image first.", 400)
    user = current_user()
    path = uploads.save_image(file, "avatars")
    users.update(user["user_id"], avatar_path=path)
    uploads.remove_image(user["avatar_path"])
    return jsonify({"avatar_path": path})


def _delete_account(user):
    uid = user["user_id"]
    if order.history(uid):
        raise ApiError("This account has orders, so it has to stay on record.", 409)
    users.delete(uid)
    cart.clear(uid)
    review.delete_for_user(uid)
    notification.delete_for_user(uid)
    uploads.remove_image(user["avatar_path"])


@login_required
def delete_me():
    _delete_account(current_user())
    session.clear()
    return "", 204


@admin_required
def list_users():
    return jsonify(users.list_all())


@admin_required
def create_user():
    data = v.body()
    role = data.get("role", "customer")
    if role not in ("customer", "admin"):
        raise ApiError("Choose a valid role.", 422)
    uid = users.create(v.email(data), generate_password_hash(v.password(data)),
                       v.text(data, "full_name", "a name", 120), role)
    activity.log(current_user()["user_id"], "admin_created_user", {"targetUserId": uid})
    return jsonify(users.get(uid)), 201


@admin_required
def update_user(user_id):
    data = v.body()
    if users.get(user_id) is None:
        raise ApiError("That user does not exist.", 404)
    _apply_profile(user_id, data)
    if "role" in data:
        if data["role"] not in ("customer", "admin"):
            raise ApiError("Choose a valid role.", 422)
        if user_id == current_user()["user_id"] and data["role"] != "admin":
            raise ApiError("You cannot remove your own staff access.", 409)
        users.update(user_id, role=data["role"])
    activity.log(current_user()["user_id"], "admin_updated_user", {"targetUserId": user_id})
    return jsonify(users.get(user_id))


@admin_required
def delete_user(user_id):
    user = users.get(user_id)
    if user is None:
        raise ApiError("That user does not exist.", 404)
    if user_id == current_user()["user_id"]:
        raise ApiError("You cannot delete the account you are signed in with.", 409)
    _delete_account(user)
    activity.log(current_user()["user_id"], "admin_deleted_user", {"targetUserId": user_id})
    return "", 204
