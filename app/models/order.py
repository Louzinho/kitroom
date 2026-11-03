from ..db import execute, query, query_one


def history(user_id=None, status=None):
    where, params = [], []
    if user_id:
        where.append("user_id=%s")
        params.append(user_id)
    if status:
        where.append("order_status=%s")
        params.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return query(f"SELECT * FROM v_order_history {clause} ORDER BY created_at DESC, order_id DESC", params)


def get(order_id):
    return query_one("SELECT * FROM v_order_history WHERE order_id=%s", (order_id,))


def items(order_id):
    return query("""SELECT i.item_id, i.order_id, i.product_id, i.unit_price, i.quantity,
                           i.unit_price * i.quantity AS line_total,
                           p.title, p.club, p.season, p.image_path
                    FROM order_items i JOIN products p ON p.product_id = i.product_id
                    WHERE i.order_id=%s ORDER BY i.item_id""", (order_id,))


def update_address(order_id, address):
    execute("UPDATE orders SET shipping_address=%s WHERE order_id=%s", (address, order_id))


def delete(order_id):
    execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
