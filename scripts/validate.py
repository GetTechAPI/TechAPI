"""Validate seed JSON against the schema and conventions (§9.3, §15.3).

Checks: required fields, slug convention (§14.1), value ranges/units (§14.3),
and foreign-key integrity by slug. Run with ``python -m scripts.validate``;
exits non-zero on the first failure set (used by CI ``validate-data.yml``).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

BRAND_REQUIRED = {"slug", "name", "country", "categories"}
BRAND_CATEGORIES = {
    "smartphone-oem",
    "soc-designer",
    "cpu-designer",
    "gpu-designer",
    "ip-licensor",
    "aib-partner",
    "pc-oem",
    "chipset-maker",
    "sub-brand",
    "defunct",
}
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
SOC_REQUIRED = {"slug", "name", "manufacturer", "release_date", "process_nm", "gpu_name"}
PHONE_REQUIRED = {
    "slug",
    "name",
    "brand",
    "soc",
    "release_date",
    "ram_gb",
    "battery_mah",
    "weight_g",
    "os",
}

GPU_REQUIRED = {
    "slug",
    "name",
    "manufacturer",
    "architecture",
    "release_date",
    "memory_gb",
    "memory_type",
    "memory_bus_bit",
    "base_clock_mhz",
    "boost_clock_mhz",
    "tdp_w",
    "pcie_version",
}

CPU_REQUIRED = {
    "slug",
    "name",
    "manufacturer",
    "release_date",
    "segment",
    "architecture",
    "cores",
    "threads",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load(subdir: str) -> list[tuple[str, dict[str, Any]]]:
    path = DATA_DIR / subdir
    if not path.exists():
        return []
    return [
        (str(f.relative_to(DATA_DIR)), json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(path.rglob("*.json"))  # recurse into brand subfolders
    ]


def _check_required(
    name: str, record: dict[str, Any], required: set[str], errors: list[str]
) -> None:
    missing = required - record.keys()
    if missing:
        errors.append(f"{name}: missing required fields {sorted(missing)}")


def _check_slug(name: str, slug: object, errors: list[str]) -> None:
    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        errors.append(f"{name}: invalid slug '{slug}' (must be kebab-case, §14.1)")


def _check_range(
    name: str, field: str, value: object, lo: float, hi: float, errors: list[str]
) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or not (lo <= value <= hi):
        errors.append(f"{name}: {field}={value} out of range [{lo}, {hi}]")


def _check_date(name: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, str) or not DATE_RE.match(value):
        errors.append(f"{name}: release_date '{value}' must be ISO 8601 YYYY-MM-DD (§14.2)")


def _check_unique_slugs(
    category: str, records: list[tuple[str, dict[str, Any]]], errors: list[str]
) -> None:
    """Each category's `slug` must be unique — seed/dump load into a UNIQUE column."""
    seen: dict[str, str] = {}
    for fname, rec in records:
        slug = rec.get("slug")
        if not isinstance(slug, str):
            continue
        if slug in seen:
            errors.append(
                f"{fname}: duplicate {category} slug '{slug}' (also in {seen[slug]})"
            )
        else:
            seen[slug] = fname


def validate() -> list[str]:
    errors: list[str] = []

    brands = _load("brand")
    socs = _load("soc")
    phones = _load("smartphone")
    gpus = _load("gpu")
    cpus = _load("cpu")

    brand_slugs = {rec["slug"] for _, rec in brands if "slug" in rec}
    soc_slugs = {rec["slug"] for _, rec in socs if "slug" in rec}

    for category, records in (
        ("brand", brands),
        ("soc", socs),
        ("smartphone", phones),
        ("gpu", gpus),
        ("cpu", cpus),
    ):
        _check_unique_slugs(category, records, errors)

    for fname, rec in brands:
        _check_required(fname, rec, BRAND_REQUIRED, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "founded_year" in rec:
            _check_range(fname, "founded_year", rec["founded_year"], 1800, 2100, errors)
        country = rec.get("country")
        if country is not None and not (isinstance(country, str) and COUNTRY_RE.match(country)):
            errors.append(f"{fname}: country '{country}' must be ISO 3166 alpha-2 (e.g. 'KR')")
        cats = rec.get("categories")
        if not isinstance(cats, list) or not cats:
            errors.append(f"{fname}: categories must be a non-empty list")
        else:
            bad = [c for c in cats if c not in BRAND_CATEGORIES]
            if bad:
                errors.append(
                    f"{fname}: invalid categories {bad}; allowed = {sorted(BRAND_CATEGORIES)}"
                )
            if len(set(cats)) != len(cats):
                errors.append(f"{fname}: categories contains duplicates")
        # Path convention: brand/<country_lower>/<slug>.json
        parts = Path(fname).parts
        if len(parts) != 3:
            errors.append(
                f"{fname}: must live at 'brand/<country_lower>/<slug>.json' "
                f"(got {len(parts) - 1} subpath components)"
            )
        elif isinstance(country, str) and parts[1] != country.lower():
            errors.append(
                f"{fname}: lives in '{parts[1]}/' but country='{country}' "
                f"(expected '{country.lower()}/')"
            )

    for fname, rec in socs:
        _check_required(fname, rec, SOC_REQUIRED, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "process_nm", rec.get("process_nm"), 1.0, 100.0, errors)
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")

    for fname, rec in phones:
        _check_required(fname, rec, PHONE_REQUIRED, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "ram_gb", rec.get("ram_gb"), 1, 64, errors)
        _check_range(fname, "battery_mah", rec.get("battery_mah"), 500, 12000, errors)
        _check_range(fname, "weight_g", rec.get("weight_g"), 50, 500, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 5000, errors)
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        if rec.get("soc") not in soc_slugs:
            errors.append(f"{fname}: soc '{rec.get('soc')}' not a known SoC")

    for fname, rec in gpus:
        _check_required(fname, rec, GPU_REQUIRED, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "memory_gb", rec.get("memory_gb"), 0.001, 512, errors)
        _check_range(fname, "tdp_w", rec.get("tdp_w"), 1, 3000, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 100000, errors)
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")

    valid_segments = {"desktop", "laptop", "hedt", "server"}
    for fname, rec in cpus:
        _check_required(fname, rec, CPU_REQUIRED, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "cores", rec.get("cores"), 1, 512, errors)
        _check_range(fname, "threads", rec.get("threads"), 1, 1024, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 20, 50000, errors)
        if rec.get("segment") not in valid_segments:
            seg = rec.get("segment")
            errors.append(f"{fname}: segment '{seg}' not in {sorted(valid_segments)}")
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")

    return errors


def run() -> int:
    errors = validate()
    if errors:
        print(f"❌ Data validation failed ({len(errors)} issue(s)):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("✅ Data validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
