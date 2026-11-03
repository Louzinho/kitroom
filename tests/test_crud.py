import io

from PIL import Image

from app.db import mongo
from .conftest import PASSWORD, Client, TestConfig


def png():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "PNG")
    buf.seek(0)
    return buf


def test_auth_and_profile(app, customer):
    assert customer.get("/me").get_json()["email"] == "cust@test.io"
    customer.patch("/me", json={"full_name": "New Name"}, expect=200)
    assert customer.put("/me/password", json={"current_password": "x", "new_password": "newpassword"}).status_code == 403
    customer.put("/me/password", json={"current_password": PASSWORD, "new_password": "newpassword"}, expect=204)
    customer.post("/auth/logout", expect=204)
    assert customer.post("/auth/login", json={"email": "cust@test.io", "password": PASSWORD}).status_code == 401
    customer.post("/auth/login", json={"email": "cust@test.io", "password": "newpassword"}, expect=200)


def test_duplicate_email_and_validation(app, customer):
    c = Client(app)
    payload = {"email": "cust@test.io", "password": PASSWORD, "full_name": "x"}
    assert c.post("/auth/register", json=payload).status_code == 409
    assert c.post("/auth/register", json={**payload, "email": "no"}).status_code == 422
    assert c.post("/auth/register", json={**payload, "email": "a@b.io", "password": "x"}).status_code == 422


def test_permissions(app, customer, shop):
    anon = Client(app)
    assert anon.get("/cart").status_code == 401
    assert customer.post("/categories", json={"name": "x"}).status_code == 403
    assert customer.get("/admin/logs").status_code == 403
    assert customer.get("/users").status_code == 403


def test_csrf_header_is_required(app):
    r = app.test_client().post("/api/auth/login", json={})
    assert r.status_code == 403


def test_orders_are_private(client_for, customer, shop):
    a = shop()
    customer.post("/cart/items", json={"product_id": a, "quantity": 1}, expect=201)
    oid = customer.post("/checkout", json={"shipping_address": "x"}, expect=201).get_json()["order_id"]
    other = client_for("other@test.io")
    assert other.get(f"/orders/{oid}").status_code == 404
    assert other.post(f"/orders/{oid}/cancel").status_code == 404


def test_category_crud(admin, shop):
    cid = admin.post("/categories", json={"name": "Temp"}, expect=201).get_json()["category_id"]
    admin.put(f"/categories/{cid}", json={"name": "Renamed"}, expect=200)
    admin.delete(f"/categories/{cid}", expect=204)
    shop()
    used = next(c for c in admin.get("/categories").get_json() if c["name"] == "Test")
    assert admin.delete(f"/categories/{used['category_id']}").status_code == 409


def test_product_crud_with_local_image(admin, shop):
    cat = admin.post("/categories", json={"name": "Up"}, expect=201).get_json()["category_id"]
    form = {"category_id": cat, "title": "T", "club": "C", "season": "1990", "price": "12.5",
            "stock_quantity": "3", "image": (png(), "a.png")}
    made = admin.post("/products", data=form, expect=201).get_json()
    assert made["image_path"].startswith("products/") and made["image_path"].endswith(".png")
    from app.config import Config
    path = Config.UPLOAD_ROOT / made["image_path"]
    assert path.exists()
    bad = {**form, "image": (io.BytesIO(b"not an image"), "x.png")}
    assert admin.post("/products", data=bad).status_code == 400
    admin.put(f"/products/{made['product_id']}", json={
        "category_id": cat, "title": "T2", "club": "C", "season": "1990", "price": 20,
        "stock_quantity": 4, "status": "archived"}, expect=200)
    listed = admin.get("/products?q=T2").get_json()
    assert listed["total"] == 0  # archived shirts leave the public catalogue
    assert admin.get("/products?q=T2&status=all").get_json()["total"] == 1
    admin.delete(f"/products/{made['product_id']}", expect=204)
    assert not path.exists()


def test_product_with_orders_cannot_be_deleted(admin, customer, shop):
    p = shop()
    customer.post("/cart/items", json={"product_id": p, "quantity": 1}, expect=201)
    customer.post("/checkout", json={"shipping_address": "x"}, expect=201)
    r = admin.delete(f"/products/{p}")
    assert r.status_code == 409 and r.get_json()["code"] == "has_orders"


def test_cart_crud(customer, shop):
    p, q = shop("P", stock=3), shop("Q", stock=3)
    customer.post("/cart/items", json={"product_id": p, "quantity": 2}, expect=201)
    customer.post("/cart/items", json={"product_id": p, "quantity": 1}, expect=201)
    assert customer.post("/cart/items", json={"product_id": p, "quantity": 1}).status_code == 409
    customer.post("/cart/items", json={"product_id": q, "quantity": 1}, expect=201)
    cart = customer.patch(f"/cart/items/{p}", json={"quantity": 1}, expect=200).get_json()
    assert {i["product_id"]: i["quantity"] for i in cart["items"]} == {p: 1, q: 1}
    assert len(customer.delete(f"/cart/items/{p}", expect=200).get_json()["items"]) == 1
    customer.delete("/cart", expect=204)
    assert customer.get("/cart").get_json()["items"] == []


