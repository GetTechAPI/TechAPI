"""Open scoring algorithm (§8).

Scores are on a 0–100 scale, carry an ``algorithm_version`` (§8.2), and return
``None`` for any category whose inputs are missing (never 0).

Phase 0 uses **reference-based** min–max normalization: each metric is scaled
against fixed reference bounds representative of the 2025 flagship range. This
keeps a single detail response self-contained. Phase 1 switches to dataset-wide
min–max re-normalized yearly (§8.4).

Weights are kept here as module constants for Phase 0; §8.2 calls for moving
them to ``config/scoring.yaml`` in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.models.smartphone import Smartphone
from app.models.soc import SoC

ALGORITHM_VERSION = settings.scoring_algorithm_version


@dataclass(frozen=True, slots=True)
class Bounds:
    """Reference min/max used for min–max normalization."""

    lo: float
    hi: float


# Reference bounds (2025 flagship range).
GEEKBENCH_SINGLE = Bounds(1000, 3500)
GEEKBENCH_MULTI = Bounds(3000, 10000)
ANTUTU = Bounds(800_000, 3_000_000)
RAM = Bounds(4, 24)
BATTERY = Bounds(3000, 6000)
WIRED_CHARGE = Bounds(15, 120)
WIRELESS_CHARGE = Bounds(0, 50)
PROCESS_NM = Bounds(2.0, 7.0)  # smaller is better → inverted
BRIGHTNESS = Bounds(800, 3000)
PPI = Bounds(300, 600)
REFRESH = Bounds(60, 144)
MAIN_CAMERA_MP = Bounds(12, 200)
MSRP = Bounds(300, 1600)


def _normalize(value: float, bounds: Bounds, *, invert: bool = False) -> float:
    """Min–max normalize ``value`` into 0–100, clamped to the bounds."""
    span = bounds.hi - bounds.lo
    if span <= 0:
        return 0.0
    scaled = (value - bounds.lo) / span
    scaled = max(0.0, min(1.0, scaled))
    if invert:
        scaled = 1.0 - scaled
    return round(scaled * 100, 1)


@dataclass(slots=True)
class Scores:
    """Computed category scores (§8.1)."""

    algorithm_version: str
    overall: float | None
    performance: float | None
    camera: float | None
    battery: float | None
    display: float | None
    value: float | None


def _performance_score(soc: SoC, ram_gb: int) -> float | None:
    """Performance from CPU/GPU benchmarks + RAM (§8.3)."""
    if soc.geekbench_single is None or soc.geekbench_multi is None:
        return None
    single = _normalize(soc.geekbench_single, GEEKBENCH_SINGLE)
    multi = _normalize(soc.geekbench_multi, GEEKBENCH_MULTI)
    # AnTuTu is a whole-system score; used here as a GPU/system proxy (ADR-006: input only).
    gpu = _normalize(soc.antutu_score, ANTUTU) if soc.antutu_score is not None else multi
    ram = _normalize(ram_gb, RAM)
    return round(single * 0.25 + multi * 0.30 + gpu * 0.30 + ram * 0.15, 1)


def _camera_score(cameras: list[dict[str, Any]]) -> float | None:
    if not cameras:
        return None
    main = next((c for c in cameras if c.get("type") == "main"), cameras[0])
    mp = main.get("mp")
    if mp is None:
        return None
    base = _normalize(float(mp), MAIN_CAMERA_MP)
    ois_bonus = 8.0 if main.get("ois") else 0.0
    rear = [c for c in cameras if c.get("type") != "selfie"]
    versatility = min(len(rear), 4) / 4 * 20  # up to +20 for a full rear array
    return round(min(100.0, base * 0.6 + versatility + ois_bonus), 1)


def _battery_score(
    battery_mah: int,
    wired_w: float | None,
    wireless_w: float | None,
    process_nm: float | None,
) -> float | None:
    if battery_mah <= 0:
        return None
    capacity = _normalize(battery_mah, BATTERY)
    wired = _normalize(wired_w, WIRED_CHARGE) if wired_w is not None else 0.0
    wireless = _normalize(wireless_w, WIRELESS_CHARGE) if wireless_w is not None else 0.0
    efficiency = _normalize(process_nm, PROCESS_NM, invert=True) if process_nm is not None else 50.0
    return round(capacity * 0.45 + wired * 0.20 + wireless * 0.10 + efficiency * 0.25, 1)


def _display_score(display: dict[str, Any]) -> float | None:
    if not display:
        return None
    refresh = display.get("refresh_hz")
    brightness = display.get("brightness_nits")
    ppi = display.get("ppi")
    if refresh is None and brightness is None and ppi is None:
        return None
    refresh_n = _normalize(float(refresh), REFRESH) if refresh is not None else 50.0
    brightness_n = _normalize(float(brightness), BRIGHTNESS) if brightness is not None else 50.0
    ppi_n = _normalize(float(ppi), PPI) if ppi is not None else 50.0
    return round(refresh_n * 0.35 + brightness_n * 0.35 + ppi_n * 0.30, 1)


def _value_score(overall: float | None, msrp_usd: int | None) -> float | None:
    if overall is None or not msrp_usd:
        return None
    # Higher overall per dollar → higher value, normalized against the MSRP range.
    affordability = _normalize(float(msrp_usd), MSRP, invert=True)
    return round(overall * 0.5 + affordability * 0.5, 1)


def compute_scores(smartphone: Smartphone, soc: SoC) -> Scores:
    """Compute all category scores for a smartphone (§8)."""
    performance = _performance_score(soc, smartphone.ram_gb)
    camera = _camera_score(smartphone.cameras)
    battery = _battery_score(
        smartphone.battery_mah,
        smartphone.charging_wired_w,
        smartphone.charging_wireless_w,
        soc.process_nm,
    )
    display = _display_score(smartphone.display)

    components = [s for s in (performance, camera, battery, display) if s is not None]
    overall = round(sum(components) / len(components), 1) if components else None
    value = _value_score(overall, smartphone.msrp_usd)

    return Scores(
        algorithm_version=ALGORITHM_VERSION,
        overall=overall,
        performance=performance,
        camera=camera,
        battery=battery,
        display=display,
        value=value,
    )
