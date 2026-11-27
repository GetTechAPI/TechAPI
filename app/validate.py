"""Validate the records under ``data/`` with the standard library only.

Checks: required fields, the slug convention, value ranges and units, the
folder a record lives in, and that references by slug (brand, soc, cpu, gpu,
socket) resolve. Run with ``python -m app.validate``; it prints every issue and exits
non-zero if there is any. ``pr-checks.yml`` runs it on every PR and
``.github/scripts/build-api.sh`` runs it before the API is generated.

Section numbers in the messages (§14.1, §14.2) are those of
``docs/SPEC.md`` in TechEngine, whose ``app/validate.py`` is the full
validator.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
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
# Media links may only point at free Wikimedia Commons files, never third-party hotlinks.
COMMONS_UPLOAD_RE = re.compile(r"https://upload\.wikimedia\.org/wikipedia/commons/\S+")
COMMONS_FILEPATH_RE = re.compile(r"https://commons\.wikimedia\.org/wiki/Special:FilePath/\S+")
# Chips need identity and a source too. Other specs stay null when no source
# states them. A chip without a release date lives under <manufacturer>/unknown/
# in place of the year folder, and a CPU without a segment under <year>/unknown/
# in place of the segment folder.
SOC_REQUIRED = {"slug", "name", "manufacturer"}
CHIP_UNKNOWN_SEGMENT_DIR = "unknown"
# Devices need identity and a source only. Specs a source does not state
# (release_date, ram_gb, os; a monitor's size_inch, resolution) stay null, and a
# device without a release date lives under <brand>/unknown/.
DEVICE_UNKNOWN_YEAR_DIR = "unknown"
PHONE_REQUIRED = {
    "slug",
    "name",
    "brand",
}

MOBILE_DEVICE_REQUIRED = {
    "slug",
    "name",
    "brand",
    "source_urls",
    "verified",
}

GPU_REQUIRED = {
    "slug",
    "name",
    "manufacturer",
}

CPU_REQUIRED = {
    "slug",
    "name",
    "manufacturer",
}

LAPTOP_REQUIRED = {
    "slug",
    "name",
    "brand",
    "source_urls",
    "verified",
}

MONITOR_REQUIRED = {
    "slug",
    "name",
    "brand",
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
SOCKET_REQUIRED = {
    "slug",
    "name",
    "source_urls",
    "verified",
}

CHIPSET_REQUIRED = {
    "slug",
    "name",
    "manufacturer",
    "source_urls",
    "verified",
}
CHIPSET_SEGMENTS = {"desktop", "mobile", "server", "workstation", "embedded"}
FORM_FACTORS = {"phone", "tablet", "watch", "tv", "other"}
# Categories a catalog entry can be promoted to (``promoted_to`` = "<category>/<slug>").
PROMOTION_TARGETS = {"smartphone", "tablet", "watch", "pda"}
DATE_PRECISIONS = {"day", "month", "year", "year_estimated"}
RELEASE_YEAR_SOURCES = {"model_code", "record"}
RESOLUTION_RE = re.compile(r"^[1-9]\d{1,4}x[1-9]\d{1,4}$")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Sockets and chipsets only: sources often give just the year or the month.
PARTIAL_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


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


def _check_partial_date(name: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, str) or not PARTIAL_DATE_RE.match(value):
        errors.append(
            f"{name}: release_date '{value}' must be YYYY, YYYY-MM or YYYY-MM-DD"
        )


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_integer(
    name: str, field: str, value: object, lo: int, hi: int, errors: list[str]
) -> None:
    """Optional integer in [lo, hi]; true/false and 4.0 are not integers."""
    if value is not None and not _is_integer(value):
        errors.append(f"{name}: {field} must be an integer")
    else:
        _check_range(name, field, value, lo, hi, errors)


def _check_number(
    name: str, field: str, value: object, lo: float, hi: float, errors: list[str]
) -> None:
    """Optional number in [lo, hi]; unlike _check_range, true/false is not a number."""
    if isinstance(value, bool):
        errors.append(f"{name}: {field}={value!r} must be a number")
    else:
        _check_range(name, field, value, lo, hi, errors)


def _check_optional_string(
    name: str, record: dict[str, Any], field: str, errors: list[str]
) -> None:
    value = record.get(field)
    if value is not None and not (isinstance(value, str) and value.strip()):
        errors.append(f"{name}: {field} must be a non-empty string or null")


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


def _image_urls(value: Any) -> Iterator[Any]:
    """Every ``image_url`` at any depth; ``raw_merged_records`` keep merged-in copies."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "image_url":
                yield item
            else:
                yield from _image_urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _image_urls(item)


