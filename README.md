# TechAPI

> **Curated, open dataset for consumer electronics specs.** Free, share-alike, machine-readable.

[![validate-data](https://github.com/GetTechAPI/TechAPI/actions/workflows/validate-data.yml/badge.svg)](https://github.com/GetTechAPI/TechAPI/actions/workflows/validate-data.yml)
&nbsp;Data: **CC-BY-SA 4.0**

This repo holds the curated **dataset** and the **public site** (Astro intro +
playground). The API server, ingestion crawlers, coverage checks, and the
static-dump generator live in
[**TechEngine**](https://github.com/GetTechAPI/TechEngine).

## Layout

```
data/brand/<slug>.json                                  # e.g. data/brand/samsung.json
data/soc/<manufacturer>/<slug>.json                     # data/soc/qualcomm/snapdragon-8-elite.json
data/smartphone/<brand>/<slug>.json                     # data/smartphone/samsung/galaxy-s25.json
data/gpu/<manufacturer>/<year>/<segment>/<slug>.json    # data/gpu/nvidia/2025/consumer/geforce-rtx-5090.json
data/cpu/<manufacturer>/<year>/<segment>/<slug>.json    # data/cpu/intel/2023/consumer/core-i9-14900k.json
```

All paths use singular folder names. Slugs are kebab-case and unique within each category.

The Astro site lives under `site/` and is the deploy target for GitHub Pages —
it consumes the static JSON dump produced by TechEngine's `weekly-refresh` workflow.

## Self-check

A lightweight bundled validator lives at `app/validate.py`. It runs on every PR via
[`validate-data.yml`](.github/workflows/validate-data.yml) and is also chained into
the heavier TechEngine validation workflow as a downstream job.

```bash
python -m app.validate
```

The validator uses only the Python standard library — no install step required.

## Contributing

Open a PR with the new/updated JSON file. The PR template walks through what to
include. The validator must pass and `source_urls` must cite at least one canonical
reference (vendor product page, Wikipedia infobox, datasheet).

## License

Data is licensed **CC-BY-SA 4.0** — attribute "Data from TechAPI" and share alike.
The bundled validator code is [MIT](LICENSE).
