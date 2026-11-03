# Screenshots

Every capture comes from the running app. The dark bar states what it proves, and red outlines mark the relevant area.

## SQL features

**SQL READ: catalogue from products JOIN categories, filters and pagination in SQL. Average ratings come from MongoDB.**

![SQL READ: catalogue from products JOIN categories, filters and pagination in SQL. Average ratings come from MongoDB.](1-sql/01-catalogue.png)

**SQL READ: search and league filter translated to a parameterised WHERE clause**

![SQL READ: search and league filter translated to a parameterised WHERE clause](1-sql/02-catalogue-search.png)

**SQL CREATE: account form. The password is stored only as a salted hash in users.password_hash**

![SQL CREATE: account form. The password is stored only as a salted hash in users.password_hash](1-sql/03-create-account-form.png)

**SQL UPDATE: users row saved. Avatar upload stores the file on the local disk; account deletion is at the bottom.**

![SQL UPDATE: users row saved. Avatar upload stores the file on the local disk; account deletion is at the bottom.](1-sql/04-profile-update.png)

**SQL READ: revenue and top sellers use JOIN, GROUP BY and HAVING. Active carts and reviews come from MongoDB.**

![SQL READ: revenue and top sellers use JOIN, GROUP BY and HAVING. Active carts and reviews come from MongoDB.](1-sql/05-staff-overview.png)

**SQL READ: inventory. Aston Villa home has 8 in stock before the change**

![SQL READ: inventory. Aston Villa home has 8 in stock before the change](1-sql/06-inventory-before.png)

**SQL UPDATE: stock_quantity + 1 (relative update, so it cannot overwrite a concurrent sale). Now 9**

![SQL UPDATE: stock_quantity + 1 (relative update, so it cannot overwrite a concurrent sale). Now 9](1-sql/07-inventory-after.png)

**SQL CREATE: new product. The image is validated and saved on the server's own disk**

