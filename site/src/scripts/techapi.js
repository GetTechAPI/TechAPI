// TechAPI — homepage interactions (Astro client script)
// Real static-JSON fetch against import.meta.env.BASE_URL (static JSON dump).
const raw = import.meta.env.BASE_URL;
const base = raw.endsWith("/") ? raw : raw + "/";
const absUrl = (path) => new URL(path.replace(/^\//, ""), location.origin + base).href;
const esc = (s) => String(s)
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");

/* ---- theme: follow OS preference until the user picks one (persisted) ---- */
const root = document.documentElement;
const mqLight = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
// initial theme — saved choice wins, otherwise the OS preference.
// (also applied pre-paint by the inline <head> script to avoid a flash)
if (!localStorage.getItem("techapi-theme")) {
  root.setAttribute("data-theme", mqLight && mqLight.matches ? "light" : "dark");
}
document.getElementById("theme-toggle")?.addEventListener("click", () => {
  const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
  root.setAttribute("data-theme", next);
  localStorage.setItem("techapi-theme", next);
});
// live-follow OS changes while the user hasn't made an explicit choice
mqLight?.addEventListener?.("change", (e) => {
  if (!localStorage.getItem("techapi-theme")) {
    root.setAttribute("data-theme", e.matches ? "light" : "dark");
  }
});

/* ---- JSON syntax highlight ---- */
function highlightJSON(obj) {
  const json = esc(JSON.stringify(obj, null, 2));
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (m) => {
      let cls = "j-num";
      if (/^"/.test(m)) cls = /:$/.test(m) ? "j-key" : "j-str";
      else if (/true|false/.test(m)) cls = "j-bool";
      else if (/null/.test(m)) cls = "j-null";
      return `<span class="${cls}">${m}</span>`;
    }
  ).replace(/([{}\[\],])/g, '<span class="j-punc">$1</span>');
}

async function getJSON(path) {
  const r = await fetch(base + path);
  if (!r.ok) throw new Error(r.status + " " + r.statusText);
  return r.json();
}

const listCache = {};
async function loadList(resource) {
  if (!listCache[resource]) {
    const data = await getJSON(`v1/${resource}/index.json`);
    listCache[resource] = data.results || [];
  }
  return listCache[resource];
}

/* ============================================================
   HERO terminal — cycles real requests, streams the response
   ============================================================ */
(function heroTerminal() {
  const cmdEl = document.getElementById("term-cmd");
  const statusEl = document.getElementById("term-status");
  const respEl = document.getElementById("term-resp");
  if (!cmdEl) return;

  const DEMOS = [
    { resource: "smartphones", slug: "galaxy-s25-ultra" },
    { resource: "socs", slug: "snapdragon-8-elite" },
    { resource: "gpus", slug: "geforce-rtx-5090" },
  ];
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let di = 0, timers = [];
  const wait = (fn, ms) => timers.push(setTimeout(fn, ms));

  function slim(obj) {
    // trim a detail response to a compact, readable subset for the terminal
    const keep = ["slug", "name", "brand", "soc", "manufacturer", "ram_gb", "battery_mah",
      "vram_gb", "tdp_w", "cores", "process_nm", "architecture", "display", "score"];
    const out = {};
    for (const k of keep) {
      if (obj[k] == null) continue;
      let v = obj[k];
      if (v && typeof v === "object" && v.name) v = v.name;       // {name,slug} → name
      if (k === "display" && v) v = { size_inch: v.size_inch, refresh_hz: v.refresh_hz };
      if (k === "score" && v) v = { overall: v.overall, performance: v.performance, camera: v.camera, cpu: v.cpu, gpu: v.gpu };
      out[k] = v;
    }
    return out;
  }

  async function runDemo() {
    timers.forEach(clearTimeout); timers = [];
    const demo = DEMOS[di];
    const full = `curl techapi.dev/v1/${demo.resource}/${demo.slug}`;
    statusEl.innerHTML = ""; respEl.innerHTML = "";

    let data;
    try { data = await getJSON(`v1/${demo.resource}/${demo.slug}/index.json`); }
    catch { data = null; }

    if (reduce) { typed(full); finish(data); return; }

    let i = 0;
    (function type() {
      i++;
      cmdEl.innerHTML = '<span class="p">$ </span>' + esc(full.slice(0, i)) + '<span class="typing-cursor"></span>';
      if (i < full.length) wait(type, 20 + Math.random() * 36);
      else { typed(full); wait(pending, 300); }
    })();

    function pending() {
      statusEl.innerHTML = '<span class="muted">● sending…</span>';
      wait(finish, 340);
    }
    function finish() {
      if (!data) {
        statusEl.innerHTML = '<span class="muted">● build the dataset to see live responses</span>';
        di = (di + 1) % DEMOS.length; wait(runDemo, 2600); return;
      }
      const ms = 28 + Math.round(Math.random() * 44);
      statusEl.innerHTML = '<span class="dot-ok">●</span> 200 OK <span class="muted">· ' + ms + 'ms · application/json</span>';
      stream(slim(data));
    }
    function typed(s) { cmdEl.innerHTML = '<span class="p">$ </span>' + esc(s); }
    function stream(body) {
      const lines = highlightJSON(body).split("\n");
      let k = 0;
      (function next() {
        respEl.innerHTML = lines.slice(0, ++k).join("\n");
        if (k < lines.length) wait(next, 36);
        else { di = (di + 1) % DEMOS.length; wait(runDemo, 2800); }
      })();
    }
  }
  cmdEl.innerHTML = '<span class="p">$ </span><span class="typing-cursor"></span>';
  wait(runDemo, 700);
})();

/* ============================================================
   STATS count-up (from v1/index.json collection counts)
   ============================================================ */
(function stats() {
  const el = document.getElementById("stats");
  if (!el) return;
  const order = ["smartphones", "socs", "gpus", "cpus", "brands"];
  const label = { smartphones: "phones", socs: "socs", gpus: "gpus", cpus: "cpus", brands: "brands" };
  getJSON("v1/index.json").then((m) => {
    el.innerHTML = "";
    for (const k of order) {
      const col = m.collections?.[k];
      const total = col?.count;
      if (total == null) continue;
      // "scored / total" when the dump exposes a benchmarked count; else plain total.
      const scored = col.scored ?? col.benchmarked ?? col.with_scores ?? null;
      const num = scored == null ? total : scored;
      const den = scored == null ? "" : `<span class="den">/${total.toLocaleString()}</span>`;
      el.insertAdjacentHTML("beforeend",
        `<div class="stat"><div class="n"><span class="num" data-n="${num}">0</span>${den}</div><div class="l">${label[k]}</div></div>`);
    }
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        el.querySelectorAll(".num").forEach((n) => countUp(n, +n.dataset.n));
        obs.disconnect();
      });
    }, { threshold: .4 });
    obs.observe(el);
  }).catch(() => {
    el.innerHTML = '<div class="stat"><div class="n">—</div><div class="l">build data first</div></div>';
  });
})();

