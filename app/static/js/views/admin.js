import { act, api, baht, confirmDialog, esc, fail, formDialog, img, tag, toast, when } from "../core.js";

const TABS = [["", "Overview"], ["products", "Shirts"], ["categories", "Leagues"], ["orders", "Orders"], ["users", "Users"],
  ["alerts", "Alerts"], ["activity", "Activity"], ["sync", "Sync queue"], ["lab", "Transaction lab"]];
let liveTimer;

export async function adminView(main, tab = "") {
  clearInterval(liveTimer);
  main.innerHTML = `<div class="wrap"><h1>Staff</h1>
    <nav class="sub" aria-label="Staff">${TABS.map(([t, label]) => `<a href="#/staff${t ? `/${t}` : ""}" class="${t === tab ? "on" : ""}">${label}</a>`).join("")}</nav>
    <div id="tab"></div></div>`;
  const el = main.querySelector("#tab");
  await ({ "": overview, products, categories, orders, users, alerts, activity, sync, lab })[tab]?.(el);
}

const del = (title, body, confirm) => confirmDialog({ title, body, confirm });

async function overview(el) {
  const d = await api("/admin/dashboard");
  el.innerHTML = `<div class="stats">
    <div class="stat"><b>${baht(d.revenue.v)}</b>revenue from ${d.revenue.n} orders</div>
    <div class="stat"><b>${d.active_carts}</b>active carts</div>
    <div class="stat"><b>${d.reviews}</b>reviews</div>
    <div class="stat"><b>${d.pending_sync}</b>events waiting to sync</div></div>
    <div class="two"><section class="panel"><h2>Running low</h2>${d.low_stock.length ? `<table><tbody>${d.low_stock.map((p) => `<tr><td><a href="#/shirt/${p.product_id}">${esc(p.title)}</a></td><td class="num">${p.stock_quantity}</td></tr>`).join("")}</tbody></table>` : `<p class="muted">Every shirt has more than 3 in stock.</p>`}</section>
    <section class="panel"><h2>Top sellers</h2>${d.top_sellers.length ? `<table><tbody>${d.top_sellers.map((p) => `<tr><td>${esc(p.title)}</td><td class="num">${p.sold} sold</td><td class="num">${baht(p.revenue)}</td></tr>`).join("")}</tbody></table>` : `<p class="muted">No sales yet.</p>`}</section></div>`;
}

async function products(el) {
  const [{ items }, cats] = await Promise.all([api("/products?status=all&per_page=100&sort=title"), api("/categories")]);
  const form = (p) => formDialog({ title: p ? `Edit ${p.title}` : "Add a shirt", submit: p ? "Save shirt" : "Add shirt", multipart: true,
    fields: [{ name: "title", label: "Title", value: p?.title, required: true }, { name: "club", label: "Club or country", value: p?.club, required: true },
      { name: "season", label: "Season", value: p?.season, required: true, hint: "For example 1998-99" },
      { name: "category_id", label: "League", type: "select", value: p?.category_id, options: cats.map((c) => [c.category_id, c.name]) },
      { name: "price", label: "Price in baht", type: "number", step: "0.01", min: "0.01", value: p?.price, required: true },
      { name: "stock_quantity", label: "Stock", type: "number", min: 0, value: p?.stock_quantity ?? 0, required: true },
      { name: "status", label: "Status", type: "select", value: p?.status ?? "active", options: [["active", "On sale"], ["archived", "Archived"]] },
      { name: "description", label: "Description", type: "textarea", value: p?.description },
      { name: "image", label: "Image", type: "file", hint: "Saved on this server. JPG, PNG or WEBP, up to 5 MB" }],
    onSubmit: async (data) => {
      await api(p ? `/products/${p.product_id}` : "/products", { method: p ? "PUT" : "POST", form: data });
      toast(p ? "Shirt saved" : "Shirt added");
      products(el);
    } });
  el.innerHTML = `<div class="row between" style="margin-bottom:14px"><span>${items.length} shirts</span><button class="btn" id="add">Add a shirt</button></div>
    <div class="table-wrap"><table><thead><tr><th></th><th>Shirt</th><th>League</th><th class="num">Price</th><th>Stock</th><th>Status</th><th></th></tr></thead>
    <tbody>${items.map((p) => `<tr><td><img class="thumb" src="${img(p.image_path)}" alt=""></td>
      <td><a href="#/shirt/${p.product_id}">${esc(p.title)}</a><br><span class="muted">${esc(p.season)}</span></td><td>${esc(p.category_name)}</td>
      <td class="num">${baht(p.price)}</td>
      <td><div class="row"><button class="btn alt small" data-stock="-1" data-id="${p.product_id}" aria-label="One less of ${esc(p.title)}">−</button><strong>${p.stock_quantity}</strong><button class="btn alt small" data-stock="1" data-id="${p.product_id}" aria-label="One more of ${esc(p.title)}">+</button></div></td>
      <td>${tag(p.status)}</td><td><div class="row"><button class="btn alt small" data-edit="${p.product_id}">Edit</button><button class="btn danger small" data-del="${p.product_id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>`;
  el.querySelector("#add").onclick = () => form();
  el.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.stock) { await act(() => api(`/products/${t.dataset.id}/stock`, { method: "PATCH", json: { delta: Number(t.dataset.stock) } }), "Stock updated"); products(el); }
    if (t.dataset.edit) form(items.find((p) => p.product_id === Number(t.dataset.edit)));
    if (t.dataset.del && await del("Delete this shirt?", "Its image and reviews go too. Shirts with past orders can only be archived.", "Delete shirt")) {
      await act(() => api(`/products/${t.dataset.del}`, { method: "DELETE" }), "Shirt deleted");
      products(el);
    }
  };
}

