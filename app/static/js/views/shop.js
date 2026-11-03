import { act, api, baht, confirmDialog, esc, formDialog, img, state, stars, toast, when, yearOf } from "../core.js";

function stockNote(p) {
  if (p.stock_quantity === 0) return `<span class="gone">Sold out</span>`;
  if (p.stock_quantity <= 3) return `<span class="low">${p.stock_quantity} left</span>`;
  return "";
}

const card = (p) => `<a class="kit" href="#/shirt/${p.product_id}">
  <div class="kit-panel c${p.product_id % 5}"><b aria-hidden="true">${yearOf(p.season)}</b>
    <img src="${img(p.image_path)}" alt="${esc(p.title)} shirt" loading="lazy"></div>
  <div class="kit-body"><strong>${esc(p.title)}</strong>
    <span class="kit-meta">${esc(p.season)}, ${esc(p.category_name)}</span>
    ${p.rating ? `<span>${stars(Math.round(p.rating.avg))} <span class="muted">(${p.rating.count})</span></span>` : ""}
    <div class="kit-foot"><span class="price">${baht(p.price)}</span>${stockNote(p)}</div></div></a>`;

export async function shopView(main) {
  const cats = await api("/categories");
  const filters = { q: "", category: "", sort: "newest", page: 1 };
  const rail = (await api("/products?per_page=6&sort=price_desc")).items;
  main.innerHTML = `<section class="hero"><div class="hero-in">
      <h1>Shirts that were there.</h1>
      <p>Original football shirts from the seasons people still talk about, checked, stocked and shipped from Bangkok.</p>
      <div class="rail">${rail.map((p) => `<a href="#/shirt/${p.product_id}" aria-label="${esc(p.title)}"><img src="${img(p.image_path)}" alt=""></a>`).join("")}</div>
    </div></section>
    <div class="wrap"><form class="filters" id="filters" role="search">
      <label class="grow">Search club, shirt or season<input name="q" type="search" placeholder="Milan, 1998"></label>
      <label>League<select name="category"><option value="">All leagues</option>
        ${cats.map((c) => `<option value="${c.category_id}">${esc(c.name)} (${c.product_count})</option>`).join("")}</select></label>
      <label>Sort by<select name="sort"><option value="newest">Newest in</option><option value="price_asc">Price, low to high</option>
        <option value="price_desc">Price, high to low</option><option value="title">Name</option></select></label>
    </form><div id="results"></div></div>`;

  const results = main.querySelector("#results");
  async function load() {
    const q = new URLSearchParams({ ...filters, per_page: 12 });
    const data = await api(`/products?${q}`);
    const pages = Math.ceil(data.total / data.per_page);
    results.innerHTML = data.items.length
      ? `<div class="grid">${data.items.map(card).join("")}</div>
         ${pages > 1 ? `<div class="row between" style="margin-top:22px">
           <button class="btn alt" data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>Previous page</button>
           <span>Page ${data.page} of ${pages}</span>
           <button class="btn alt" data-page="${data.page + 1}" ${data.page >= pages ? "disabled" : ""}>Next page</button></div>` : ""}`
      : `<div class="empty"><p>No shirts match that search. Try a club name or a year.</p></div>`;
  }
  results.onclick = (e) => {
    const b = e.target.closest("[data-page]");
    if (b) { filters.page = Number(b.dataset.page); load(); }
  };
  const form = main.querySelector("#filters");
  let timer;
  form.oninput = () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      Object.assign(filters, Object.fromEntries(new FormData(form)), { page: 1 });
      load();
    }, 200);
  };
  form.onsubmit = (e) => e.preventDefault();
  await load();
}

function reviewForm(existing, onSubmit) {
  const fields = [
    { name: "rating", label: "Rating", type: "select", value: existing?.rating ?? 5,
      options: [[5, "5, outstanding"], [4, "4, very good"], [3, "3, fine"], [2, "2, disappointing"], [1, "1, poor"]] },
    { name: "comment", label: "Your review", type: "textarea", required: true, value: existing?.comment },
    { name: "sizeFeedback", label: "How does it fit?", type: "select", value: existing?.sizeFeedback ?? "",
      options: [["", "Rather not say"], ["small", "Runs small"], ["true", "True to size"], ["large", "Runs large"]] },
  ];
  if (!existing) fields.push({ name: "photo", label: "Photo (optional)", type: "file", hint: "JPG, PNG or WEBP, up to 5 MB" });
  formDialog({ title: existing ? "Edit your review" : "Write a review", fields, multipart: !existing,
    submit: existing ? "Save review" : "Post review", onSubmit });
}

