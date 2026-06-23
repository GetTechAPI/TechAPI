"""Tier 2/3 tests: exact-heading rule, surgical write-back, no-clobber, escalation."""

from pathlib import Path

from app.verify import crossref, promote
from app.verify.crossref import Candidate


class FakeFetcher:
    def __init__(self, candidates):
        self._c = candidates

    def search(self, name):
        return self._c


# --- exact-heading rule ----------------------------------------------------------


def test_exact_heading_confirms():
    rec = {"slug": "iphone-xr", "name": "iPhone XR", "release_date": "2018-10-26"}
    f = FakeFetcher([Candidate("iPhone XR", "https://en.wikipedia.org/wiki/IPhone_XR", 2018)])
    res = crossref.crossref_record(rec, f)
    assert res.decision == crossref.CONFIRM and res.exact_heading


def test_near_miss_is_ambiguous_not_confirm():
    # A different SKU comes back; fuzzy match must NOT auto-confirm.
    rec = {"slug": "iphone-xr", "name": "iPhone XR"}
    f = FakeFetcher([Candidate("iPhone XS", "https://en.wikipedia.org/wiki/IPhone_XS")])
    res = crossref.crossref_record(rec, f)
    assert res.decision == crossref.AMBIGUOUS and not res.exact_heading


def test_year_contradiction_blocks_confirm():
    rec = {"slug": "x", "name": "Widget 9000", "release_date": "2018-01-01"}
    f = FakeFetcher([Candidate("Widget 9000", "http://x", 2010)])
    assert crossref.crossref_record(rec, f).decision == crossref.CONTRADICT


def test_no_candidates_is_notfound():
    rec = {"slug": "x", "name": "Obscure Thing"}
    assert crossref.crossref_record(rec, FakeFetcher([])).decision == crossref.NOTFOUND


def test_normalize_heading():
    assert crossref.normalize_heading("iPhone XR") == "iphonexr"
    assert crossref.normalize_heading("Core i9-14900K") == "corei914900k"


# --- surgical write-back ---------------------------------------------------------

SEED = (
    '{\n'
    '  "slug": "demo",\n'
    '  "name": "Demo",\n'
    '  "storage_options_gb": [64, 128, 256],\n'
    '  "verified": false,\n'
    '  "source_urls": [\n'
    '    "https://en.wikipedia.org/wiki/Demo"\n'
    '  ]\n'
    '}\n'
)


def test_flip_only_touches_verified_token():
    out = promote.flip_verified_text(SEED)
    assert out is not None
    # Exactly one line changed; inline array preserved verbatim.
    assert '"verified": true,' in out
    assert '"storage_options_gb": [64, 128, 256],' in out
    diff = [(a, b) for a, b in zip(SEED.splitlines(), out.splitlines()) if a != b]
    assert diff == [('  "verified": false,', '  "verified": true,')]


def test_flip_refuses_already_true():
    assert promote.flip_verified_text(SEED.replace("false", "true")) is None


def test_write_back_atomic_lf_preserved():
    path = Path(__file__).parent / "_scratch_seed.json"
    try:
        path.write_bytes(SEED.encode("utf-8"))
        assert promote.write_verified_true(path) is True
        raw = path.read_bytes()
        assert b'"verified": true,' in raw
        assert b"\r\n" not in raw  # LF preserved on Windows
        assert raw.endswith(b"}\n")
        # idempotent guard: second call refuses (already true)
        assert promote.write_verified_true(path) is False
    finally:
        path.unlink(missing_ok=True)


# --- promotion decision ----------------------------------------------------------


def test_green_with_live_t1_promotes():
    cache = {"https://en.wikipedia.org/wiki/X": {"alive": True}}
    d = promote.decide(
        band="green", source_urls=["https://en.wikipedia.org/wiki/X"],
        url_cache=cache, crossref_decision=None,
    )
    assert d.promote and d.reason == "green+live-source"


def test_green_with_live_t2_promotes():
    # A reputable T2 spec/benchmark DB (cpubenchmark) that is alive also promotes.
    cache = {"https://www.cpubenchmark.net/cpu.php?id=1": {"alive": True}}
    d = promote.decide(
        band="green", source_urls=["https://www.cpubenchmark.net/cpu.php?id=1"],
        url_cache=cache, crossref_decision=None,
    )
    assert d.promote and d.reason == "green+live-source"


def test_green_with_only_t3_source_held():
    # kaggle (T3) alive is NOT enough to promote even if green.
    cache = {"https://www.kaggle.com/x": {"alive": True}}
    d = promote.decide(
        band="green", source_urls=["https://www.kaggle.com/x"],
        url_cache=cache, crossref_decision=None,
    )
    assert not d.promote


def test_green_without_live_source_blocked():
    d = promote.decide(band="green", source_urls=["https://en.wikipedia.org/wiki/X"],
                       url_cache={}, crossref_decision=None)
    assert not d.promote


def test_yellow_with_crossref_confirm_promotes():
    d = promote.decide(band="yellow", source_urls=[], url_cache={}, crossref_decision="confirm")
    assert d.promote and d.reason == "crossref-confirm"


def test_dead_t1_does_not_promote():
    cache = {"https://en.wikipedia.org/wiki/X": {"alive": False}}
    d = promote.decide(band="green", source_urls=["https://en.wikipedia.org/wiki/X"],
                       url_cache=cache, crossref_decision=None)
    assert not d.promote
