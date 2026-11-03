import threading

import pytest

from app.db import mongo
from app.services import orders as service
from .conftest import TestConfig, counts, stock

ADDRESS = {"shipping_address": "1 Test Road"}


def me_id(c):
    return c.get("/me").get_json()["user_id"]


def test_checkout_commits_everything(customer, shop):
    a, b = shop("A", 100, 5), shop("B", 250, 3)
    customer.post("/cart/items", json={"product_id": a, "quantity": 2}, expect=201)
    customer.post("/cart/items", json={"product_id": b, "quantity": 1}, expect=201)
    res = customer.post("/checkout", json=ADDRESS, expect=201).get_json()
    assert res["synced"] and float(res["total"]) == 450
    assert (stock(a), stock(b)) == (3, 2)
    assert counts() == {"o": 1, "i": 2, "e": 1}
    uid, db = me_id(customer), mongo(TestConfig)
    assert customer.get("/cart").get_json()["items"] == []
    assert db.user_activity_logs.count_documents({"userId": uid, "action_type": "order_placed"}) == 1
    assert db.user_notifications.count_documents({"userId": uid, "kind": "order"}) == 1
    detail = customer.get(f"/orders/{res['order_id']}").get_json()
    assert detail["item_count"] == 3 and len(detail["items"]) == 2


def test_insufficient_stock_rolls_back_all_lines(admin, customer, shop):
    a, b = shop("A", stock=5), shop("B", stock=2)
    customer.post("/cart/items", json={"product_id": a, "quantity": 1}, expect=201)
    customer.post("/cart/items", json={"product_id": b, "quantity": 2}, expect=201)
    admin.patch(f"/products/{b}/stock", json={"delta": -1}, expect=200)  # sold elsewhere
    r = customer.post("/checkout", json=ADDRESS, expect=409)
    assert r.get_json()["code"] == "insufficient_stock"
    assert (stock(a), stock(b)) == (5, 1)
    assert counts() == {"o": 0, "i": 0, "e": 0}
    assert len(customer.get("/cart").get_json()["items"]) == 2  # cart survives


@pytest.mark.parametrize("point", ["after_deduct", "after_order", "mid_items"])
def test_crash_mid_transaction_rolls_back(admin, shop, point):
    a, b = shop("A", stock=5), shop("B", stock=5)
    r = admin.post("/admin/lab/run", json={"scenario": point, "product_a": a, "product_b": b},
                   expect=200).get_json()
    assert r["error"] and "rolled back" in r["error"]
    assert r["before"] == r["after"]
    assert (stock(a), stock(b)) == (5, 5)
    assert counts() == {"o": 0, "i": 0, "e": 0}
    assert any(s["step"] == "ROLLBACK" for s in r["trace"])


def test_lab_insufficient_stock(admin, shop):
    a, b = shop("A", stock=5), shop("B", stock=1)
    r = admin.post("/admin/lab/run", json={"scenario": "insufficient_stock", "product_a": a,
                                           "product_b": b}, expect=200).get_json()
    assert "Not enough stock" in r["error"]
    assert r["before"] == r["after"] and (stock(a), stock(b)) == (5, 1)


def test_mongo_failure_keeps_order_and_replay_repairs(admin, shop):
    a, b = shop("A"), shop("B")
    r = admin.post("/admin/lab/run", json={"scenario": "mongo_sync", "product_a": a, "product_b": b},
                   expect=200).get_json()
    assert r["after"]["orders"] == r["before"]["orders"] + 1  # SQL committed
    # MongoDB aborted: the cart delete that ran before the failure was undone.
    assert r["after"]["cart_lines"] == 2
    assert r["after"]["order_logs"] == 0 and r["after"]["outbox_pending"] == 1
    event = r["result"]["outbox_id"]
    fixed = admin.post(f"/admin/outbox/{event}/retry", expect=200).get_json()
    assert fixed["synced"] and fixed["event"]["status"] == "done"
    assert admin.get("/cart").get_json()["items"] == []
    uid, db = me_id(admin), mongo(TestConfig)
    assert db.user_activity_logs.count_documents({"userId": uid, "action_type": "order_placed"}) == 1
    # Replaying a finished event changes nothing.
    admin.post(f"/admin/outbox/{event}/retry", expect=200)
    assert db.user_notifications.count_documents({"userId": uid, "kind": "order"}) == 1


def test_replay_does_not_empty_a_cart_changed_since(admin, shop):
    a, b, c = shop("A"), shop("B"), shop("C")
    r = admin.post("/admin/lab/run", json={"scenario": "mongo_sync", "product_a": a, "product_b": b},
                   expect=200).get_json()
    admin.post("/cart/items", json={"product_id": c, "quantity": 1}, expect=201)
    admin.post(f"/admin/outbox/{r['result']['outbox_id']}/retry", expect=200)
    assert len(admin.get("/cart").get_json()["items"]) == 3


