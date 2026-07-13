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
    { resource: "smartphones", slug: "galaxy-s26-ultra" },
    { resource: "socs", slug: "snapdragon-8-elite-gen-5" },
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
      if (k === "score" && v) {
        const ax = v.perf || v.multi || v.graphics || v.cpu || {};
        v = { overall: v.overall, tier: ax.tier, index: ax.index, source: ax.source };
      }
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
  const order = ["smartphones", "tablets", "watches", "pdas", "socs", "gpus", "cpus", "brands"];
  const label = {
    smartphones: "phones",
    tablets: "tablets",
    watches: "watches",
    pdas: "pdas",
    socs: "socs",
    gpus: "gpus",
    cpus: "cpus",
    brands: "brands",
  };
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

function countUp(node, target, opts = {}) {
  const { decimals = 0, suffix = "" } = opts;
  const dur = 1100, t0 = performance.now();
  (function tick(t) {
    const p = Math.min(1, (t - t0) / dur);
    const v = target * (1 - Math.pow(1 - p, 3));
    node.textContent = (decimals ? v.toFixed(decimals) : Math.round(v).toLocaleString()) + suffix;
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

  const order = ["smartphones", "tablets", "watches", "pdas", "socs", "gpus", "cpus", "brands"];
  const label = {
    smartphones: "Phones",
    tablets: "Tablets",
    watches: "Watches",
    pdas: "PDAs",
    socs: "SoCs",
    gpus: "GPUs",
    cpus: "CPUs",
    brands: "Brands",
  };
  const shortLabel = {
    smartphones: "phones",
    tablets: "tablets",
    watches: "watches",
    pdas: "pdas",
    socs: "socs",
    gpus: "gpus",
    cpus: "cpus",
    brands: "brands",
  };
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
      .filter((row) => row.delta !== 0)
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
      .slice(0, 3);
  }

  function formatDelta(delta, baseline = false) {
    if (baseline) return "baseline";
    if (delta > 0) return "+" + delta.toLocaleString();
    if (delta < 0) return delta.toLocaleString();
    return "no change";
  }

  // Most dump commits share one boilerplate title ("chore(site): refresh public
  // dump for X import"). The timeline is about growth, not commit messages, so we
  // strip the conventional-commit prefix and the dump-refresh boilerplate and keep
  // only the distinctive bit (e.g. "GSMArena Kaggle"), or "" when there is none.
  function shortTitle(raw) {
    let t = String(raw || "").trim();
    if (/^revert\b/i.test(t)) return "reverted";
    t = t.replace(/^[a-z]+(\([^)]*\))?:\s*/i, "");           // drop "chore(site): "
    const m = t.match(/\bdump\s+(?:for|after)\s+(.+?)(?:\s+imports?)?\s*$/i);
    if (m) return m[1].trim();
    if (/\b(refresh|regenerate|update)\b.*\bdump\b/i.test(t)) return ""; // pure boilerplate
    return t;                                                // genuinely distinctive
  }

  function renderHistory(points) {
    if (!points.length) throw new Error("empty history");
    const maxTotal = Math.max(...points.map((point) => point.total));
    const minTotal = Math.min(...points.map((point) => point.total));
    const range = Math.max(1, maxTotal - minTotal);
    // Growth curve: every sync as a point on an area chart scaled to the panel
    // width, so the whole timeline fits with nothing clipped or scrolled.
    const VW = 1000, VH = 150, PAD = 6;
    const xs = (i) => PAD + (points.length < 2 ? 0 : (i / (points.length - 1)) * (VW - 2 * PAD));
    const ys = (t) => VH - PAD - ((t - minTotal) / range) * (VH - 2 * PAD);
    const line = points.map((p, i) => `${i ? "L" : "M"}${xs(i).toFixed(1)} ${ys(p.total).toFixed(1)}`).join(" ");
    const area = `${line} L${xs(points.length - 1).toFixed(1)} ${VH} L${xs(0).toFixed(1)} ${VH} Z`;
    chartEl.innerHTML = `<svg class="history-svg" viewBox="0 0 ${VW} ${VH}" preserveAspectRatio="none" aria-label="Dataset growth curve">
        <defs><linearGradient id="histfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity=".34"></stop>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"></stop>
        </linearGradient></defs>
        <path d="${area}" fill="url(#histfill)"></path>
        <path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"></path>
      </svg>`;

    // Show every sync (newest first), growth-first. The list scrolls (CSS
    // max-height) so the full history stays reachable without a giant section.
    listEl.innerHTML = points.slice().reverse().map((point) => {
      const changes = point.changes.length
        ? point.changes.map((row) => `${shortLabel[row.key]} ${formatDelta(row.delta)}`).join(", ")
        : (point.baseline ? "baseline snapshot" : `total ${formatDelta(point.delta)}`);
      const tag = shortTitle(point.title);
      const delta = point.baseline ? "baseline" : formatDelta(point.delta);
      return `<li><span class="history-dot"></span><span class="history-item">
        <a class="history-head" href="${esc(point.url)}" target="_blank" rel="noopener">
          <span class="history-when">${esc(point.when)}</span>
          <b class="history-recs">${point.total.toLocaleString()}</b>
          <span class="history-delta${point.delta < 0 ? " is-negative" : ""}">${esc(delta)}</span>
        </a>
        <small>${esc(changes)}${tag ? ` · ${esc(tag)}` : ""}</small>
      </span></li>`;
    }).join("");

    // Hover the curve: snap to the nearest sync and show its date + total + delta.
    const hover = document.createElement("div");
    hover.className = "history-hover";
    hover.hidden = true;
    hover.innerHTML = `<span class="hh-line"></span><span class="hh-dot"></span><div class="hh-tip"></div>`;
    chartEl.appendChild(hover);
    const hLine = hover.querySelector(".hh-line");
    const hDot = hover.querySelector(".hh-dot");
    const hTip = hover.querySelector(".hh-tip");

    function moveHover(clientX) {
      const rect = chartEl.getBoundingClientRect();
      if (!rect.width) return;
      const relX = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      const i = Math.round(relX * (points.length - 1));
      const p = points[i];
      const px = (xs(i) / VW) * rect.width;
      const py = (ys(p.total) / VH) * rect.height;
      hover.hidden = false;
      hLine.style.left = px + "px";
      hDot.style.left = px + "px";
      hDot.style.top = py + "px";
      const chg = p.changes && p.changes.length
        ? p.changes.map((row) => `${shortLabel[row.key]} ${formatDelta(row.delta)}`).join(", ")
        : "";
      hTip.innerHTML = `<b>${esc(p.when)}</b>` +
        `<span>${p.total.toLocaleString()} records</span>` +
        `<span class="hh-delta${p.delta < 0 ? " is-negative" : ""}">${p.baseline ? "baseline" : esc(formatDelta(p.delta))}</span>` +
        (chg ? `<span class="hh-chg">${esc(chg)}</span>` : "");
      const tipW = hTip.offsetWidth || 150;
      let tx = px + 14;
      if (tx + tipW > rect.width) tx = px - tipW - 14;
      hTip.style.left = Math.max(4, tx) + "px";
      hTip.style.top = Math.min(rect.height - (hTip.offsetHeight || 70) - 4, Math.max(4, py - 24)) + "px";
    }
    chartEl.onmousemove = (e) => moveHover(e.clientX);
    chartEl.onmouseleave = () => { hover.hidden = true; };
    chartEl.ontouchstart = chartEl.ontouchmove = (e) => {
      if (e.touches[0]) moveHover(e.touches[0].clientX);
    };
  }

  const fmtWhen = (date) => date
    ? date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
    : "recent";
  const rowsFromCounts = (counts) => order
    .map((key) => ({ key, count: counts?.[key] }))
    .filter((row) => row.count != null);

  // Preferred path: a single prebuilt manifest (build-history.mjs) holding the
  // FULL dump timeline. No GitHub API, no per-commit fetches, no rate limit, and
  // old commits stay visible (the live API path only ever showed the last 7).
  async function pointsFromStaticHistory() {
    const data = await getJSON("v1/history.json");
    const points = (data.points || []).map((p) => {
      const date = p.date ? new Date(p.date) : null;
      return {
        sha: String(p.sha || "").slice(0, 7),
        dateValue: date ? date.getTime() : 0,
        when: fmtWhen(date),
        title: String(p.title || "Dataset sync").split("\n")[0],
        url: p.url || "https://github.com/GetTechAPI/TechAPI",
        rows: rowsFromCounts(p.counts),
        total: p.total != null ? p.total : rowsFromCounts(p.counts).reduce((s, r) => s + r.count, 0),
      };
    }).filter((p) => p.total > 0);
    return points.sort((a, b) => a.dateValue - b.dateValue);
  }

  // Fallback (e.g. local `astro dev` with no prebuilt history.json): the old live
  // GitHub API replay, capped at the most recent commits.
  async function pointsFromGitHubApi() {
    const commitsUrl = `https://api.github.com/repos/GetTechAPI/TechAPI/commits?path=${encodeURIComponent(dumpPath)}&per_page=10`;
    const response = await fetch(commitsUrl);
    if (!response.ok) throw new Error(response.statusText);
    const commits = await response.json();
    const items = Array.isArray(commits) ? commits.slice(0, 10) : [];
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
        when: fmtWhen(date),
        title: (item.commit?.message || "Dataset sync").split("\n")[0],
        url: item.html_url || "https://github.com/GetTechAPI/TechAPI",
        rows: countRows(manifest),
        total: totalRecords(manifest),
      };
    }));
    return snapshots.filter(Boolean).sort((a, b) => a.dateValue - b.dateValue);
  }

  async function loadCommitHistory(currentManifest) {
    let points = await pointsFromStaticHistory().catch(() => null);
    if (!points || !points.length) points = await pointsFromGitHubApi();
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
      points[i].baseline = !prev;
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
   VERIFICATION — live band distribution + verified ratio
   (from v1/verification.json, built from data/_verify/status.json)
   ============================================================ */
(function verification() {
  const pctEl = document.getElementById("verify-pct");
  if (!pctEl) return;
  const bar = document.getElementById("verify-bar");
  const countEl = document.getElementById("verify-count");
  const updatedEl = document.getElementById("verify-updated");
  const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };

  getJSON("v1/verification.json").then((d) => {
    const t = d.totals || {};
    const total = t.records || 0;
    if (!total) throw new Error("empty snapshot");
    const pct = t.verified_pct != null ? t.verified_pct : (t.verified || 0) / total * 100;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        countUp(pctEl, pct, { decimals: 1, suffix: "%" });
        obs.disconnect();
      });
    }, { threshold: .4 });
    obs.observe(pctEl);
    pctEl.textContent = pct.toFixed(1) + "%";

    countEl.textContent = `${(t.verified || 0).toLocaleString()} / ${total.toLocaleString()}`;

    const g = t.green || 0, y = t.yellow || 0, r = t.red || 0;
    const sum = Math.max(1, g + y + r);
    const seg = bar.querySelectorAll(".vb");
    if (seg[0]) seg[0].style.width = (g / sum * 100).toFixed(2) + "%";
    if (seg[1]) seg[1].style.width = (y / sum * 100).toFixed(2) + "%";
    if (seg[2]) seg[2].style.width = (r / sum * 100).toFixed(2) + "%";
    setText("verify-green", g.toLocaleString());
    setText("verify-yellow", y.toLocaleString());
    setText("verify-red", r.toLocaleString());

    if (d.generated_at) {
      const dt = new Date(d.generated_at);
      if (!isNaN(dt)) updatedEl.textContent = "snapshot updated " +
        dt.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    }
  }).catch(() => {
    pctEl.textContent = "—";
    if (countEl) countEl.textContent = "snapshot unavailable";
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
  slugIn.value = (items[0] && items[0].slug) || "galaxy-s26-ultra";
  run("smartphones", slugIn.value);
});

