"""Tier 3 — hybrid escalation + safe ``verified:true`` write-back.

Promotion rules (only ever ``false -> true``, never a demotion):
* band green AND >=1 cited source is a *live* Tier-1 host  -> auto-promote
* Tier 2 cross-reference returned ``confirm`` (exact heading) -> promote
* otherwise stay unverified, with a logged reason

Write-back is *surgical*: only the ``"verified": false`` token is rewritten to
``true`` in the raw bytes. Full re-serialization is intentionally avoided because
the seed files keep short arrays inline (``[64, 128, 256]``) while ``json.dumps``
would expand them, producing a huge spurious diff and defeating the "only verified
changed" guard. Edits are atomic (temp file + ``os.replace``) and preserve LF.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, NamedTuple

from . import hosts
from .common import STATE_DIR

CROSSREF_CACHE_PATH = STATE_DIR / "crossref_cache.jsonl"

# A top-level, one-key-per-line "verified": false entry (2-space indented).
_VERIFIED_FALSE_RE = re.compile(r'^(  )"verified": false(,?)[ \t]*$', re.MULTILINE)


class PromotionDecision(NamedTuple):
    promote: bool
    reason: str


def has_live_authoritative_source(
    source_urls: list[str], url_cache: dict[str, dict[str, Any]]
) -> bool:
    """True if some cited URL is an authoritative host (Tier 1 *or* Tier 2) AND
    confirmed alive. The green band already requires a T1/T2 source + completeness
    + consistency; this just adds "and that source actually resolves". Requiring a
    *manufacturer/encyclopaedia* (T1 only) was too strict — it never promoted the
    many green records sourced from reputable spec/benchmark DBs (gsmarena,
    cpubenchmark, ...), so verified never moved off its floor.
    """
    for u in source_urls:
        entry = url_cache.get(u)
        if entry and entry.get("alive") and hosts.tier_of_host(hosts.host_of(u)) in (1, 2):
            return True
    return False


# Backwards-compatible alias (older callers/tests).
has_live_t1 = has_live_authoritative_source


def decide(
    *, band: str, source_urls: list[str], url_cache: dict[str, dict[str, Any]],
    crossref_decision: str | None,
) -> PromotionDecision:
    if crossref_decision == "confirm":
        return PromotionDecision(True, "crossref-confirm")
    if band == "green" and has_live_authoritative_source(source_urls, url_cache):
        return PromotionDecision(True, "green+live-source")
    return PromotionDecision(False, "needs-confirmation")


# --- surgical write-back ---------------------------------------------------------


def flip_verified_text(raw: str) -> str | None:
    """Return ``raw`` with a single top-level ``verified:false`` flipped to true.

    Returns None (refuse) unless exactly one such token exists, so we never touch
    a record that isn't shaped the way we expect.
    """
    new, n = _VERIFIED_FALSE_RE.subn(r'\g<1>"verified": true\g<2>', raw)
    return new if n == 1 else None


def write_verified_true(abs_path: Path) -> bool:
    """Atomically flip verified false->true in a seed file. Returns True if written."""
    raw = abs_path.read_bytes().decode("utf-8")
    new = flip_verified_text(raw)
    if new is None:
        return False
    tmp = abs_path.with_suffix(abs_path.suffix + ".tmp")
    tmp.write_bytes(new.encode("utf-8"))
    os.replace(tmp, abs_path)
    return True


def load_crossref_cache(path=CROSSREF_CACHE_PATH) -> dict[tuple[str, str], dict[str, Any]]:
    from . import ledger
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for e in ledger.iter_entries(path):
        cat, slug = e.get("category"), e.get("slug")
        if isinstance(cat, str) and isinstance(slug, str):
            out[(cat, slug)] = e
    return out
