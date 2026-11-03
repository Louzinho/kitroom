"""Integration tests: they run against real MySQL and MongoDB (databases *_test)."""
import pytest

import manage
from app import create_app
from app.config import Config
from app.db import connect_mysql, mongo


class TestConfig(Config):
    TESTING = True
    MYSQL_DATABASE = "kitroom_test"
    MONGO_DATABASE = "kitroom_test"


PASSWORD = "password123"


@pytest.fixture(scope="session")
def app():
    manage.reset(TestConfig)
    manage.migrate(TestConfig)
    return create_app(TestConfig)


@pytest.fixture(autouse=True)
def clean(app):
    conn = connect_mysql(TestConfig)
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for t in ("sync_outbox", "order_items", "orders", "products", "categories", "users"):
            cur.execute(f"TRUNCATE TABLE {t}")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.close()
    db = mongo(TestConfig)
    for c in ("shopping_carts", "product_reviews", "user_notifications", "user_activity_logs"):
        db[c].delete_many({})


class Client:
    def __init__(self, app):
        self.c = app.test_client()

    def call(self, method, path, json=None, data=None, expect=None):
        r = self.c.open(f"/api{path}", method=method, json=json, data=data,
                        headers={"X-Requested-With": "KitRoom"})
        if expect:
            assert r.status_code == expect, r.get_data(as_text=True)
        return r

    def get(self, path, **k): return self.call("GET", path, **k)
    def post(self, path, **k): return self.call("POST", path, **k)
    def patch(self, path, **k): return self.call("PATCH", path, **k)
    def put(self, path, **k): return self.call("PUT", path, **k)
    def delete(self, path, **k): return self.call("DELETE", path, **k)


@pytest.fixture
def client_for(app):
    def make(email, role="customer"):
        c = Client(app)
        c.post("/auth/register", json={"email": email, "password": PASSWORD, "full_name": email[:4]},
               expect=201)
        if role == "admin":
            conn = connect_mysql(TestConfig)
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET role='admin' WHERE email=%s", (email,))
            conn.close()
        return c
    return make


@pytest.fixture
def admin(client_for):
    return client_for("admin@test.io", "admin")


@pytest.fixture
def customer(client_for):
    return client_for("cust@test.io")


@pytest.fixture
def shop(admin):
    cat = admin.post("/categories", json={"name": "Test"}, expect=201).get_json()["category_id"]

    def product(title="Shirt", price=100, stock=5):
        return admin.post("/products", json={
            "category_id": cat, "title": title, "club": "FC", "season": "1990",
            "price": price, "stock_quantity": stock}, expect=201).get_json()["product_id"]
    return product


def counts():
    conn = connect_mysql(TestConfig)
    with conn.cursor() as cur:
        cur.execute("SELECT (SELECT COUNT(*) FROM orders) o, (SELECT COUNT(*) FROM order_items) i, "
                    "(SELECT COUNT(*) FROM sync_outbox) e")
        row = cur.fetchone()
    conn.close()
    return row


def stock(pid):
    conn = connect_mysql(TestConfig)
    with conn.cursor() as cur:
        cur.execute("SELECT stock_quantity s FROM products WHERE product_id=%s", (pid,))
        value = cur.fetchone()["s"]
    conn.close()
    return value