/* ============================================================
   FEATURED DEVICES
   ============================================================ */

function bar(label, v) {
  const w = v == null ? 0 : Math.round(v);
  return `<div class="sb"><span class="sb-l">${label}</span>
    <span class="sb-track"><span class="sb-fill" data-w="${w}"></span></span>
    <span class="sb-v">${v == null ? "—" : v}</span></div>`;
}

// Per-category card shape: spec chips, score bars (label + value), subtitle, and the
// primary axis whose hybrid tier/era/source is surfaced as a badge + provenance line.
const withUnit = (v, suffix = "") => (v == null ? null : `${v}${suffix}`);
const CARD = {
  smartphones: {
    sub: (d) => d.soc?.name || "",
    specs: (d) => [withUnit(d.ram_gb, "GB"), withUnit(d.battery_mah, "mAh"),
      d.display?.size_inch ? `${d.display.size_inch}"` : null, withUnit(d.display?.refresh_hz, "Hz")],
    bars: (sc) => [["Perf", sc.performance], ["Cam", sc.camera], ["Batt", sc.battery], ["Disp", sc.display]],
    axis: (sc) => sc.perf,
  },
  cpus: {
    sub: (d) => d.architecture || d.segment || "",
    specs: (d) => [d.cores ? `${d.cores}C/${d.threads}T` : null, withUnit(d.boost_clock_ghz, "GHz"),
      withUnit(d.tdp_w, "W"), d.process_node],
    bars: (sc) => [["Single", sc.single?.index], ["Multi", sc.multi?.index]],
    axis: (sc) => sc.multi,
  },
  gpus: {
    sub: (d) => d.architecture || "",
    specs: (d) => [withUnit(d.memory_gb, "GB"), d.memory_type, withUnit(d.tdp_w, "W"), withUnit(d.boost_clock_mhz, "MHz")],
    bars: (sc) => [["Graphics", sc.graphics?.index]],
    axis: (sc) => sc.graphics,
  },
  socs: {
    sub: (d) => d.gpu_name || "",
    specs: (d) => [withUnit(d.process_nm, "nm"), d.gpu_name, withUnit(d.gpu_cores, " GPU"), withUnit(d.npu_tops, " TOPS")],
    bars: (sc) => [["CPU", sc.cpu?.index], ["System", sc.system?.index]],
    axis: (sc) => sc.cpu,
  },
};
const prettyBench = (s) => s ? s.replace(/_/g, " ").replace(/\b(cpu|gpu|g3d|fp32|r23|r15|r10|r11 5|2024)\b/gi,
  (m) => m.toUpperCase()).replace(/\bcinebench\b/i, "Cinebench").replace(/\bgeekbench\b/i, "Geekbench")
  .replace(/\bpassmark\b/i, "PassMark").replace(/\bantutu score\b/i, "AnTuTu").replace(/\btimespy\b/i, "Time Spy") : "";

