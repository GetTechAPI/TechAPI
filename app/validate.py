"""Validate seed JSON against the schema and conventions (§9.3, §15.3).

Checks: required fields, slug convention (§14.1), value ranges/units (§14.3),
and foreign-key integrity by slug. Run with ``python -m app.validate``;
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

# country is optional: many device makers have no sourced country, and it is
# never guessed. A brand without one lives under brand/unknown/.
BRAND_REQUIRED = {"slug", "name", "categories", "source_urls"}
BRAND_UNKNOWN_COUNTRY_DIR = "unknown"
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
    "os",
}

MOBILE_DEVICE_REQUIRED = {
    "slug",
    "name",
    "brand",
    "release_date",
    "ram_gb",
    "os",
    "source_urls",
    "verified",
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

LAPTOP_REQUIRED = {
    "slug",
    "name",
    "brand",
    "release_date",
    "ram_gb",
    "os",
    "source_urls",
    "verified",
}

MONITOR_REQUIRED = {
    "slug",
    "name",
    "brand",
    "release_date",
    "size_inch",
    "resolution",
    "source_urls",
    "verified",
}

GAME_REQUIRED = {
    "slug",
    "name",
    "source_urls",
    "verified",
}

SOFTWARE_REQUIRED = {
    "slug",
    "name",
    "source_urls",
    "verified",
}

WEBSITE_REQUIRED = {
    "slug",
    "name",
    "source_urls",
    "verified",
}

DEVICE_CATALOG_REQUIRED = {
    "slug",
    "name",
    "brand",
    "source_urls",
    "verified",
}
FORM_FACTORS = {"phone", "tablet", "watch", "tv", "other"}
# Categories a catalog entry can be promoted to (``promoted_to`` = "<category>/<slug>").
PROMOTION_TARGETS = {"smartphone", "tablet", "watch", "pda"}
DATE_PRECISIONS = {"day", "month", "year", "year_estimated"}
RELEASE_YEAR_SOURCES = {"model_code", "record"}
RESOLUTION_RE = re.compile(r"^[1-9]\d{1,4}x[1-9]\d{1,4}$")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load(subdir: str) -> list[tuple[str, dict[str, Any]]]:
    path = DATA_DIR / subdir
    if not path.exists():
        return []
    return [
        (str(f.relative_to(DATA_DIR)), json.loads(f.read_text(encoding="utf-8-sig")))
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


def _check_string_list(
    name: str, record: dict[str, Any], field: str, errors: list[str]
) -> None:
    """Optional list field: unique, non-empty strings (absent = [])."""
    if field not in record:
        return
    value = record[field]
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        errors.append(f"{name}: {field} must be a list of non-empty strings")
    elif len(set(value)) != len(value):
        errors.append(f"{name}: {field} contains duplicates")


def _check_identity_fields(name: str, record: dict[str, Any], errors: list[str]) -> None:
    """model_numbers / codenames / release_date_precision on device records."""
    _check_string_list(name, record, "model_numbers", errors)
    _check_string_list(name, record, "codenames", errors)
    precision = record.get("release_date_precision")
    if precision is not None and precision not in DATE_PRECISIONS:
        errors.append(
            f"{name}: release_date_precision '{precision}' not in {sorted(DATE_PRECISIONS)}"
        )


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


def _check_source_urls(name: str, record: dict[str, Any], errors: list[str]) -> None:
    urls = record.get("source_urls")
    if not isinstance(urls, list) or not urls or not all(
        isinstance(url, str) and url.startswith(("http://", "https://")) for url in urls
    ):
        errors.append(f"{name}: source_urls must be a non-empty list of http(s) URL strings")


def _check_storage_options_gb(name: str, record: dict[str, Any], errors: list[str]) -> None:
    values = record.get("storage_options_gb")
    if values is None:
        return
    if not isinstance(values, list):
        errors.append(f"{name}: storage_options_gb must be a list of integer GB values")
        return
    bad = [value for value in values if not isinstance(value, int) or value < 1]
    if bad:
        errors.append(f"{name}: storage_options_gb contains invalid integer GB values {bad}")


def _check_variant_path(
    fname: str,
    rec: dict[str, Any],
    category: str,
    errors: list[str],
    *,
    allow_flat: bool = False,
) -> None:
    parts = Path(fname).parts
    if allow_flat and len(parts) == 4:
        return
    if len(parts) != 5:
        errors.append(
            f"{fname}: {category} variants must live at "
            f"'{category}/<brand>/<year>/<base_model_slug>/<slug>.json'"
        )
        return
    _, brand, year, base_model_slug, filename = parts
    if rec.get("brand") != brand:
        errors.append(f"{fname}: lives in brand '{brand}' but brand='{rec.get('brand')}'")
    release_year = str(rec.get("release_date", ""))[:4]
    if release_year and year != release_year:
        errors.append(
            f"{fname}: lives in year '{year}' but release_date starts with '{release_year}'"
        )
    if rec.get("base_model_slug") and rec.get("base_model_slug") != base_model_slug:
        errors.append(
            f"{fname}: lives under base '{base_model_slug}' but "
            f"base_model_slug='{rec.get('base_model_slug')}'"
        )
    if filename != f"{rec.get('slug')}.json":
        errors.append(f"{fname}: filename must match slug '{rec.get('slug')}'")


def validate() -> list[str]:
    errors: list[str] = []

    brands = _load("brand")
    socs = _load("soc")
    phones = _load("smartphone")
    tablets = _load("tablet")
    watches = _load("watch")
    pdas = _load("pda")
    gpus = _load("gpu")
    cpus = _load("cpu")
    laptops = _load("laptop")
    monitors = _load("monitor")
    games = _load("game")
    software = _load("software")
    websites = _load("website")
    catalog = _load("device_catalog")

    brand_slugs = {rec["slug"] for _, rec in brands if "slug" in rec}
    soc_slugs = {rec["slug"] for _, rec in socs if "slug" in rec}
    cpu_slugs = {rec["slug"] for _, rec in cpus if "slug" in rec}
    gpu_slugs = {rec["slug"] for _, rec in gpus if "slug" in rec}

    for category, records in (
        ("brand", brands),
        ("soc", socs),
        ("smartphone", phones),
        ("tablet", tablets),
        ("watch", watches),
        ("pda", pdas),
        ("gpu", gpus),
        ("cpu", cpus),
        ("laptop", laptops),
        ("monitor", monitors),
        ("game", games),
        ("software", software),
        ("website", websites),
        ("device_catalog", catalog),
    ):
        _check_unique_slugs(category, records, errors)

    for fname, rec in brands:
        _check_required(fname, rec, BRAND_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
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
        # Path convention: brand/<country_lower or "unknown">/<slug>.json
        parts = Path(fname).parts
        folder = country.lower() if isinstance(country, str) else BRAND_UNKNOWN_COUNTRY_DIR
        if len(parts) != 3:
            errors.append(
                f"{fname}: must live at 'brand/<country_lower>/<slug>.json' "
                f"(got {len(parts) - 1} subpath components)"
            )
        elif parts[1] != folder:
            errors.append(
                f"{fname}: lives in '{parts[1]}/' but country={country!r} "
                f"(expected '{folder}/')"
            )

    for fname, rec in socs:
        _check_required(fname, rec, SOC_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "process_nm", rec.get("process_nm"), 1.0, 100.0, errors)
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")

    for fname, rec in phones:
        _check_required(fname, rec, PHONE_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "ram_gb", rec.get("ram_gb"), 0.016, 64, errors)
        _check_identity_fields(fname, rec, errors)
        _check_range(fname, "battery_mah", rec.get("battery_mah"), 500, 12000, errors)
        _check_range(fname, "weight_g", rec.get("weight_g"), 50, 1500, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 5000, errors)
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        if rec.get("soc") not in soc_slugs:
            errors.append(f"{fname}: soc '{rec.get('soc')}' not a known SoC")
        _check_variant_path(fname, rec, "smartphone", errors, allow_flat=True)

    for category, records in (("tablet", tablets), ("watch", watches), ("pda", pdas)):
        for fname, rec in records:
            _check_required(fname, rec, MOBILE_DEVICE_REQUIRED, errors)
            _check_source_urls(fname, rec, errors)
            _check_slug(fname, rec.get("slug"), errors)
            if "release_date" in rec:
                _check_date(fname, rec["release_date"], errors)
            _check_range(fname, "ram_gb", rec.get("ram_gb"), 0.016, 64, errors)
            _check_identity_fields(fname, rec, errors)
            _check_range(fname, "battery_mah", rec.get("battery_mah"), 50, 20000, errors)
            _check_range(fname, "weight_g", rec.get("weight_g"), 10, 2000, errors)
            if "msrp_usd" in rec:
                _check_range(fname, "msrp_usd", rec["msrp_usd"], 10, 10000, errors)
            if rec.get("brand") not in brand_slugs:
                errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
            if rec.get("soc") is not None and rec.get("soc") not in soc_slugs:
                errors.append(f"{fname}: soc '{rec.get('soc')}' not a known SoC")
            _check_storage_options_gb(fname, rec, errors)
            _check_variant_path(fname, rec, category, errors)

    for fname, rec in gpus:
        _check_required(fname, rec, GPU_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
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
        _check_source_urls(fname, rec, errors)
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

    for fname, rec in laptops:
        _check_required(fname, rec, LAPTOP_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "ram_gb", rec.get("ram_gb"), 1, 256, errors)
        if rec.get("storage_gb") is not None:
            _check_range(fname, "storage_gb", rec.get("storage_gb"), 1, 65536, errors)
        if rec.get("weight_g") is not None:
            _check_range(fname, "weight_g", rec.get("weight_g"), 300, 6000, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 50000, errors)
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        if rec.get("cpu") is not None and rec.get("cpu") not in cpu_slugs:
            errors.append(f"{fname}: cpu '{rec.get('cpu')}' not a known CPU")
        if rec.get("gpu") is not None and rec.get("gpu") not in gpu_slugs:
            errors.append(f"{fname}: gpu '{rec.get('gpu')}' not a known GPU")
        _check_variant_path(fname, rec, "laptop", errors, allow_flat=True)

    for fname, rec in monitors:
        _check_required(fname, rec, MONITOR_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "release_date" in rec:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "size_inch", rec.get("size_inch"), 5, 120, errors)
        _check_range(fname, "refresh_hz", rec.get("refresh_hz"), 24, 1000, errors)
        if rec.get("ppi") is not None:
            _check_range(fname, "ppi", rec.get("ppi"), 20, 1000, errors)
        if rec.get("rating") is not None:
            _check_range(fname, "rating", rec.get("rating"), 0, 5, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 10, 50000, errors)
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        _check_variant_path(fname, rec, "monitor", errors, allow_flat=True)

    for fname, rec in games:
        _check_required(fname, rec, GAME_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        if rec.get("rating") is not None:
            _check_range(fname, "rating", rec.get("rating"), 0, 5, errors)
        if rec.get("metacritic") is not None:
            _check_range(fname, "metacritic", rec.get("metacritic"), 0, 100, errors)

    for fname, rec in software:
        _check_required(fname, rec, SOFTWARE_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)

    for fname, rec in websites:
        _check_required(fname, rec, WEBSITE_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("launch_date") is not None:
            _check_date(fname, rec["launch_date"], errors)

    for fname, rec in catalog:
        _check_required(fname, rec, DEVICE_CATALOG_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("base_model_slug") is not None:
            _check_slug(fname, rec["base_model_slug"], errors)
        if "verified" in rec and not isinstance(rec["verified"], bool):
            errors.append(f"{fname}: verified must be a boolean")
        for field in ("model_numbers", "codenames", "marketing_names"):
            _check_string_list(fname, rec, field, errors)
        for field in ("form_factor", "device_type_guess"):
            value = rec.get(field)
            if value is not None and value not in FORM_FACTORS:
                errors.append(f"{fname}: {field} '{value}' not in {sorted(FORM_FACTORS)}")
        for field, lo, hi in (
            ("android_sdk_min", 1, 99),
            ("android_sdk_max", 1, 99),
            ("screen_density_dpi", 50, 1500),
            ("release_year", 1990, 2100),
        ):
            value = rec.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                errors.append(f"{fname}: {field} must be an integer")
            else:
                _check_range(fname, field, value, lo, hi, errors)
        sdk_min, sdk_max = rec.get("android_sdk_min"), rec.get("android_sdk_max")
        if isinstance(sdk_min, int) and isinstance(sdk_max, int) and sdk_max < sdk_min:
            errors.append(f"{fname}: android_sdk_max={sdk_max} < android_sdk_min={sdk_min}")
        if isinstance(rec.get("ram_gb"), bool):
            errors.append(f"{fname}: ram_gb must be a number")
        else:
            _check_range(fname, "ram_gb", rec.get("ram_gb"), 0.016, 64, errors)
        for field in ("soc_raw", "gpu_raw"):
            value = rec.get(field)
            if value is not None and not (isinstance(value, str) and value.strip()):
                errors.append(f"{fname}: {field} must be a non-empty string")
        resolution = rec.get("screen_resolution")
        if resolution is not None and not (
            isinstance(resolution, str) and RESOLUTION_RE.match(resolution)
        ):
            errors.append(f"{fname}: screen_resolution '{resolution}' must look like '1080x2400'")
        year_source = rec.get("release_year_source")
        if year_source is not None and year_source not in RELEASE_YEAR_SOURCES:
            errors.append(
                f"{fname}: release_year_source '{year_source}' "
                f"not in {sorted(RELEASE_YEAR_SOURCES)}"
            )
        if (rec.get("release_year") is None) != (year_source is None):
            errors.append(f"{fname}: release_year and release_year_source must be set together")
        if rec.get("soc") is not None and rec.get("soc") not in soc_slugs:
            errors.append(f"{fname}: soc '{rec.get('soc')}' not a known SoC")
        promoted = rec.get("promoted_to")
        if promoted is not None:
            target, _, target_slug = str(promoted).partition("/")
            if target not in PROMOTION_TARGETS or not SLUG_RE.match(target_slug):
                errors.append(
                    f"{fname}: promoted_to '{promoted}' must be '<category>/<slug>' "
                    f"with category in {sorted(PROMOTION_TARGETS)}"
                )
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        # No year folder: a catalog entry's release date is unknown by definition.
        parts = Path(fname).parts
        if len(parts) != 3:
            errors.append(f"{fname}: device_catalog entries must live at "
                          "'device_catalog/<brand>/<slug>.json'")
        else:
            if parts[1] != rec.get("brand"):
                errors.append(
                    f"{fname}: lives in brand '{parts[1]}' but brand='{rec.get('brand')}'"
                )
            if parts[2] != f"{rec.get('slug')}.json":
                errors.append(f"{fname}: filename must match slug '{rec.get('slug')}'")

    return errors


def run() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
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
