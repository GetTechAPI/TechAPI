"""Unit tests for cross-field consistency predicates (app.verify.signals)."""

from app.verify import signals

NOW = 2026
NO_SOC: dict[str, str] = {}


def _named(sigs, name):
    return next(s for s in sigs if s.name == name)


def test_threads_below_cores_is_hard_fail():
    rec = {"cores": 8, "threads": 4, "release_date": "2020-01-01"}
    s = _named(signals.cpu_signals(rec, NOW), "threads_ge_cores")
    assert s.failed and s.hard


def test_threads_ge_cores_passes():
    rec = {"cores": 8, "threads": 16, "release_date": "2020-01-01"}
    assert _named(signals.cpu_signals(rec, NOW), "threads_ge_cores").result == "pass"


def test_boost_below_base_is_hard_fail():
    rec = {"base_clock_ghz": 3.5, "boost_clock_ghz": 3.0, "cores": 4, "threads": 4}
    s = _named(signals.cpu_signals(rec, NOW), "boost_ge_base")
    assert s.failed and s.hard


def test_missing_inputs_are_na_not_fail():
    rec = {"cores": 4, "threads": 4}  # no clocks
    assert _named(signals.cpu_signals(rec, NOW), "boost_ge_base").result == "na"


def test_future_release_is_hard_fail():
    rec = {"cores": 1, "threads": 1, "release_date": "2099-01-01"}
    s = _named(signals.cpu_signals(rec, NOW), "release_not_future")
    assert s.failed and s.hard


def test_hybrid_core_sum():
    ok = {"cores": 8, "threads": 8, "p_cores": 4, "e_cores": 4}
    bad = {"cores": 8, "threads": 8, "p_cores": 4, "e_cores": 2}
    assert _named(signals.cpu_signals(ok, NOW), "hybrid_core_sum").result == "pass"
    assert _named(signals.cpu_signals(bad, NOW), "hybrid_core_sum").result == "fail"


def test_gpu_boost_and_vendor_core():
    rec = {
        "manufacturer": "nvidia", "base_clock_mhz": 1500, "boost_clock_mhz": 1800,
        "cuda_cores": 4096, "release_date": "2022-01-01",
    }
    sigs = signals.gpu_signals(rec, NOW)
    assert _named(sigs, "boost_ge_base").result == "pass"
    assert _named(sigs, "vendor_core_field").result == "pass"


def test_gpu_rt_cores_before_turing_fail():
    rec = {"manufacturer": "nvidia", "rt_cores": 50, "release_date": "2015-01-01",
           "cuda_cores": 2048}
    assert _named(signals.gpu_signals(rec, NOW), "rt_cores_era").result == "fail"


def test_ppi_consistency():
    # 1792x828 over 6.1" -> ~326 ppi (matches iPhone XR).
    good = {"display": {"size_inch": 6.1, "resolution": "1792x828", "ppi": 326}}
    bad = {"display": {"size_inch": 6.1, "resolution": "1792x828", "ppi": 500}}
    assert _named(signals.mobile_signals(good, NOW, NO_SOC), "ppi_consistent").result == "pass"
    assert _named(signals.mobile_signals(bad, NOW, NO_SOC), "ppi_consistent").result == "fail"


def test_storage_must_be_sorted_positive_unique():
    good = {"storage_options_gb": [64, 128, 256]}
    bad = {"storage_options_gb": [256, 64]}
    assert _named(signals.mobile_signals(good, NOW, NO_SOC), "storage_sane").result == "pass"
    assert _named(signals.mobile_signals(bad, NOW, NO_SOC), "storage_sane").result == "fail"


def test_soc_not_after_device_is_soft():
    rec = {"soc": "chip-x", "release_date": "2020-01-01"}
    soc_release = {"chip-x": "2022-01-01"}
    s = _named(signals.mobile_signals(rec, NOW, soc_release), "soc_not_after_device")
    assert s.failed and not s.hard  # flagged but never forces red


def test_soc_process_nm_era():
    rec = {"process_nm": 5.0, "release_date": "2010-01-01", "gpu_name": "x"}
    assert _named(signals.soc_signals(rec, NOW), "process_nm_era").result == "fail"