def test_stale_sync_does_not_cause_a_duplicate_order(admin, shop):
    a, b = shop("A"), shop("B")
    admin.post("/admin/lab/run", json={"scenario": "mongo_sync", "product_a": a, "product_b": b},
               expect=200)
    # The cart still looks full, but the pending event clears it before checkout reads it.
    assert admin.post("/checkout", json=ADDRESS).status_code == 400
    assert counts()["o"] == 1


def test_last_unit_race_has_one_winner(app, client_for, shop):
    pid = shop("Last one", stock=1)
    buyers = [client_for(f"b{i}@test.io") for i in range(6)]
    for b in buyers:
        b.post("/cart/items", json={"product_id": pid, "quantity": 1}, expect=201)
    results, barrier = [], threading.Barrier(len(buyers))

    def go(b):
        barrier.wait()
        results.append(b.post("/checkout", json=ADDRESS).status_code)

    threads = [threading.Thread(target=go, args=(b,)) for b in buyers]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [201] + [409] * 5
    assert stock(pid) == 0 and counts()["o"] == 1


def test_opposite_order_carts_do_not_deadlock(client_for, shop):
    a, b = shop("A", stock=50), shop("B", stock=50)
    buyers = [client_for(f"d{i}@test.io") for i in range(4)]
    results = []

    def go(c, first, second):
        for _ in range(5):
            c.post("/cart/items", json={"product_id": first, "quantity": 1})
            c.post("/cart/items", json={"product_id": second, "quantity": 1})
            results.append(c.post("/checkout", json=ADDRESS).status_code)

    threads = [threading.Thread(target=go, args=(c, *((a, b) if i % 2 else (b, a))))
               for i, c in enumerate(buyers)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results == [201] * 20
    assert (stock(a), stock(b)) == (30, 30)


def test_check_constraint_blocks_negative_stock(admin, shop):
    p = shop("A", stock=2)
    r = admin.patch(f"/products/{p}/stock", json={"delta": -3})
    assert r.status_code == 409 and stock(p) == 2


def test_cancel_restocks_and_notifies(customer, shop):
    a = shop("A", stock=5)
    customer.post("/cart/items", json={"product_id": a, "quantity": 2}, expect=201)
    order = customer.post("/checkout", json=ADDRESS, expect=201).get_json()["order_id"]
    assert stock(a) == 3
    customer.post(f"/orders/{order}/cancel", expect=200)
    assert stock(a) == 5
    customer.post(f"/orders/{order}/cancel", expect=409)
    assert stock(a) == 5  # a second cancel must not restock twice


def test_order_line_operations(admin, customer, shop):
    a, b, c = shop("A", 100, 5), shop("B", 200, 5), shop("C", 50, 5)
    customer.post("/cart/items", json={"product_id": a, "quantity": 1}, expect=201)
    customer.post("/cart/items", json={"product_id": b, "quantity": 2}, expect=201)
    oid = customer.post("/checkout", json=ADDRESS, expect=201).get_json()["order_id"]
    detail = admin.post(f"/orders/{oid}/items", json={"product_id": c, "quantity": 1},
                        expect=201).get_json()
    assert detail["total_amount"] == 550 and stock(c) == 4
    line_b = next(i for i in detail["items"] if i["product_id"] == b)["item_id"]
    detail = admin.patch(f"/orders/{oid}/items/{line_b}", json={"quantity": 1}, expect=200).get_json()
    assert detail["total_amount"] == 350 and stock(b) == 4
    assert admin.patch(f"/orders/{oid}/items/{line_b}", json={"quantity": 50}).status_code == 409
    assert stock(b) == 4
    for line in list(detail["items"]):
        detail = customer.delete(f"/orders/{oid}/items/{line['item_id']}", expect=200).get_json()
    assert detail["order_status"] == "cancelled"  # last line removed
    assert (stock(a), stock(b), stock(c)) == (5, 5, 5)


def test_status_flow_is_enforced(admin, customer, shop):
    a = shop()
    customer.post("/cart/items", json={"product_id": a, "quantity": 1}, expect=201)
    oid = customer.post("/checkout", json=ADDRESS, expect=201).get_json()["order_id"]
    assert admin.patch(f"/orders/{oid}/status", json={"status": "delivered"}).status_code == 409
    admin.patch(f"/orders/{oid}/status", json={"status": "shipped"}, expect=200)
    assert customer.post(f"/orders/{oid}/cancel").status_code == 409
    assert admin.delete(f"/orders/{oid}").status_code == 409
