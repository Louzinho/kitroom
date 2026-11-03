from functools import wraps

from flask import g, session

from .errors import ApiError
from .models import user as users


def current_user():
    if "user" not in g:
        uid = session.get("user_id")
        g.user = users.get(uid) if uid else None
        if uid and g.user is None:
            session.clear()
    return g.user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            raise ApiError("Sign in to continue.", 401)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            raise ApiError("Sign in to continue.", 401)
        if user["role"] != "admin":
            raise ApiError("This page is for staff accounts.", 403)
        return fn(*args, **kwargs)
    return wrapper
