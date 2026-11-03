"""Local file storage. Files are checked with Pillow and renamed, never trusted by name."""
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError

from .errors import ApiError

FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def save_image(file_storage, folder):
    try:
        image = Image.open(file_storage.stream)
        fmt = image.format
        image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ApiError("That file is not a readable image. Use a JPG, PNG or WEBP.", 400)
    if fmt not in FORMATS:
        raise ApiError("Use a JPG, PNG or WEBP image.", 400)
    name = f"{uuid.uuid4().hex}.{FORMATS[fmt]}"
    target = current_app.config["APP_CONFIG"].UPLOAD_ROOT / folder
    target.mkdir(parents=True, exist_ok=True)
    file_storage.stream.seek(0)
    file_storage.save(target / name)
    return f"{folder}/{name}"


def remove_image(path):
    if path:
        (current_app.config["APP_CONFIG"].UPLOAD_ROOT / path).unlink(missing_ok=True)
