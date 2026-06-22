"""Tier 0 scorer + host classification tests."""

from app.verify import hosts, offline
from app.verify.common import Record

NOW = 2026
NO_SOC: dict[str, str] = {}


def _score(category, data):
    return offline.score_record(Record(category, f"{category}/x.json", data), NOW, NO_SOC)


def test_host_tiers():
    assert hosts.tier_of_host("en.wikipedia.org") == 1
    assert hosts.tier_of_host("ark.intel.com") == 1  # subdomain of intel.com
    assert hosts.tier_of_host("gsmarena.com") == 2
    assert hosts.tier_of_host("www.kaggle.com") == 3
    assert hosts.tier_of_host("example.org") == 0
    assert hosts.best_tier(["https://kaggle.com/x", "https://en.wikipedia.org/y"]) == 1


def test_complete_authoritative_cpu_is_green():
    rec = {
        "slug": "core-i9-14900k", "cores": 24, "threads": 32,
        "base_clock_ghz": 3.2, "boost_clock_ghz": 6.0, "l3_cache_mb": 36,
        "socket": "LGA1700", "tdp_w": 125, "passmark_cpu_mark": 60000,
        "architecture": "Raptor Lake", "release_date": "2023-10-17",
        "source_urls": ["https://ark.intel.com/x", "https://en.wikipedia.org/wiki/x"],
    }
    s = _score("cpu", rec)
    assert s.band == "green"
    assert s.best_tier == 1


def test_hard_violation_forces_red_despite_good_source():
    rec = {
        "slug": "bad", "cores": 16, "threads": 8,  # threads < cores -> hard
        "base_clock_ghz": 3.0, "boost_clock_ghz": 4.0, "release_date": "2023-01-01",
        "architecture": "x", "socket": "y", "tdp_w": 65, "l3_cache_mb": 8,
        "passmark_cpu_mark": 20000,
        "source_urls": ["https://en.wikipedia.org/wiki/x"],
    }
    s = _score("cpu", rec)
    assert s.band == "red"
    assert "!threads_ge_cores" in s.flags


def test_kaggle_only_sparse_is_not_green():
    rec = {
        "slug": "sgh-x", "name": "SGH-X", "release_date": "2016-01-01",
        "display": {"type": "Alphanumeric"},
        "source_urls": ["https://www.kaggle.com/datasets/msainani/gsmarena-mobile-devices"],
    }
    s = _score("smartphone", rec)
    assert s.band != "green"  # T3-only source can never auto-green
    assert s.best_tier == 3


def test_future_release_red():
    rec = {
        "slug": "ghost", "cores": 8, "threads": 16, "release_date": "2099-01-01",
        "source_urls": ["https://en.wikipedia.org/wiki/x"],
    }
    assert _score("cpu", rec).band == "red"
