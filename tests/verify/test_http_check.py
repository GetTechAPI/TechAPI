"""Tier 1 liveness tests — fully offline via a fake opener."""

from app.verify import http_check
from app.verify.http_check import CheckResult


class FakeOpener:
    """Maps url -> (status, final_url) or raises a urllib-style error with .code."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def open(self, url, method):
        self.calls.append((url, method))
        val = self.table[url]
        if isinstance(val, Exception):
            raise val
        return val


def _factory(table):
    op = FakeOpener(table)
    return lambda: op


def test_alive_200():
    table = {"https://en.wikipedia.org/wiki/X": (200, "https://en.wikipedia.org/wiki/X")}
    [res] = http_check.check_urls(list(table), opener_factory=_factory(table), min_interval=0)
    assert res.alive and res.status == 200


def test_dead_404():
    table = {"https://gsmarena.com/x-9999.php": (404, "https://gsmarena.com/x-9999.php")}
    [res] = http_check.check_urls(list(table), opener_factory=_factory(table), min_interval=0)
    assert not res.alive and res.reason == "http-404"


def test_homepage_redirect_is_soft_dead():
    table = {"https://phonedb.net/index.php?m=device&id=123": (200, "https://phonedb.net/")}
    [res] = http_check.check_urls(list(table), opener_factory=_factory(table), min_interval=0)
    assert not res.alive and res.reason == "homepage-redirect"


def test_head_rejected_falls_back_to_get():
    err = type("E", (Exception,), {"code": 405, "url": None})()
    table = {"https://x.com/deep/page": err}

    class TwoStep:
        def __init__(self):
            self.n = 0

        def open(self, url, method):
            self.n += 1
            if method == "HEAD":
                raise err
            return (200, "https://x.com/deep/page")

    res = http_check.check_one("https://x.com/deep/page", TwoStep())
    assert res.alive and res.status == 200


def test_connection_error_is_dead():
    table = {"https://nope.invalid/x": ConnectionError("no route")}
    [res] = http_check.check_urls(list(table), opener_factory=_factory(table), min_interval=0)
    assert not res.alive and res.reason == "error"


def test_dedupe_by_host_and_path():
    urls = [
        "https://www.kaggle.com/datasets/a",
        "https://www.kaggle.com/datasets/a",  # exact dup
        "https://www.kaggle.com/datasets/b",
    ]
    assert len(http_check.dedupe_urls(urls)) == 2


def test_cache_freshness():
    from datetime import datetime, timezone
    now = datetime(2026, 6, 22, tzinfo=timezone.utc)
    fresh = {"checked_at": "2026-06-20T00:00:00Z"}
    stale = {"checked_at": "2026-01-01T00:00:00Z"}
    assert http_check.is_fresh(fresh, now, ttl_days=30)
    assert not http_check.is_fresh(stale, now, ttl_days=30)


def test_record_liveness():
    cache = {
        "a": {"alive": True}, "b": {"alive": False}, "c": {"alive": True},
    }
    assert http_check.record_liveness(["a", "b", "c", "missing"], cache) == (2, 1)


def test_cache_roundtrip():
    # tmp_path fixture is unreliable on this Windows runner; use a local scratch file.
    from pathlib import Path
    path = Path(__file__).parent / "_scratch_url_cache.jsonl"
    try:
        r = CheckResult("https://x.com/y", 200, "https://x.com/y", True, "http-200")
        http_check.save_cache({r.url: http_check.result_to_entry(r, "2026-06-22T00:00:00Z")}, path)
        loaded = http_check.load_cache(path)
        assert loaded["https://x.com/y"]["alive"] is True
    finally:
        path.unlink(missing_ok=True)
