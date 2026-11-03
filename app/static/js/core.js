// Shared helpers: API calls, escaping, formatting, toasts, dialogs.
export const state = { user: null };

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export async function api(path, { method = "GET", json, form } = {}) {
  const headers = { "X-Requested-With": "KitRoom" };
  const options = { method, headers, credentials: "same-origin" };
  if (json !== undefined) { headers["Content-Type"] = "application/json"; options.body = JSON.stringify(json); }
  if (form) options.body = form;
  const response = await fetch(`/api${path}`, options);
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error || "The server did not respond. Check that it is running.");
    Object.assign(error, data, { status: response.status });
    throw error;
  }
  return data;
}

export const baht = (n) => `฿${Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
export const when = (d) => new Date(d).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
export const img = (path) => (path ? `/static/uploads/${esc(path)}` : "");
export const stars = (n) => `<span class="stars" aria-label="${n} out of 5">${"★".repeat(n)}${"☆".repeat(5 - n)}</span>`;
export const tag = (t) => `<span class="tag ${esc(t)}">${esc(t)}</span>`;
export const yearOf = (season) => `’${esc(String(season).split("-")[0].slice(-2))}`;

export function toast(message, bad = false) {
  const el = document.createElement("div");
  el.className = `toast${bad ? " bad" : ""}`;
  el.textContent = message;
  document.getElementById("toasts").append(el);
  setTimeout(() => el.remove(), bad ? 7000 : 3500);
}

export const fail = (error) => toast(error.message, true);

// Runs an action, reports its failure, and refreshes the header counters.
export async function act(fn, success) {
  try {
    const out = await fn();
    if (success) toast(success);
    window.dispatchEvent(new Event("kitroom:changed"));
    return out ?? true;
  } catch (error) { fail(error); return false; }
}

const modal = () => document.getElementById("modal");

function fieldHtml(f) {
  const v = f.value ?? "";
  const attrs = `name="${esc(f.name)}" ${f.required ? "required" : ""} ${f.min !== undefined ? `min="${f.min}"` : ""} ${f.step ? `step="${f.step}"` : ""}`;
  let control;
  if (f.type === "select") {
    control = `<select ${attrs}>${f.options.map(([val, label]) =>
      `<option value="${esc(val)}" ${String(val) === String(v) ? "selected" : ""}>${esc(label)}</option>`).join("")}</select>`;
  } else if (f.type === "textarea") {
    control = `<textarea ${attrs}>${esc(v)}</textarea>`;
  } else {
    control = `<input type="${f.type || "text"}" ${attrs} value="${f.type === "file" ? "" : esc(v)}" ${f.autocomplete ? `autocomplete="${f.autocomplete}"` : ""}>`;
  }
  return `<label>${esc(f.label)}${f.hint ? `<span class="hint">${esc(f.hint)}</span>` : ""}${control}</label>`;
}

export const fieldsHtml = (fields) => fields.map(fieldHtml).join("");

export function formDialog({ title, fields, submit, onSubmit, multipart = false }) {
  const d = modal();
  d.innerHTML = `<form class="dialog-in" method="dialog">
    <h2>${esc(title)}</h2>${fieldsHtml(fields)}
    <div class="row"><button class="btn" type="submit">${esc(submit)}</button>
    <button class="btn alt" type="button" data-close>Cancel</button></div></form>`;
  const form = d.querySelector("form");
  d.querySelector("[data-close]").onclick = () => d.close();
  form.onsubmit = async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    try {
      await onSubmit(multipart ? data : Object.fromEntries(data));
      d.close();
    } catch (error) { fail(error); }
  };
  d.showModal();
}

export function confirmDialog({ title, body, confirm, danger = true }) {
  return new Promise((resolve) => {
    const d = modal();
    d.innerHTML = `<div class="dialog-in"><h2>${esc(title)}</h2><p>${esc(body)}</p>
      <div class="row"><button class="btn ${danger ? "danger" : ""}" data-yes>${esc(confirm)}</button>
      <button class="btn alt" data-no>Keep it</button></div></div>`;
    const done = (value) => { d.close(); resolve(value); };
    d.querySelector("[data-yes]").onclick = () => done(true);
    d.querySelector("[data-no]").onclick = () => done(false);
    d.showModal();
  });
}

export function emptyState(text, href, label) {
  return `<div class="empty"><p>${esc(text)}</p>${href ? `<a class="btn" href="${href}">${esc(label)}</a>` : ""}</div>`;
}
