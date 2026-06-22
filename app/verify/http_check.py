"""Tier 1 — source_urls liveness.

Answers "do this record's cited sources actually resolve?" without trusting the
page contents (that is Tier 2). Pure-ish: all network I/O goes through an injected
*opener* so tests run offline with a fake.

Design constraints (project memory): stdlib only (urllib + concurrent.futures),
per-host rate limiting, a resumable TTL cache, and never re-check fresh URLs.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, NamedTuple
from urllib.parse import urlparse
from urllib.request import Request, build_opener

from . import ledger
from .common import STATE_DIR
from .hosts import host_of

URL_CACHE_PATH = STATE_DIR / "url_cache.jsonl"
DEFAULT_TTL_DAYS = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 TechAPI-verify/0.1"
)


class CheckResult(NamedTuple):
    url: str
    status: int | None
    final_url: str | None
    alive: bool
    reason: str


# --- opener abstraction (injectable for tests) -----------------------------------


class _Opener:
    """Thin wrapper over urllib's opener exposing ``open(url, method) -> (status, final)``."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._opener = build_opener()
        self.timeout = timeout

    def open(self, url: str, method: str) -> tuple[int, str]:
        req = Request(url, method=method, headers={"User-Agent": USER_AGENT})
        resp = self._opener.open(req, timeout=self.timeout)
        try:
            status = getattr(resp, "status", None) or resp.getcode()
            final = resp.geturl()
            return int(status), final
        finally:
            resp.close()


def default_opener_factory(timeout: float = 10.0) -> _Opener:
    return _Opener(timeout=timeout)


# --- classification --------------------------------------------------------------


def _path_depth(url: str) -> int:
    try:
        path = urlparse(url).path.strip("/")
    except Exception:
        return 0
    return len([p for p in path.split("/") if p])


def _is_homepage_redirect(original: str, final: str) -> bool:
    """A deep page that redirects to the site root is a soft-404 ("not found" page)."""
    if not final or final == original:
        return False
    return _path_depth(original) >= 1 and _path_depth(final) == 0


def classify(original_url: str, status: int | None, final_url: str | None) -> tuple[bool, str]:
    if status is None:
        return False, "error"
    if status >= 400:
        return False, f"http-{status}"
    if final_url and _is_homepage_redirect(original_url, final_url):
        return False, "homepage-redirect"
    return True, f"http-{status}"


def check_one(url: str, opener: Any) -> CheckResult:
    """HEAD first; fall back to GET when HEAD is rejected (405/403) or errors."""
    status: int | None = None
    final: str | None = None
    for method in ("HEAD", "GET"):
        try:
            status, final = opener.open(url, method)
            if method == "HEAD" and status in (400, 403, 405, 501):
                continue  # server dislikes HEAD -> retry GET
            break
        except Exception as exc:  # HTTPError carries a code; everything else is dead
            code = getattr(exc, "code", None)
            if isinstance(code, int):
                status, final = code, getattr(exc, "url", None) or url
                if method == "HEAD" and code in (400, 403, 405, 501):
                    continue
                break
            status, final = None, None
    alive, reason = classify(url, status, final)
    return CheckResult(url, status, final, alive, reason)


# --- rate limiting ---------------------------------------------------------------


class HostRateLimiter:
    """Token-ish per-host limiter: enforce a minimum interval between requests."""

    def __init__(self, min_interval: float = 1.0) -> None:
        self.min_interval = min_interval
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.time()
            prev = self._last.get(host, 0.0)
            sleep_for = max(0.0, self.min_interval - (now - prev))
            self._last[host] = now + sleep_for
        if sleep_for > 0:
            time.sleep(sleep_for)


# --- batch driver ----------------------------------------------------------------


def dedupe_urls(urls: Iterable[str]) -> list[str]:
    """Collapse to one representative per (host, path) — kaggle dumps share a URL."""
    seen: dict[tuple[str, str], str] = {}
    for u in urls:
        try:
            p = urlparse(u)
        except Exception:
            continue
        key = (p.netloc.lower(), p.path.rstrip("/"))
        seen.setdefault(key, u)
    return list(seen.values())


def check_urls(
    urls: list[str],
    *,
    max_workers: int = 8,
    min_interval: float = 1.0,
    opener_factory: Callable[[], Any] = default_opener_factory,
    limiter: HostRateLimiter | None = None,
) -> list[CheckResult]:
    limiter = limiter or HostRateLimiter(min_interval)
    local = threading.local()

    def _get_opener() -> Any:
        op = getattr(local, "opener", None)
        if op is None:
            op = opener_factory()
            local.opener = op
        return op

    def _task(url: str) -> CheckResult:
        limiter.wait(host_of(url))
        return check_one(url, _get_opener())

    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_task, urls))


# --- cache -----------------------------------------------------------------------


def load_cache(path=URL_CACHE_PATH) -> dict[str, dict[str, Any]]:
    return {e["url"]: e for e in ledger.iter_entries(path) if isinstance(e.get("url"), str)}


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def is_fresh(entry: dict[str, Any], now: datetime, ttl_days: int) -> bool:
    ts = _parse_ts(entry.get("checked_at", ""))
    if ts is None:
        return False
    return (now - ts).days < ttl_days


def save_cache(cache: dict[str, dict[str, Any]], path=URL_CACHE_PATH) -> None:
    ledger.replace_all(list(cache.values()), path)


def result_to_entry(r: CheckResult, ts: str) -> dict[str, Any]:
    return {
        "url": r.url,
        "status": r.status,
        "final_url": r.final_url,
        "alive": r.alive,
        "reason": r.reason,
        "checked_at": ts,
    }


def record_liveness(source_urls: list[str], cache: dict[str, dict[str, Any]]) -> tuple[int, int]:
    """(#live, #dead) for a record's URLs that are present in the cache."""
    live = dead = 0
    for u in source_urls:
        e = cache.get(u)
        if e is None:
            continue
        if e.get("alive"):
            live += 1
        else:
            dead += 1
    return live, dead
