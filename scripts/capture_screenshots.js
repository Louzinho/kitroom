// Regenerates docs/screenshots from a freshly seeded app:
//   python manage.py reset && python manage.py seed && python run.py
//   BASE=http://127.0.0.1:5000 node scripts/capture_screenshots.js
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.env.BASE || "http://127.0.0.1:5000";
const OUT = path.resolve(__dirname, "../docs/screenshots");
const PASSWORD = "KitRoom2026";
const index = [];

async function caption(page, text, focus, keepToasts) {
  await page.evaluate(([t, keep]) => {
    document.getElementById("shot-note")?.remove();
    if (!keep) document.querySelectorAll(".toast").forEach((e) => e.remove());
    const d = document.createElement("div");
    d.id = "shot-note";
    d.textContent = t;
    d.style.cssText = "position:relative;z-index:99;background:#15201b;color:#fff;padding:10px 16px;font:600 16px Barlow,sans-serif;border-bottom:4px solid #f5c518";
    (document.querySelector("dialog[open]") || document.body).prepend(d);
    window.scrollTo(0, 0);
  }, [text, keepToasts]);
  if (focus) {
    await page.locator(focus).evaluateAll((els) => els.forEach((e) => {
      e.style.outline = "4px solid #d6001c";
      e.style.outlineOffset = "3px";
    }));
  }
}

async function shot(page, group, name, text, { focus, full = true, keepToasts = false } = {}) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(250);
  await caption(page, text, focus, keepToasts);
  const file = `${group}/${name}.png`;
  fs.mkdirSync(path.join(OUT, group), { recursive: true });
  await page.screenshot({ path: path.join(OUT, file), fullPage: full });
  index.push({ group, file, text });
}

const go = async (page, hash, wait) => { await page.goto(`${BASE}/#${hash}`); await page.waitForSelector(wait); };
async function signIn(page, email) {
  await go(page, "/sign-in", "#f");
  await page.fill("[name=email]", email);
  await page.fill("[name=password]", PASSWORD);
  await page.click("#f button");
  await page.waitForSelector(".kit");
}

async function pick(page, select, text) {
  const value = await page.$eval(select, (el, t) => [...el.options].find((o) => o.text.includes(t)).value, text);
  await page.selectOption(select, value);
}

