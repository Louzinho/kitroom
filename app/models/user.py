from ..db import execute, query, query_one

PUBLIC = "user_id, email, full_name, role, avatar_path, created_at"


def create(email, password_hash, full_name, role="customer"):
    return execute(
        "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
        (email, password_hash, full_name, role))


def get(user_id):
    return query_one(f"SELECT {PUBLIC} FROM users WHERE user_id=%s", (user_id,))


def get_auth(email):
    return query_one("SELECT * FROM users WHERE email=%s", (email,))


def get_hash(user_id):
    row = query_one("SELECT password_hash FROM users WHERE user_id=%s", (user_id,))
    return row["password_hash"] if row else None


def list_all():
    return query(f"""SELECT {', '.join('u.' + c for c in PUBLIC.split(', '))},
                     COUNT(o.order_id) AS order_count
                     FROM users u LEFT JOIN orders o ON o.user_id = u.user_id
                     GROUP BY u.user_id ORDER BY u.user_id""")


def update(user_id, **fields):
    if fields:
        cols = ", ".join(f"{k}=%s" for k in fields)
        execute(f"UPDATE users SET {cols} WHERE user_id=%s", (*fields.values(), user_id))


def delete(user_id):
    execute("DELETE FROM users WHERE user_id=%s", (user_id,))
