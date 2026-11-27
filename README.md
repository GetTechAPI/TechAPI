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

### Repository map

```text
data/         # the dataset: one JSON file per record (categories below)
app/          # the bundled validator, standard library only (python -m app.validate)
site/         # the Astro site that GitHub Pages serves, with the generated API
TechEngine/   # the engine, a submodule pinned to one commit: full validator,
              # integrity gate, API dump, collectors and verification
.github/
  workflows/
    pr-checks.yml        # read-only checks on every PR into develop or main
    final-check.yml      # full build and verification of a PR labelled final-check
    collect.yml          # runs one engine collector by hand; uploads a patch
    pages.yml            # builds the API and the site from main and deploys them
  scripts/
    build-api.sh         # validates, then generates site/public/v1 and openapi.json
    check_dump.py        # compares the generated API with data/
    open-collect-pr.sh   # opens the PR for one collect.yml run
```

### Data

Every record is one JSON file named `<slug>.json`. Folder names are singular,
slugs are kebab-case and unique within their category. Counts are as of
November 2026.

| Category | Path under `data/` | Files | Example |
| --- | --- | ---: | --- |
| `brand` | `brand/<country>/<slug>.json` | 3,101 | `brand/kr/samsung.json` |
| `soc` | `soc/<manufacturer>/<year>/<slug>.json` | 1,449 | `soc/qualcomm/2024/snapdragon-8-elite.json` |
| `cpu` | `cpu/<manufacturer>/<year>/<consumer\|enterprise>/<slug>.json` | 6,412 | `cpu/intel/2023/consumer/core-i9-14900k.json` |
| `gpu` | `gpu/<manufacturer>/<year>/<consumer\|enterprise>/<slug>.json` | 2,864 | `gpu/nvidia/2025/consumer/geforce-rtx-5090.json` |
| `socket` | `socket/<slug>.json` | 82 | `socket/lga1156.json` |
| `chipset` | `chipset/<manufacturer>/<slug>.json` | 725 | `chipset/intel/intel-z790.json` |
| `smartphone` | `smartphone/<brand>/<year>/<slug>.json` or `smartphone/<brand>/<year>/<base_model>/<slug>.json` | 96,471 | `smartphone/samsung/2025/galaxy-s25.json` |
| `tablet` | `tablet/<brand>/<year>/<base_model>/<slug>.json` | 3,577 | `tablet/huawei/2020/matepad-t8/matepad-t8.json` |
| `watch` | `watch/<brand>/<year>/<base_model>/<slug>.json` | 580 | `watch/samsung/2024/galaxy-watch-fe/…` |
| `pda` | `pda/<brand>/<year>/<base_model>/<slug>.json` | 443 | `pda/hp/2000/ipaq-h3600/ipaq-h3600-base.json` |
| `laptop` | `laptop/<brand>/<year>/<base_model>/<slug>.json` | 4,401 | `laptop/dell/2017/dell-inspiron-5567/…` |
| `monitor` | `monitor/<brand>/<year>/<base_model>/<slug>.json` | 440 | `monitor/samsung/2023/samsung-m50b/…` |
| `device_catalog` | `device_catalog/<brand>/<slug>.json` | 20,366 | `device_catalog/kazam/kazam-thunder-345-lte.json` |
| `software` | `software/<prefix>/<slug>.json` | 42,492 | `software/sw/sweble.json` |
| `website` | `website/<prefix>/<slug>.json` | 39,930 | `website/pc/pc-gamer-uk.json` |

