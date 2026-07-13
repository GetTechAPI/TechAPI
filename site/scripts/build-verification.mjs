// Expose the verification snapshot to the homepage at build time.
//
// The verification aggregate lives at data/_verify/status.json (kept in sync by
// TechEngine's verify-status workflow). The site only serves site/public/v1/**,
// so we copy a trimmed, render-ready view into site/public/v1/verification.json
// during the Pages build. Build-only + gitignored: always reflects the committed
// status.json, never hand-edited, no extra churn in data PRs.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SITE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(SITE_DIR, "..");
const SRC = resolve(REPO_ROOT, "data/_verify/status.json");
const OUT = resolve(SITE_DIR, "public/v1/verification.json");

function main() {
  let status = null;
  try {
    status = JSON.parse(readFileSync(SRC, "utf8"));
  } catch (err) {
    console.warn(`[build-verification] status.json unavailable: ${err.message}`);
  }

  const out = status
    ? {
        generated_at: status.generated_at || null,
        schema: 1,
        totals: status.totals || {},
        by_category: status.by_category || {},
      }
    : { generated_at: null, schema: 1, totals: {}, by_category: {} };

  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  const v = out.totals.verified_pct;
  console.log(`[build-verification] wrote ${OUT}${v != null ? ` (verified ${v}%)` : " (empty)"}`);
}

main();
