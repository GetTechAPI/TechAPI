# TechAPI

> Curated, open dataset for consumer electronics specifications and game metadata.

[![validate-data](https://github.com/GetTechAPI/TechAPI/actions/workflows/validate-data.yml/badge.svg)](https://github.com/GetTechAPI/TechAPI/actions/workflows/validate-data.yml)
Data: **CC-BY-SA 4.0**

This repository owns the versioned dataset and the public Astro site. The API
server, ingestion crawlers, coverage checks, and static-dump generator live in
[TechEngine](https://github.com/GetTechAPI/TechEngine), included here as the
`TechEngine` submodule.

## Layout

```text
data/brand/<country>/<slug>.json
data/cpu/<manufacturer>/<year>/<segment>/<slug>.json
data/gpu/<manufacturer>/<year>/<segment>/<slug>.json
data/smartphone/<brand>/<year>/<slug>.json
data/game/<slug[:2]>/<slug>.json
site/                       # Astro Pages site
site/public/v1/             # committed static API dump from TechEngine
app/validate.py             # stdlib-only, fast repository self-check
```

The game directory is sharded by normalized slug rather than genre or import
batch. See [the data layout guide](docs/DATA_LAYOUT.md) before adding or moving
game records.

## Local workflow

```bash
python -m app.validate
cd site && npm ci && npm run build
```

Use TechEngine for ingest, API, and dump generation. Do not change its code or
submodule pointer as part of a data-only change. The committed
`site/public/v1/` dump is deployed by GitHub Pages; its contents must remain in
the repository even when it is too large to browse comfortably locally.

For a focused workflow and the boundary between this repository and TechEngine,
see [docs/LOCAL_WORKFLOW.md](docs/LOCAL_WORKFLOW.md).

## License

Data is licensed **CC-BY-SA 4.0**. The bundled validator is [MIT](LICENSE).
