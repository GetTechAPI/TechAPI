// Precompute the dataset growth timeline from git history at build time.
//
// The homepage History section used to call the GitHub API live and could only
// show the last ~7 commits (per_page=8 + slice(7)), so older syncs were invisible
// and the unauthenticated API rate limit (60/h) made it fragile. Instead we walk
// the full git history of `site/public/v1/index.json` once during the deploy build
// and emit `site/public/v1/history.json` — a single static file the page reads.
//
// The dump stopped being committed on 2026-10-29 (pages.yml generates it at
// deploy time), so index.json has no newer commits. Later points come from the
// commits that changed data/ instead, counting one JSON file per record, which
// is what the manifest counts.
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

// Categories we sum into the record total: every collection in the public dump
// manifest (v1/index.json). Old manifests that predate a collection just lack it.
const ORDER = [
  "smartphones", "tablets", "laptops", "monitors", "watches", "pdas", "socs", "gpus", "cpus",
  "brands", "software", "websites", "device-catalog",
];
// The data/ folder behind each of those collections.
const DATA_DIR = {
  smartphones: "smartphone", tablets: "tablet", laptops: "laptop", monitors: "monitor",
  watches: "watch", pdas: "pda", socs: "soc", gpus: "gpu", cpus: "cpu", brands: "brand",
  software: "software", websites: "website", "device-catalog": "device_catalog",
};
// Keep the chart legible if the history ever grows large: downsample to at most
// MAX points, always preserving the first (baseline) and last (latest) commits.
const MAX = 40;
// Data commits counted after the last committed manifest (each one lists the
// whole data tree, so keep this small).
const DATA_MAX = 20;

function git(args) {
  // stderr is captured, not printed: a commit without the manifest (such as the
  // one that stopped committing it) is skipped, not a "fatal:" line in the log.
  return execFileSync("git", ["-C", REPO_ROOT, ...args], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    stdio: ["ignore", "pipe", "pipe"],
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

// Counts at one commit from its tree: data/<folder>/**/*.json, skipping files
// whose name starts with "_" (the same rule the deploy uses to check the dump).
function countsAt(sha) {
  const files = {};
  for (const path of git(["ls-tree", "-r", "--name-only", sha, "--", "data/"]).split("\n")) {
    const parts = path.split("/");
    const name = parts[parts.length - 1];
    if (parts.length < 3 || !name.endsWith(".json") || name.startsWith("_")) continue;
    files[parts[1]] = (files[parts[1]] || 0) + 1;
  }
  const counts = {};
  let total = 0;
  for (const key of ORDER) {
    const n = files[DATA_DIR[key]];
    if (n) {
      counts[key] = n;
      total += n;
    }
  }
  return { counts, total };
}

function downsample(points, max = MAX) {
  if (points.length <= max) return points;
  const step = (points.length - 1) / (max - 1);
  const picked = [];
  const seen = new Set();
  for (let i = 0; i < max; i++) {
    const idx = Math.round(i * step);
    if (!seen.has(idx)) {
      seen.add(idx);
      picked.push(points[idx]);
    }
  }
  return picked;
}

// %H sha, %cI committer ISO date, %s subject — 0x1f-separated, one line/commit.
function commitsOf(args) {
  const raw = git(["log", "--format=%H%x1f%cI%x1f%s", ...args]).trim();
  if (!raw) return [];
  const commits = raw.split("\n").map((line) => {
    const [sha, date, ...rest] = line.split("\x1f");
    return { sha, date, title: rest.join("\x1f") };
  });
  // git log is newest-first; the timeline reads oldest-first.
  return commits.reverse();
}

function pointOf(c, { counts, total }) {
  return {
    sha: c.sha.slice(0, 7),
    date: c.date,
    title: (c.title || "Dataset sync").trim(),
    url: `${REPO_URL}/commit/${c.sha}`,
    total,
    counts,
  };
}

function buildPoints() {
  const points = [];
  for (const c of commitsOf(["--", TRACKED])) {
    let manifest;
    try {
      manifest = JSON.parse(git(["show", `${c.sha}:${TRACKED}`]));
    } catch {
      continue; // file absent/unparseable at this commit — skip it
    }
    const tally = countsOf(manifest);
    if (!tally.total) continue;
    points.push(pointOf(c, tally));
  }

  // Since the last manifest: the commits on this branch's first-parent line
  // that changed data/ (releases on main, merged PRs on develop).
  const last = points[points.length - 1];
  const since = commitsOf(["--first-parent", "--", "data/"])
    .filter((c) => !last || Date.parse(c.date) > Date.parse(last.date));
  for (const c of downsample(since, DATA_MAX)) {
    const tally = countsAt(c.sha);
    if (tally.total) points.push(pointOf(c, tally));
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
