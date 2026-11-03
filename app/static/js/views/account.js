import { act, api, confirmDialog, emptyState, esc, fail, img, state, stars, toast, when } from "../core.js";

export function loginView(main) {
  main.innerHTML = `<div class="wrap narrow"><h1>Sign in</h1><form class="panel" id="f">
    <label>Email<input type="email" name="email" required autocomplete="email"></label>
    <label>Password<input type="password" name="password" required autocomplete="current-password"></label>
    <button class="btn">Sign in</button></form>
    <p>New here? <a href="#/join">Create an account</a></p></div>`;
  main.querySelector("#f").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("/auth/login", { method: "POST", json: Object.fromEntries(new FormData(e.target)) });
      location.hash = "#/";
    } catch (error) { fail(error); }
  };
}

export function registerView(main) {
  main.innerHTML = `<div class="wrap narrow"><h1>Create an account</h1><form class="panel" id="f">
    <label>Full name<input name="full_name" required autocomplete="name"></label>
    <label>Email<input type="email" name="email" required autocomplete="email"></label>
    <label>Password<span class="hint">At least 8 characters</span><input type="password" name="password" required minlength="8" autocomplete="new-password"></label>
    <button class="btn">Create account</button></form>
    <p>Already have one? <a href="#/sign-in">Sign in</a></p></div>`;
  main.querySelector("#f").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("/auth/register", { method: "POST", json: Object.fromEntries(new FormData(e.target)) });
      toast("Account created");
      location.hash = "#/";
    } catch (error) { fail(error); }
  };
}

export async function notificationsView(main) {
  const notes = await api("/notifications");
  main.innerHTML = `<div class="wrap narrow"><div class="row between"><h1>Alerts</h1>
    ${notes.some((n) => !n.isRead) ? `<button class="btn alt" id="all">Mark all as read</button>` : ""}</div>
    ${notes.length ? notes.map((n) => `<article class="note ${n.isRead ? "" : "unread"}">
      <div><strong>${esc(n.title)}</strong><p>${esc(n.message)}</p><span class="muted">${when(n.sentAt)}</span></div>
      <div class="row">${n.isRead ? "" : `<button class="btn alt small" data-read="${n._id}">Mark as read</button>`}
      <button class="btn danger small" data-del="${n._id}">Dismiss</button></div></article>`).join("")
      : emptyState("No alerts. Order updates will show up here.")}</div>`;
  const reload = () => notificationsView(main);
  main.querySelector("#all")?.addEventListener("click", async () => {
    await act(() => api("/notifications/read-all", { method: "POST" }));
    reload();
  });
  main.querySelector(".wrap").onclick = async (e) => {
    const t = e.target.closest("button");
    if (t?.dataset.read) { await act(() => api(`/notifications/${t.dataset.read}`, { method: "PATCH", json: { isRead: true } })); reload(); }
    if (t?.dataset.del) { await act(() => api(`/notifications/${t.dataset.del}`, { method: "DELETE" }), "Alert dismissed"); reload(); }
  };
}

export async function accountView(main) {
  const u = state.user;
  const reviews = await api("/me/reviews");
  main.innerHTML = `<div class="wrap narrow"><h1>Your account</h1>
    <section class="panel"><div class="row" style="margin-bottom:16px">
      ${u.avatar_path ? `<img class="avatar" src="${img(u.avatar_path)}" alt="Your photo">` : `<div class="avatar" aria-hidden="true">${esc(u.full_name[0])}</div>`}
      <form id="avatar" class="row"><label style="margin:0">Profile photo<input type="file" name="avatar" accept="image/*" required></label>
      <button class="btn alt" style="align-self:end">Upload photo</button></form></div>
      <p class="muted">Member since ${when(u.created_at)}</p>
      <form id="profile"><label>Full name<input name="full_name" required value="${esc(u.full_name)}"></label>
      <label>Email<input type="email" name="email" required value="${esc(u.email)}"></label>
      <button class="btn">Save profile</button></form></section>
    <form class="panel" id="password"><h2>Change password</h2>
      <label>Current password<input type="password" name="current_password" required autocomplete="current-password"></label>
      <label>New password<span class="hint">At least 8 characters</span><input type="password" name="new_password" required minlength="8" autocomplete="new-password"></label>
      <button class="btn">Change password</button></form>
    <section class="panel"><h2>Your reviews</h2>${reviews.length ? reviews.map((r) => `<article class="review">
      <a href="#/shirt/${r.productId}">${esc(r.productTitle)}</a> ${stars(r.rating)}<p>${esc(r.comment)}</p></article>`).join("")
      : `<p class="muted">Reviews you write will show up here.</p>`}</section>
    <section class="panel"><h2>Delete account</h2><p>This removes your profile, cart, reviews and alerts. Accounts with orders stay on record.</p>
      <button class="btn danger" id="delete">Delete my account</button></section></div>`;

  main.querySelector("#profile").onsubmit = async (e) => {
    e.preventDefault();
    await act(() => api("/me", { method: "PATCH", json: Object.fromEntries(new FormData(e.target)) }), "Profile saved");
  };
  main.querySelector("#avatar").onsubmit = async (e) => {
    e.preventDefault();
    if (await act(() => api("/me/avatar", { method: "POST", form: new FormData(e.target) }), "Photo uploaded")) accountView(main).catch(fail);
  };
  main.querySelector("#password").onsubmit = async (e) => {
    e.preventDefault();
    if (await act(() => api("/me/password", { method: "PUT", json: Object.fromEntries(new FormData(e.target)) }), "Password changed")) e.target.reset();
  };
  main.querySelector("#delete").onclick = async () => {
    if (await confirmDialog({ title: "Delete your account?", body: "This cannot be undone.", confirm: "Delete my account" })) {
      if (await act(() => api("/me", { method: "DELETE" }), "Account deleted")) location.hash = "#/";
    }
  };
}