def _check_media(name: str, record: dict[str, Any], errors: list[str]) -> None:
    """Photos and logos may only link Wikimedia Commons files; photos carry their credit."""
    if any(
        url is not None and not (isinstance(url, str) and COMMONS_UPLOAD_RE.fullmatch(url))
        for url in _image_urls(record)
    ):
        errors.append(
            f"{name}: image_url must be an upload.wikimedia.org/wikipedia/commons file or null"
        )
    elif record.get("image_url") is not None and not (
        record.get("image_license") and record.get("image_attribution")
    ):
        errors.append(f"{name}: image_url needs image_license and image_attribution")
    logo = record.get("logo_url")
    if logo is not None and not (
        isinstance(logo, str)
        and (COMMONS_UPLOAD_RE.fullmatch(logo) or COMMONS_FILEPATH_RE.fullmatch(logo))
    ):
        errors.append(f"{name}: logo_url must be a Wikimedia Commons file or null")


def _check_year_folder(fname: str, rec: dict[str, Any], year: str, errors: list[str]) -> None:
    """Year folder = release year, or DEVICE_UNKNOWN_YEAR_DIR without a release date."""
    release_date = rec.get("release_date")
    if release_date is None:
        if year != DEVICE_UNKNOWN_YEAR_DIR:
            errors.append(
                f"{fname}: lives in year '{year}' but release_date is null "
                f"(expected '{DEVICE_UNKNOWN_YEAR_DIR}/')"
            )
        return
    release_year = str(release_date)[:4]
    if year != release_year:
        errors.append(
            f"{fname}: lives in year '{year}' but release_date starts with '{release_year}'"
        )


