import { act, api, baht, confirmDialog, emptyState, esc, fail, formDialog, img, state, tag, toast, when } from "../core.js";

export async function cartView(main) {
  const cart = await api("/cart");
  if (!cart.items.length) {
    main.innerHTML = `<div class="wrap narrow"><h1>Your cart</h1>${emptyState("Your cart is empty.", "#/", "Browse shirts")}</div>`;
    return;
  }
  main.innerHTML = `<div class="wrap"><h1>Your cart</h1>
    <div class="table-wrap panel" style="padding:0"><table>
      <thead><tr><th></th><th>Shirt</th><th>Quantity</th><th class="num">Price</th><th class="num">Subtotal</th><th></th></tr></thead>
      <tbody>${cart.items.map((i) => `<tr>
        <td><img class="thumb" src="${img(i.image_path)}" alt=""></td>
        <td><a href="#/shirt/${i.product_id}">${esc(i.title)}</a><br><span class="muted">${esc(i.season ?? "")}</span>
          ${i.quantity > i.stock ? `<br><span class="low">Only ${i.stock} left. Lower the quantity to check out.</span>` : ""}
          ${i.price_changed ? `<br><span class="low">Price changed since you added it</span>` : ""}</td>
        <td><input class="qty" type="number" min="1" max="99" value="${i.quantity}" data-qty="${i.product_id}" aria-label="Quantity of ${esc(i.title)}"></td>
        <td class="num">${baht(i.price)}</td><td class="num">${baht(i.price * i.quantity)}</td>
        <td><button class="btn danger small" data-remove="${i.product_id}">Remove</button></td></tr>`).join("")}</tbody>
    </table></div>
    <div class="row between panel"><button class="btn alt" id="clear">Clear cart</button><span class="price">Total ${baht(cart.total)}</span></div>
    <form class="panel" id="checkout"><h2>Delivery</h2>
      <label>Delivery address<input name="shipping_address" required maxlength="255" autocomplete="street-address"></label>
      <button class="btn gold">Place order</button></form></div>`;

  const reload = () => cartView(main);
  main.querySelector("table").onchange = async (e) => {
    const id = e.target.dataset.qty;
    if (id) { await act(() => api(`/cart/items/${id}`, { method: "PATCH", json: { quantity: Number(e.target.value) } })); reload(); }
  };
  main.querySelector("table").onclick = async (e) => {
    const id = e.target.dataset.remove;
    if (id) { await act(() => api(`/cart/items/${id}`, { method: "DELETE" }), "Removed from cart"); reload(); }
  };
  main.querySelector("#clear").onclick = async () => {
    if (await confirmDialog({ title: "Clear your cart?", body: "All shirts will be removed from it.", confirm: "Clear cart" })) {
      await act(() => api("/cart", { method: "DELETE" }), "Cart cleared");
      reload();
    }
  };
  main.querySelector("#checkout").onsubmit = async (e) => {
    e.preventDefault();
    const button = e.target.querySelector("button");
    button.disabled = true; // a double click must not place two orders
    try {
      const order = await api("/checkout", { method: "POST", json: Object.fromEntries(new FormData(e.target)) });
      toast(`Order #${order.order_id} placed`);
      window.dispatchEvent(new Event("kitroom:changed"));
      location.hash = `#/orders/${order.order_id}`;
    } catch (error) {
      fail(error);
      button.disabled = false;
      if (error.code === "insufficient_stock") reload();
    }
  };
}

export async function ordersView(main) {
  const orders = await api("/orders");
  main.innerHTML = `<div class="wrap"><h1>Your orders</h1>${orders.length ? `<div class="table-wrap"><table>
    <thead><tr><th>Order</th><th>Placed</th><th class="num">Shirts</th><th class="num">Total</th><th>Status</th></tr></thead>
    <tbody>${orders.map((o) => `<tr><td><a href="#/orders/${o.order_id}">#${o.order_id}</a></td><td>${when(o.created_at)}</td>
      <td class="num">${o.item_count}</td><td class="num">${baht(o.total_amount)}</td><td>${tag(o.order_status)}</td></tr>`).join("")}</tbody>
    </table></div>` : emptyState("You have not ordered anything yet.", "#/", "Browse shirts")}</div>`;
}

const NEXT = { pending: ["shipped", "Mark as shipped"], shipped: ["delivered", "Mark as delivered"] };

