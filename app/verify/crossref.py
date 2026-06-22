"""Tier 2 — external cross-reference under a strict exact-heading rule.

Confirms a record describes a real, documented part by finding an authoritative
page (Wikidata / Wikipedia) whose *title* matches the record name exactly after
normalization. Fuzzy matches are explicitly NOT trusted: project experience shows
fuzzy heading matching serves the wrong SKU ~35% of the time, so a non-exact
candidate yields ``ambiguous`` (never an auto-promote).

All network access goes through an injected ``fetcher`` so the decision logic is
unit-tested offline. The concrete fetcher (urllib against the Wikipedia/Wikidata
REST APIs) is only used by the CLI / scheduled workflow.
"""

from __future__ import annotations

import json
import re
from typing import Any, NamedTuple, Protocol
from urllib.parse import quote
from urllib.request import Request, urlopen

# Decisions
CONFIRM = "confirm"
AMBIGUOUS = "ambiguous"
CONTRADICT = "contradict"
NOTFOUND = "notfound"

_NORM_RE = re.compile(r"[^a-z0-9]+")


def normalize_heading(text: str) -> str:
    """Lowercase, drop everything but [a-z0-9]. 'iPhone XR' -> 'iphonexr'."""
    return _NORM_RE.sub("", text.lower())


class Candidate(NamedTuple):
    title: str
    url: str
    year: int | None = None  # release/inception year if the source exposes one


class Fetcher(Protocol):
    def search(self, name: str) -> list[Candidate]:
        ...


class CrossrefResult(NamedTuple):
    slug: str
    source: str
    decision: str
    exact_heading: bool
    matched_url: str | None
    spec_agreements: int


def _year_of(value: Any) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def crossref_record(
    rec: dict[str, Any], fetcher: Fetcher, source: str = "wikidata"
) -> CrossrefResult:
    """Decide confirm/ambiguous/contradict/notfound for one record."""
    name = rec.get("name")
    slug = rec.get("slug") or ""
    if not isinstance(name, str) or not name.strip():
        return CrossrefResult(slug, source, NOTFOUND, False, None, 0)

    candidates = fetcher.search(name)
    if not candidates:
        return CrossrefResult(slug, source, NOTFOUND, False, None, 0)

    target = normalize_heading(name)
    exact = [c for c in candidates if normalize_heading(c.title) == target]
    if not exact:
        # Something came back, but no title matches exactly -> do not trust.
        return CrossrefResult(slug, source, AMBIGUOUS, False, candidates[0].url, 0)

    cand = exact[0]
    # Secondary gate: if both sides expose a release year, they must roughly agree.
    rec_year = _year_of(rec.get("release_date"))
    agreements = 0
    if rec_year is not None and cand.year is not None:
        if abs(cand.year - rec_year) <= 1:
            agreements = 1
        else:
            return CrossrefResult(slug, source, CONTRADICT, True, cand.url, 0)
    return CrossrefResult(slug, source, CONFIRM, True, cand.url, agreements)


# --- concrete fetchers (network; not exercised by unit tests) --------------------


class WikipediaFetcher:
    """Queries the MediaWiki opensearch API for candidate page titles."""

    API = "https://en.wikipedia.org/w/api.php"
    UA = "TechAPI-verify/0.1 (https://github.com/GetTechAPI)"

    def __init__(self, timeout: float = 10.0, limit: int = 5) -> None:
        self.timeout = timeout
        self.limit = limit

    def search(self, name: str) -> list[Candidate]:
        url = (
            f"{self.API}?action=opensearch&format=json&limit={self.limit}"
            f"&search={quote(name)}"
        )
        try:
            req = Request(url, headers={"User-Agent": self.UA})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []
        # opensearch returns [query, [titles...], [descs...], [urls...]]
        titles = data[1] if len(data) > 1 else []
        urls = data[3] if len(data) > 3 else []
        out: list[Candidate] = []
        for i, title in enumerate(titles):
            url_i = urls[i] if i < len(urls) else ""
            out.append(Candidate(title=title, url=url_i))
        return out
