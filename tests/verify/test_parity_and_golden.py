"""Guardrail tests:

* RANGES parity — signals.RANGES must not drift from app.validate's bounds.
* Golden subset — the offline scorer, blind to the ``verified`` flag, should
  reproduce the human-curated verified CPU set with high agreement. This is the
  empirical justification for using the offline score to drive promotion.
"""

import pytest

from app.verify import offline, signals
from app.verify.common import foreign_key_sets, load_all


def test_ranges_parity_with_validator():
    """If app.validate's numeric bounds change, this test should force a sync.

    Mirrors the _check_range call sites in app/validate.py. Keep in lockstep.
    """
    expected = {
        ("brand", "founded_year"): (1800, 2100),
        ("soc", "process_nm"): (1.0, 100.0),
        ("smartphone", "ram_gb"): (1, 64),
        ("smartphone", "battery_mah"): (500, 12000),
        ("smartphone", "weight_g"): (50, 500),
        ("smartphone", "msrp_usd"): (50, 5000),
        ("mobile", "ram_gb"): (0.016, 64),
        ("mobile", "battery_mah"): (50, 20000),
        ("mobile", "weight_g"): (10, 2000),
        ("mobile", "msrp_usd"): (10, 10000),
        ("gpu", "memory_gb"): (0.001, 512),
        ("gpu", "tdp_w"): (1, 3000),
        ("gpu", "msrp_usd"): (50, 100000),
        ("cpu", "cores"): (1, 512),
        ("cpu", "threads"): (1, 1024),
        ("cpu", "msrp_usd"): (20, 50000),
    }
    assert signals.RANGES == expected


@pytest.mark.slow
def test_verified_cpus_land_green():
    """≥95% of already-verified CPUs should score green under the offline tier."""
    records = load_all()
    _, _, soc_release = foreign_key_sets(records)
    now_year = offline.now_year_today()

    verified = [r for r in records["cpu"] if r.verified and r.slug]
    if not verified:
        pytest.skip("no verified CPUs in dataset")
    green = sum(
        1 for r in verified
        if offline.score_record(r, now_year, soc_release).band == "green"
    )
    ratio = green / len(verified)
    assert ratio >= 0.95, f"only {ratio:.1%} of verified CPUs scored green"