export async function orderView(main, id) {
  const o = await api(`/orders/${id}`);
  const staff = state.user.role === "admin";
  const open = o.order_status === "pending";
  main.innerHTML = `<div class="wrap">
    <div class="row between"><h1>Order #${o.order_id}</h1>${tag(o.order_status)}</div>
    <p class="muted">Placed ${when(o.created_at)}${staff ? ` by ${esc(o.full_name)} (${esc(o.email)})` : ""}</p>
    <div class="table-wrap panel" style="padding:0"><table>
      <thead><tr><th></th><th>Shirt</th><th class="num">Quantity</th><th class="num">Unit price</th><th class="num">Line total</th>${open ? "<th></th>" : ""}</tr></thead>
      <tbody>${o.items.map((i) => `<tr><td><img class="thumb" src="${img(i.image_path)}" alt=""></td>
        <td><a href="#/shirt/${i.product_id}">${esc(i.title)}</a><br><span class="muted">${esc(i.season)}</span></td>
        <td class="num">${i.quantity}</td><td class="num">${baht(i.unit_price)}</td><td class="num">${baht(i.line_total)}</td>
        ${open ? `<td><div class="row">${staff ? `<button class="btn alt small" data-qty="${i.item_id}" data-current="${i.quantity}">Change quantity</button>` : ""}
          <button class="btn danger small" data-line="${i.item_id}">Remove</button></div></td>` : ""}</tr>`).join("")}</tbody>
      <tfoot><tr><td colspan="4"><strong>Total</strong></td><td class="num"><strong>${baht(o.total_amount)}</strong></td>${open ? "<td></td>" : ""}</tr></tfoot>
    </table></div>
    <div class="panel"><h2>Delivery address</h2><p>${esc(o.shipping_address)}</p>
      <div class="row">
        ${open ? `<button class="btn alt" id="address">Change address</button><button class="btn danger" id="cancel">Cancel order</button>` : ""}
        ${staff && open ? `<button class="btn alt" id="add-line">Add a shirt</button>` : ""}
        ${staff && NEXT[o.order_status] ? `<button class="btn" id="advance">${NEXT[o.order_status][1]}</button>` : ""}
        ${staff && o.order_status === "cancelled" ? `<button class="btn danger" id="delete">Delete order</button>` : ""}
      </div></div></div>`;

  const reload = () => orderView(main, id);
  const on = (sel, fn) => main.querySelector(sel)?.addEventListener("click", fn);
  on("#address", () => formDialog({ title: "Change delivery address", submit: "Save address",
    fields: [{ name: "shipping_address", label: "Delivery address", value: o.shipping_address, required: true }],
    onSubmit: async (json) => { await api(`/orders/${id}/address`, { method: "PATCH", json }); toast("Address saved"); reload(); } }));
  on("#cancel", async () => {
    if (await confirmDialog({ title: `Cancel order #${id}?`, body: "The shirts go back into stock and this cannot be undone.", confirm: "Cancel order" })) {
      await act(() => api(`/orders/${id}/cancel`, { method: "POST" }), "Order cancelled");
      reload();
    }
  });
  on("#advance", async () => {
    await act(() => api(`/orders/${id}/status`, { method: "PATCH", json: { status: NEXT[o.order_status][0] } }), "Status updated");
    reload();
  });
  on("#delete", async () => {
    if (await confirmDialog({ title: `Delete order #${id}?`, body: "The order and its lines are erased for good.", confirm: "Delete order" })) {
      if (await act(() => api(`/orders/${id}`, { method: "DELETE" }), "Order deleted")) location.hash = "#/staff/orders";
    }
  });
  on("#add-line", async () => {
    const { items } = await api("/products?per_page=100&sort=title");
    formDialog({ title: "Add a shirt to this order", submit: "Add shirt",
      fields: [{ name: "product_id", label: "Shirt", type: "select", options: items.map((p) => [p.product_id, `${p.title} ${p.season} (${p.stock_quantity} in stock)`]) },
        { name: "quantity", label: "Quantity", type: "number", value: 1, min: 1, required: true }],
      onSubmit: async (json) => { await api(`/orders/${id}/items`, { method: "POST", json }); toast("Shirt added"); reload(); } });
  });
  main.querySelector("table").onclick = async (e) => {
    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.line && await confirmDialog({ title: "Remove this shirt?", body: o.items.length === 1 ? "It is the last shirt, so the order will be cancelled." : "It goes back into stock and the total is updated.", confirm: "Remove shirt" })) {
      await act(() => api(`/orders/${id}/items/${t.dataset.line}`, { method: "DELETE" }), "Shirt removed");
      reload();
    }
    if (t.dataset.qty) formDialog({ title: "Change quantity", submit: "Save quantity",
      fields: [{ name: "quantity", label: "Quantity", type: "number", value: t.dataset.current, min: 1, required: true }],
      onSubmit: async (json) => { await api(`/orders/${id}/items/${t.dataset.qty}`, { method: "PATCH", json }); toast("Quantity saved"); reload(); } });
  };
}