const FIT = { small: "Runs small", true: "True to size", large: "Runs large" };

export async function productView(main, id) {
  const [p, reviews] = await Promise.all([api(`/products/${id}`), api(`/products/${id}/reviews`)]);
  const me = state.user;
  const mine = me && reviews.items.find((r) => r.userId === me.user_id);
  main.innerHTML = `<div class="wrap">
    <div class="product">
      <div class="kit-panel c${p.product_id % 5}"><b aria-hidden="true">${yearOf(p.season)}</b><img src="${img(p.image_path)}" alt="${esc(p.title)} shirt"></div>
      <div>
        <h1>${esc(p.title)}</h1>
        <p class="muted">${esc(p.club)}, ${esc(p.season)}, ${esc(p.category_name)}</p>
        ${p.rating ? `<p>${stars(Math.round(p.rating.avg))} ${p.rating.avg} from ${p.rating.count} review${p.rating.count > 1 ? "s" : ""}</p>` : ""}
        <p>${esc(p.description)}</p>
        <p><span class="price">${baht(p.price)}</span> ${stockNote(p)}</p>
        ${p.status === "archived" ? `<p class="gone">No longer on sale</p>` : p.stock_quantity > 0 ? `
        <form id="buy" class="row"><label style="margin:0">Quantity<input class="qty" type="number" name="quantity" min="1" max="${p.stock_quantity}" value="1"></label>
          <button class="btn gold" style="align-self:end">Add to cart</button></form>` : ""}
      </div>
    </div>
    <section class="panel" style="margin-top:32px">
      <div class="row between"><h2>Reviews</h2>
        ${me ? (mine ? "" : `<button class="btn alt" id="write">Write a review</button>`) : `<a href="#/sign-in">Sign in to review</a>`}</div>
      ${reviews.items.length ? reviews.items.map((r) => `<article class="review">
        <strong>${esc(r.userName)}</strong> ${r.verifiedPurchase ? `<span class="tag delivered">Verified buyer</span>` : ""}
        ${r.sizeFeedback ? `<span class="tag">${FIT[r.sizeFeedback]}</span>` : ""}
        <div>${stars(r.rating)} <span class="muted">${when(r.createdAt)}${r.editedAt ? ", edited" : ""}</span></div>
        <p>${esc(r.comment)}</p>${r.photo ? `<img src="${img(r.photo)}" alt="Photo from ${esc(r.userName)}">` : ""}
        <div class="row">
          ${me ? `<button class="btn alt small" data-like="${r._id}">${r.likedBy?.includes(me.user_id) ? "Liked" : "Helpful"} (${r.likes})</button>` : `<span class="muted">${r.likes} found this helpful</span>`}
          ${me?.user_id === r.userId ? `<button class="btn alt small" data-edit="${r._id}">Edit</button>` : ""}
          ${me && (me.user_id === r.userId || me.role === "admin") ? `<button class="btn danger small" data-del="${r._id}">Delete</button>` : ""}
        </div></article>`).join("") : `<p class="muted">No reviews yet. Bought this shirt? Be the first to review it.</p>`}
    </section></div>`;

  const reload = () => productView(main, id);
  main.querySelector("#buy")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!me) { toast("Sign in to add shirts to your cart."); location.hash = "#/sign-in"; return; }
    await act(() => api("/cart/items", { method: "POST", json: {
      product_id: p.product_id, quantity: Number(new FormData(e.target).get("quantity")) } }), "Added to cart");
  });
  main.querySelector("#write")?.addEventListener("click", () => reviewForm(null, async (form) => {
    await api(`/products/${id}/reviews`, { method: "POST", form });
    toast("Review posted");
    reload();
  }));
  main.querySelector(".panel").onclick = async (e) => {
    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.like) { await act(() => api(`/reviews/${t.dataset.like}/like`, { method: "POST" })); reload(); }
    if (t.dataset.edit) reviewForm(reviews.items.find((r) => r._id === t.dataset.edit), async (json) => {
      await api(`/reviews/${t.dataset.edit}`, { method: "PUT", json });
      toast("Review saved");
      reload();
    });
    if (t.dataset.del && await confirmDialog({ title: "Delete this review?", body: "It will be removed from the shirt's page.", confirm: "Delete review" })) {
      await act(() => api(`/reviews/${t.dataset.del}`, { method: "DELETE" }), "Review deleted");
      reload();
    }
  };
}