function deviceCard(d, category = "smartphones") {
  const cfg = CARD[category] || CARD.smartphones;
  const sc = d.score || {};
  const overall = sc.overall == null ? "—" : Math.round(sc.overall);
  const brandName = d.brand?.name || d.manufacturer?.name || "";
  const initial = (brandName || d.name || "?").charAt(0).toUpperCase();
  const specs = cfg.specs(d).filter(Boolean);
  const axis = cfg.axis(sc) || {};
  const tier = axis.tier ? `<span class="tier tier-${esc(axis.tier)}">${esc(axis.tier)}</span>` : "";
  const era = axis.era ? `<span class="chip chip-era">${esc(axis.era)}</span>` : "";
  const src = axis.source ? `<div class="card-src">via ${esc(prettyBench(axis.source))}</div>` : "";
  const el = document.createElement("article");
  el.className = "card"; el.dataset.slug = d.slug;
  el.innerHTML = `
    <div class="card-top">
      <div class="thumb"><span class="thumb-fallback">${esc(initial)}</span></div>
      <div class="card-id">
        <div class="card-brand">${esc(brandName)}</div>
        <div class="card-name">${esc(d.name)}</div>
        <div class="card-soc">${esc(cfg.sub(d))}</div>
      </div>
      <div class="ring" style="--p:${sc.overall || 0}"><b>${overall}</b><i>score</i></div>
    </div>
    <div class="chips">${tier}${era}${specs.map((s) => `<span class="chip">${esc(s)}</span>`).join("")}</div>
    <div class="bars">${cfg.bars(sc).map(([l, v]) => bar(l, v)).join("")}</div>${src}`;
  if (d.image_url) {
    const img = new Image();
    img.src = d.image_url; img.alt = d.name; img.loading = "lazy"; img.className = "thumb-img";
    img.onload = () => el.querySelector(".thumb").appendChild(img);
  }
  el.addEventListener("click", () => {
    resSel.value = category; slugIn.value = d.slug; run(category, d.slug);
    document.getElementById("playground").scrollIntoView({ behavior: "smooth" });
  });
  return el;
}