function countUp(node, target) {
  const dur = 1100, t0 = performance.now();
  (function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    node.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString();
    if (p < 1) requestAnimationFrame(tick);
  })(performance.now());
}

/* ============================================================
   HISTORY
   ============================================================ */
(function history() {
  const totalEl = document.getElementById("history-total");
  const countsEl = document.getElementById("history-counts");
  const chartEl = document.getElementById("history-chart");
  const listEl = document.getElementById("history-list");
  if (!totalEl || !countsEl || !chartEl || !listEl) return;

  const order = ["smartphones", "socs", "gpus", "cpus", "brands"];
  const label = { smartphones: "Phones", socs: "SoCs", gpus: "GPUs", cpus: "CPUs", brands: "Brands" };
  const shortLabel = { smartphones: "phones", socs: "socs", gpus: "gpus", cpus: "cpus", brands: "brands" };
  const dumpPath = "site/public/v1/index.json";
  const countRows = (manifest) => order
    .map((key) => ({ key, count: manifest.collections?.[key]?.count }))
    .filter((row) => row.count != null);
  const totalRecords = (manifest) => countRows(manifest).reduce((sum, row) => sum + row.count, 0);
  const sumByKey = (rows) => rows.reduce((out, row) => {
    out[row.key] = row.count;
    return out;
  }, {});

  function renderSnapshot(manifest) {
    const rows = countRows(manifest);
    const total = rows.reduce((sum, row) => sum + row.count, 0);
    totalEl.textContent = total.toLocaleString() + " records";
    countsEl.innerHTML = rows.map((row) =>
      `<div class="history-count"><span>${label[row.key]}</span><b>${row.count.toLocaleString()}</b></div>`
    ).join("");
  }

  function largestChanges(prevRows, nextRows) {
    if (!prevRows) return [];
    const prev = sumByKey(prevRows);
    return nextRows
      .map((row) => ({ key: row.key, delta: row.count - (prev[row.key] || 0) }))
      .filter((row) => row.delta > 0)
      .sort((a, b) => b.delta - a.delta)
      .slice(0, 2);
  }

  function renderHistory(points) {
    if (!points.length) throw new Error("empty history");
    const maxTotal = Math.max(...points.map((point) => point.total));
    const minTotal = Math.min(...points.map((point) => point.total));
    const range = Math.max(1, maxTotal - minTotal);
    chartEl.innerHTML = points.map((point) => {
      const pct = 18 + ((point.total - minTotal) / range) * 82;
      const deltaText = point.delta > 0 ? "+" + point.delta.toLocaleString() : "baseline";
      return `<a class="history-bar" href="${esc(point.url)}" target="_blank" rel="noopener" style="--h:${pct.toFixed(1)}%" title="${esc(point.title)}">
        <span class="history-bar-fill"></span>
        <span class="history-bar-total">${point.total.toLocaleString()}</span>
        <span class="history-bar-delta">${esc(deltaText)}</span>
      </a>`;
    }).join("");

    listEl.innerHTML = points.slice().reverse().map((point) => {
      const changes = point.changes.length
        ? point.changes.map((row) => `${shortLabel[row.key]} +${row.delta.toLocaleString()}`).join(", ")
        : (point.delta > 0 ? `total +${point.delta.toLocaleString()}` : "baseline snapshot");
      return `<li><span class="history-dot"></span><span>
        <a href="${esc(point.url)}" target="_blank" rel="noopener">${esc(point.title)}</a>
        <small>${esc(point.when)} - ${esc(point.sha)} - ${esc(changes)}</small>
      </span></li>`;
    }).join("");
  }

  async function loadCommitHistory(currentManifest) {
    const commitsUrl = `https://api.github.com/repos/GetTechAPI/TechAPI/commits?path=${encodeURIComponent(dumpPath)}&per_page=8`;
    const response = await fetch(commitsUrl);
    if (!response.ok) throw new Error(response.statusText);
    const commits = await response.json();
    const items = Array.isArray(commits) ? commits.slice(0, 7) : [];
    const snapshots = await Promise.all(items.map(async (item) => {
      const sha = String(item.sha || "");
      const rawUrl = `https://raw.githubusercontent.com/GetTechAPI/TechAPI/${sha}/${dumpPath}`;
      const raw = await fetch(rawUrl);
      if (!raw.ok) return null;
      const manifest = await raw.json();
      const date = item.commit?.committer?.date ? new Date(item.commit.committer.date) : null;
      return {
        sha: sha.slice(0, 7),
        dateValue: date ? date.getTime() : 0,
        when: date ? date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "recent",
        title: (item.commit?.message || "Dataset sync").split("\n")[0],
        url: item.html_url || "https://github.com/GetTechAPI/TechAPI",
        rows: countRows(manifest),
        total: totalRecords(manifest),
      };
    }));

    const points = snapshots.filter(Boolean).sort((a, b) => a.dateValue - b.dateValue);
    if (!points.length) throw new Error("empty history");

    const currentTotal = totalRecords(currentManifest);
    const latest = points[points.length - 1];
    if (latest.total !== currentTotal) {
      points.push({
        sha: "current",
        dateValue: Date.now(),
        when: "current",
        title: "Current published snapshot",
        url: base + "v1/index.json",
        rows: countRows(currentManifest),
        total: currentTotal,
      });
    }

    for (let i = 0; i < points.length; i++) {
      const prev = points[i - 1];
      points[i].delta = prev ? points[i].total - prev.total : 0;
      points[i].changes = largestChanges(prev?.rows, points[i].rows);
    }
    renderHistory(points);
  }

  getJSON("v1/index.json").then((manifest) => {
    renderSnapshot(manifest);
    return loadCommitHistory(manifest).catch(() => {
      chartEl.innerHTML = '<div class="history-empty">Growth chart unavailable</div>';
      listEl.innerHTML = '<li><span class="history-dot"></span><span>Current static dump is available; commit history could not be loaded.<small>GitHub API unavailable</small></span></li>';
    });
  }).catch(() => {
    totalEl.textContent = "sync unavailable";
    countsEl.innerHTML = '<div class="history-count"><span>Static dump</span><b>offline</b></div>';
    chartEl.innerHTML = '<div class="history-empty">Growth chart unavailable</div>';
    listEl.innerHTML = '<li><span class="history-dot"></span><span>Current static dump could not be loaded.<small>Build the public data first</small></span></li>';
  });
})();

