# Local workflow

## Ownership boundary

TechAPI owns versioned record files, the small standard-library validator, and
the Astro Pages site. TechEngine owns ingestion, the API service, schemas,
database models, dump generation, and heavy validation. Keep a schema change
coordinated across both repositories; do not modify the `TechEngine` submodule
pointer for an ordinary data cleanup.

## Game records

Games are individual JSON files under `data/game/<shard>/`. The shard is the
first two characters of `slug` (or the whole slug when it has one character).
The layout is intentionally independent of genre, platform, developer, and
import source so that imports stay stable and directories stay bounded.

Before an import:

1. Put each record in its slug shard.
2. Keep `slug`, `name`, `source_urls`, and `verified` present.
3. Run `python -m app.validate`.
4. Generate or verify the static dump through TechEngine when the API output
   needs to change.

## Generated files

- `site/public/v1/` is committed API output used by GitHub Pages; do not delete
  it as a local cleanup shortcut.
- `site/public/v1/history.json` and `verification.json` are build outputs and
  are ignored.
- `.claude/archive/` contains local historical work notes and is ignored.
- Python caches (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`) are disposable.
