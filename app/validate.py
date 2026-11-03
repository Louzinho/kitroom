from decimal import Decimal, InvalidOperation

from flask import request

from .errors import ApiError


def body():
    if request.mimetype == "application/json":
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def text(data, field, label, maximum=255, required=True):
    value = str(data.get(field) or "").strip()
    if required and not value:
        raise ApiError(f"Enter {label}.", 422, field=field)
    if len(value) > maximum:
        raise ApiError(f"{label.capitalize()} must be {maximum} characters or fewer.", 422, field=field)
    return value


def integer(data, field, label, minimum=None, maximum=None):
    try:
        value = int(data.get(field))
    except (TypeError, ValueError):
        raise ApiError(f"Enter a whole number for {label}.", 422, field=field)
    if minimum is not None and value < minimum:
        raise ApiError(f"{label.capitalize()} must be at least {minimum}.", 422, field=field)
    if maximum is not None and value > maximum:
        raise ApiError(f"{label.capitalize()} must be at most {maximum}.", 422, field=field)
    return value


def money(data, field, label):
    try:
        value = Decimal(str(data.get(field)))
    except InvalidOperation:
        raise ApiError(f"Enter a price for {label}.", 422, field=field)
    if not value.is_finite() or value <= 0 or value >= Decimal("100000000"):
        raise ApiError(f"{label.capitalize()} must be a positive price.", 422, field=field)
    return value.quantize(Decimal("0.01"))


def email(data):
    value = text(data, "email", "an email address", 190).lower()
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ApiError("Enter a valid email address.", 422, field="email")
    return value


def password(data, field="password"):
    value = str(data.get(field) or "")
    if len(value) < 8:
        raise ApiError("Use a password of at least 8 characters.", 422, field=field)
    return value
