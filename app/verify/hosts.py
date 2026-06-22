"""Source-host trust classification.

Grounded in a real signal in the dataset: already-``verified`` records cite
authoritative hosts (en.wikipedia.org, ark.intel.com, amd.com, apple.com,
cpubenchmark.net, ...), while bulk-imported unverified records cite *only*
kaggle.com. The host a record's ``source_urls`` point at is therefore a strong,
learned discriminator of "is this a real, documented part?".
"""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

# Tier 1 — primary/manufacturer + top reference encyclopaedias. A live T1 source
# is strong enough to auto-promote a green record without external cross-ref.
T1_HOSTS: frozenset[str] = frozenset(
    {
        "ark.intel.com",
        "intel.com",
        "amd.com",
        "qualcomm.com",
        "apple.com",
        "nvidia.com",
        "samsung.com",
        "mediatek.com",
        "arm.com",
        "en.wikipedia.org",
        "wikipedia.org",
        "wikichip.org",
        "en.wikichip.org",
        "techpowerup.com",
    }
)

# Tier 2 — reputable spec/benchmark databases. Trustworthy but secondary.
T2_HOSTS: frozenset[str] = frozenset(
    {
        "gsmarena.com",
        "phonedb.net",
        "cpubenchmark.net",
        "videocardbenchmark.net",
        "nanoreview.net",
        "technical.city",
        "topcpu.net",
        "notebookcheck.net",
        "geekbench.com",
        "kimovil.com",
        "devicespecifications.com",
    }
)

# Tier 3 — bulk dumps / aggregators / CDNs. Present in nearly every unverified
# import; on their own they do not establish real-world existence.
T3_HOSTS: frozenset[str] = frozenset(
    {
        "kaggle.com",
        "github.com",
        "raw.githubusercontent.com",
        "commons.wikimedia.org",
        "jsdelivr.net",
        "cdn.jsdelivr.net",
        "aitoolbuzz.com",
    }
)


def host_of(url: str) -> str:
    """Return the lowercased registrable-ish host of a URL (``www.`` stripped)."""
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return ""
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _matches(host: str, hosts: frozenset[str]) -> bool:
    # Exact host or a subdomain of a listed host (e.g. "x.intel.com" -> "intel.com").
    if host in hosts:
        return True
    return any(host.endswith("." + h) for h in hosts)


def tier_of_host(host: str) -> int:
    """1, 2, or 3 for a known host; 0 for unknown/unclassified."""
    if _matches(host, T1_HOSTS):
        return 1
    if _matches(host, T2_HOSTS):
        return 2
    if _matches(host, T3_HOSTS):
        return 3
    return 0


def best_tier(urls: Iterable[str]) -> int:
    """Best (lowest-numbered) known tier among ``urls``; 0 if none classified.

    Note: lower tier number == higher trust, so "best" means the minimum of the
    classified tiers (1 beats 2 beats 3).
    """
    classified = [t for t in (tier_of_host(host_of(u)) for u in urls) if t]
    return min(classified) if classified else 0


def distinct_strong_hosts(urls: Iterable[str]) -> int:
    """Count of distinct T1/T2 hosts — used for a corroboration bonus."""
    strong: set[str] = set()
    for u in urls:
        h = host_of(u)
        if tier_of_host(h) in (1, 2):
            strong.add(h)
    return len(strong)
