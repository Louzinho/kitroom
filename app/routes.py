"""Every URL of the REST API, in one table. Handlers live in app/controllers."""
from flask import Blueprint

from .controllers import accounts as a, admin as ad, catalog as c, community as m, shopping as s

api = Blueprint("api", __name__, url_prefix="/api")

ROUTES = [
    # SQL: accounts
    ("POST", "/auth/register", a.register), ("POST", "/auth/login", a.login),
    ("POST", "/auth/logout", a.logout), ("GET", "/me", a.me), ("PATCH", "/me", a.update_me),
    ("DELETE", "/me", a.delete_me), ("PUT", "/me/password", a.change_password),
    ("POST", "/me/avatar", a.upload_avatar),
    ("GET", "/users", a.list_users), ("POST", "/users", a.create_user),
    ("PATCH", "/users/<int:user_id>", a.update_user), ("DELETE", "/users/<int:user_id>", a.delete_user),
    # SQL: catalogue
    ("GET", "/categories", c.list_categories), ("POST", "/categories", c.create_category),
    ("PUT", "/categories/<int:category_id>", c.update_category),
    ("DELETE", "/categories/<int:category_id>", c.delete_category),
    ("GET", "/products", c.list_products), ("POST", "/products", c.create_product),
    ("GET", "/products/<int:product_id>", c.get_product),
    ("PUT", "/products/<int:product_id>", c.update_product),
    ("PATCH", "/products/<int:product_id>/stock", c.adjust_stock),
    ("DELETE", "/products/<int:product_id>", c.delete_product),
    # SQL: orders and order lines
    ("POST", "/checkout", s.checkout), ("GET", "/orders", s.list_orders),
    ("GET", "/admin/orders", s.list_all_orders), ("GET", "/orders/<int:order_id>", s.get_order),
    ("PATCH", "/orders/<int:order_id>/address", s.update_order_address),
    ("PATCH", "/orders/<int:order_id>/status", s.update_order_status),
    ("POST", "/orders/<int:order_id>/cancel", s.cancel_order),
    ("DELETE", "/orders/<int:order_id>", s.delete_order),
    ("POST", "/orders/<int:order_id>/items", s.add_order_item),
    ("PATCH", "/orders/<int:order_id>/items/<int:item_id>", s.update_order_item),
    ("DELETE", "/orders/<int:order_id>/items/<int:item_id>", s.delete_order_item),
    # NoSQL: shopping_carts
    ("GET", "/cart", s.get_cart), ("POST", "/cart/items", s.add_to_cart),
    ("PATCH", "/cart/items/<int:product_id>", s.update_cart_item),
    ("DELETE", "/cart/items/<int:product_id>", s.remove_cart_item), ("DELETE", "/cart", s.clear_cart),
    # NoSQL: product_reviews
    ("GET", "/products/<int:product_id>/reviews", m.list_reviews),
    ("POST", "/products/<int:product_id>/reviews", m.create_review),
    ("GET", "/me/reviews", m.my_reviews), ("PUT", "/reviews/<review_id>", m.update_review),
    ("POST", "/reviews/<review_id>/like", m.like_review), ("DELETE", "/reviews/<review_id>", m.delete_review),
    # NoSQL: user_notifications
    ("GET", "/notifications", m.list_notifications),
    ("PATCH", "/notifications/<note_id>", m.read_notification),
    ("POST", "/notifications/read-all", m.read_all_notifications),
    ("DELETE", "/notifications/<note_id>", m.delete_notification),
    ("GET", "/admin/notifications", m.admin_list_notifications),
    ("POST", "/admin/notifications", m.admin_send_notification),
    ("PUT", "/admin/notifications/<note_id>", m.admin_update_notification),
    ("DELETE", "/admin/notifications/<note_id>", m.admin_delete_notification),
    # NoSQL: user_activity_logs
    ("GET", "/admin/logs", m.list_logs), ("POST", "/admin/logs", m.create_log),
    ("PATCH", "/admin/logs/<log_id>", m.update_log), ("DELETE", "/admin/logs/<log_id>", m.delete_log),
    # Operations
    ("GET", "/health", ad.health), ("GET", "/admin/dashboard", ad.dashboard),
    ("GET", "/admin/outbox", ad.list_outbox), ("POST", "/admin/outbox/retry", ad.retry_all_outbox),
    ("POST", "/admin/outbox/<int:outbox_id>/retry", ad.retry_outbox),
    ("DELETE", "/admin/outbox/<int:outbox_id>", ad.delete_outbox),
    ("POST", "/admin/lab/run", ad.run_lab),
]

for method, path, handler in ROUTES:
    api.add_url_rule(path, f"{method}_{path}", handler, methods=[method])