async function categories(el) {
  const cats = await api("/categories");
  const form = (c) => formDialog({ title: c ? `Edit ${c.name}` : "Add a league", submit: c ? "Save league" : "Add league",
    fields: [{ name: "name", label: "Name", value: c?.name, required: true }, { name: "description", label: "Description", value: c?.description }],
    onSubmit: async (json) => { await api(c ? `/categories/${c.category_id}` : "/categories", { method: c ? "PUT" : "POST", json }); toast(c ? "League saved" : "League added"); categories(el); } });
  el.innerHTML = `<div class="row between" style="margin-bottom:14px"><span>${cats.length} leagues</span><button class="btn" id="add">Add a league</button></div>
    <div class="table-wrap"><table><thead><tr><th>Name</th><th>Description</th><th class="num">Shirts on sale</th><th></th></tr></thead>
    <tbody>${cats.map((c) => `<tr><td>${esc(c.name)}</td><td>${esc(c.description)}</td><td class="num">${c.product_count}</td>
      <td><div class="row"><button class="btn alt small" data-edit="${c.category_id}">Edit</button><button class="btn danger small" data-del="${c.category_id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>`;
  el.querySelector("#add").onclick = () => form();
  el.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.edit) form(cats.find((c) => c.category_id === Number(t.dataset.edit)));
    if (t?.dataset.del && await del("Delete this league?", "Leagues that still hold shirts cannot be deleted.", "Delete league")) {
      await act(() => api(`/categories/${t.dataset.del}`, { method: "DELETE" }), "League deleted");
      categories(el);
    }
  };
}

