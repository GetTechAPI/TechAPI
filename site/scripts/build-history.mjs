// Precompute the dataset growth timeline from git history at build time.
//
// The homepage History section used to call the GitHub API live and could only
// show the last ~7 commits (per_page=8 + slice(7)), so older syncs were invisible
// and the unauthenticated API rate limit (60/h) made it fragile. Instead we walk
// the full git history of `site/public/v1/index.json` once during the deploy build
// and emit `site/public/v1/history.json` — a single static file the page reads.
//
// Build-only artifact (gitignored): regenerated on every Pages deploy, so it is
// always complete and never churns data PRs. Requires a full-depth checkout
// (fetch-depth: 0) to see old commits; degrades to an empty timeline otherwise.

import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SITE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(SITE_DIR, "..");
const TRACKED = "site/public/v1/index.json";
const OUT = resolve(SITE_DIR, "public/v1/history.json");
const REPO_URL = "https://github.com/GetTechAPI/TechAPI";

// Categories we sum into the record total (matches the public dump manifest).
const ORDER = ["smartphones", "tablets", "watches", "pdas", "socs", "gpus", "cpus", "brands"];
// Keep the chart legible if the history ever grows large: downsample to at most
// MAX points, always preserving the first (baseline) and last (latest) commits.
const MAX = 40;

function git(args) {
  return execFileSync("git", ["-C", REPO_ROOT, ...args], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
}

function countsOf(manifest) {
  const counts = {};
  let total = 0;
  for (const key of ORDER) {
    const n = manifest?.collections?.[key]?.count;
    if (typeof n === "number") {
      counts[key] = n;
      total += n;
    }
  }
  return { counts, total };
}

function downsample(points) {
  if (points.length <= MAX) return points;
  const step = (points.length - 1) / (MAX - 1);
  const picked = [];
  const seen = new Set();
  for (let i = 0; i < MAX; i++) {
    const idx = Math.round(i * step);
    if (!seen.has(idx)) {
      seen.add(idx);
      picked.push(points[idx]);
    }
  }
  return picked;
}

function buildPoints() {
  // %H sha, %cI committer ISO date, %s subject — 0x1f-separated, one line/commit.
  const raw = git(["log", "--format=%H%x1f%cI%x1f%s", "--", TRACKED]).trim();
  if (!raw) return [];
  const commits = raw.split("\n").map((line) => {
    const [sha, date, ...rest] = line.split("\x1f");
    return { sha, date, title: rest.join("\x1f") };
  });
  // git log is newest-first; the timeline reads oldest-first.
  commits.reverse();

  const points = [];
  for (const c of commits) {
    let manifest;
    try {
      manifest = JSON.parse(git(["show", `${c.sha}:${TRACKED}`]));
    } catch {
      continue; // file absent/unparseable at this commit — skip it
    }
    const { counts, total } = countsOf(manifest);
    if (!total) continue;
    points.push({
      sha: c.sha.slice(0, 7),
      date: c.date,
      title: (c.title || "Dataset sync").trim(),
      url: `${REPO_URL}/commit/${c.sha}`,
      total,
      counts,
    });
  }
  return downsample(points);
}

function main() {
  let points = [];
  try {
    points = buildPoints();
  } catch (err) {
    console.warn(`[build-history] git history unavailable: ${err.message}`);
  }
  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(
    OUT,
    JSON.stringify({ generated_at: new Date().toISOString(), schema: 1, points }, null, 2),
  );
  console.log(`[build-history] wrote ${points.length} point(s) -> ${OUT}`);
}

main();