async function runLab(page, scenario, a, b) {
  await go(page, "/staff/lab", "#lab");
  await page.check(`input[value=${scenario}]`);
  await pick(page, "[name=product_a]", a);
  await pick(page, "[name=product_b]", b);
  await page.click("#lab .btn.gold");
  await page.waitForFunction((s) => document.querySelector(".verdict"), scenario);
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on("pageerror", (e) => { throw e; });

  // SQL: customer side
  await go(page, "/", ".kit");
  await shot(page, "1-sql", "01-catalogue", "SQL READ: catalogue from products JOIN categories, filters and pagination in SQL. Average ratings come from MongoDB.", { full: false });
  await page.fill("[name=q]", "199");
  await pick(page, "[name=category]", "Internationals");
  await page.waitForTimeout(500);
  await shot(page, "1-sql", "02-catalogue-search", "SQL READ: search and league filter translated to a parameterised WHERE clause", { focus: "#filters" });
  await go(page, "/join", "#f");
  await page.fill("[name=full_name]", "Nina Demo");
  await page.fill("[name=email]", "nina@kitroom.test");
  await page.fill("[name=password]", PASSWORD);
  await shot(page, "1-sql", "03-create-account-form", "SQL CREATE: account form. The password is stored only as a salted hash in users.password_hash", { focus: "#f" });
  await page.click("#f button");
  await page.waitForSelector(".kit");
  await page.goto(`${BASE}/#/account`);
  await page.waitForSelector("#profile");
  await page.fill("#profile [name=full_name]", "Nina Demo-Roux");
  await page.click("#profile button");
  await page.waitForSelector(".toast");
  await shot(page, "1-sql", "04-profile-update", "SQL UPDATE: users row saved. Avatar upload stores the file on the local disk; account deletion is at the bottom.", { focus: "#profile" });

  // SQL: staff side
  await page.click("#sign-out");
  await page.waitForTimeout(300);
  await signIn(page, "admin@kitroom.test");
  await go(page, "/staff", ".stats");
  await shot(page, "1-sql", "05-staff-overview", "SQL READ: revenue and top sellers use JOIN, GROUP BY and HAVING. Active carts and reviews come from MongoDB.");
  await go(page, "/staff/products", "#add");
  await shot(page, "1-sql", "06-inventory-before", "SQL READ: inventory. Aston Villa home has 8 in stock before the change", { focus: "tr:has(a:text('Aston Villa home')) td:nth-child(5)", full: false });
  await page.click("tr:has(a:text('Aston Villa home')) [data-stock='1']");
  await page.waitForTimeout(500);
  await shot(page, "1-sql", "07-inventory-after", "SQL UPDATE: stock_quantity + 1 (relative update, so it cannot overwrite a concurrent sale). Now 9", { focus: "tr:has(a:text('Aston Villa home')) td:nth-child(5)", full: false });
  await page.click("#add");
  await page.fill("dialog [name=title]", "Test shirt");
  await page.fill("dialog [name=club]", "Kasetsart FC");
  await page.fill("dialog [name=season]", "2026-27");
  await page.fill("dialog [name=price]", "1500");
  await page.fill("dialog [name=stock_quantity]", "3");
  await page.setInputFiles("dialog [name=image]", path.resolve(__dirname, "../app/static/uploads/products/kit-20.png"));
  await shot(page, "1-sql", "08-product-create", "SQL CREATE: new product. The image is validated and saved on the server's own disk", { focus: "dialog", full: false });
  await page.click("dialog button[type=submit]");
  await page.waitForTimeout(500);
  await page.click("tr:has(a:text('Test shirt')) [data-edit]");
  await page.fill("dialog [name=price]", "1750");
  await page.click("dialog button[type=submit]");
  await page.waitForTimeout(500);
  await shot(page, "1-sql", "09-product-update", "SQL UPDATE: Test shirt saved with its new price of 1,750", { focus: "tr:has(a:text('Test shirt'))" });
  await page.click("tr:has(a:text('Test shirt')) [data-del]");
  await page.waitForSelector("dialog [data-yes]");
  await shot(page, "1-sql", "10-product-delete", "SQL DELETE: confirmation. Shirts with past orders are refused (foreign key) and must be archived", { focus: "dialog", full: false });
  await page.click("dialog [data-yes]");
  await page.waitForTimeout(500);
  await page.click("tr:has(a:text('Inter home')) [data-del]");
  await page.click("dialog [data-yes]");
  await page.waitForSelector(".toast.bad");
  await shot(page, "1-sql", "11-delete-blocked", "SQL constraint: Inter home has order lines, so the DELETE is refused", { focus: ".toast.bad", full: false, keepToasts: true });
  await page.evaluate(() => document.querySelectorAll(".toast").forEach((e) => e.remove()));
  await go(page, "/staff/categories", "#add");
  await shot(page, "1-sql", "12-categories", "SQL CRUD: leagues (categories table) with a live product count from a LEFT JOIN");
  await go(page, "/staff/users", "#add");
  await shot(page, "1-sql", "13-users", "SQL CRUD: users with their order count (LEFT JOIN orders, GROUP BY)");
  await go(page, "/staff/orders", "tbody a");
  await shot(page, "1-sql", "14-order-history", "SQL READ: order history from view v_order_history, joining orders, users and order_items");

  // NoSQL
  await page.click("#sign-out");
  await page.waitForTimeout(300);
  await signIn(page, "mali@kitroom.test");
  await go(page, "/cart", "#checkout");
  await shot(page, "2-nosql", "01-cart", "NoSQL READ: shopping_carts document with embedded items, joined in the API with live SQL price and stock");
  await page.fill("[data-qty] >> nth=0", "2");
  await page.press("[data-qty] >> nth=0", "Tab");
  await page.waitForTimeout(600);
  await shot(page, "2-nosql", "02-cart-update", "NoSQL UPDATE: positional $set on items.$.quantity; the document version goes up", { focus: "[data-qty] >> nth=0" });
  await page.click("[data-remove] >> nth=1");
  await page.waitForTimeout(600);
  await shot(page, "2-nosql", "03-cart-remove", "NoSQL DELETE: $pull removes one embedded line; Clear cart deletes the document");
  await go(page, "/orders", "tbody a");
  await shot(page, "1-sql", "15-my-orders", "SQL READ: a customer sees only their own orders");
  await page.click("tbody a >> nth=-1");
  await page.waitForSelector("tfoot");
  await shot(page, "1-sql", "16-order-detail", "SQL READ: order_items JOIN products. Unit prices are the ones paid at purchase time");
  await page.goto(`${BASE}/#/shirt/4`);
  await page.waitForSelector("#write, [data-edit]");
  await shot(page, "2-nosql", "04-reviews", "NoSQL READ: product_reviews with an average from an aggregation pipeline. Optional fields appear only on some documents");
  await page.goto(`${BASE}/#/shirt/1`);
  await page.waitForSelector(".review");
  await page.goto(`${BASE}/#/shirt/12`);
  await page.waitForSelector("#write");
  await page.click("#write");
  await page.fill("dialog [name=comment]", "The garnet is deeper than in the photos. Lovely shirt.");
  await page.selectOption("dialog [name=sizeFeedback]", "true");
  await shot(page, "2-nosql", "05-review-post", "NoSQL CREATE: posting a review. Size feedback and photo are optional document fields", { focus: "dialog", full: false });
  await page.click("dialog button[type=submit]");
  await page.waitForSelector("[data-edit]");
  await page.click("[data-edit]");
  await page.selectOption("dialog [name=rating]", "4");
  await page.click("dialog button[type=submit]");
  await page.waitForFunction(() => document.querySelector(".review .muted")?.textContent.includes("edited"));
  await shot(page, "2-nosql", "06-review-edit", "NoSQL UPDATE: the review now has rating 4 and an editedAt field. Delete is next to Edit", { focus: ".review:has([data-edit])" });
  await go(page, "/alerts", ".note");
  await shot(page, "2-nosql", "07-notifications", "NoSQL: user_notifications panel. Mark as read updates isRead; Dismiss deletes the document", { focus: ".note.unread >> nth=0" });
  await page.click("[data-read] >> nth=0");
  await page.waitForTimeout(500);
  await shot(page, "2-nosql", "08-notification-read", "NoSQL UPDATE: isRead set to true, and the header counter drops");
  await page.click("#sign-out");
  await page.waitForTimeout(300);
  await signIn(page, "admin@kitroom.test");
  await go(page, "/staff/activity", "#log tbody tr");
  await shot(page, "2-nosql", "09-activity-log", "NoSQL: live user_activity_logs view, refreshed every 3 seconds. The metadata shape differs per action", { focus: ".meta:has-text('productId') >> nth=0", full: false });
  await go(page, "/staff/alerts", "#add");
  await page.click("#add");
  await page.fill("dialog [name=title]", "Shipping update");
  await page.fill("dialog [name=message]", "Orders placed this week leave on Friday.");
  await shot(page, "2-nosql", "10-broadcast", "NoSQL CREATE: a staff alert inserts one document per recipient", { focus: "dialog", full: false });
  await page.click("dialog button[type=submit]");
  await page.waitForTimeout(500);

  // Transactions
  await runLab(page, "success", "Aston Villa", "Barcelona");
  await shot(page, "3-transactions", "01-checkout-success", "COMMIT: stock, orders, order_items change in MySQL; cart, log and alert change in MongoDB", { focus: "tr.changed" });
  await runLab(page, "insufficient_stock", "Chelsea", "Fiorentina");
  await shot(page, "3-transactions", "02-rollback-insufficient-stock", "ROLLBACK: one shirt too many requested. Before and After are identical");
  await runLab(page, "after_deduct", "Chelsea", "Liverpool");
  await shot(page, "3-transactions", "03-rollback-after-deduct", "ROLLBACK: crash after stock was deducted. The deduction is undone");
  await runLab(page, "after_order", "Chelsea", "Liverpool");
  await shot(page, "3-transactions", "04-rollback-after-order", "ROLLBACK: crash after the order row existed. No orphan order remains");
  await runLab(page, "mid_items", "Chelsea", "Liverpool");
  await shot(page, "3-transactions", "05-rollback-mid-items", "ROLLBACK: crash with one of two lines written. No partial order remains");
  await runLab(page, "mongo_sync", "Chelsea", "Liverpool");
  await shot(page, "3-transactions", "06-mongo-failure", "Hybrid failure: SQL committed, MongoDB transaction aborted. The cart delete was undone and the event is pending", { focus: "tr.changed" });
  await go(page, "/staff/sync", "#all");
  await shot(page, "3-transactions", "07-sync-queue-pending", "Outbox: the event is pending with its error, and the order is not lost", { focus: "tr:has(.tag.pending)", full: false });
  await page.click("[data-retry]");
  await page.waitForSelector(".toast");
  await page.waitForTimeout(500);
  await shot(page, "3-transactions", "08-sync-queue-replayed", "Outbox: replay succeeded, so MongoDB and MySQL agree again", { focus: "tbody tr >> nth=0", full: false });

  // Customer-facing stock error: stock falls after the shirts went into the cart
  await page.click("#sign-out");
  await page.waitForTimeout(300);
  await signIn(page, "arthit@kitroom.test");
  await go(page, "/cart", "#checkout");
  const pid = await page.getAttribute("[data-qty]", "data-qty");
  const context2 = await browser.newContext();
  const admin = await context2.newPage();
  await signIn(admin, "admin@kitroom.test");
  await admin.evaluate(async (id) => {
    const h = { "X-Requested-With": "KitRoom", "Content-Type": "application/json" };
    const p = await (await fetch(`/api/products/${id}`)).json();
    await fetch(`/api/products/${id}/stock`, { method: "PATCH", headers: h, body: JSON.stringify({ delta: -p.stock_quantity }) });
  }, pid);
  await page.fill("[name=shipping_address]", "Rama IV Road, Bangkok 10500");
  await page.click("#checkout button");
  await page.waitForSelector(".toast.bad");
  await page.waitForTimeout(400);
  await shot(page, "3-transactions", "09-customer-stock-error", "Customer view of a rollback: the shirt sold out after it went into the cart. No order, and the cart is kept", { focus: ".toast.bad", full: false, keepToasts: true });
  await admin.evaluate(async (id) => {
    await fetch(`/api/products/${id}/stock`, { method: "PATCH", headers: { "X-Requested-With": "KitRoom", "Content-Type": "application/json" }, body: JSON.stringify({ delta: 4 }) });
  }, pid);

  fs.mkdirSync(path.join(OUT, "4-documentation"), { recursive: true });
  for (const [f, text] of [["architecture", "System architecture"], ["er-diagram", "SQL ER diagram"], ["nosql-schema", "NoSQL document schema"], ["collection-flow", "NoSQL collection flow"], ["checkout-sequence", "Checkout sequence and rollback paths"]]) {
    fs.copyFileSync(path.resolve(__dirname, `../docs/diagrams/${f}.png`), path.join(OUT, "4-documentation", `${f}.png`));
    index.push({ group: "4-documentation", file: `4-documentation/${f}.png`, text });
  }
  const titles = { "1-sql": "SQL features", "2-nosql": "NoSQL features", "3-transactions": "Transaction proof", "4-documentation": "Documentation" };
  let md = "# Screenshots\n\nEvery capture comes from the running app. The dark bar states what it proves, and red outlines mark the relevant area.\n\n";
  for (const [g, t] of Object.entries(titles)) {
    md += `## ${t}\n\n`;
    const rows = index.filter((i) => i.group === g).sort((a, b) => a.file.localeCompare(b.file));
    if (g === "3-transactions") md += "Raw database output for the same scenarios is in [db-proof](3-transactions/db-proof.md).\n\n";
    for (const i of rows) md += `**${i.text}**\n\n![${i.text}](${i.file})\n\n`;
  }
  fs.writeFileSync(path.join(OUT, "README.md"), md);
  await browser.close();
  console.log(index.length, "captures");
})().catch((e) => { console.error(e); process.exit(1); });
