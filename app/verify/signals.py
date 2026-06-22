"""Per-category cross-field consistency predicates (pure functions).

The structural validator only range-checks single fields. These predicates check
*relations between fields* — the kind of contradiction that means a record cannot
describe a real part (threads < cores, a chip that postdates the device it powers,
a clock that boosts below its base). Each predicate yields a :class:`Signal`.

Severity:
* ``hard`` — logically impossible. Forces the record's band to red regardless of score.
* soft  — implausible but physically possible; only subtracts from the score.

``NA`` results (inputs absent) are neither pass nor fail and never penalize.
"""

from __future__ import annotations

import math
import re
from typing import Any, NamedTuple

# Range table mirrored from app.validate's _check_range call sites, keyed by
# (category, field) -> (lo, hi). A parity smoke test asserts this stays in sync.
RANGES: dict[tuple[str, str], tuple[float, float]] = {
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

_RESOLUTION_RE = re.compile(r"(\d{2,5})\s*[x×]\s*(\d{2,5})")
_ANDROID_RE = re.compile(r"android\s*(\d{1,2})", re.IGNORECASE)

# Earliest plausible release year for a given Android major version (release-vs-era).
_ANDROID_MIN_YEAR: dict[int, int] = {
    4: 2011, 5: 2014, 6: 2015, 7: 2016, 8: 2017, 9: 2018,
    10: 2019, 11: 2020, 12: 2021, 13: 2022, 14: 2023, 15: 2024, 16: 2025,
}


class Signal(NamedTuple):
    name: str
    result: str  # "pass" | "fail" | "na"
    hard: bool = False

    @property
    def failed(self) -> bool:
        return self.result == "fail"


def _num(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _cmp_ge(name: str, a: Any, b: Any, *, hard: bool) -> Signal:
    """``a >= b`` when both present, else NA."""
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return Signal(name, "na", hard)
    return Signal(name, "pass" if x >= y else "fail", hard)


def _year_of(value: Any) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def parse_resolution(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    m = _RESOLUTION_RE.search(value)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _release_not_future(rec: dict[str, Any], now_year: int) -> Signal:
    y = _year_of(rec.get("release_date"))
    if y is None:
        return Signal("release_not_future", "na", hard=True)
    return Signal("release_not_future", "pass" if y <= now_year + 1 else "fail", hard=True)


# --- per-category predicate sets -------------------------------------------------


def cpu_signals(rec: dict[str, Any], now_year: int) -> list[Signal]:
    out = [
        _cmp_ge("threads_ge_cores", rec.get("threads"), rec.get("cores"), hard=True),
        _cmp_ge("boost_ge_base", rec.get("boost_clock_ghz"), rec.get("base_clock_ghz"), hard=True),
        _cmp_ge("max_tdp_ge_tdp", rec.get("max_tdp_w"), rec.get("tdp_w"), hard=False),
        _cmp_ge("passmark_multi_ge_single", rec.get("passmark_cpu_mark"), rec.get("passmark_single"), hard=False),
        _cmp_ge("cb23_multi_ge_single", rec.get("cinebench_r23_multi"), rec.get("cinebench_r23_single"), hard=False),
        _cmp_ge("gb_multi_ge_single", rec.get("geekbench_multi"), rec.get("geekbench_single"), hard=False),
        _release_not_future(rec, now_year),
    ]
    # p_cores + e_cores == cores (hybrid parts), only when both core splits given.
    p, e, c = _num(rec.get("p_cores")), _num(rec.get("e_cores")), _num(rec.get("cores"))
    if p is not None and e is not None and c is not None:
        out.append(Signal("hybrid_core_sum", "pass" if p + e == c else "fail", hard=False))
    else:
        out.append(Signal("hybrid_core_sum", "na", hard=False))
    return out


def gpu_signals(rec: dict[str, Any], now_year: int) -> list[Signal]:
    out = [
        _cmp_ge("boost_ge_base", rec.get("boost_clock_mhz"), rec.get("base_clock_mhz"), hard=True),
        _release_not_future(rec, now_year),
    ]
    # Vendor core field present: nvidia -> cuda_cores, amd/intel -> stream_processors.
    mfr = str(rec.get("manufacturer") or "").lower()
    if mfr == "nvidia":
        has_core = _num(rec.get("cuda_cores")) is not None
    elif mfr in {"amd", "intel"}:
        has_core = _num(rec.get("stream_processors")) is not None
    else:
        has_core = _num(rec.get("cuda_cores")) is not None or _num(rec.get("stream_processors")) is not None
    out.append(Signal("vendor_core_field", "pass" if has_core else "fail", hard=False))
    # RT / Tensor cores only plausible on post-2018 (Turing / RDNA2) parts.
    y = _year_of(rec.get("release_date"))
    rt = _num(rec.get("rt_cores"))
    if rt is not None and rt > 0 and y is not None:
        out.append(Signal("rt_cores_era", "pass" if y >= 2018 else "fail", hard=False))
    else:
        out.append(Signal("rt_cores_era", "na", hard=False))
    return out


def _ppi_signal(display: dict[str, Any]) -> Signal:
    size = _num(display.get("size_inch"))
    ppi = _num(display.get("ppi"))
    res = parse_resolution(display.get("resolution"))
    if size is None or ppi is None or res is None or size <= 0:
        return Signal("ppi_consistent", "na", hard=False)
    w, h = res
    computed = math.hypot(w, h) / size
    return Signal("ppi_consistent", "pass" if abs(computed - ppi) <= 0.15 * ppi else "fail", hard=False)


def _storage_signal(rec: dict[str, Any]) -> Signal:
    vals = rec.get("storage_options_gb")
    if not isinstance(vals, list) or not vals:
        return Signal("storage_sane", "na", hard=False)
    nums = [v for v in vals if isinstance(v, int) and not isinstance(v, bool)]
    if len(nums) != len(vals):
        return Signal("storage_sane", "fail", hard=False)
    ok = all(v >= 1 for v in nums) and len(set(nums)) == len(nums) and nums == sorted(nums)
    return Signal("storage_sane", "pass" if ok else "fail", hard=False)


def _android_era_signal(rec: dict[str, Any]) -> Signal:
    text = f"{rec.get('os') or ''} {rec.get('os_version') or ''}"
    m = _ANDROID_RE.search(text)
    y = _year_of(rec.get("release_date"))
    if not m or y is None:
        return Signal("os_era", "na", hard=False)
    major = int(m.group(1))
    min_year = _ANDROID_MIN_YEAR.get(major)
    if min_year is None:
        return Signal("os_era", "na", hard=False)
    return Signal("os_era", "pass" if y >= min_year else "fail", hard=False)


def mobile_signals(
    rec: dict[str, Any], now_year: int, soc_release: dict[str, str]
) -> list[Signal]:
    """Shared by smartphone / tablet / watch / pda."""
    display = rec.get("display") if isinstance(rec.get("display"), dict) else {}
    out = [
        _ppi_signal(display),
        _storage_signal(rec),
        _android_era_signal(rec),
        _release_not_future(rec, now_year),
    ]
    # ram_gb <= max(storage_options_gb)
    ram = _num(rec.get("ram_gb"))
    vals = rec.get("storage_options_gb")
    if ram is not None and isinstance(vals, list) and vals:
        nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            out.append(Signal("ram_le_storage", "pass" if ram <= max(nums) else "fail", hard=False))
        else:
            out.append(Signal("ram_le_storage", "na", hard=False))
    else:
        out.append(Signal("ram_le_storage", "na", hard=False))
    # SoC should not postdate the device it powers. SOFT, not hard: the dataset's
    # SoC release_dates are largely placeholder "YYYY-01-01" values that skew late
    # (e.g. Snapdragon 888 stored as 2022-01-01), so a mismatch usually means the
    # *SoC* record's date is wrong, not the device. We flag + penalize but don't
    # force-red the device on the strength of a second record's bad date.
    soc = rec.get("soc")
    dev_year = _year_of(rec.get("release_date"))
    soc_year = _year_of(soc_release.get(soc)) if isinstance(soc, str) else None
    if dev_year is not None and soc_year is not None:
        out.append(Signal("soc_not_after_device", "pass" if soc_year <= dev_year else "fail", hard=False))
    else:
        out.append(Signal("soc_not_after_device", "na", hard=False))
    return out


def soc_signals(rec: dict[str, Any], now_year: int) -> list[Signal]:
    out = [_release_not_future(rec, now_year)]
    # process_nm vs era: no sub-7nm before 2017, no sub-3nm before 2022 (coarse guard).
    nm = _num(rec.get("process_nm"))
    y = _year_of(rec.get("release_date"))
    if nm is not None and y is not None:
        too_advanced = (nm < 7 and y < 2017) or (nm < 3 and y < 2022)
        out.append(Signal("process_nm_era", "fail" if too_advanced else "pass", hard=False))
    else:
        out.append(Signal("process_nm_era", "na", hard=False))
    gpu_name = rec.get("gpu_name")
    out.append(
        Signal("gpu_name_present", "pass" if isinstance(gpu_name, str) and gpu_name.strip() else "fail", hard=False)
    )
    return out


def brand_signals(rec: dict[str, Any], now_year: int) -> list[Signal]:
    fy = _num(rec.get("founded_year"))
    if fy is None:
        founded = Signal("founded_not_future", "na", hard=False)
    else:
        founded = Signal("founded_not_future", "pass" if fy <= now_year else "fail", hard=False)
    return [founded]


def signals_for(
    category: str, rec: dict[str, Any], now_year: int, soc_release: dict[str, str]
) -> list[Signal]:
    if category == "cpu":
        return cpu_signals(rec, now_year)
    if category == "gpu":
        return gpu_signals(rec, now_year)
    if category == "soc":
        return soc_signals(rec, now_year)
    if category == "brand":
        return brand_signals(rec, now_year)
    if category in {"smartphone", "tablet", "watch", "pda"}:
        return mobile_signals(rec, now_year, soc_release)
    return []