/* ============================================================
   PLAYGROUND
   ============================================================ */
const resSel = document.getElementById("pg-resource");
const slugIn = document.getElementById("pg-slug");
const dataList = document.getElementById("pg-slugs");
const out = document.getElementById("pg-output");
const urlEl = document.getElementById("pg-url");
const statusEl = document.getElementById("pg-status");

async function populateSlugs(resource) {
  try {
    const items = await loadList(resource);
    dataList.innerHTML = items.map((it) => `<option value="${esc(it.slug)}">${esc(it.name)}</option>`).join("");
    return items;
  } catch { return []; }
}

async function run(resource, slug) {
  urlEl.textContent = `/v1/${resource}/${slug}`;
  statusEl.textContent = "···"; statusEl.className = "status pending";
  out.innerHTML = '<span class="j-null">Loading…</span>';
  const t0 = performance.now();
  try {
    const data = await getJSON(`v1/${resource}/${slug}/index.json`);
    statusEl.textContent = `200 OK · ${Math.max(1, Math.round(performance.now() - t0))}ms`;
    statusEl.className = "status ok";
    out.innerHTML = highlightJSON(data);
  } catch {
    statusEl.textContent = "404 Not Found"; statusEl.className = "status err";
    out.innerHTML = `<span class="j-null">No data for "${esc(slug)}". Pick a slug from the suggestions.</span>`;
  }
}

