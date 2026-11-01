<p align="center">
  <img src="site/public/techapi-mark.png" alt="TechAPI" width="120">
</p>

<h1 align="center">TechAPI</h1>

<p align="center">
  <strong>Curated, open dataset for consumer electronics specs.</strong><br>
  Free, share-alike, machine-readable.
</p>

<p align="center">
  <a href="https://github.com/GetTechAPI/TechAPI/actions/workflows/pages.yml"><img src="https://github.com/GetTechAPI/TechAPI/actions/workflows/pages.yml/badge.svg" alt="pages"></a>
  &nbsp;Data: <strong>CC-BY-SA 4.0</strong>
</p>

This repo holds the curated **dataset** and the **public site** (Astro intro +
playground). The API server, ingestion crawlers, coverage checks, and the
static-dump generator live in
[**TechEngine**](https://github.com/GetTechAPI/TechEngine).

## Layout

```text
data/brand/<country>/<slug>.json                       # e.g. data/brand/kr/samsung.json
data/soc/<manufacturer>/<year>/<slug>.json             # data/soc/qualcomm/2024/snapdragon-8-elite.json
data/smartphone/<brand>/<year>/<slug>.json             # data/smartphone/samsung/2025/galaxy-s25.json
data/gpu/<manufacturer>/<year>/<segment>/<slug>.json   # data/gpu/nvidia/2025/consumer/geforce-rtx-5090.json
data/cpu/<manufacturer>/<year>/<segment>/<slug>.json   # data/cpu/intel/2023/consumer/core-i9-14900k.json
```

All paths use singular folder names. Slugs are kebab-case and unique within each category.

The Astro site lives under `site/` and is the deploy target for GitHub Pages.
[`pages.yml`](.github/workflows/pages.yml) generates the static JSON API from
`main`'s data with the pinned TechEngine at deploy time, checks it against
`data/`, and publishes it with the site. The generated API is not committed;
only the hand-made `site/public/v1/games/index.json` pointer is. To preview the
site with the API locally:

```bash
git submodule update --init TechEngine   # never --recursive
python -m pip install -e ./TechEngine
bash .github/scripts/build-api.sh        # validates, then writes site/public/v1
cd site && npm ci && npm run dev
```

## Self-Check

A lightweight bundled validator lives at `app/validate.py`:

```bash
python -m app.validate
```

The validator uses only the Python standard library; no install step required.

Every PR into `develop` or `main` runs
[`pr-checks.yml`](.github/workflows/pr-checks.yml): this validator, TechEngine's
validator on the changed records, the integrity gate and, when `site/` changes,
the site build. It has no secrets and reports in the job summary, never in
comments.

For an important PR, a maintainer adds the `final-check` label.
[`final-check.yml`](.github/workflows/final-check.yml) then builds everything
`pages.yml` would publish from the PR and runs TechEngine's Tier 0-3
verification of the changed records. TechEngineBot posts one comment with the
verdict; adding the label again updates that comment.

New and refreshed records come from
[`collect.yml`](.github/workflows/collect.yml), which a maintainer runs by hand
from the Actions tab on `develop`. It runs one of TechEngine's collectors
(`ingest`, `refresh` or `promote`) and keeps one open PR per task on a fixed
`collect/*` branch, updated in place by later runs. That PR comes from
github-actions[bot] and starts no checks of its own, so the collector validates
before it pushes and writes the result into the PR body. Collection never runs
on a schedule and never posts comments.

## Branching

This repo follows git-flow:

| Branch | Role |
| --- | --- |
| `main` | Released state. Publishing the site fires on a push here, so it only moves through a release PR. |
| `develop` | Integration. Every data, feature and fix branch targets this. |
| `feat/*`, `data/*`, `fix/*`, `chore/*` | Short-lived work branches, cut from `develop`. |

A release is a PR from `develop` to `main`; merging it deploys the site.
The TechEngine pin and the pinned action SHAs are bumped by hand, in a PR into
`develop` that pr-checks validates like any other. Dependabot can't do it:
TechEngine carries TechAPI as its own submodule, and Dependabot's recursive
clone runs out of disk on that loop.

## Contributing

Open a PR **against `develop`** with the new/updated JSON file — that is also
the default branch, so a PR from a fork targets it automatically. The PR
template walks through what to include, and the validator must pass. Every
record, in every category, must include `source_urls` with at least one
canonical reference (vendor product page, Wikipedia infobox, datasheet).

## License

Data is licensed **CC-BY-SA 4.0**; attribute "Data from TechAPI" and share alike
(see [`data/LICENSE.md`](data/LICENSE.md)).
The bundled validator code is [MIT](LICENSE).
