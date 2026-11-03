import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit
    UPLOAD_ROOT = BASE_DIR / "app" / "static" / "uploads"

    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "kitroom")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "kitroom_dev")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "kitroom")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/?replicaSet=rs0")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE", "kitroom")
