# TechAPI

> **Open data platform for consumer electronics specs.** Free and open-source.

[![test](https://github.com/GetTechAPI/techapi/actions/workflows/test.yml/badge.svg)](https://github.com/GetTechAPI/techapi/actions/workflows/test.yml)
&nbsp;Code: **MIT** · Data: **CC-BY-SA 4.0**

TechAPI is a free, public RESTful API for structured smartphone, SoC, and GPU specs.
It is a shared platform for any app, website, AI agent, or researcher — not the backend
of any single product (see ADR-008). This repository is the **Phase 0 (MVP)** implementation.

## Try it

Run it locally (see [Quickstart](#quickstart)), then:

```bash
curl http://localhost:8000/v1/smartphones/galaxy-s25
```

Browse the interactive docs at **http://localhost:8000/scalar** (or `/docs`).

## Quickstart

### Option A — Docker Compose (Postgres, one command)

```bash
cp .env.example .env        # optional; compose sets its own DATABASE_URL
docker compose up --build
```

This starts PostgreSQL 16, seeds the database from `data/`, and serves the API on
`http://localhost:8000`.

### Option B — Local (SQLite, no external services)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m scripts.seed                 # creates ./techapi.db and loads data/
uvicorn app.main:app --reload
```

## Endpoints (v1)

| Method | Path | Description |
|---|---|---|
| GET | `/v1/health` | Health check |
| GET | `/v1/version` | API + scoring algorithm versions |
| GET | `/v1/brands` · `/v1/brands/{slug}` | Brands |
| GET | `/v1/brands/{slug}/smartphones` | Phones by brand |
| GET | `/v1/socs` · `/v1/socs/{slug}` | SoCs |
| GET | `/v1/socs/{slug}/smartphones` | Phones using a SoC |
| GET | `/v1/smartphones` · `/v1/smartphones/{slug}` | Smartphones |
| GET | `/v1/smartphones/{slug}/score` | Computed scores |
| GET | `/v1/gpus` · `/v1/gpus/{slug}` | Discrete GPUs |
| GET | `/v1/cpus` · `/v1/cpus/{slug}` | Desktop/laptop CPUs (`?segment=`) |

List responses are paginated (`?limit`, `?offset`) and follow the
`{count, next, previous, results}` envelope. Smartphones support `?brand=`, `?soc=`,
and `?sort=` (e.g. `?sort=-msrp_usd`).

## Development

```bash
ruff check app scripts tests     # lint
mypy app                         # type check
python -m scripts.validate       # validate seed data
pytest --cov=app                 # tests + coverage (target >60%)
```

## Data model & scoring

- **Models** (`app/models/`): `Brand`, `SoC`, `Smartphone`, `DiscreteGPU` (§6).
- **Scoring** (`app/services/scoring.py`): open 0–100 scores carrying an
  `algorithm_version`; missing inputs return `null`, never `0` (§8). Raw third-party
  benchmark numbers are algorithm inputs only and are never re-exposed (ADR-006).

## Static dataset & automation

The live API can be exported to a **static JSON dump** that needs
no server:

```bash
python -m scripts.dump            # writes ./dump/v1/... mirroring the API
```

A scheduled workflow ([refresh-data.yml](.github/workflows/refresh-data.yml))
regenerates the dump weekly and on data changes. See
[docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md) for static-hosting options.

This repo intentionally contains only the API, the curated dataset, and the
static dump. The dataset is **curated and periodically updated** through an
internal pipeline.

## Contributing

Issues and PRs welcome — use the issue templates under `.github/ISSUE_TEMPLATE/`.
PR titles follow [Conventional Commits](https://www.conventionalcommits.org). Data
additions/corrections must include at least one source URL and pass
`python -m scripts.validate`.

Data is organised by category and brand with singular folder names. It is a
**curated subset, not an exhaustive catalog of every device**:

```
data/brand/<slug>.json                       # e.g. data/brand/samsung.json
data/soc/<manufacturer>/<slug>.json           # data/soc/qualcomm/snapdragon-8-elite.json
data/smartphone/<brand>/<slug>.json           # data/smartphone/samsung/galaxy-s25.json
data/gpu/<manufacturer>/<year>/<segment>/<slug>.json  # data/gpu/nvidia/2025/consumer/geforce-rtx-5090.json (split by year then consumer/enterprise)
data/cpu/<manufacturer>/<year>/<slug>.json    # data/cpu/intel/2023/core-i9-14900k.json (CPU also by year)
```

## License

Code is licensed under the [MIT License](LICENSE). Data (under `data/`) is licensed
**CC-BY-SA 4.0** — attribute "Data from TechAPI" and share alike.

The full project specification lives in [`docs/SPEC.md`](docs/SPEC.md).
