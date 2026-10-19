"use strict";

const $ = (id) => document.getElementById(id);
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
  },
};

let config = { access_code_required: false, languages: ["English"] };
let current = null; // the label currently shown
let meds = store.get("meds", []);

// ---------- API ----------

async function api(path, body) {
  const headers = { "Content-Type": "application/json" };
  const code = store.get("accessCode", "");
  if (code) headers["X-Access-Code"] = code;
  const res = await fetch(path, body ? { method: "POST", headers, body: JSON.stringify(body) } : { headers });
  if (res.status === 401 && config.access_code_required) {
    await askAccessCode();
    return api(path, body);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong. Try again.");
  return data;
}

function askAccessCode() {
  return new Promise((resolve) => {
    const dialog = $("access");
    $("access-code").value = "";
    dialog.showModal();
    $("access-form").onsubmit = () => {
      store.set("accessCode", $("access-code").value.trim());
      resolve();
    };
  });
}

// ---------- UI helpers ----------

function setStatus(message, kind = "") {
  const el = $("status");
  el.hidden = !message;
  el.textContent = message || "";
  el.className = "status " + kind;
}

function renderMarkdown(el, markdown) {
  el.innerHTML = DOMPurify.sanitize(marked.parse(markdown));
}

function language() {
  return $("language").value;
}

// ---------- Look up and explain ----------

async function lookUp(name) {
  name = name.trim();
  if (!name) return;
  $("query").value = name;
  $("result").hidden = true;
  setStatus(`Finding the FDA label for ${name}…`, "loading");
  try {
    current = await api(`/api/label?name=${encodeURIComponent(name)}`);
    current.query = name;
  } catch (err) {
    setStatus(err.message, "error");
    return;
  }
  showLabel(current);
  await explain();
}

function showLabel(info) {
  $("drug-name").textContent = info.display_name;
  $("drug-meta").textContent = [info.generic_name, info.manufacturer].filter(Boolean).join(" · ");
  const boxed = info.sections["Boxed warning"];
  $("boxed").hidden = !boxed;
  $("boxed").innerHTML = boxed ? "<strong>Boxed warning: the FDA's strongest warning</strong>" : "";
  if (boxed) $("boxed").append(boxed);

  const official = $("official");
  official.replaceChildren();
  for (const [title, text] of Object.entries(info.sections)) {
    const h = document.createElement("h4");
    h.textContent = title;
    const p = document.createElement("p");
    p.textContent = text;
    official.append(h, p);
  }
  $("explanation").replaceChildren();
  updateAddButton();
  $("result").hidden = false;
}

async function explain() {
  if (!current) return;
  setStatus("Explaining the label in plain language…", "loading");
  try {
    const { explanation } = await api("/api/explain", { name: current.query, language: language() });
    renderMarkdown($("explanation"), explanation);
    setStatus("");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

// ---------- Photo ----------

async function shrinkPhoto(file) {
  // Resize to at most 1600px and re-encode as JPEG. This also converts iPhone HEIC photos.
  const img = await new Promise((resolve, reject) => {
    const i = new Image();
    i.onload = () => resolve(i);
    i.onerror = () => reject(new Error("That photo couldn't be opened. Try a JPG or PNG."));
    i.src = URL.createObjectURL(file);
  });
  const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * scale);
  canvas.height = Math.round(img.naturalHeight * scale);
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  URL.revokeObjectURL(img.src);
  return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
}

async function readPhoto(file) {
  if (!file) return;
  $("result").hidden = true;
  setStatus("Reading the packaging…", "loading");
  try {
    const image = await shrinkPhoto(file);
    const found = await api("/api/photo", { image, media_type: "image/jpeg" });
    await lookUp(found.name || found.active_ingredient);
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    $("photo").value = "";
  }
}

// ---------- My medicines ----------

function updateAddButton() {
  const inList = current && meds.some((m) => m.toLowerCase() === current.query.toLowerCase());
  $("add-med").textContent = inList ? "✓ In my medicines" : "Add to my medicines";
  $("add-med").disabled = Boolean(inList);
}

function renderMeds() {
  const list = $("meds-list");
  list.replaceChildren();
  for (const med of meds) {
    const li = document.createElement("li");
    const name = document.createElement("button");
    name.className = "name";
    name.textContent = med;
    name.onclick = () => { lookUp(med); window.scrollTo({ top: 0, behavior: "smooth" }); };
    const remove = document.createElement("button");
    remove.className = "btn";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${med}`);
    remove.onclick = () => {
      meds = meds.filter((m) => m !== med);
      store.set("meds", meds);
      renderMeds();
      updateAddButton();
    };
    li.append(name, remove);
    list.append(li);
  }
  $("meds-count").textContent = meds.length;
  $("meds-empty").hidden = meds.length > 0;
  $("check").hidden = meds.length < 2;
  $("interactions").hidden = true;
}

async function checkTogether() {
  const out = $("interactions");
  const button = $("check");
  button.disabled = true;
  out.hidden = false;
  out.textContent = "Comparing the labels…";
  try {
    const { result } = await api("/api/interactions", { names: meds, language: language() });
    renderMarkdown(out, result);
  } catch (err) {
    out.textContent = err.message;
  } finally {
    button.disabled = false;
  }
}

// ---------- Start ----------

async function start() {
  try { config = await api("/api/config"); } catch { /* keep defaults */ }
  const select = $("language");
  const saved = store.get("language", "English");
  for (const lang of ["English", ...config.languages.filter((l) => l !== "English")]) {
    select.add(new Option(lang, lang, false, lang === saved));
  }
  select.onchange = () => { store.set("language", language()); if (current) explain(); };

  $("search").onsubmit = (e) => { e.preventDefault(); lookUp($("query").value); };
  $("photo").onchange = (e) => readPhoto(e.target.files[0]);
  $("add-med").onclick = () => {
    if (!current) return;
    meds.push(current.query);
    store.set("meds", meds);
    renderMeds();
    updateAddButton();
  };
  $("check").onclick = checkTogether;
  renderMeds();
}

start();