def _check_chip_path(fname: str, rec: dict[str, Any], category: str, errors: list[str]) -> None:
    """CPU/GPU year folder: <category>/<manufacturer>/<year or "unknown">/<segment>/<slug>.json."""
    parts = Path(fname).parts
    if len(parts) == 5:
        _check_year_folder(fname, rec, parts[2], errors)
    elif rec.get("release_date") is None:
        errors.append(
            f"{fname}: release_date is null, so it must live at "
            f"'{category}/<manufacturer>/{DEVICE_UNKNOWN_YEAR_DIR}/<segment>/<slug>.json'"
        )


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
        _check_year_folder(fname, rec, parts[2], errors)
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
    _check_year_folder(fname, rec, year, errors)
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
    software = _load("software")
    websites = _load("website")
    catalog = _load("device_catalog")
    sockets = _load("socket")
    chipsets = _load("chipset")

    brand_slugs = {rec["slug"] for _, rec in brands if "slug" in rec}
    soc_slugs = {rec["slug"] for _, rec in socs if "slug" in rec}
    cpu_slugs = {rec["slug"] for _, rec in cpus if "slug" in rec}
    gpu_slugs = {rec["slug"] for _, rec in gpus if "slug" in rec}
    socket_slugs = {rec["slug"] for _, rec in sockets if "slug" in rec}

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
        ("software", software),
        ("website", websites),
        ("device_catalog", catalog),
        ("socket", sockets),
        ("chipset", chipsets),
    ):
        _check_unique_slugs(category, records, errors)
        for fname, rec in records:
            _check_media(fname, rec, errors)

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
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "process_nm", rec.get("process_nm"), 1.0, 100.0, errors)
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")
        # Path convention: soc/<manufacturer>/<year or "unknown">/<slug>.json
        parts = Path(fname).parts
        if len(parts) == 4:
            _check_year_folder(fname, rec, parts[2], errors)
        elif rec.get("release_date") is None:
            errors.append(
                f"{fname}: release_date is null, so it must live at "
                f"'soc/<manufacturer>/{DEVICE_UNKNOWN_YEAR_DIR}/<slug>.json'"
            )

    for fname, rec in phones:
        _check_required(fname, rec, PHONE_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "ram_gb", rec.get("ram_gb"), 0.016, 64, errors)
        _check_identity_fields(fname, rec, errors)
        _check_range(fname, "battery_mah", rec.get("battery_mah"), 500, 12000, errors)
        _check_range(fname, "weight_g", rec.get("weight_g"), 50, 1500, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 5000, errors)
        if rec.get("brand") not in brand_slugs:
            errors.append(f"{fname}: brand '{rec.get('brand')}' not a known brand")
        if rec.get("soc") is not None and rec.get("soc") not in soc_slugs:
            errors.append(f"{fname}: soc '{rec.get('soc')}' not a known SoC")
        _check_variant_path(fname, rec, "smartphone", errors, allow_flat=True)

    for category, records in (("tablet", tablets), ("watch", watches), ("pda", pdas)):
        for fname, rec in records:
            _check_required(fname, rec, MOBILE_DEVICE_REQUIRED, errors)
            _check_source_urls(fname, rec, errors)
            _check_slug(fname, rec.get("slug"), errors)
            if rec.get("release_date") is not None:
                _check_date(fname, rec["release_date"], errors)
            # Lower bound 0.0001: 1990s PDAs shipped with 128-512 KB.
            _check_range(fname, "ram_gb", rec.get("ram_gb"), 0.0001, 64, errors)
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
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "memory_gb", rec.get("memory_gb"), 0.001, 512, errors)
        _check_number(fname, "tdp_w", rec.get("tdp_w"), 1, 3000, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 50, 100000, errors)
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")
        _check_chip_path(fname, rec, "gpu", errors)

    valid_segments = {"desktop", "laptop", "hedt", "server"}
    for fname, rec in cpus:
        _check_required(fname, rec, CPU_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        _check_range(fname, "cores", rec.get("cores"), 1, 512, errors)
        _check_range(fname, "threads", rec.get("threads"), 1, 1024, errors)
        # Fractional watts are real (4.5 W mobile parts, sub-watt embedded ones).
        _check_number(fname, "tdp_w", rec.get("tdp_w"), 0, 10000, errors)
        if "msrp_usd" in rec:
            _check_range(fname, "msrp_usd", rec["msrp_usd"], 20, 50000, errors)
        seg = rec.get("segment")
        if seg is not None and seg not in valid_segments:
            errors.append(f"{fname}: segment '{seg}' not in {sorted(valid_segments)}")
        # Path convention: cpu/<manufacturer>/<year>/<consumer|enterprise>/<slug>.json,
        # with DEVICE_UNKNOWN_YEAR_DIR as the year when the release date is unknown and
        # CHIP_UNKNOWN_SEGMENT_DIR as the folder when the segment is unknown.
        _check_chip_path(fname, rec, "cpu", errors)
        parts = Path(fname).parts
        segment_dir = parts[3] if len(parts) == 5 else None
        if seg is None and segment_dir != CHIP_UNKNOWN_SEGMENT_DIR:
            errors.append(
                f"{fname}: segment is null, so it must live at "
                f"'cpu/<manufacturer>/<year>/{CHIP_UNKNOWN_SEGMENT_DIR}/<slug>.json'"
            )
        elif seg is not None and segment_dir == CHIP_UNKNOWN_SEGMENT_DIR:
            errors.append(
                f"{fname}: lives in '{CHIP_UNKNOWN_SEGMENT_DIR}/' but segment='{seg}'"
            )
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")

    for fname, rec in laptops:
        _check_required(fname, rec, LAPTOP_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if rec.get("release_date") is not None:
            _check_date(fname, rec["release_date"], errors)
        # Lower bound 0.0001: 1980s portables shipped with 256 KB and weighed 7-8 kg.
        _check_number(fname, "ram_gb", rec.get("ram_gb"), 0.0001, 256, errors)
        if rec.get("storage_gb") is not None:
            _check_range(fname, "storage_gb", rec.get("storage_gb"), 1, 65536, errors)
        if rec.get("weight_g") is not None:
            _check_range(fname, "weight_g", rec.get("weight_g"), 300, 10000, errors)
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
        if rec.get("release_date") is not None:
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

    for fname, rec in sockets:
        _check_required(fname, rec, SOCKET_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "verified" in rec and not isinstance(rec["verified"], bool):
            errors.append(f"{fname}: verified must be a boolean")
        _check_string_list(fname, rec, "aliases", errors)
        if rec.get("release_date") is not None:
            _check_partial_date(fname, rec["release_date"], errors)
        _check_optional_string(fname, rec, "package_type", errors)
        _check_integer(fname, "pin_count", rec.get("pin_count"), 1, 10000, errors)
        # A socket shared by several makers has no manufacturer.
        if rec.get("manufacturer") is not None and rec["manufacturer"] not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec['manufacturer']}' not a known brand")
        # Flat: a socket's manufacturer may be null, so there is no maker folder.
        parts = Path(fname).parts
        if len(parts) != 2:
            errors.append(f"{fname}: sockets must live at 'socket/<slug>.json'")
        elif parts[1] != f"{rec.get('slug')}.json":
            errors.append(f"{fname}: filename must match slug '{rec.get('slug')}'")

    for fname, rec in chipsets:
        _check_required(fname, rec, CHIPSET_REQUIRED, errors)
        _check_source_urls(fname, rec, errors)
        _check_slug(fname, rec.get("slug"), errors)
        if "verified" in rec and not isinstance(rec["verified"], bool):
            errors.append(f"{fname}: verified must be a boolean")
        _check_string_list(fname, rec, "aliases", errors)
        if rec.get("memory_types") is not None:
            _check_string_list(fname, rec, "memory_types", errors)
        for field in ("series", "pcie_version"):
            _check_optional_string(fname, rec, field, errors)
        if rec.get("release_date") is not None:
            _check_partial_date(fname, rec["release_date"], errors)
        socket_refs = rec.get("sockets", [])
        if not isinstance(socket_refs, list) or not all(isinstance(s, str) for s in socket_refs):
            errors.append(f"{fname}: sockets must be a list of socket slugs")
        else:
            if len(set(socket_refs)) != len(socket_refs):
                errors.append(f"{fname}: sockets contains duplicates")
            for socket_slug in socket_refs:
                if socket_slug not in socket_slugs:
                    errors.append(f"{fname}: socket '{socket_slug}' not a known socket")
        segment = rec.get("segment")
        if segment is not None and segment not in CHIPSET_SEGMENTS:
            errors.append(f"{fname}: segment '{segment}' not in {sorted(CHIPSET_SEGMENTS)}")
        overclocking = rec.get("cpu_overclocking")
        if overclocking is not None and not isinstance(overclocking, bool):
            errors.append(f"{fname}: cpu_overclocking must be a boolean or null")
        _check_number(fname, "max_memory_gb", rec.get("max_memory_gb"), 0.001, 65536, errors)
        _check_number(fname, "tdp_w", rec.get("tdp_w"), 0.01, 1000, errors)
        _check_number(fname, "process_nm", rec.get("process_nm"), 1, 10000, errors)
        _check_integer(fname, "sata_ports", rec.get("sata_ports"), 0, 64, errors)
        usb_ports = rec.get("usb_ports")
        if usb_ports is not None and not (
            isinstance(usb_ports, dict)
            and all(
                isinstance(key, str) and key.strip() and _is_integer(count) and 0 <= count <= 64
                for key, count in usb_ports.items()
            )
        ):
            errors.append(
                f"{fname}: usb_ports must map a port type to an integer count (0-64), or be null"
            )
        if rec.get("manufacturer") not in brand_slugs:
            errors.append(f"{fname}: manufacturer '{rec.get('manufacturer')}' not a known brand")
        parts = Path(fname).parts
        if len(parts) != 3:
            errors.append(f"{fname}: chipsets must live at 'chipset/<manufacturer>/<slug>.json'")
        else:
            if parts[1] != rec.get("manufacturer"):
                errors.append(
                    f"{fname}: lives in manufacturer '{parts[1]}' but "
                    f"manufacturer='{rec.get('manufacturer')}'"
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