async function orders(el) {
  const rows = await api("/admin/orders");
  el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Order</th><th>Customer</th><th>Placed</th><th class="num">Shirts</th><th class="num">Total</th><th>Status</th></tr></thead>
    <tbody>${rows.map((o) => `<tr><td><a href="#/orders/${o.order_id}">#${o.order_id}</a></td><td>${esc(o.full_name)}<br><span class="muted">${esc(o.email)}</span></td>
      <td>${when(o.created_at)}</td><td class="num">${o.item_count}</td><td class="num">${baht(o.total_amount)}</td><td>${tag(o.order_status)}</td></tr>`).join("")}</tbody></table></div>`;
}

async function users(el) {
  const rows = await api("/users");
  const form = (u) => formDialog({ title: u ? `Edit ${u.full_name}` : "Add a user", submit: u ? "Save user" : "Add user",
    fields: [{ name: "full_name", label: "Full name", value: u?.full_name, required: true }, { name: "email", label: "Email", type: "email", value: u?.email, required: true },
      ...(u ? [] : [{ name: "password", label: "Password", type: "password", required: true, hint: "At least 8 characters" }]),
      { name: "role", label: "Role", type: "select", value: u?.role ?? "customer", options: [["customer", "Customer"], ["admin", "Staff"]] }],
    onSubmit: async (json) => { await api(u ? `/users/${u.user_id}` : "/users", { method: u ? "PATCH" : "POST", json }); toast(u ? "User saved" : "User added"); users(el); } });
  el.innerHTML = `<div class="row between" style="margin-bottom:14px"><span>${rows.length} users</span><button class="btn" id="add">Add a user</button></div>
    <div class="table-wrap"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th class="num">Orders</th><th>Joined</th><th></th></tr></thead>
    <tbody>${rows.map((u) => `<tr><td>${esc(u.full_name)}</td><td>${esc(u.email)}</td><td>${tag(u.role)}</td><td class="num">${u.order_count}</td><td>${when(u.created_at)}</td>
      <td><div class="row"><button class="btn alt small" data-edit="${u.user_id}">Edit</button><button class="btn danger small" data-del="${u.user_id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>`;
  el.querySelector("#add").onclick = () => form();
  el.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.edit) form(rows.find((u) => u.user_id === Number(t.dataset.edit)));
    if (t?.dataset.del && await del("Delete this user?", "Their cart, reviews and alerts go too. Users with orders stay on record.", "Delete user")) {
      await act(() => api(`/users/${t.dataset.del}`, { method: "DELETE" }), "User deleted");
      users(el);
    }
  };
}

async function alerts(el) {
  const [notes, people] = await Promise.all([api("/admin/notifications"), api("/users")]);
  const names = Object.fromEntries(people.map((u) => [u.user_id, u.full_name]));
  el.innerHTML = `<div class="row between" style="margin-bottom:14px"><span>Last ${notes.length} alerts</span><button class="btn" id="add">Send an alert</button></div>
    <div class="table-wrap"><table><thead><tr><th>To</th><th>Alert</th><th>Sent</th><th>Read</th><th></th></tr></thead>
    <tbody>${notes.map((n) => `<tr><td>${esc(names[n.userId] ?? `User ${n.userId}`)}</td><td><strong>${esc(n.title)}</strong><br>${esc(n.message)}</td><td>${when(n.sentAt)}</td><td>${n.isRead ? "Yes" : "No"}</td>
      <td><div class="row"><button class="btn alt small" data-edit="${n._id}">Edit</button><button class="btn danger small" data-del="${n._id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>`;
  el.querySelector("#add").onclick = () => formDialog({ title: "Send an alert", submit: "Send alert",
    fields: [{ name: "user_id", label: "Send to", type: "select", options: [["", "Everyone"], ...people.map((u) => [u.user_id, u.full_name])] },
      { name: "title", label: "Title", required: true }, { name: "message", label: "Message", type: "textarea", required: true }],
    onSubmit: async (json) => { const r = await api("/admin/notifications", { method: "POST", json }); toast(`Alert sent to ${r.sent}`); alerts(el); } });
  el.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.edit) {
      const n = notes.find((x) => x._id === t.dataset.edit);
      formDialog({ title: "Edit alert", submit: "Save alert",
        fields: [{ name: "title", label: "Title", value: n.title, required: true }, { name: "message", label: "Message", type: "textarea", value: n.message, required: true }],
        onSubmit: async (json) => { await api(`/admin/notifications/${n._id}`, { method: "PUT", json }); toast("Alert saved"); alerts(el); } });
    }
    if (t?.dataset.del && await del("Delete this alert?", "The customer will no longer see it.", "Delete alert")) {
      await act(() => api(`/admin/notifications/${t.dataset.del}`, { method: "DELETE" }), "Alert deleted");
      alerts(el);
    }
  };
}