function send() { const s = slugIn.value.trim(); if (s) run(resSel.value, s); }
resSel?.addEventListener("change", async () => {
  const items = await populateSlugs(resSel.value);
  if (items.length) { slugIn.value = items[0].slug; send(); }
});
document.getElementById("pg-send")?.addEventListener("click", send);
slugIn?.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
document.getElementById("pg-random")?.addEventListener("click", async () => {
  const items = await loadList(resSel.value).catch(() => []);
  if (items.length) { slugIn.value = items[Math.floor(Math.random() * items.length)].slug; send(); }
});
document.getElementById("pg-copy")?.addEventListener("click", (e) => {
  navigator.clipboard?.writeText("curl " + absUrl(urlEl.textContent + "/index.json"));
  const b = e.currentTarget, p = b.textContent; b.textContent = "Copied ✓"; setTimeout(() => (b.textContent = p), 1200);
});
if (resSel) populateSlugs("smartphones").then((items) => {
  slugIn.value = (items[0] && items[0].slug) || "galaxy-s25-ultra";
  run("smartphones", slugIn.value);
});

/* ============================================================
   FEATURED DEVICES
   ============================================================ */
const PREFERRED = ["galaxy-s25-ultra", "iphone-16-pro-max", "pixel-9-pro",
  "oneplus-13", "xiaomi-15-ultra", "galaxy-z-fold-6"];

