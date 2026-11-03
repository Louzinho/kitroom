"""Connections to both database engines.

MySQL: one connection per request, autocommit ON. Multi-statement work must go
through `transaction()`, which is the single place that issues BEGIN/COMMIT/ROLLBACK.
MongoDB: one shared client (it owns its own pool).
"""
from contextlib import contextmanager

import pymysql
from flask import current_app, g, has_app_context
from pymongo import MongoClient

from .config import Config

_mongo_clients = {}


def connect_mysql(cfg=Config, database=True):
    return pymysql.connect(
        host=cfg.MYSQL_HOST, port=cfg.MYSQL_PORT, user=cfg.MYSQL_USER,
        password=cfg.MYSQL_PASSWORD,
        database=cfg.MYSQL_DATABASE if database else None,
        cursorclass=pymysql.cursors.DictCursor, autocommit=True, charset="utf8mb4",
    )


def sql():
    if "mysql" not in g:
        g.mysql = connect_mysql(current_app.config["APP_CONFIG"])
    return g.mysql


def close_sql(_exc=None):
    conn = g.pop("mysql", None)
    if conn is not None:
        conn.close()


def query(statement, params=()):
    with sql().cursor() as cur:
        cur.execute(statement, params)
        return cur.fetchall()


def query_one(statement, params=()):
    rows = query(statement, params)
    return rows[0] if rows else None


def execute(statement, params=()):
    with sql().cursor() as cur:
        cur.execute(statement, params)
        return cur.lastrowid


@contextmanager
def transaction():
    """BEGIN ... COMMIT, with an explicit ROLLBACK on any exception."""
    conn = sql()
    conn.begin()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def mongo_client(cfg=None):
    cfg = cfg or (current_app.config["APP_CONFIG"] if has_app_context() else Config)
    if cfg.MONGO_URI not in _mongo_clients:
        _mongo_clients[cfg.MONGO_URI] = MongoClient(cfg.MONGO_URI, serverSelectionTimeoutMS=3000, tz_aware=True)
    return _mongo_clients[cfg.MONGO_URI]


def mongo(cfg=None):
    cfg = cfg or (current_app.config["APP_CONFIG"] if has_app_context() else Config)
    return mongo_client(cfg)[cfg.MONGO_DATABASE]


def mongo_supports_transactions():
    return bool(mongo_client().admin.command("hello").get("setName"))