- `<year>` is the release year, as in the record's `release_date`. A device
  whose source states no release date has `release_date: null` and lives under
  `unknown/` in place of the year. Other specs a source does not state (RAM, OS,
  a monitor's size and resolution) are null as well.
- `<country>` is the brand's ISO 3166 country code in lower case. A brand with
  no sourced country lives under `brand/unknown/`; that is most of them (2,674).
- `<consumer|enterprise>` is a coarse folder split. A CPU record's own `segment`
  field is finer: `desktop`, `laptop`, `hedt` or `server`.
- A CPU, GPU or SoC needs only its name, manufacturer and a source; other specs
  may be null. A chip without a `release_date` lives under `unknown/` in place
  of the year: `soc/<manufacturer>/unknown/<slug>.json`,
  `cpu/<manufacturer>/unknown/<consumer|enterprise>/<slug>.json`. A CPU without
  a `segment` lives at `cpu/<manufacturer>/<year>/unknown/<slug>.json`.
- A chip whose source states the release only to the month or the year keeps a
  full `release_date` with the unstated parts as `01`, and
  `release_date_precision` (`month` or `year`) says so.
- Sockets and chipsets have no year folder. `socket/` is flat because a socket
  shared by several makers has `manufacturer: null`. Their `release_date` may
  be `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, as precise as the source; every other
  category keeps the full date. A chipset lists the sockets it supports by
  slug in `sockets`, and each must exist under `socket/`.
- A CPU's optional `socket_slug` is the slug of its socket record and must
  exist under `socket/`. The free-text `socket` stays as the source wrote it;
  a CPU whose text names a BGA package, several sockets or a socket without a
  record has no `socket_slug`.
- `<base_model>` groups the variants of one model (memory, storage, region).
  About a third of the smartphones (31,093) sit directly in the year folder
  instead.
- `<prefix>` is the first two characters of the slug, or the whole slug when it
  is one character long.
- `device_catalog` lists device identities (model numbers, codenames) whose
  release date is unknown, so it has no year folder.
- `data/_verify/` is not a category. It holds the verification ledger
  (`ledger.jsonl`), the status aggregate (`status.json`) and the caches under
  `state/` that TechEngine's verify tools write. Don't edit it by hand.

### Site

The Astro site lives under `site/` and is the deploy target for GitHub Pages.
[`pages.yml`](.github/workflows/pages.yml) generates the static JSON API from
`main`'s data with the pinned TechEngine at deploy time, checks it against
`data/`, and publishes it with the site. The generated API is not committed;
only the hand-made `site/public/v1/games/index.json` pointer is. To preview the
site with the API locally:

```bash
git submodule update --init TechEngine
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
verdict; adding the label again updates that comment. The comment can't mention
anyone or reference other issues: `@` is dropped and `#123` links are broken.

New and refreshed records come from
[`collect.yml`](.github/workflows/collect.yml), which a maintainer runs by hand
from the Actions tab on `develop`. It runs one of TechEngine's collectors
(`ingest`, `refresh` or `promote`) with a read-only token: the run validates
its changes and uploads them as a patch, and never pushes, opens a PR or posts
a comment. The maintainer then runs the helper below by hand. Their account
pushes the run's branch and TechEngineBot opens the PR, so pr-checks runs on
it like on any PR:

```bash
bash .github/scripts/open-collect-pr.sh <run-id>   # from any TechAPI clone
```

TechEngineBot's gh login is kept apart from the maintainer's own. The helper
prints the one-time login command if it is missing.

Each task keeps one open PR on a fixed `collect/*` branch, updated in place by
later runs. Collection never runs on a schedule.

## Branching

This repo follows git-flow:

| Branch | Role |
| --- | --- |
| `main` | Released state. Publishing the site fires on a push here, so it only moves through a release PR. |
| `develop` | Integration. Every data, feature and fix branch targets this. |
| `feat/*`, `data/*`, `fix/*`, `chore/*` | Short-lived work branches, cut from `develop`. |

A release is a PR from `develop` to `main`; merging it deploys the site.
The TechEngine pin and the pinned action SHAs are bumped by hand, in a PR into
`develop` that pr-checks validates like any other; Dependabot is not used.

## Related repositories

| Repository | What it holds |
| --- | --- |
| [TechEngine](https://github.com/GetTechAPI/TechEngine) | The engine pinned here as a submodule: validation, the static API generator, the collectors and the verification tiers. |
| [game-catalog](https://github.com/GetTechAPI/game-catalog) | Video game records. They moved out of this repo in September 2026; `site/public/v1/games/index.json` points there. |
| [cpu-engineering-samples](https://github.com/GetTechAPI/cpu-engineering-samples) | Engineering-sample CPUs, kept apart from the retail CPUs in `data/cpu/`. |
| [TechMachine](https://github.com/GetTechAPI/TechMachine) | The organisation's repository health check and the scaffolder for new satellite data repos. |

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