function bar(label, v) {
  const w = v == null ? 0 : Math.round(v);
  return `<div class="sb"><span class="sb-l">${label}</span>
    <span class="sb-track"><span class="sb-fill" data-w="${w}"></span></span>
    <span class="sb-v">${v == null ? "—" : v}</span></div>`;
}
function deviceCard(d) {
  const sc = d.score || {};
  const overall = sc.overall == null ? "—" : Math.round(sc.overall);
  const initial = (d.brand?.name || d.name || "?").charAt(0).toUpperCase();
  const specs = [
    d.ram_gb ? `${d.ram_gb}GB` : null,
    d.battery_mah ? `${d.battery_mah}mAh` : null,
    d.display?.size_inch ? `${d.display.size_inch}"` : null,
    d.display?.refresh_hz ? `${d.display.refresh_hz}Hz` : null,
  ].filter(Boolean);
  const el = document.createElement("article");
  el.className = "card"; el.dataset.slug = d.slug;
  el.innerHTML = `
    <div class="card-top">
      <div class="thumb"><span class="thumb-fallback">${esc(initial)}</span></div>
      <div class="card-id">
        <div class="card-brand">${esc(d.brand?.name || "")}</div>
        <div class="card-name">${esc(d.name)}</div>
        <div class="card-soc">${esc(d.soc?.name || "")}</div>
      </div>
      <div class="ring" style="--p:${sc.overall || 0}"><b>${overall}</b><i>score</i></div>
    </div>
    <div class="chips">${specs.map((s) => `<span class="chip">${esc(s)}</span>`).join("")}</div>
    <div class="bars">${bar("Perf", sc.performance)}${bar("Cam", sc.camera)}${bar("Batt", sc.battery)}${bar("Disp", sc.display)}</div>`;
  if (d.image_url) {
    const img = new Image();
    img.src = d.image_url; img.alt = d.name; img.loading = "lazy"; img.className = "thumb-img";
    img.onload = () => el.querySelector(".thumb").appendChild(img);
  }
  el.addEventListener("click", () => {
    resSel.value = "smartphones"; slugIn.value = d.slug; run("smartphones", d.slug);
    document.getElementById("playground").scrollIntoView({ behavior: "smooth" });
  });
  return el;
}

(async function featured() {
  const cards = document.getElementById("cards");
  if (!cards) return;
  try {
    const items = await loadList("smartphones");
    const have = new Set(items.map((i) => i.slug));
    let slugs = PREFERRED.filter((s) => have.has(s));
    for (const it of items) { if (slugs.length >= 6) break; if (!slugs.includes(it.slug)) slugs.push(it.slug); }
    const details = await Promise.all(slugs.slice(0, 6).map((s) =>
      getJSON(`v1/smartphones/${s}/index.json`).catch(() => null)));
    cards.innerHTML = "";
    details.filter(Boolean).forEach((d) => cards.appendChild(deviceCard(d)));
    if (!cards.children.length) cards.innerHTML = '<p class="muted">Build the dataset to see featured devices.</p>';
    const obs = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.querySelectorAll(".sb-fill").forEach((f) => { f.style.transform = `scaleX(${(+f.dataset.w) / 100})`; });
      obs.unobserve(e.target);
    }), { threshold: .3 });
    cards.querySelectorAll(".card").forEach((c) => obs.observe(c));
  } catch {
    cards.innerHTML = '<p class="muted">Build the dataset to see featured devices.</p>';
  }
})();

/* ---- reveal on scroll (with safety fallback) ---- */
const revEls = [...document.querySelectorAll("[data-reveal]")];
const rev = new IntersectionObserver((es) => es.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add("in"); rev.unobserve(e.target); }
}), { threshold: .12, rootMargin: "0px 0px -8% 0px" });
revEls.forEach((el) => rev.observe(el));
setTimeout(() => revEls.forEach((el) => el.classList.add("in")), 2500);