def test_review_crud(client_for, customer, shop):
    p = shop()
    made = customer.post(f"/products/{p}/reviews", json={
        "rating": 4, "comment": "Nice", "sizeFeedback": "small"}, expect=201).get_json()
    assert made["sizeFeedback"] == "small" and made["verifiedPurchase"] is False
    assert customer.post(f"/products/{p}/reviews", json={"rating": 4, "comment": "x"}).status_code == 409
    other = client_for("o2@test.io")
    assert other.post(f"/products/{p}/reviews", json={"rating": 9, "comment": "x"}).status_code == 422
    other.post(f"/products/{p}/reviews", json={"rating": 2, "comment": "Meh"}, expect=201)
    stats = customer.get(f"/products/{p}/reviews").get_json()["stats"]
    assert stats == {"avg": 3.0, "count": 2}
    assert other.put(f"/reviews/{made['_id']}", json={"rating": 1, "comment": "x"}).status_code == 403
    other.post(f"/reviews/{made['_id']}/like", expect=200)
    assert other.post(f"/reviews/{made['_id']}/like", expect=200).get_json()["likes"] == 0
    assert other.post(f"/reviews/{made['_id']}/like", expect=200).get_json()["likes"] == 1
    assert customer.put(f"/reviews/{made['_id']}", json={"rating": 5, "comment": "Great"},
                        expect=200).get_json()["rating"] == 5
    assert other.delete(f"/reviews/{made['_id']}").status_code == 403
    customer.delete(f"/reviews/{made['_id']}", expect=204)
    assert customer.put("/reviews/not-an-id", json={"rating": 1, "comment": "x"}).status_code == 404


def test_notifications_crud(admin, customer):
    uid = customer.get("/me").get_json()["user_id"]
    admin.post("/admin/notifications", json={"user_id": uid, "title": "T", "message": "M"}, expect=201)
    notes = customer.get("/notifications").get_json()
    note = next(n for n in notes if n["title"] == "T")
    assert customer.get("/me").get_json()["unread"] == 2
    customer.patch(f"/notifications/{note['_id']}", json={"isRead": True}, expect=200)
    assert customer.get("/me").get_json()["unread"] == 1
    admin.put(f"/admin/notifications/{note['_id']}", json={"title": "T2", "message": "M2"}, expect=200)
    assert admin.delete(f"/notifications/{note['_id']}").status_code == 404  # not hers to dismiss
    customer.delete(f"/notifications/{note['_id']}", expect=204)
    assert admin.post("/admin/notifications", json={"title": "All", "message": "x"}, expect=201).get_json()["sent"] == 2


def test_activity_log_crud(admin):
    admin.post("/admin/logs", json={"action_type": "manual_note", "note": "hello"}, expect=201)
    data = admin.get("/admin/logs?action=manual_note").get_json()
    entry = data["items"][0]
    assert entry["source"] == "manual" and "manual_note" in data["actions"]
    admin.patch(f"/admin/logs/{entry['_id']}", json={"adminNote": "seen"}, expect=204)
    admin.delete(f"/admin/logs/{entry['_id']}", expect=204)


def test_user_admin_and_cross_db_cleanup(admin, customer, shop):
    uid = customer.get("/me").get_json()["user_id"]
    p = shop()
    customer.post(f"/products/{p}/reviews", json={"rating": 5, "comment": "x"}, expect=201)
    admin.patch(f"/users/{uid}", json={"full_name": "Renamed"}, expect=200)
    db = mongo(TestConfig)
    assert db.product_reviews.find_one({"userId": uid})["userName"] == "Renamed"
    admin.delete(f"/users/{uid}", expect=204)
    assert db.product_reviews.count_documents({"userId": uid}) == 0
    assert db.user_notifications.count_documents({"userId": uid}) == 0
    assert admin.delete(f"/users/{admin.get('/me').get_json()['user_id']}").status_code == 409


def test_user_with_orders_stays(admin, customer, shop):
    uid = customer.get("/me").get_json()["user_id"]
    p = shop()
    customer.post("/cart/items", json={"product_id": p, "quantity": 1}, expect=201)
    customer.post("/checkout", json={"shipping_address": "x"}, expect=201)
    assert admin.delete(f"/users/{uid}").status_code == 409


def test_outbox_rules(admin, shop):
    a, b = shop("A"), shop("B")
    r = admin.post("/admin/lab/run", json={"scenario": "mongo_sync", "product_a": a, "product_b": b}, expect=200).get_json()
    e = r["result"]["outbox_id"]
    assert admin.delete(f"/admin/outbox/{e}").status_code == 409
    admin.post("/admin/outbox/retry", expect=200)
    admin.delete(f"/admin/outbox/{e}", expect=204)


def test_health(app):
    data = app.test_client().get("/api/health").get_json()
    assert data == {"mysql": True, "mongodb": True, "replica_set": True}