async function activity(el) {
  const filter = { action: "" };
  el.innerHTML = `<div class="filters"><label>Action<select id="action"><option value="">All actions</option></select></label>
    <button class="btn" id="add">Add a note</button><span class="muted" style="align-self:center">Updates every 3 seconds</span></div><div id="log"></div>`;
  const select = el.querySelector("#action");
  async function load() {
    const data = await api(`/admin/logs?action=${encodeURIComponent(filter.action)}`);
    const known = [...select.options].map((o) => o.value);
    data.actions.filter((a) => !known.includes(a)).forEach((a) => select.add(new Option(a, a)));
    el.querySelector("#log").innerHTML = `<div class="table-wrap"><table><thead><tr><th>When</th><th>User</th><th>Action</th><th>Details</th><th>IP</th><th></th></tr></thead>
      <tbody>${data.items.map((l) => `<tr><td>${when(l.timestamp)}</td><td>${l.userId ?? "Guest"}</td><td>${esc(l.action_type)}</td>
        <td class="meta">${esc(JSON.stringify(l.metadata ?? {}))}${l.adminNote ? `<br><strong>Note: ${esc(l.adminNote)}</strong>` : ""}</td><td>${esc(l.ip_address ?? "")}</td>
        <td><div class="row"><button class="btn alt small" data-note="${l._id}">Annotate</button><button class="btn danger small" data-del="${l._id}">Delete</button></div></td></tr>`).join("")}</tbody></table></div>`;
  }
  select.onchange = () => { filter.action = select.value; load(); };
  el.querySelector("#add").onclick = () => formDialog({ title: "Add a note to the log", submit: "Add note",
    fields: [{ name: "action_type", label: "Action name", value: "staff_note", required: true }, { name: "note", label: "Note", type: "textarea" }],
    onSubmit: async (json) => { await api("/admin/logs", { method: "POST", json }); load(); } });
  el.querySelector("#log").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.note) formDialog({ title: "Annotate log entry", submit: "Save note",
      fields: [{ name: "adminNote", label: "Note" }],
      onSubmit: async (json) => { await api(`/admin/logs/${t.dataset.note}`, { method: "PATCH", json }); load(); } });
    if (t?.dataset.del) { await act(() => api(`/admin/logs/${t.dataset.del}`, { method: "DELETE" }), "Entry deleted"); load(); }
  };
  await load();
  liveTimer = setInterval(() => { if (!document.getElementById("log")) clearInterval(liveTimer); else if (!document.getElementById("modal").open) load().catch(() => {}); }, 3000);
}

async function sync(el) {
  const rows = await api("/admin/outbox");
  const pending = rows.some((r) => r.status === "pending");
  el.innerHTML = `<div class="row between" style="margin-bottom:14px"><span>When an order commits in MySQL, its MongoDB follow-up is queued here until it succeeds.</span>
    ${pending ? `<button class="btn" id="all">Replay all pending</button>` : ""}</div>
    <div class="table-wrap"><table><thead><tr><th>Event</th><th>Order</th><th>Type</th><th>Status</th><th class="num">Attempts</th><th>Last error</th><th></th></tr></thead>
    <tbody>${rows.map((r) => `<tr><td>${r.outbox_id}</td><td><a href="#/orders/${r.order_id}">#${r.order_id}</a></td><td>${esc(r.event_type)}</td><td>${tag(r.status)}</td><td class="num">${r.attempts}</td><td class="meta">${esc(r.last_error ?? "")}</td>
      <td>${r.status === "pending" ? `<button class="btn small" data-retry="${r.outbox_id}">Replay</button>` : `<button class="btn danger small" data-del="${r.outbox_id}">Delete</button>`}</td></tr>`).join("")}</tbody></table></div>`;
  el.querySelector("#all")?.addEventListener("click", async () => { await act(() => api("/admin/outbox/retry", { method: "POST" }), "Replayed"); sync(el); });
  el.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.retry) { await act(() => api(`/admin/outbox/${t.dataset.retry}/retry`, { method: "POST" }), "Replayed"); sync(el); }
    if (t?.dataset.del) { await act(() => api(`/admin/outbox/${t.dataset.del}`, { method: "DELETE" }), "Event deleted"); sync(el); }
  };
}

