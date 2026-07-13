# data/ — curated dataset

These JSON files are the **curated, validated** records the API serves. Layout is
singular folder names, organised by brand:

```
brand/<slug>.json
soc/<manufacturer>/<slug>.json
smartphone/<brand>/<slug>.json
gpu/<manufacturer>/<year>/<segment>/<slug>.json   # GPUs are split by release year then segment (consumer | enterprise)
cpu/<manufacturer>/<year>/<segment>/<slug>.json   # CPUs split by release year then segment (consumer | enterprise)
```

GPU `<segment>` is:
* `consumer` — gaming/desktop & laptop dGPUs (GeForce GTX/RTX, Radeon RX/R9/HD, Arc, Voodoo, MTT S60/S70/S80, …)
* `enterprise` — datacenter compute, AI accelerators, workstation pro cards (Tesla, A100/H100/B200, Quadro/RTX A/RTX PRO, Radeon Pro W, Instinct MI, MTT S3000/S4000, Vega Frontier, AI-focused TITAN V/RTX, …)

> ⚠️ **This is a curated subset — NOT an exhaustive list of every device/chip.**
> It is hand-verified and intentionally partial. Breadth is expanded out-of-band
> through an internal pipeline that publishes curated records here after review;
> each record carries `source_urls`. Don't assume a device is missing-by-error —
> it may simply not be curated yet.

Validate after edits: `python -m app.validate`. Add only real, sourced models.
