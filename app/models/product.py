from ..db import execute, query, query_one

SELECT = """SELECT p.*, c.name AS category_name
            FROM products p JOIN categories c ON c.category_id = p.category_id"""
SORTS = {"newest": "p.created_at DESC, p.product_id DESC", "price_asc": "p.price ASC",
         "price_desc": "p.price DESC", "title": "p.title ASC"}
WRITABLE = ("category_id", "title", "club", "season", "description", "price",
            "stock_quantity", "status", "image_path")


def search(q=None, category_id=None, status="active", sort="newest", page=1, per_page=12):
    where, params = [], []
    if status != "all":
        where.append("p.status=%s")
        params.append(status)
    if category_id:
        where.append("p.category_id=%s")
        params.append(category_id)
    if q:
        where.append("(p.title LIKE %s OR p.club LIKE %s OR p.season LIKE %s)")
        params += [f"%{q}%"] * 3
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = query_one(f"SELECT COUNT(*) AS n FROM products p {clause}", params)["n"]
    rows = query(f"{SELECT} {clause} ORDER BY {SORTS.get(sort, SORTS['newest'])} LIMIT %s OFFSET %s",
                 (*params, per_page, (page - 1) * per_page))
    return rows, total


def get(product_id):
    return query_one(f"{SELECT} WHERE p.product_id=%s", (product_id,))


def get_many(ids):
    if not ids:
        return []
    marks = ",".join(["%s"] * len(ids))
    return query(f"{SELECT} WHERE p.product_id IN ({marks})", tuple(ids))


def create(data):
    cols = [c for c in WRITABLE if c in data]
    return execute(f"INSERT INTO products ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                   tuple(data[c] for c in cols))


def update(product_id, data):
    cols = [c for c in WRITABLE if c in data]
    if cols:
        execute(f"UPDATE products SET {', '.join(c + '=%s' for c in cols)} WHERE product_id=%s",
                (*[data[c] for c in cols], product_id))


def delete(product_id):
    execute("DELETE FROM products WHERE product_id=%s", (product_id,))


def has_orders(product_id):
    return query_one("SELECT 1 AS x FROM order_items WHERE product_id=%s LIMIT 1", (product_id,)) is not None
