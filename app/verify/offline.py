"""Tier 0 — offline, deterministic plausibility scoring over the whole dataset.

No network. Combines four sub-scores into 0..100 and a green/yellow/red band:

* completeness   0..25  — how richly populated beyond the required fields
* consistency    0..35  — cross-field predicates from :mod:`signals`
* host trust     0..30  — authority of the cited ``source_urls`` (:mod:`hosts`)
* provenance     0..10  — clean normalized data vs raw-blob-only imports

Hard predicate violations (threads<cores, boost<base, chip postdates device,
future release) force the band to red regardless of the numeric score.
"""

from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple

from . import hosts, signals
from .common import Record

# Weights (max points per sub-score). Tunable after inspecting the histogram.
W_COMPLETENESS = 25.0
W_CONSISTENCY = 35.0
W_HOST = 30.0
W_PROVENANCE = 10.0

GREEN_MIN = 75.0
RED_MAX = 45.0  # strictly below -> red

# "Rich" fields per category: presence (non-null) signals a fleshed-out record.
# Dotted paths index into nested dicts (e.g. "display.ppi").
RICH_FIELDS: dict[str, tuple[str, ...]] = {
    "cpu": ("architecture", "base_clock_ghz", "boost_clock_ghz", "l3_cache_mb",
            "socket", "tdp_w", "passmark_cpu_mark"),
    "gpu": ("architecture", "boost_clock_mhz", "memory_type", "memory_bandwidth_gbps",
            "fp32_tflops", "cuda_cores", "stream_processors"),
    "soc": ("transistors_billion", "cpu_config", "gpu_cores", "gpu_clock_mhz",
            "npu_tops", "geekbench_multi"),
    "smartphone": ("soc", "display.size_inch", "display.resolution", "display.ppi",
                   "cameras", "storage_options_gb", "charging_wired_w", "os_version"),
    "tablet": ("display.size_inch", "display.resolution", "storage_options_gb",
               "cameras", "os_version"),
    "watch": ("display.size_inch", "display.resolution", "os_version"),
    "pda": ("display.size_inch", "display.resolution", "os_version"),
    "brand": ("founded_year", "description_en"),
}


class Score(NamedTuple):
    score: float
    band: str  # "green" | "yellow" | "red"
    subscores: dict[str, float]
    flags: list[str]  # names of failed predicates (hard prefixed with "!")
    best_tier: int


def _get_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _completeness(category: str, data: dict[str, Any]) -> float:
    fields = RICH_FIELDS.get(category, ())
    if not fields:
        return W_COMPLETENESS
    present = sum(1 for f in fields if _get_path(data, f) not in (None, "", [], {}))
    return W_COMPLETENESS * present / len(fields)


def _consistency(sigs: list[signals.Signal]) -> tuple[float, list[str], bool]:
    evaluated = [s for s in sigs if s.result in ("pass", "fail")]
    failed = [s for s in sigs if s.failed]
    hard_failed = any(s.hard for s in failed)
    flags = [("!" if s.hard else "") + s.name for s in failed]
    if not evaluated:
        return W_CONSISTENCY, flags, hard_failed
    passed = sum(1 for s in evaluated if s.result == "pass")
    return W_CONSISTENCY * passed / len(evaluated), flags, hard_failed


def _host_score(urls: list[str]) -> tuple[float, int]:
    best = hosts.best_tier(urls)
    base = {1: 26.0, 2: 18.0, 3: 6.0, 0: 3.0}[best]
    if hosts.distinct_strong_hosts(urls) >= 2:
        base += 4.0
    return min(base, W_HOST), best


def _provenance(data: dict[str, Any], best_tier: int) -> float:
    has_raw = any(k.startswith("raw_") for k in data.keys())
    if not has_raw:
        return 7.0
    prov = 5.0 + (3.0 if best_tier in (1, 2) else -3.0)
    return max(0.0, min(prov, W_PROVENANCE))


def score_record(
    rec: Record, now_year: int, soc_release: dict[str, str]
) -> Score:
    data = rec.data
    urls = [u for u in data.get("source_urls", []) if isinstance(u, str)]

    completeness = _completeness(rec.category, data)
    sigs = signals.signals_for(rec.category, data, now_year, soc_release)
    consistency, flags, hard_failed = _consistency(sigs)
    host, best_tier = _host_score(urls)
    provenance = _provenance(data, best_tier)

    total = completeness + consistency + host + provenance
    subscores = {
        "completeness": round(completeness, 1),
        "consistency": round(consistency, 1),
        "host": round(host, 1),
        "provenance": round(provenance, 1),
    }

    if hard_failed:
        band = "red"
    elif total >= GREEN_MIN and best_tier in (1, 2):
        band = "green"
    elif total < RED_MAX:
        band = "red"
    else:
        band = "yellow"

    return Score(round(total, 1), band, subscores, flags, best_tier)


def now_year_today() -> int:
    return date.today().year