![SQL CREATE: new product. The image is validated and saved on the server's own disk](1-sql/08-product-create.png)

**SQL UPDATE: Test shirt saved with its new price of 1,750**

![SQL UPDATE: Test shirt saved with its new price of 1,750](1-sql/09-product-update.png)

**SQL DELETE: confirmation. Shirts with past orders are refused (foreign key) and must be archived**

![SQL DELETE: confirmation. Shirts with past orders are refused (foreign key) and must be archived](1-sql/10-product-delete.png)

**SQL constraint: Inter home has order lines, so the DELETE is refused**

![SQL constraint: Inter home has order lines, so the DELETE is refused](1-sql/11-delete-blocked.png)

**SQL CRUD: leagues (categories table) with a live product count from a LEFT JOIN**

![SQL CRUD: leagues (categories table) with a live product count from a LEFT JOIN](1-sql/12-categories.png)

**SQL CRUD: users with their order count (LEFT JOIN orders, GROUP BY)**

![SQL CRUD: users with their order count (LEFT JOIN orders, GROUP BY)](1-sql/13-users.png)

**SQL READ: order history from view v_order_history, joining orders, users and order_items**

![SQL READ: order history from view v_order_history, joining orders, users and order_items](1-sql/14-order-history.png)

**SQL READ: a customer sees only their own orders**

![SQL READ: a customer sees only their own orders](1-sql/15-my-orders.png)

**SQL READ: order_items JOIN products. Unit prices are the ones paid at purchase time**

![SQL READ: order_items JOIN products. Unit prices are the ones paid at purchase time](1-sql/16-order-detail.png)

## NoSQL features

**NoSQL READ: shopping_carts document with embedded items, joined in the API with live SQL price and stock**

![NoSQL READ: shopping_carts document with embedded items, joined in the API with live SQL price and stock](2-nosql/01-cart.png)

**NoSQL UPDATE: positional $set on items.$.quantity; the document version goes up**

![NoSQL UPDATE: positional $set on items.$.quantity; the document version goes up](2-nosql/02-cart-update.png)

**NoSQL DELETE: $pull removes one embedded line; Clear cart deletes the document**

![NoSQL DELETE: $pull removes one embedded line; Clear cart deletes the document](2-nosql/03-cart-remove.png)

**NoSQL READ: product_reviews with an average from an aggregation pipeline. Optional fields appear only on some documents**

![NoSQL READ: product_reviews with an average from an aggregation pipeline. Optional fields appear only on some documents](2-nosql/04-reviews.png)

**NoSQL CREATE: posting a review. Size feedback and photo are optional document fields**

![NoSQL CREATE: posting a review. Size feedback and photo are optional document fields](2-nosql/05-review-post.png)

**NoSQL UPDATE: the review now has rating 4 and an editedAt field. Delete is next to Edit**

![NoSQL UPDATE: the review now has rating 4 and an editedAt field. Delete is next to Edit](2-nosql/06-review-edit.png)

**NoSQL: user_notifications panel. Mark as read updates isRead; Dismiss deletes the document**

![NoSQL: user_notifications panel. Mark as read updates isRead; Dismiss deletes the document](2-nosql/07-notifications.png)

**NoSQL UPDATE: isRead set to true, and the header counter drops**

![NoSQL UPDATE: isRead set to true, and the header counter drops](2-nosql/08-notification-read.png)

**NoSQL: live user_activity_logs view, refreshed every 3 seconds. The metadata shape differs per action**

![NoSQL: live user_activity_logs view, refreshed every 3 seconds. The metadata shape differs per action](2-nosql/09-activity-log.png)

**NoSQL CREATE: a staff alert inserts one document per recipient**

![NoSQL CREATE: a staff alert inserts one document per recipient](2-nosql/10-broadcast.png)

## Transaction proof

Raw database output for the same scenarios is in [db-proof](3-transactions/db-proof.md).

**COMMIT: stock, orders, order_items change in MySQL; cart, log and alert change in MongoDB**

![COMMIT: stock, orders, order_items change in MySQL; cart, log and alert change in MongoDB](3-transactions/01-checkout-success.png)

**ROLLBACK: one shirt too many requested. Before and After are identical**

![ROLLBACK: one shirt too many requested. Before and After are identical](3-transactions/02-rollback-insufficient-stock.png)

**ROLLBACK: crash after stock was deducted. The deduction is undone**

![ROLLBACK: crash after stock was deducted. The deduction is undone](3-transactions/03-rollback-after-deduct.png)

**ROLLBACK: crash after the order row existed. No orphan order remains**

![ROLLBACK: crash after the order row existed. No orphan order remains](3-transactions/04-rollback-after-order.png)

**ROLLBACK: crash with one of two lines written. No partial order remains**

![ROLLBACK: crash with one of two lines written. No partial order remains](3-transactions/05-rollback-mid-items.png)

**Hybrid failure: SQL committed, MongoDB transaction aborted. The cart delete was undone and the event is pending**

![Hybrid failure: SQL committed, MongoDB transaction aborted. The cart delete was undone and the event is pending](3-transactions/06-mongo-failure.png)

**Outbox: the event is pending with its error, and the order is not lost**

![Outbox: the event is pending with its error, and the order is not lost](3-transactions/07-sync-queue-pending.png)

**Outbox: replay succeeded, so MongoDB and MySQL agree again**

![Outbox: replay succeeded, so MongoDB and MySQL agree again](3-transactions/08-sync-queue-replayed.png)

**Customer view of a rollback: the shirt sold out after it went into the cart. No order, and the cart is kept**

![Customer view of a rollback: the shirt sold out after it went into the cart. No order, and the cart is kept](3-transactions/09-customer-stock-error.png)

## Documentation

**System architecture**

![System architecture](4-documentation/architecture.png)

**Checkout sequence and rollback paths**

![Checkout sequence and rollback paths](4-documentation/checkout-sequence.png)

**NoSQL collection flow**

![NoSQL collection flow](4-documentation/collection-flow.png)

**SQL ER diagram**

![SQL ER diagram](4-documentation/er-diagram.png)

**NoSQL document schema**

![NoSQL document schema](4-documentation/nosql-schema.png)

