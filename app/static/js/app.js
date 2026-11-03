import { api, esc, state, toast, act } from "./core.js";
import { accountView, loginView, registerView, notificationsView } from "./views/account.js";
import { adminView } from "./views/admin.js";
import { cartView, ordersView, orderView } from "./views/orders.js";
import { productView, shopView } from "./views/shop.js";

const main = document.getElementById("main");

const routes = [
  [/^\/?$/, shopView],
  [/^\/shirt\/(\d+)$/, productView],
  [/^\/cart$/, cartView, "user"],
  [/^\/orders$/, ordersView, "user"],
  [/^\/orders\/(\d+)$/, orderView, "user"],
  [/^\/alerts$/, notificationsView, "user"],
  [/^\/account$/, accountView, "user"],
  [/^\/sign-in$/, loginView],
  [/^\/join$/, registerView],
  [/^\/staff(?:\/([a-z]+))?$/, adminView, "admin"],
];

export async function refreshUser() {
  state.user = await api("/me").catch(() => null);
  renderHeader();
}

function renderHeader() {
  const u = state.user;
  const here = location.hash.slice(1) || "/";
  const link = (href, label, count) => `<a href="#${href}" class="${here === href || (href !== "/" && here.startsWith(href)) ? "on" : ""}">${label}${count ? `<span class="count">${count}</span>` : ""}</a>`;
  document.getElementById("site-header").innerHTML = `<div class="bar"><div class="bar-in">
    <a class="logo" href="#/">The Kit Room</a>
    <nav aria-label="Main">${link("/", "Shop")}
      ${u ? `${link("/cart", "Cart", u.cart_count)}${link("/orders", "Orders")}${link("/alerts", "Alerts", u.unread)}${link("/account", esc(u.full_name.split(" ")[0]))}
             ${u.role === "admin" ? link("/staff", "Staff") : ""}
             <button id="sign-out">Sign out</button>`
          : `${link("/sign-in", "Sign in")}${link("/join", "Create account")}`}
    </nav></div></div>`;
  document.getElementById("sign-out")?.addEventListener("click", async () => {
    await act(() => api("/auth/logout", { method: "POST" }));
    await refreshUser();
    location.hash = "#/";
  });
}

export async function render() {
  const path = location.hash.slice(1) || "/";
  await refreshUser();
  for (const [pattern, view, access] of routes) {
    const match = path.split("?")[0].match(pattern);
    if (!match) continue;
    if (access && !state.user) { location.hash = "#/sign-in"; return; }
    if (access === "admin" && state.user.role !== "admin") { main.innerHTML = `<div class="wrap"><h1>This page is for staff accounts</h1></div>`; return; }
    try {
      await view(main, ...match.slice(1));
    } catch (error) {
      main.innerHTML = `<div class="wrap narrow"><h1>That page could not load</h1><p>${esc(error.message)}</p><a class="btn" href="#/">Back to the shop</a></div>`;
    }
    window.scrollTo(0, 0);
    return;
  }
  main.innerHTML = `<div class="wrap narrow"><h1>Nothing hangs here</h1><a class="btn" href="#/">Back to the shop</a></div>`;
}

window.addEventListener("hashchange", render);
window.addEventListener("kitroom:changed", refreshUser);
window.addEventListener("error", (e) => toast(e.message, true));
render();
