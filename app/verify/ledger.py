"""Append-only JSONL verification ledger — the audit trail + resume cursor.

One decision per line in ``data/_verify/ledger.jsonl`` (git-tracked, diffable,
merge-friendly). Each tier appends; the latest entry per (category, slug) wins.
A record whose ``content_hash`` is unchanged since its last fresh decision can be
skipped, which is what makes multi-tier runs incremental and resumable.

Timestamps are passed in by the caller (never generated here) so the module stays
pure and the CLI controls the clock.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from .common import LEDGER_PATH, ensure_verify_dirs


def append(entry: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    ensure_verify_dirs()
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")


def append_many(entries: list[dict[str, Any]], path: Path = LEDGER_PATH) -> None:
    if not entries:
        return
    ensure_verify_dirs()
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def replace_all(entries: list[dict[str, Any]], path: Path) -> None:
    """Truncate-write a full result set (used for the cheap-to-recompute scores cache)."""
    ensure_verify_dirs()
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def iter_entries(path: Path = LEDGER_PATH) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def latest_by_key(path: Path = LEDGER_PATH) -> dict[tuple[str, str], dict[str, Any]]:
    """Most-recent ledger entry per (category, slug). Later lines override earlier."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in iter_entries(path):
        cat, slug = entry.get("category"), entry.get("slug")
        if isinstance(cat, str) and isinstance(slug, str):
            out[(cat, slug)] = entry
    return out


def make_tier0_entry(
    category: str,
    slug: str,
    rel_path: str,
    content_hash: str,
    score: float,
    band: str,
    subscores: dict[str, float],
    flags: list[str],
    best_tier: int,
    ts: str,
) -> dict[str, Any]:
    return {
        "ts": ts,
        "category": category,
        "slug": slug,
        "path": rel_path,
        "hash": content_hash,
        "tier0": {
            "score": score,
            "band": band,
            "subscores": subscores,
            "flags": flags,
            "best_host_tier": best_tier,
        },
    }


def is_fresh(
    entry: dict[str, Any] | None, content_hash: str, tier: str
) -> bool:
    """True if ``entry`` already has a result for ``tier`` and the record is unchanged."""
    if not entry:
        return False
    if entry.get("hash") != content_hash:
        return False  # record edited since -> stale
    return tier in entry
