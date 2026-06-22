"""TechAPI data *verification* layer (§ existence/trust, sits above structural validation).

``app.validate`` answers "is this record well-formed?". ``app.verify`` answers
"does this record describe a real, actually-existing device/part — confidently
enough to mark it ``verified``?".

It is a separate, additive layer: the structural validator (``app/validate.py``)
stays the fast CI gate and is never rewritten. Verification is tiered:

* Tier 0 — offline deterministic plausibility score over the whole dataset
  (``offline``/``signals``/``hosts``); bands records green/yellow/red.
* Tier 1 — ``source_urls`` HTTP liveness (``http_check``).
* Tier 2 — external cross-reference under an exact-heading rule (``crossref``).
* Tier 3 — hybrid escalation + safe ``verified:true`` write-back (``promote``).

Decisions are recorded append-only in ``data/_verify/ledger.jsonl`` so runs are
incremental and resumable.
"""
