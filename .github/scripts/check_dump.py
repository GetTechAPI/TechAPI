"""Check a generated API dump against the data it was generated from.

For each collection the record count must agree in five places: the data
files (names starting with "_" excluded), the v1/index.json manifest, the
collection's index.json, its results list, and the slug pages on disk. Scored
collections also need a score page per slug. openapi.json and the hand-made
v1/games pointer must exist. The table goes to the job summary when
GITHUB_STEP_SUMMARY is set; any mismatch exits 1.

Run it from TechEngine/, so app.* resolves to the engine:
    python ../.github/scripts/check_dump.py ../site/public ../data
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from app.categories import CATEGORIES, COLLECTIONS  # noqa: E402
from app.dump import SCORED  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(public: Path, data: Path) -> int:
    v1 = public / "v1"
    manifest = load(v1 / "index.json")["collections"]
    bad: list[str] = []
    rows: list[str] = []
    for category in CATEGORIES:
        name = COLLECTIONS[category]
        files = sum(1 for p in (data / category).rglob("*.json") if not p.name.startswith("_"))
        index = load(v1 / name / "index.json")
        slugs = [r["slug"] for r in index["results"]]
        pages = sum((v1 / name / s / "index.json").is_file() for s in slugs)
        scores = sum((v1 / name / s / "score" / "index.json").is_file() for s in slugs)
        listed = manifest.get(name, {}).get("count")
        ok = files == listed == index["count"] == len(slugs) == pages
        if name in SCORED:
            ok = ok and scores == len(slugs)
        else:
            scores = "-"
        rows.append(f"| {name} | {files} | {listed} | {index['count']} | {pages} | {scores} | {'ok' if ok else '**FAIL**'} |")
        if not ok:
            bad.append(name)
    for extra in (public / "openapi.json", v1 / "games" / "index.json"):
        if not extra.is_file():
            bad.append(str(extra.relative_to(public)))

    table = [
        "## Generated API",
        "",
        "| Collection | Data files | Manifest | Index | Pages | Score pages | |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        *rows,
        "",
    ]
    print("\n".join(table))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("\n".join(table) + "\n")
    if bad:
        print(f"::error::generated API does not match data: {', '.join(bad)}")
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