const SCENARIOS = [
  ["success", "Successful checkout", "Everything commits in MySQL, then in MongoDB."],
  ["insufficient_stock", "Not enough stock", "Asks for one more than exists. Fails at the stock check."],
  ["after_deduct", "Crash after stock deduction", "Stock has been deducted when the error hits."],
  ["after_order", "Crash after the order insert", "The order row exists when the error hits."],
  ["mid_items", "Crash between order lines", "One of two lines is written when the error hits."],
  ["mongo_sync", "MongoDB fails after the commit", "The order stays. The cross-database step aborts and queues for replay."],
];
const ROWS = [["orders", "MySQL orders rows"], ["order_items", "MySQL order_items rows"], ["outbox_pending", "MySQL pending sync events"],
  ["cart_lines", "MongoDB cart lines"], ["order_logs", "MongoDB order_placed logs"], ["order_notifications", "MongoDB order alerts"]];

async function lab(el) {
  const { items } = await api("/products?per_page=100&sort=title");
  const options = items.filter((p) => p.stock_quantity > 0).map((p) => `<option value="${p.product_id}">${esc(p.title)} ${esc(p.season)} (${p.stock_quantity} in stock)</option>`).join("");
  el.innerHTML = `<form class="panel" id="lab"><h2>Run the real checkout with a chosen failure</h2>
    <p>Each run replaces your own cart with one of each shirt below and calls the same code customers use.</p>
    <div class="scenarios">${SCENARIOS.map(([v, t, d], i) => `<label class="scenario"><input type="radio" name="scenario" value="${v}" ${i === 0 ? "checked" : ""}><strong>${t}</strong><span>${d}</span></label>`).join("")}</div>
    <div class="two"><label>First shirt<select name="product_a">${options}</select></label>
    <label>Second shirt<select name="product_b">${options}</select></label></div>
    <button class="btn gold" style="margin-top:12px">Run checkout</button></form><div id="result"></div>`;
  const form = el.querySelector("#lab");
  form.elements.product_b.selectedIndex = Math.min(1, form.elements.product_b.options.length - 1);
  form.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await api("/admin/lab/run", { method: "POST", json: Object.fromEntries(new FormData(form)) });
      const label = SCENARIOS.find(([v]) => v === r.scenario)[1];
      const stockRows = Object.keys(r.before.stock).map((id) => [r.titles[id] + " stock", r.before.stock[id], r.after.stock[id]]);
      const allRows = [...stockRows, ...ROWS.map(([k, name]) => [name, r.before[k], r.after[k]])];
      const same = allRows.every(([, b, a]) => b === a);
      const verdict = r.error ? (same ? "Rolled back. Every value is identical before and after." : r.error)
        : r.result.synced ? `Committed as order #${r.result.order_id}, and MongoDB is in sync.`
        : `Order #${r.result.order_id} committed. MongoDB aborted with no partial writes, and the event waits in the sync queue.`;
      el.querySelector("#result").innerHTML = `<div class="verdict ${r.error || !r.result.synced ? "fail" : ""}">${esc(label)}: ${esc(verdict)}</div>
        ${r.error ? `<p>Error shown to the customer: ${esc(r.error)}</p>` : ""}
        <div class="two"><section class="panel"><h2>What ran</h2><ol class="trace">${r.trace.map((s) => `<li class="${s.ok ? "ok" : "fail"}"><strong>${esc(s.step)}</strong><small>${esc(s.detail)}</small></li>`).join("")}</ol></section>
        <section class="panel"><h2>Database state</h2><div class="table-wrap"><table><thead><tr><th>Value</th><th class="num">Before</th><th class="num">After</th></tr></thead>
        <tbody>${allRows.map(([n, b, a]) => `<tr class="${b !== a ? "changed" : ""}"><td>${esc(n)}</td><td class="num">${b}</td><td class="num">${a}</td></tr>`).join("")}</tbody></table></div></section></div>
        ${!r.error && !r.result.synced ? `<p style="margin-top:16px"><a class="btn" href="#/staff/sync">Open the sync queue</a></p>` : ""}`;
      window.dispatchEvent(new Event("kitroom:changed"));
    } catch (error) { fail(error); }
  };
}
