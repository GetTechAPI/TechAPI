# data/ — curated dataset

These JSON files are the **curated, validated** records the API serves: one
file per record, named `<slug>.json`, in singular category folders.

```
brand/<country>/<slug>.json                                 # country code in lower case, or unknown/
soc/<manufacturer>/<year>/<slug>.json
cpu/<manufacturer>/<year>/<consumer|enterprise>/<slug>.json
gpu/<manufacturer>/<year>/<consumer|enterprise>/<slug>.json
smartphone/<brand>/<year>/<slug>.json                       # or <year>/<base_model>/<slug>.json
tablet/<brand>/<year>/<base_model>/<slug>.json              # watch/, pda/, laptop/ and monitor/ are the same
device_catalog/<brand>/<slug>.json                          # device identities with no known release date
software/<prefix>/<slug>.json                               # prefix = first two characters of the slug
website/<prefix>/<slug>.json
_verify/                                                    # not records: see below
```

The [root README](../README.md#layout) has the same table with file counts and
an example for each category.

The `consumer` / `enterprise` folder is a coarse split. For GPUs:
* `consumer` — gaming/desktop & laptop dGPUs (GeForce GTX/RTX, Radeon RX/R9/HD, Arc, Voodoo, MTT S60/S70/S80, …)
* `enterprise` — datacenter compute, AI accelerators, workstation pro cards (Tesla, A100/H100/B200, Quadro/RTX A/RTX PRO, Radeon Pro W, Instinct MI, MTT S3000/S4000, Vega Frontier, AI-focused TITAN V/RTX, …)

For CPUs, `enterprise` holds server and most HEDT parts. The record's own
`segment` field is finer: `desktop`, `laptop`, `hedt` or `server`.

`_verify/` holds the verification ledger (`ledger.jsonl`), the status aggregate
(`status.json`) and the caches under `state/`. TechEngine's verify tools write
them; don't edit them by hand.

> ⚠️ **This is a curated subset — NOT an exhaustive list of every device/chip.**
> It is intentionally partial. New records come from TechEngine's collectors and
> land here through a reviewed PR; each record carries `source_urls`, and
> `verified` says whether it has passed verification. Don't assume a device is
> missing-by-error — it may simply not be curated yet.

Validate after edits: `python -m app.validate`. Add only real, sourced models.
