from ..db import execute, query, query_one


def list_all():
    return query("""SELECT c.*, COUNT(p.product_id) AS product_count
                    FROM categories c LEFT JOIN products p
                      ON p.category_id = c.category_id AND p.status = 'active'
                    GROUP BY c.category_id ORDER BY c.name""")


def get(category_id):
    return query_one("SELECT * FROM categories WHERE category_id=%s", (category_id,))


def create(name, description):
    return execute("INSERT INTO categories (name, description) VALUES (%s,%s)", (name, description))


def update(category_id, name, description):
    execute("UPDATE categories SET name=%s, description=%s WHERE category_id=%s",
            (name, description, category_id))


def delete(category_id):
    execute("DELETE FROM categories WHERE category_id=%s", (category_id,))
