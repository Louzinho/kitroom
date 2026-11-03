"""Database commands: python manage.py migrate | seed | reset | sync"""
import sys
from pathlib import Path

from app.config import Config
from app.db import connect_mysql, mongo
from database.mongo_setup import setup

MIGRATIONS = Path(__file__).parent / "database" / "migrations"


def migrate(cfg=Config):
    """Applies each .sql file once, tracked in schema_migrations."""
    conn = connect_mysql(cfg)
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                         filename VARCHAR(190) PRIMARY KEY,
                         applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("SELECT filename FROM schema_migrations")
        done = {r["filename"] for r in cur.fetchall()}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in done:
                continue
            sql_text = "\n".join(l for l in path.read_text(encoding="utf-8").splitlines()
                                 if not l.strip().startswith("--"))
            for statement in sql_text.split(";"):
                if statement.strip():
                    cur.execute(statement)
            cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print("applied", path.name)
    conn.close()
    setup(mongo(cfg))
    print("mongodb collections and indexes ready")


def reset(cfg=Config):
    conn = connect_mysql(cfg)
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("DROP VIEW IF EXISTS v_order_history")
        for t in ("sync_outbox", "order_items", "orders", "products", "categories", "users",
                  "schema_migrations"):
            cur.execute(f"DROP TABLE IF EXISTS {t}")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.close()
    db = mongo(cfg)
    for name in db.list_collection_names():
        db.drop_collection(name)
    print("both databases emptied")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    if command == "migrate":
        migrate()
    elif command == "reset":
        reset()
        migrate()
    elif command == "seed":
        from database.seeds.seed import seed
        seed()
    elif command == "sync":
        from app import create_app
        from app.services.sync import process_pending
        with create_app().app_context():
            print(process_pending())
    else:
        print(__doc__)