// A cross-category showcase so the scoring is visible across phones + CPU + GPU + SoC.
const FEATURED = [
  { cat: "smartphones", slug: "galaxy-s26-ultra" },
  { cat: "cpus", slug: "core-i9-14900k" },
  { cat: "gpus", slug: "geforce-rtx-5090" },
  { cat: "smartphones", slug: "iphone-17-pro-max" },
  { cat: "socs", slug: "snapdragon-8-elite" },
  { cat: "cpus", slug: "ryzen-9-7950x" },
];
(async function featured() {
  const cards = document.getElementById("cards");
  if (!cards) return;
  try {
    let picks = await Promise.all(FEATURED.map((f) =>
      getJSON(`v1/${f.cat}/${f.slug}/index.json`).then((d) => ({ d, cat: f.cat })).catch(() => null)));
    picks = picks.filter(Boolean);
    if (!picks.length) {  // fallback: first few phones if the curated slugs are absent
      const items = await loadList("smartphones");
      const details = await Promise.all(items.slice(0, 6).map((it) =>
        getJSON(`v1/smartphones/${it.slug}/index.json`).then((d) => ({ d, cat: "smartphones" })).catch(() => null)));
      picks = details.filter(Boolean);
    }
    cards.innerHTML = "";
    picks.forEach(({ d, cat }) => cards.appendChild(deviceCard(d, cat)));
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
