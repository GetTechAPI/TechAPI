# TechAPI — development guide & handoff

> Read this first. Full spec: [SPEC.md](SPEC.md). Static-dump design:
> [DATA_PIPELINE.md](DATA_PIPELINE.md).

## What this is

TechAPI — a free, open REST API for consumer-electronics specs (smartphones,
SoCs, GPUs, CPUs, brands). FastAPI + SQLModel. **This repo is
the public product: the API + a curated dataset + a static JSON dump.** It does
**not** contain data-collection/scraping tooling (that is maintained separately;
see "Data scope" below).

## Current status (Phase 0 MVP — DONE and verified)

- **Stack**: FastAPI, SQLModel, Pydantic v2, Python 3.12. DB defaults to SQLite
  (`DATABASE_URL`); Postgres 16 via `docker-compose.yml`.
- **Endpoints** (under `/v1`): `health`, `version`, `brands`(+`/{slug}` +`/{slug}/smartphones`),
  `socs`(+`/{slug}` +`/{slug}/smartphones`), `smartphones`(+`/{slug}` +`/{slug}/score`),
  `gpus`(+`/{slug}`), `cpus`(+`/{slug}`, `?segment=`). Docs at `/scalar` and `/docs`.
- **Formats**: list `{count,next,previous,results}` (§7.4); error
  `{error:{code,message,request_id,documentation_url}}` (§7.5); smartphone detail
  per SPEC appendix C (embeds brand+soc+manufacturer + computed `score`).
- **Tests**: `pytest` → passing, ~98% coverage. `ruff` + `mypy app scripts` clean.
- **NOT done**: cloud deploy (Railway/Fly need accounts) and public static hosting.
  Dockerfile + workflows written but not executed in the cloud.

### Curated dataset (validated, what the API serves) — 365 records
brand 19 · soc 72 · smartphone 184 · gpu 49 · cpu 41. **This is a curated subset,
NOT an exhaustive catalog of every device.** It is intentionally hand-verified;
breadth is expanded out-of-band (see "Data scope").

### Data scope (important)
This repo holds only **curated, validated** data and serves/dumps it. Bulk
collection/scraping and the pre-review candidate pool are **not part of this
repo** and are maintained through a separate pipeline. Local contributors working
in this Codespace: see `NOTES.local.md` (gitignored, not committed).

## Repo layout

```
app/                 FastAPI app
  main.py            entrypoint (CORS, request-id mw, error handlers, Scalar, routers)
  config.py          pydantic-settings (DATABASE_URL, etc.)
  database.py        engine + get_session (SQLite or Postgres)
  models/            SQLModel tables: brand, soc, smartphone, gpu, cpu
  schemas/           Pydantic response models + serializers.py (ORM→schema, URLs)
  services/scoring.py  open 0–100 scoring (§8); reference-based min-max (Phase 0)
  routers/           meta, brands, socs, smartphones, gpus, cpus
  errors.py          §7.5 error envelope + handlers
data/                CURATED SEED DATA — singular folder names, organised by brand:
  brand/<slug>.json
  soc/<manufacturer>/<slug>.json          e.g. soc/qualcomm/snapdragon-8-elite.json
  smartphone/<brand>/<slug>.json          e.g. smartphone/samsung/galaxy-s25.json
  gpu/<manufacturer>/<slug>.json
  cpu/<manufacturer>/<year>/<slug>.json   e.g. cpu/intel/2023/core-i9-14900k.json (CPU also split by year)
scripts/
  seed.py            data/ → DB (recurses brand subfolders; coerces ISO dates)
  validate.py        schema/range/FK/slug checks (run in CI on data changes)
  dump.py            DB → static JSON dump (replays API) → ./dump
tests/               unit/ + integration/ (conftest seeds a temp SQLite from data/)
docs/                SPEC.md, DATA_PIPELINE.md, DEVELOPMENT.md
.github/workflows/   test.yml, validate-data.yml, refresh-data.yml
```

> Note: **data folders are singular** (`data/soc/…`) but **API routes are plural**
> (`/v1/socs`). Intentional.

## How to run

```bash
pip install -e ".[dev]"          # deps already installed in this Codespace
python -m scripts.validate       # check curated data
python -m scripts.seed           # data/ → ./techapi.db (SQLite)
uvicorn app.main:app --reload    # serve; curl http://localhost:8000/v1/smartphones/galaxy-s25
pytest -q --cov=app              # tests (target >60%, currently ~98%)
ruff check app scripts tests && mypy app scripts
python -m scripts.dump           # generate ./dump/ static tree (gitignored)
```

## Key decisions / deviations from the original SPEC

- **CPU category added** (not in original §6) — `app/models/cpu.py`, `/v1/cpus`,
  recorded as **ADR-011** / **§6.7** in docs/SPEC.md (maintainer wants computer chips).
- **GPU activated** — model existed (§6.5); endpoints + data added.
- **Data restructured** to singular names + brand subfolders (maintainer request).
- **Static-dump pivot** — `scripts/dump.py` exports the API to a static JSON tree,
  refreshed by GitHub Actions (`refresh-data.yml`).
- **Scoring** is a Phase-0 reference-based approximation; Phase 1 → dataset-wide
  min-max (§8.4). Raw third-party benchmarks (Geekbench/AnTuTu/Cinebench/Time Spy)
  are stored as algorithm inputs but NOT exposed (ADR-006).

## Conventions (IMPORTANT)

- **Commits**: Conventional Commits (`feat(api): …`, `data: …`, `docs: …`).
  Keep commit messages clean — no tool/AI attribution trailers. Commit/push only when asked.
- **Data accuracy**: only real, sourced models (each record needs `source_urls`).
  Do not fabricate unsourced "all devices" data (SPEC §1.6).
- 100% type hints; tests alongside code; new top-level data fields must match the
  SQLModel (seeder does `Model(**record)` — unknown keys break it).

## Gotchas

- SQLModel `table=True` models skip Pydantic validation, so `seed.py` coerces
  `release_date` strings to `date` objects manually.
- `app/services/scoring.py` camera score is intentionally simple (a 50MP flagship
  can score below a 200MP phone) — known Phase-0 limitation, not a data bug.
- Nothing is committed yet — `git status` shows the build as adds.
