# The Kit Room: video script

Target length: about 10:30. Hard limit: 12:00.

## Before recording

1. In the project folder: `python manage.py reset`, then `python manage.py seed`, then `python run.py`.
2. Open two browser windows: one signed in as `mali@kitroom.test`, one as `admin@kitroom.test` (password `KitRoom2026` for both).
3. Open the deck in Present mode. Keep a terminal ready in the project folder with `(.venv)` active.

Speak slowly. The words below are a guide: say them in your own way. Text in *italics* is what you do on screen.

---

## Part 1. The project (0:00 to 2:20)

**Slide 1, The Kit Room** (0:00)

> Hello everyone, I'm Louis. My project is called The Kit Room. It is an online shop that sells old football shirts. The interesting part is that it uses two different databases at the same time, MySQL and MongoDB. In the next ten minutes I'll show you how I designed the data, and how the two databases stay correct together.

**Slide 2, What the app does** (0:20)

> There are two kinds of users. Customers browse the shirts, put them in a cart, place orders and write reviews. Staff manage the catalogue, the stock and the orders. Everything runs on my own computer: both databases are installed locally, and the images are stored on the server's disk.

**Slide 3, Why two databases?** (0:50)

> Why two databases instead of one? Because each one is good at something different. MySQL is a relational database: data lives in tables with fixed columns, and the database itself checks the rules. I use it for money and stock, things that must never be wrong.
> MongoDB stores documents, a bit like JSON objects, and two documents in the same collection can have different fields. I use it for carts, reviews, notifications and logs, which change often and don't all have the same shape.

**Slide 4, System architecture** (1:40)

> Here is how the pieces connect. The web page in the browser never touches a database directly. It sends requests to my server, written in Python with Flask. Inside the server, each layer has one job: routes receive the request, controllers check it, services run multi-step work like placing an order, and models contain the queries. Only the models talk to MySQL and MongoDB.

## Part 2. Database design (2:20 to 5:20)

**Slide 5, The data model in UML** (2:20). This is the key slide: take your time.

> This is the whole data model as a UML class diagram. Each box is a class, with its main attributes. Green boxes become MySQL tables, blue boxes become MongoDB collections.
> *Point at User and Order.* Read the numbers on the lines as "how many". One User places zero or many Orders.
> *Point at Order and OrderItem.* One Order contains one or many OrderItems. The black diamond means composition: an order item cannot exist without its order, so they are deleted together.
> *Point at ShoppingCart and CartItem.* Same idea in MongoDB: the cart contains its items directly inside the document.
> *Point at a dashed line.* Solid lines are real foreign keys, checked by MySQL. Dashed lines go from MongoDB to MySQL: a review stores a productId, but MongoDB cannot check it, so my code does.
> The SyncOutbox table looks strange here. I'll explain it in the transactions part.

**Slide 6, From UML to SQL tables** (3:40)

> Now we turn the green part into real tables. The rule is simple: each class becomes a table, and each one-to-many line becomes a foreign key on the "many" side. So the orders table has a user_id column.
> Orders and products are many-to-many: an order has many shirts, and a shirt appears in many orders. So we need the order_items table in the middle.
> The tables are in third normal form, so no data is repeated. I also put rules inside the database: a CHECK constraint refuses negative stock, even if my code has a bug. And order_items keeps the price paid, so changing a price later does not change old orders.

**Slide 7, From UML to MongoDB documents** (4:30)

> The blue part becomes four collections. In MongoDB the main question is: embed or reference? A cart and its items are always read together, so the items are embedded in the cart document: one read gets everything.
> Reviews reference the product by its id, and keep a copy of the user's name, so showing reviews needs no join. Some fields are optional: only some reviews have a photo, and that's fine in MongoDB. Logs are deleted automatically after 180 days.

## Part 3. Live demo of CRUD (5:20 to 7:00)

*Switch to the browser, Mali's window.*

> Let's see it working. I'm signed in as a customer.

- *Type "199" in the search and choose Internationals.* "This search is a SQL query with a join between products and categories."
- *Open a shirt, add it to the cart, open the cart, change the quantity, remove a line.* "The cart is one MongoDB document. Adding, changing and removing a line are updates inside that single document."
- *Open a shirt you have not reviewed, post a review, then edit it.* "Reviews are documents too: create, then update."
- *Open Alerts, click Mark as read.* "Notifications: the isRead field changes from false to true."

*Switch to the admin window, Staff > Shirts.*

- *Press + on a stock value.* "Staff update the stock in MySQL."
- *Click Delete on Inter home.* "This shirt is in past orders. The foreign key refuses the delete, so it must be archived instead."

## Part 4. Transactions (7:00 to 9:45)

**Slide 8, Placing an order: all or nothing** (7:00)

> A transaction means "all or nothing". Placing an order touches several tables, so these five steps run inside one MySQL transaction. If anything fails, even at the last step, MySQL does a ROLLBACK and the database goes back exactly as before.
> Step one locks the shirt rows, so if two people buy the last shirt at the same time, only one succeeds.
> But MySQL and MongoDB cannot share one transaction. So, in the same MySQL transaction, I write a small "to do" note: the outbox event. After the commit, a MongoDB transaction empties the cart and sends the notification. If MongoDB fails, nothing is half-written, the note stays, and it is replayed later. The order is never lost.

*Switch to the admin window, Staff > Transaction lab.* (8:00)

> This screen runs the real checkout, and can make it fail on purpose.

- *Choose Successful checkout, click Run checkout.* "Everything succeeds. The yellow rows changed: stock went down, an order was created, and the cart was emptied in MongoDB."
- *Choose Crash between order lines, click Run checkout.* "Now the crash happens after one of two order lines was written. Look: before and after are identical. The rollback undid everything."
- *Choose MongoDB fails after the commit, click Run checkout.* "This time MySQL committed, so the order exists. But MongoDB failed: the cart is still full and the event is pending."
- *Open Sync queue, click Replay.* "I replay the event. Now it is done, and both databases agree again."

**Slide 9, Proof** (9:15)

> This slide sums it up: even when the crash happens after the stock was removed, every value comes back unchanged.

*Optional, only if you have time:* in the terminal, run `python -m pytest tests -q` and show `31 passed`.

**Slide 10, Results and limits** (9:45)

> To finish: all ten entities can be created, read, updated and deleted from the web interface. 31 automated tests run on the real databases, including six people buying the last shirt at the same time: exactly one wins.
> What could be better: today staff replay failed events by hand, there is no real payment, and MongoDB runs on a single server. Thank you for watching.

*End at about 10:30.*

---

If you run long, cut in this order: the pytest run, the review edit, the search. Keep the UML slide and the Transaction lab: they carry the grade.
