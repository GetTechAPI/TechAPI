"""Command-line entry for the verification layer: ``python -m app.verify ...``.

Phase A implements the offline tier:

* ``score``  — score records, print a band histogram, append Tier 0 ledger entries.
* ``report`` — summarize the latest ledger state per category.

Network subcommands (``check-urls``, ``crossref``, ``promote``) are added in later
phases; they are declared here so ``--help`` lists the eventual surface.
"""

from __future__ import annotations

import argparse
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone

from . import crossref, http_check, ledger, offline, promote
from .common import (
    CATEGORIES,
    SCORES_PATH,
    Record,
    configure_stdout,
    foreign_key_sets,
    load_all,
    repo_path,
)

BANDS = ("green", "yellow", "red")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _changed_data_slugs() -> set[str]:
    """Repo-relative data/ paths changed vs origin/main (for CI --changed)."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD", "--", "data/"],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        out = ""
    # strip leading "data/" so it matches Record.path
    paths = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("data/") and line.endswith(".json"):
            paths.add(line[len("data/"):])
    return paths


def _iter_selected(
    records: dict[str, list[Record]],
    categories: tuple[str, ...],
    unverified_only: bool,
    changed: set[str] | None,
    limit: int | None,
):
    count = 0
    for cat in categories:
        for rec in records[cat]:
            if unverified_only and rec.verified:
                continue
            if changed is not None and rec.path not in changed:
                continue
            yield rec
            count += 1
            if limit is not None and count >= limit:
                return


def cmd_score(args: argparse.Namespace) -> int:
    records = load_all()
    _, _, soc_release = foreign_key_sets(records)
    now_year = offline.now_year_today()
    ts = _now_iso()

    categories = tuple(args.category) if args.category else CATEGORIES
    changed = _changed_data_slugs() if args.changed else None

    # The scores cache is a full-dataset snapshot; only rewrite it on a full run.
    full_scope = args.category is None and args.max is None and not args.changed
    write_cache = full_scope and not args.no_cache

    # category -> band -> count
    hist: dict[str, Counter] = defaultdict(Counter)
    hard_flags: Counter = Counter()
    entries = []
    scored = 0

    for rec in _iter_selected(records, categories, args.unverified_only, changed, args.max):
        if not rec.slug:
            continue
        s = offline.score_record(rec, now_year, soc_release)
        hist[rec.category][s.band] += 1
        scored += 1
        for f in s.flags:
            if f.startswith("!"):
                hard_flags[f] += 1
        if write_cache:
            entries.append(
                ledger.make_tier0_entry(
                    rec.category, rec.slug, rec.path, rec.content_hash(),
                    s.score, s.band, s.subscores, s.flags, s.best_tier, ts,
                )
            )

    if write_cache:
        ledger.replace_all(entries, SCORES_PATH)

    if getattr(args, "format", "text") == "md":
        _print_markdown(hist, scored, hard_flags)
    else:
        _print_histogram(hist, scored, hard_flags, wrote_cache=write_cache)
    return 0


def _print_histogram(hist, scored, hard_flags, wrote_cache) -> None:
    print(f"Tier 0 offline score — {scored} record(s)\n")
    header = f"{'category':<12} {'green':>8} {'yellow':>8} {'red':>8} {'total':>8}"
    print(header)
    print("-" * len(header))
    totals = Counter()
    for cat in CATEGORIES:
        if cat not in hist:
            continue
        c = hist[cat]
        tot = sum(c.values())
        totals.update(c)
        print(f"{cat:<12} {c['green']:>8} {c['yellow']:>8} {c['red']:>8} {tot:>8}")
    print("-" * len(header))
    gtot = sum(totals.values()) or 1
    print(
        f"{'ALL':<12} {totals['green']:>8} {totals['yellow']:>8} "
        f"{totals['red']:>8} {sum(totals.values()):>8}"
    )
    print(
        f"\nbands: green {100*totals['green']/gtot:.1f}%  "
        f"yellow {100*totals['yellow']/gtot:.1f}%  red {100*totals['red']/gtot:.1f}%"
    )
    if hard_flags:
        print("\ntop hard violations:")
        for name, n in hard_flags.most_common(10):
            print(f"  {n:>7}  {name}")
    if wrote_cache:
        print("\ncache: wrote full Tier 0 scores to data/_verify/state/scores.jsonl")


def _print_markdown(hist, scored, hard_flags) -> None:
    """GitHub-flavored markdown table — readable in PR comments (mirrors the
    TechEngineBot validation-stats style)."""
    if scored == 0:
        print("_No records scored._")
        return
    totals = Counter()
    rows = []
    for cat in CATEGORIES:
        if cat not in hist:
            continue
        c = hist[cat]
        tot = sum(c.values())
        totals.update(c)
        gpct = 100 * c["green"] / tot if tot else 0.0
        rows.append(
            f"| {cat} | {tot} | {c['green']} | {c['yellow']} | {c['red']} | {gpct:.1f}% |"
        )
    gtot = sum(totals.values()) or 1
    print(f"**{scored} record(s) scored.**\n")
    print("| Category | Total | 🟢 Green | 🟡 Yellow | 🔴 Red | Green % |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        print(r)
    print(
        f"| **All** | **{sum(totals.values())}** | **{totals['green']}** | "
        f"**{totals['yellow']}** | **{totals['red']}** | "
        f"**{100*totals['green']/gtot:.1f}%** |"
    )
    if hard_flags:
        print("\n**Hard violations** (forced red):\n")
        print("| Count | Check |")
        print("| ---: | --- |")
        for name, n in hard_flags.most_common(10):
            print(f"| {n} | `{name}` |")


def cmd_report(args: argparse.Namespace) -> int:
    if not SCORES_PATH.exists():
        print("no scores cache — run `python -m app.verify score` first")
        return 0
    hist: dict[str, Counter] = defaultdict(Counter)
    hard_flags: Counter = Counter()
    for entry in ledger.iter_entries(SCORES_PATH):
        cat = entry.get("category")
        t0 = entry.get("tier0", {})
        band = t0.get("band")
        if cat and band:
            hist[cat][band] += 1
        for f in t0.get("flags", []):
            if isinstance(f, str) and f.startswith("!"):
                hard_flags[f] += 1
    scored = sum(sum(c.values()) for c in hist.values())
    _print_histogram(hist, scored, hard_flags, wrote_cache=False)

    # Promotion decisions live in the git-tracked ledger.
    promoted: Counter = Counter()
    for (cat, _slug), entry in ledger.latest_by_key().items():
        if entry.get("decision") == "promote":
            promoted[cat] += 1
    if sum(promoted.values()):
        print("\npromoted to verified (ledger):")
        for cat, n in promoted.most_common():
            print(f"  {n:>7}  {cat}")
    return 0


def _ranked_unverified(records, soc_release, now_year, categories):
    """Unverified records of the given categories, scored, highest-confidence first."""
    scored = []
    for cat in categories:
        for rec in records[cat]:
            if rec.verified or not rec.slug:
                continue
            s = offline.score_record(rec, now_year, soc_release)
            scored.append((s.score, rec))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [rec for _score, rec in scored]


def cmd_check_urls(args: argparse.Namespace) -> int:
    records = load_all()
    _, _, soc_release = foreign_key_sets(records)
    now_year = offline.now_year_today()
    categories = tuple(args.category) if args.category else CATEGORIES

    frontier = _ranked_unverified(records, soc_release, now_year, categories)
    if args.max is not None:
        frontier = frontier[: args.max]

    urls: list[str] = []
    for rec in frontier:
        urls.extend(u for u in rec.data.get("source_urls", []) if isinstance(u, str))
    targets = http_check.dedupe_urls(urls)

    cache = http_check.load_cache()
    now = datetime.now(timezone.utc)
    if args.recheck:
        todo = targets
    else:
        todo = [u for u in targets if not (
            u in cache and http_check.is_fresh(cache[u], now, args.ttl_days)
        )]

    print(
        f"check-urls: {len(frontier)} record(s) -> {len(targets)} unique URL(s); "
        f"{len(targets) - len(todo)} fresh in cache, checking {len(todo)}"
    )
    if not todo:
        _summarize_cache(cache, targets)
        return 0

    ts = _now_iso()
    results = http_check.check_urls(
        todo,
        max_workers=args.workers,
        min_interval=args.min_interval,
    )
    for r in results:
        cache[r.url] = http_check.result_to_entry(r, ts)
    http_check.save_cache(cache)
    print(f"cache: wrote {len(cache)} URL result(s) to data/_verify/state/url_cache.jsonl")
    _summarize_cache(cache, targets)
    return 0


def _summarize_cache(cache, targets) -> None:
    from collections import Counter
    alive = sum(1 for u in targets if cache.get(u, {}).get("alive"))
    dead = sum(1 for u in targets if u in cache and not cache[u].get("alive"))
    print(f"\nliveness over {len(targets)} targeted URL(s): {alive} alive, {dead} dead")
    reasons = Counter(
        cache[u].get("reason") for u in targets
        if u in cache and not cache[u].get("alive")
    )
    if reasons:
        print("dead reasons:")
        for reason, n in reasons.most_common(10):
            print(f"  {n:>6}  {reason}")


def cmd_crossref(args: argparse.Namespace) -> int:
    records = load_all()
    _, _, soc_release = foreign_key_sets(records)
    now_year = offline.now_year_today()
    categories = tuple(args.category) if args.category else CATEGORIES

    # Escalation target: yellow/red unverified frontier (greens promote via live T1).
    targets = []
    for rec in _ranked_unverified(records, soc_release, now_year, categories):
        s = offline.score_record(rec, now_year, soc_release)
        if s.band in ("yellow", "red"):
            targets.append(rec)
    targets = targets[: args.max]

    fetcher = crossref.WikipediaFetcher()
    cache = promote.load_crossref_cache()
    ts = _now_iso()
    decisions = Counter()
    new_entries = []
    for rec in targets:
        key = (rec.category, rec.slug)
        if not args.recheck and key in cache:
            decisions[cache[key].get("decision", "cached")] += 1
            continue
        res = crossref.crossref_record(rec.data, fetcher)
        decisions[res.decision] += 1
        new_entries.append({
            "ts": ts, "category": rec.category, "slug": rec.slug,
            "source": res.source, "decision": res.decision,
            "exact_heading": res.exact_heading, "matched_url": res.matched_url,
        })
    if new_entries:
        cache.update({(e["category"], e["slug"]): e for e in new_entries})
        ledger.replace_all(list(cache.values()), promote.CROSSREF_CACHE_PATH)

    print(f"crossref: examined {len(targets)} record(s)")
    for decision, n in decisions.most_common():
        print(f"  {n:>6}  {decision}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    records = load_all()
    _, _, soc_release = foreign_key_sets(records)
    now_year = offline.now_year_today()
    categories = tuple(args.category) if args.category else CATEGORIES

    url_cache = http_check.load_cache()
    xref_cache = promote.load_crossref_cache()
    ts = _now_iso()

    candidates = []  # (rec, band, reason)
    blocked = Counter()
    for cat in categories:
        for rec in records[cat]:
            if rec.verified or not rec.slug:
                continue
            s = offline.score_record(rec, now_year, soc_release)
            urls = [u for u in rec.data.get("source_urls", []) if isinstance(u, str)]
            xref = xref_cache.get((cat, rec.slug), {}).get("decision")
            d = promote.decide(
                band=s.band, source_urls=urls, url_cache=url_cache, crossref_decision=xref,
            )
            if d.promote:
                candidates.append((rec, s, d.reason))
            elif s.band == "green":
                blocked["green-needs-live-t1"] += 1

    if args.max is not None:
        candidates = candidates[: args.max]

    print(f"promote: {len(candidates)} record(s) eligible "
          f"({'APPLY' if args.apply else 'dry-run'})")
    by_reason = Counter(reason for _r, _s, reason in candidates)
    for reason, n in by_reason.most_common():
        print(f"  {n:>6}  {reason}")
    if blocked:
        print("blocked (green but no live T1 source yet — run check-urls):")
        for reason, n in blocked.most_common():
            print(f"  {n:>6}  {reason}")

    if not args.apply:
        for rec, s, reason in candidates[:20]:
            print(f"  would promote: {rec.path}  [{s.band} {s.score}] {reason}")
        if len(candidates) > 20:
            print(f"  ... and {len(candidates) - 20} more")
        return 0

    written = 0
    entries = []
    for rec, s, reason in candidates:
        if promote.write_verified_true(repo_path(rec.path)):
            written += 1
            entries.append({
                "ts": ts, "category": rec.category, "slug": rec.slug, "path": rec.path,
                "hash": rec.content_hash(), "decision": "promote",
                "prev_verified": False, "new_verified": True, "reason": reason,
                "tier0": {"score": s.score, "band": s.band},
                "actor": "app.verify.promote",
            })
    ledger.append_many(entries)
    print(f"\napplied: flipped verified->true in {written} file(s); ledger updated")
    print("next: run `python -m app.validate` and `git diff` to confirm only verified changed")
    return 0


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"`{args.cmd}` is a later-phase subcommand and is not implemented yet.")
    return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.verify", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("score", help="Tier 0 offline plausibility scoring")
    sc.add_argument("--category", nargs="*", choices=CATEGORIES, help="limit to categories")
    sc.add_argument("--max", type=int, default=None, help="cap number scored")
    sc.add_argument("--unverified-only", action="store_true", help="skip verified:true records")
    sc.add_argument("--changed", action="store_true", help="only records changed vs origin/main")
    sc.add_argument("--no-cache", action="store_true", help="do not write the scores cache")
    sc.add_argument("--format", choices=["text", "md"], default="text",
                    help="output format: text histogram (default) or markdown table")
    sc.set_defaults(func=cmd_score)

    rp = sub.add_parser("report", help="summarize latest ledger state")
    rp.set_defaults(func=cmd_report)

    cu = sub.add_parser("check-urls", help="Tier 1: source_urls HTTP liveness")
    cu.add_argument("--category", nargs="*", choices=CATEGORIES, help="limit to categories")
    cu.add_argument("--max", type=int, default=500, help="number of frontier records to target")
    cu.add_argument("--workers", type=int, default=8, help="concurrent HTTP workers")
    cu.add_argument("--min-interval", type=float, default=1.0, help="seconds between hits per host")
    cu.add_argument("--ttl-days", type=int, default=http_check.DEFAULT_TTL_DAYS, help="cache freshness")
    cu.add_argument("--recheck", action="store_true", help="ignore cache freshness")
    cu.set_defaults(func=cmd_check_urls)

    cr = sub.add_parser("crossref", help="Tier 2: external cross-reference (exact heading)")
    cr.add_argument("--category", nargs="*", choices=CATEGORIES, help="limit to categories")
    cr.add_argument("--max", type=int, default=200, help="number of yellow/red records to escalate")
    cr.add_argument("--recheck", action="store_true", help="ignore crossref cache")
    cr.set_defaults(func=cmd_crossref)

    pr = sub.add_parser("promote", help="Tier 3: hybrid escalation + verified write-back")
    pr.add_argument("--category", nargs="*", choices=CATEGORIES, help="limit to categories")
    pr.add_argument("--max", type=int, default=None, help="cap number promoted")
    pr.add_argument("--apply", action="store_true", help="actually flip verified (default: dry-run)")
    pr.set_defaults(func=cmd_promote)

    return p


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
