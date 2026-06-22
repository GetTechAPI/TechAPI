"""Shared loading + identity helpers for the verification layer.

Reuses ``app.validate._load`` (the canonical seed loader) rather than
re-implementing JSON discovery, and rebuilds the brand/SoC foreign-key slug sets
the same way ``app.validate.validate`` does, so the verifier sees exactly the
data the structural gate sees.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from app.validate import DATA_DIR, _load

# Categories the verifier knows about, in load order. Mirrors app.validate.validate.
CATEGORIES: tuple[str, ...] = (
    "brand",
    "soc",
    "smartphone",
    "tablet",
    "watch",
    "pda",
    "gpu",
    "cpu",
)

VERIFY_DIR = DATA_DIR / "_verify"
LEDGER_PATH = VERIFY_DIR / "ledger.jsonl"  # git-tracked: promotion decisions only
STATE_DIR = VERIFY_DIR / "state"  # gitignored caches
SCORES_PATH = STATE_DIR / "scores.jsonl"  # full Tier 0 results (cheap to recompute)


class Record:
    """A single seed record paired with its repo-relative path and category."""

    __slots__ = ("category", "path", "data")

    def __init__(self, category: str, path: str, data: dict[str, Any]) -> None:
        self.category = category
        self.path = path  # e.g. "cpu/intel/2023/desktop/core-i9-14900k.json"
        self.data = data

    @property
    def slug(self) -> str | None:
        slug = self.data.get("slug")
        return slug if isinstance(slug, str) else None

    @property
    def verified(self) -> bool:
        return self.data.get("verified") is True

    def content_hash(self) -> str:
        """Stable hash of the record body — invalidates stale ledger decisions on edit."""
        blob = json.dumps(self.data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Record({self.category}, {self.slug!r})"


def load_category(category: str) -> list[Record]:
    """Load one category's records as :class:`Record` objects."""
    return [Record(category, path, data) for path, data in _load(category)]


def load_all(categories: Iterable[str] = CATEGORIES) -> dict[str, list[Record]]:
    """Load every category into ``{category: [Record, ...]}``."""
    return {cat: load_category(cat) for cat in categories}


def foreign_key_sets(
    records: dict[str, list[Record]],
) -> tuple[set[str], set[str], dict[str, str]]:
    """Build FK lookups the way ``app.validate`` does, plus a SoC release-date map.

    Returns ``(brand_slugs, soc_slugs, soc_release_date)`` where ``soc_release_date``
    maps a SoC slug to its ISO release date (used for "chip can't postdate device").
    """
    brand_slugs = {r.slug for r in records.get("brand", []) if r.slug}
    soc_slugs = {r.slug for r in records.get("soc", []) if r.slug}
    soc_release: dict[str, str] = {}
    for r in records.get("soc", []):
        rd = r.data.get("release_date")
        if r.slug and isinstance(rd, str):
            soc_release[r.slug] = rd
    return brand_slugs, soc_slugs, soc_release


def configure_stdout() -> None:
    """Force UTF-8 stdout so emoji/box-drawing don't crash on Windows cp949.

    Mirrors ``app.validate.run`` (validate.py:336-340).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass


def ensure_verify_dirs() -> None:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def repo_path(rel: str) -> Path:
    """Resolve a repo-relative seed path (as stored on a Record) to an absolute path."""
    return DATA_DIR / rel
