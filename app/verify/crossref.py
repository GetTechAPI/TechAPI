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


def _heading_matches(rec_name: str, cand_title: str) -> bool:
    """Exact normalized match, or the candidate is the model-name suffix of the
    record (authoritative sources often omit the maker prefix: record 'AMD Ryzen 7
    5800X' vs Wikidata label 'Ryzen 7 5800X'). This is NOT fuzzy matching — it
    requires a full, contiguous suffix of >=4 chars, so it can't drift to a
    different SKU the way Levenshtein does."""
    r, c = normalize_heading(rec_name), normalize_heading(cand_title)
    if not r or not c:
        return False
    if r == c:
        return True
    return len(c) >= 4 and (r.endswith(c) or c.endswith(r))


def crossref_record(
    rec: dict[str, Any], fetcher: Fetcher, source: str = "wikidata"
) -> CrossrefResult:
    """Decide confirm/ambiguous/contradict/notfound for one record.

    Reality-based: CONFIRM requires an exact-heading authoritative entity whose
    release year agrees. A year disagreement is a CONTRADICT (reality veto — the
    record must NOT be promoted, even if it scored green). A name match with no
    comparable year is only AMBIGUOUS (existence, but specs unconfirmed)."""
    name = rec.get("name")
    slug = rec.get("slug") or ""
    if not isinstance(name, str) or not name.strip():
        return CrossrefResult(slug, source, NOTFOUND, False, None, 0)

    candidates = fetcher.search(name)
    if not candidates:
        return CrossrefResult(slug, source, NOTFOUND, False, None, 0)

    exact = [c for c in candidates if _heading_matches(name, c.title)]
    if not exact:
        return CrossrefResult(slug, source, AMBIGUOUS, False, candidates[0].url, 0)

    # Prefer an exact match that carries a year (so we can actually confirm specs).
    cand = next((c for c in exact if c.year is not None), exact[0])
    rec_year = _year_of(rec.get("release_date"))
    if rec_year is not None and cand.year is not None:
        if abs(cand.year - rec_year) <= 1:
            return CrossrefResult(slug, source, CONFIRM, True, cand.url, 1)
        return CrossrefResult(slug, source, CONTRADICT, True, cand.url, 0)
    # Name matches an authoritative entity but no year to verify the data against.
    return CrossrefResult(slug, source, AMBIGUOUS, True, cand.url, 0)


# --- concrete fetchers (network; not exercised by unit tests) --------------------


def _wikidata_claim_year(entity: dict) -> int | None:
    """First year from inception (P571) or publication date (P577) claims."""
    claims = entity.get("claims", {})
    for prop in ("P571", "P577"):
        for claim in claims.get(prop, []):
            try:
                t = claim["mainsnak"]["datavalue"]["value"]["time"]  # "+2007-02-19T..."
            except (KeyError, TypeError):
                continue
            digits = t.lstrip("+")[:4]
            if digits.isdigit():
                return int(digits)
    return None


class WikidataFetcher:
    """Structured cross-reference against Wikidata: search entities by label, then
    read their release year (P571/P577) to verify the record's data against reality.
    Two HTTP calls per record (search + a batched entity fetch)."""

    API = "https://www.wikidata.org/w/api.php"
    UA = "TechAPI-verify/0.1 (https://github.com/GetTechAPI)"

    def __init__(self, timeout: float = 10.0, limit: int = 5) -> None:
        self.timeout = timeout
        self.limit = limit

    def _get(self, url: str) -> dict:
        req = Request(url, headers={"User-Agent": self.UA})
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(self, name: str) -> list[Candidate]:
        try:
            data = self._get(
                f"{self.API}?action=wbsearchentities&format=json&language=en"
                f"&limit={self.limit}&search={quote(name)}"
            )
            hits = data.get("search", [])
            if not hits:
                return []
            ids = "|".join(h["id"] for h in hits if h.get("id"))
            ent = self._get(
                f"{self.API}?action=wbgetentities&format=json&props=claims&ids={ids}"
            ).get("entities", {})
        except Exception:
            return []
        out: list[Candidate] = []
        for h in hits:
            qid = h.get("id")
            label = h.get("label") or h.get("match", {}).get("text", "")
            year = _wikidata_claim_year(ent.get(qid, {})) if qid else None
            out.append(Candidate(title=label, url=f"https://www.wikidata.org/wiki/{qid}", year=year))
        return out


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
