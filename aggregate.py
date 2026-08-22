"""Stage 3 — aggregate.py

Reads structured_insights.jsonl (Stage 2 output), keeps only relevant == true
items, and produces four flat-file outputs for a PM to act on:

    opportunity_summary.csv        headline ranking of blockers
    blocker_by_segment.csv         blocker x segment crosstab + concentration
    resolution_channel_summary.csv where users go off-platform to decide
    sample_quotes_by_blocker.json  3 real quotes per blocker for spot-checking

It also prints a coverage report (total / failed / relevant) so you always know
how complete the underlying extraction was — extraction failures are surfaced,
never hidden.

Pure standard library: no pandas, no ML/clustering, no database, no UI. The
blocker taxonomy is fixed on purpose so results stay comparable and countable.

Usage
-----
    python aggregate.py
    python aggregate.py --in structured_insights.jsonl --outdir .
    python aggregate.py --top-segments 12   # columns kept in the crosstab
    python aggregate.py --quotes 3          # quotes per blocker
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

# Fixed taxonomy (must match extract.py). Order here is only a stable default;
# the CSVs are sorted by score/frequency.
BLOCKER_TYPES = [
    "fit_sizing", "price", "quality_doubt", "styling_uncertainty",
    "occasion_timing", "social_validation", "trust_authenticity",
    "return_hassle", "decision_paralysis_too_many_options", "payment_friction",
    "other",
]
RESOLUTION_CHANNELS = [
    "in_app_reviews", "external_youtube", "external_friends_family",
    "external_google_search", "in_store_trial", "social_media_influencer",
    "none_mentioned",
]
# Channels that mean the user left Myntra to make up their mind.
OFF_PLATFORM_CHANNELS = {
    "external_youtube", "external_friends_family", "external_google_search",
    "in_store_trial", "social_media_influencer",
}

# Sentinel column for segments folded out of the crosstab. Parenthesized so it
# can never collide with a real (lowercased) model-inferred segment string.
OTHER_SEGMENTS = "(other segments)"

FROSTED = "frustrated"


# ---------------------------------------------------------------------------
# Load + coverage
# ---------------------------------------------------------------------------

def _is_failed_row(rec: dict) -> bool:
    return bool(rec.get("extraction_error")) or rec.get("relevant") is None


def load_records(path: str) -> list[dict]:
    """Load insights, de-duplicating on (source, id).

    Stage 2 appends when resuming, and switching backends can leave stale rows
    for the same item (e.g. an old failed local-model row lingering after a newer
    successful cloud row). So we don't blindly keep-last: a SUCCESSFUL extraction
    always wins over a failed one, and among rows of the same status the newer
    (later-in-file) one wins — so a retried success still supersedes an old one.
    """
    by_key: dict[tuple[str, str], dict] = {}
    no_id: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("id") is None:
                no_id.append(rec)
                continue
            key = (str(rec.get("source")), str(rec.get("id")))
            prev = by_key.get(key)
            # Take rec unless it would replace an existing success with a failure.
            if prev is None or _is_failed_row(prev) or not _is_failed_row(rec):
                by_key[key] = rec
    return list(by_key.values()) + no_id


def coverage_report(records: list[dict]) -> dict:
    total = len(records)
    failed = sum(1 for r in records
                 if r.get("extraction_error") or r.get("relevant") is None)
    extracted = total - failed
    relevant = sum(1 for r in records if r.get("relevant") is True)
    not_relevant = extracted - relevant
    relevant_no_blocker = sum(
        1 for r in records
        if r.get("relevant") is True and not r.get("blocker_type"))
    return {
        "total": total,
        "extracted": extracted,
        "failed": failed,
        "relevant": relevant,
        "not_relevant": not_relevant,
        "relevant_no_blocker": relevant_no_blocker,
    }


def print_coverage(cov: dict) -> None:
    total = cov["total"] or 1
    print("=== Coverage / completeness ===")
    print(f"  total records:            {cov['total']}")
    print(f"  successfully extracted:   {cov['extracted']} "
          f"({100 * cov['extracted'] / total:.1f}%)")
    print(f"  extraction FAILED:        {cov['failed']} "
          f"({100 * cov['failed'] / total:.1f}%)")
    print(f"  relevant == true:         {cov['relevant']}")
    print(f"  relevant == false:        {cov['not_relevant']}")
    print(f"  relevant, no blocker id'd:{cov['relevant_no_blocker']}")
    if cov["failed"]:
        print(f"  NOTE: {cov['failed']} items failed extraction and are excluded "
              f"from the analysis below. See extraction_run.log.")
    print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_segment(value) -> str:
    if not value:
        return "(unknown)"
    s = re.sub(r"\s+", " ", str(value).strip().lower())
    return s or "(unknown)"


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def write_csv(path: str, header: list[str], rows: list[list]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 1) opportunity_summary.csv  (headline)
# ---------------------------------------------------------------------------

def build_opportunity_summary(relevant: list[dict], path: str) -> list[dict]:
    total_relevant = len(relevant)
    by_blocker: dict[str, list[dict]] = defaultdict(list)
    for r in relevant:
        bt = r.get("blocker_type")
        if bt:  # only named blockers are opportunities; null handled in coverage
            by_blocker[bt].append(r)

    stats = []
    for bt, items in by_blocker.items():
        count = len(items)
        frustrated = sum(1 for it in items if it.get("sentiment") == FROSTED)
        frustration_rate = frustrated / count if count else 0.0
        avg_conf = (sum(safe_float(it.get("confidence")) for it in items) / count
                    if count else 0.0)
        stats.append({
            "blocker_type": bt,
            "count": count,
            "pct_of_relevant": 100 * count / total_relevant if total_relevant else 0,
            "frustration_rate": frustration_rate,
            "avg_confidence": avg_conf,
        })

    # Composite score: normalize frequency across named blockers, weight it and
    # frustration EQUALLY (0.5 / 0.5), scale to 0-100.
    max_count = max((s["count"] for s in stats), default=0)
    for s in stats:
        freq_norm = (s["count"] / max_count) if max_count else 0.0
        s["opportunity_score"] = round(
            100 * (0.5 * freq_norm + 0.5 * s["frustration_rate"]), 1)

    stats.sort(key=lambda s: s["opportunity_score"], reverse=True)

    rows = [[
        s["blocker_type"], s["count"], round(s["pct_of_relevant"], 1),
        round(100 * s["frustration_rate"], 1), round(s["avg_confidence"], 3),
        s["opportunity_score"],
    ] for s in stats]
    write_csv(path, [
        "blocker_type", "mention_count", "pct_of_all_relevant",
        "frustration_rate_pct", "avg_confidence", "opportunity_score",
    ], rows)
    return stats


# ---------------------------------------------------------------------------
# 2) blocker_by_segment.csv  (crosstab + concentration)
# ---------------------------------------------------------------------------

def build_blocker_by_segment(relevant: list[dict], path: str,
                             top_segments: int) -> None:
    # segment_signal is free-text and model-inferred, so it is high-cardinality.
    # Keep the most common segments as columns and fold the rest into "other".
    seg_counts = Counter(normalize_segment(r.get("segment_signal"))
                         for r in relevant if r.get("blocker_type"))
    top = [seg for seg, _ in seg_counts.most_common(top_segments)]
    top_set = set(top)

    grid: dict[str, Counter] = defaultdict(Counter)
    for r in relevant:
        bt = r.get("blocker_type")
        if not bt:
            continue
        seg = normalize_segment(r.get("segment_signal"))
        col = seg if seg in top_set else OTHER_SEGMENTS
        grid[bt][col] += 1

    columns = list(top)
    if any(counter.get(OTHER_SEGMENTS) for counter in grid.values()):
        columns.append(OTHER_SEGMENTS)

    header = ["blocker_type", "total"] + columns + ["top_segment",
                                                    "top_segment_share_pct"]
    rows = []
    # Sort rows by total desc for readability.
    for bt in sorted(grid, key=lambda b: sum(grid[b].values()), reverse=True):
        counter = grid[bt]
        total = sum(counter.values())
        cells = [counter.get(col, 0) for col in columns]
        if total:
            top_seg, top_seg_count = counter.most_common(1)[0]
            share = round(100 * top_seg_count / total, 1)
        else:
            top_seg, share = "", 0.0
        rows.append([bt, total] + cells + [top_seg, share])

    write_csv(path, header, rows)


# ---------------------------------------------------------------------------
# 3) resolution_channel_summary.csv  (off-platform cut)
# ---------------------------------------------------------------------------

def build_resolution_summary(relevant: list[dict], path: str) -> dict:
    total_relevant = len(relevant)
    counts = Counter()
    for r in relevant:
        ch = r.get("resolution_channel")
        if ch:
            counts[ch] += 1

    rows = []
    off_platform_total = 0
    for ch, count in counts.most_common():
        is_off = ch in OFF_PLATFORM_CHANNELS
        if is_off:
            off_platform_total += count
        rows.append([
            ch, count,
            round(100 * count / total_relevant, 1) if total_relevant else 0,
            "yes" if is_off else "no",
        ])
    write_csv(path, [
        "resolution_channel", "mention_count", "pct_of_all_relevant",
        "off_platform",
    ], rows)
    return {
        "off_platform_total": off_platform_total,
        "off_platform_pct": (100 * off_platform_total / total_relevant
                             if total_relevant else 0),
    }


# ---------------------------------------------------------------------------
# 4) sample_quotes_by_blocker.json
# ---------------------------------------------------------------------------

def build_sample_quotes(relevant: list[dict], path: str, per_blocker: int) -> None:
    by_blocker: dict[str, list[dict]] = defaultdict(list)
    for r in relevant:
        bt = r.get("blocker_type")
        if bt:
            by_blocker[bt].append(r)

    out: dict[str, list[dict]] = {}
    for bt, items in by_blocker.items():
        # "Representative" = highest-confidence examples; prefer source diversity.
        ranked = sorted(items, key=lambda it: safe_float(it.get("confidence")),
                        reverse=True)
        picked, seen_sources = [], set()
        for it in ranked:
            src = it.get("source")
            if src in seen_sources and len(picked) < len(ranked):
                continue
            seen_sources.add(src)
            picked.append(it)
            if len(picked) >= per_blocker:
                break
        # Backfill if source-diversity left us short.
        if len(picked) < per_blocker:
            for it in ranked:
                if it not in picked:
                    picked.append(it)
                if len(picked) >= per_blocker:
                    break

        out[bt] = [{
            "text": it.get("text"),
            "source": it.get("source"),
            "rating": it.get("rating"),
            "date": it.get("date"),
            "sentiment": it.get("sentiment"),
            "blocker_detail": it.get("blocker_detail"),
            "confidence": it.get("confidence"),
        } for it in picked[:per_blocker]]

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage 3 aggregation / reporting.")
    p.add_argument("--in", dest="infile", default="structured_insights.jsonl",
                   help="Input JSONL from Stage 2.")
    p.add_argument("--outdir", default=".", help="Directory for output files.")
    p.add_argument("--top-segments", type=int, default=12,
                   help="Max segment columns in the crosstab (default: 12).")
    p.add_argument("--quotes", type=int, default=3,
                   help="Sample quotes per blocker (default: 3).")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if not os.path.exists(args.infile):
        print(f"Input not found: {args.infile}. Run Stage 2 (extract.py) first.")
        return 1

    records = load_records(args.infile)
    cov = coverage_report(records)
    print_coverage(cov)

    relevant = [r for r in records if r.get("relevant") is True]
    if not relevant:
        print("No relevant==true records found — nothing to aggregate.")
        return 0

    os.makedirs(args.outdir, exist_ok=True)
    p_opp = os.path.join(args.outdir, "opportunity_summary.csv")
    p_seg = os.path.join(args.outdir, "blocker_by_segment.csv")
    p_res = os.path.join(args.outdir, "resolution_channel_summary.csv")
    p_quo = os.path.join(args.outdir, "sample_quotes_by_blocker.json")

    stats = build_opportunity_summary(relevant, p_opp)
    build_blocker_by_segment(relevant, p_seg, args.top_segments)
    res = build_resolution_summary(relevant, p_res)
    build_sample_quotes(relevant, p_quo, args.quotes)

    print("=== Outputs written ===")
    print(f"  {p_opp}")
    print(f"  {p_seg}")
    print(f"  {p_res}")
    print(f"  {p_quo}")
    print()

    if stats:
        top = stats[0]
        print(f"Headline: top opportunity = '{top['blocker_type']}' "
              f"(score {top['opportunity_score']}, {top['count']} mentions, "
              f"{round(100 * top['frustration_rate'], 1)}% frustrated).")
    print(f"Off-platform resolution: {res['off_platform_total']} mentions "
          f"({res['off_platform_pct']:.1f}% of relevant) go off Myntra to "
          f"decide before buying.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
