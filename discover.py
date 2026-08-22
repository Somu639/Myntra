"""Stage 4 — discover.py

The synthesis layer that turns the structured insights (Stage 2) into a
*discovery engine* deliverable: it answers the specific product-discovery
questions directly and, where the data allows, quantifies and ranks the
opportunity areas — rather than just summarizing reviews or scoring sentiment.

It reads structured_insights.jsonl, keeps relevant items, and writes:

    discovery_report.md    a PM-facing narrative organized by discovery question,
                           ending in a prioritized opportunity comparison.
    discovery_report.json  the same findings as machine-readable numbers.

Discovery questions answered (quantified where possible):
  1. Why do users add products to their wishlist?
  2. What prevents wishlisted products from being purchased?
  3. What uncertainties remain after a user likes a product?
  4. What causes users to postpone a purchase?
  5. How do users compare multiple shortlisted products?
  6. What information do users seek outside Myntra before buying?
  7. What role do fit, size, styling, price, reviews, occasion, social play?
  8. Wishlist as genuine intent vs. a bookmarking mechanism?
  9. How do these behaviors differ across user segments?
 10. What unmet needs emerge consistently (the opportunity areas)?

Pure standard library. No new dependencies, no ML/clustering — the fixed
taxonomy from Stage 2 is what makes these answers countable and comparable.

Usage
-----
    python discover.py
    python discover.py --in structured_insights.jsonl --outdir .
    python discover.py --quotes 3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

# Taxonomy (kept in sync with extract.py / aggregate.py).
BLOCKER_TYPES = [
    "fit_sizing", "price", "quality_doubt", "styling_uncertainty",
    "occasion_timing", "social_validation", "trust_authenticity",
    "return_hassle", "decision_paralysis_too_many_options", "payment_friction",
    "other",
]
OFF_PLATFORM_CHANNELS = {
    "external_youtube", "external_friends_family", "external_google_search",
    "in_store_trial", "social_media_influencer",
}

# Human-readable "dimension" each blocker maps to (question 7).
BLOCKER_DIMENSION = {
    "fit_sizing": "Fit & Size",
    "styling_uncertainty": "Styling",
    "price": "Price & Value",
    "quality_doubt": "Quality",
    "trust_authenticity": "Trust & Reviews",
    "return_hassle": "Returns & Exchange",
    "occasion_timing": "Occasion & Timing",
    "social_validation": "Social Validation",
    "decision_paralysis_too_many_options": "Choice / Comparison",
    "payment_friction": "Payment",
    "other": "Other",
}

# Blockers that represent lingering *uncertainty* after a user likes an item (Q3).
UNCERTAINTY_BLOCKERS = {
    "fit_sizing", "styling_uncertainty", "quality_doubt", "social_validation",
    "trust_authenticity",
}
# Blockers/behaviors that typically cause *postponement* (Q4).
POSTPONE_BLOCKERS = {
    "price", "occasion_timing", "decision_paralysis_too_many_options",
}

# Reason-for-saving heuristic buckets: genuine intent vs. bookmarking (Q8).
INTENT_HINTS = [
    "buy", "purchase", "sale", "discount", "price drop", "waiting", "later",
    "salary", "budget", "payday", "plan", "occasion", "wedding", "event",
    "cart", "checkout",
]
BOOKMARK_HINTS = [
    "like", "style", "inspir", "idea", "reference", "someday", "maybe",
    "browse", "remember", "collection", "admire",
]
# Whole-word only. "wish" as a substring matches "wishlist" and would mis-tag
# every wishlist_signal item as bookmarking (Q8).
BOOKMARK_WORD_HINTS = ["wish", "wishes", "wishing"]

FRUSTRATED = "frustrated"


# ---------------------------------------------------------------------------
# Load (dedup keep-last, matching aggregate.py)
# ---------------------------------------------------------------------------

def _is_failed_row(rec: dict) -> bool:
    return bool(rec.get("extraction_error")) or rec.get("relevant") is None


def load_records(path: str) -> list[dict]:
    """De-dupe on (source, id); a successful row always beats a failed one, and
    among same-status rows the newer one wins (so stale failed rows from an older
    backend can't shadow a newer successful extraction)."""
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
            if prev is None or _is_failed_row(prev) or not _is_failed_row(rec):
                by_key[key] = rec
    return list(by_key.values()) + no_id


def safe_float(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower()) if s else ""


def pct(n, d) -> float:
    return round(100 * n / d, 1) if d else 0.0


def top_quotes(items, n, key=lambda it: safe_float(it.get("confidence"))):
    """Highest-signal, source-diverse representative quotes."""
    ranked = sorted(items, key=key, reverse=True)
    picked, seen = [], set()
    for it in ranked:
        src = it.get("source")
        if src in seen and len(picked) < len(ranked):
            continue
        seen.add(src)
        picked.append(it)
        if len(picked) >= n:
            break
    for it in ranked:  # backfill if diversity fell short
        if len(picked) >= n:
            break
        if it not in picked:
            picked.append(it)
    return [{
        "text": it.get("text"),
        "source": it.get("source"),
        "rating": it.get("rating"),
        "blocker_type": it.get("blocker_type"),
        "confidence": it.get("confidence"),
    } for it in picked[:n]]


# ---------------------------------------------------------------------------
# Opportunity scoring (frequency + frustration, equal weight) — Q2 & Q10
# ---------------------------------------------------------------------------

def opportunity_areas(relevant: list[dict]) -> list[dict]:
    total = len(relevant)
    by_blocker: dict[str, list[dict]] = defaultdict(list)
    for r in relevant:
        bt = r.get("blocker_type")
        if bt:
            by_blocker[bt].append(r)

    rows = []
    for bt, items in by_blocker.items():
        cnt = len(items)
        frustrated = sum(1 for it in items if it.get("sentiment") == FRUSTRATED)
        frust_rate = frustrated / cnt if cnt else 0.0
        avg_conf = sum(safe_float(it.get("confidence")) for it in items) / cnt
        rows.append({
            "blocker_type": bt,
            "dimension": BLOCKER_DIMENSION.get(bt, bt),
            "mentions": cnt,
            "reach_pct_of_relevant": pct(cnt, total),
            "frustration_rate_pct": round(100 * frust_rate, 1),
            "avg_confidence": round(avg_conf, 3),
        })

    max_cnt = max((r["mentions"] for r in rows), default=0)
    for r in rows:
        freq_norm = r["mentions"] / max_cnt if max_cnt else 0.0
        r["opportunity_score"] = round(
            100 * (0.5 * freq_norm + 0.5 * r["frustration_rate_pct"] / 100), 1)
    rows.sort(key=lambda r: r["opportunity_score"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Per-question analyses
# ---------------------------------------------------------------------------

def q_reasons_for_saving(relevant):
    saves = [r for r in relevant if r.get("wishlist_signal")]
    reasons = Counter(norm(r.get("reason_for_saving")) for r in saves
                      if r.get("reason_for_saving"))
    return {
        "wishlist_mentions": len(saves),
        "top_reasons": reasons.most_common(10),
        "quotes": top_quotes(saves, 3),
    }


def _has_word(blob: str, word: str) -> bool:
    """Whole-word match so short tokens like 'wish' do not hit 'wishlist'."""
    return bool(re.search(rf"\b{re.escape(word)}\b", blob))


def q_intent_vs_bookmark(relevant):
    saves = [r for r in relevant if r.get("wishlist_signal")]
    intent = bookmark = unclear = 0
    for r in saves:
        blob = norm(r.get("reason_for_saving")) + " " + norm(r.get("text"))
        has_intent = any(h in blob for h in INTENT_HINTS)
        has_bookmark = (any(h in blob for h in BOOKMARK_HINTS)
                        or any(_has_word(blob, w) for w in BOOKMARK_WORD_HINTS))
        if has_intent and not has_bookmark:
            intent += 1
        elif has_bookmark and not has_intent:
            bookmark += 1
        else:
            unclear += 1
    return {
        "wishlist_mentions": len(saves),
        "genuine_intent": intent,
        "bookmarking": bookmark,
        "unclear": unclear,
    }


def q_dimension_roles(relevant):
    total = len([r for r in relevant if r.get("blocker_type")])
    dim = Counter(BLOCKER_DIMENSION.get(r.get("blocker_type"), "Other")
                  for r in relevant if r.get("blocker_type"))
    return {
        "total_with_blocker": total,
        "by_dimension": [
            {"dimension": d, "mentions": c, "share_pct": pct(c, total)}
            for d, c in dim.most_common()
        ],
    }


def q_subset(relevant, blocker_set, label):
    items = [r for r in relevant if r.get("blocker_type") in blocker_set]
    total_bl = len([r for r in relevant if r.get("blocker_type")])
    breakdown = Counter(r.get("blocker_type") for r in items)
    return {
        "label": label,
        "mentions": len(items),
        "share_of_blockers_pct": pct(len(items), total_bl),
        "breakdown": breakdown.most_common(),
        "quotes": top_quotes(items, 3),
    }


def q_off_platform(relevant):
    channels = Counter(r.get("resolution_channel") for r in relevant
                       if r.get("resolution_channel"))
    off = {c: n for c, n in channels.items() if c in OFF_PLATFORM_CHANNELS}
    off_total = sum(off.values())
    withchan = [r for r in relevant if r.get("resolution_channel")
                in OFF_PLATFORM_CHANNELS]
    return {
        "captured": bool(channels),
        "off_platform_total": off_total,
        "off_platform_pct_of_relevant": pct(off_total, len(relevant)),
        "by_channel": channels.most_common(),
        "quotes": top_quotes(withchan, 3),
    }


def q_segments(relevant):
    # Concentration per blocker: is a blocker focused in one segment (sharp
    # signal) or spread out (broad)? segment_signal is model-inferred free text.
    grid: dict[str, Counter] = defaultdict(Counter)
    for r in relevant:
        bt = r.get("blocker_type")
        if not bt:
            continue
        grid[bt][norm(r.get("segment_signal")) or "(unknown)"] += 1

    out = []
    for bt in sorted(grid, key=lambda b: sum(grid[b].values()), reverse=True):
        counter = grid[bt]
        total = sum(counter.values())
        # Concentration ignoring the unknown bucket, since unknown isn't a segment.
        known = Counter({k: v for k, v in counter.items() if k != "(unknown)"})
        if known:
            top_seg, top_cnt = known.most_common(1)[0]
            conc = pct(top_cnt, sum(known.values()))
        else:
            top_seg, conc = "(unknown)", 0.0
        out.append({
            "blocker_type": bt,
            "mentions": total,
            "known_segment_coverage_pct": pct(sum(known.values()), total),
            "top_segment": top_seg,
            "top_segment_concentration_pct": conc,
        })
    return out


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_report(records: list[dict]) -> dict:
    total = len(records)
    failed = sum(1 for r in records
                 if r.get("extraction_error") or r.get("relevant") is None)
    relevant = [r for r in records if r.get("relevant") is True]

    return {
        "coverage": {
            "total_records": total,
            "extracted": total - failed,
            "failed": failed,
            "relevant": len(relevant),
            "not_relevant": (total - failed) - len(relevant),
        },
        "opportunity_areas": opportunity_areas(relevant),
        "q1_why_wishlist": q_reasons_for_saving(relevant),
        "q2_purchase_blockers": opportunity_areas(relevant),  # ranked blockers
        "q3_post_like_uncertainty": q_subset(
            relevant, UNCERTAINTY_BLOCKERS, "Uncertainty after liking a product"),
        "q4_postponement": q_subset(
            relevant, POSTPONE_BLOCKERS, "Causes of postponement"),
        "q5_comparison": q_subset(
            relevant, {"decision_paralysis_too_many_options"},
            "Comparing multiple shortlisted products"),
        "q6_off_platform_research": q_off_platform(relevant),
        "q7_dimension_roles": q_dimension_roles(relevant),
        "q8_intent_vs_bookmark": q_intent_vs_bookmark(relevant),
        "q9_by_segment": q_segments(relevant),
    }


def _fmt_quotes(quotes) -> list[str]:
    lines = []
    for q in quotes:
        text = (q.get("text") or "").replace("\n", " ").strip()
        if len(text) > 180:
            text = text[:177] + "..."
        lines.append(f"  > \"{text}\"  — _{q.get('source')}_"
                     + (f" (rating {q['rating']})" if q.get("rating") else ""))
    return lines


def render_markdown(rep: dict) -> str:
    cov = rep["coverage"]
    L = []
    L.append("# Fashion Wishlist & Purchase-Intent Discovery Report\n")
    L.append("_AI-powered discovery engine — Myntra. Directional signals "
             "for opportunity prioritization, not statistically representative "
             "measurements (see data limitations in README)._\n")

    L.append("## Coverage")
    L.append(f"- Records analyzed: **{cov['total_records']}** "
             f"({cov['extracted']} extracted, {cov['failed']} failed).")
    L.append(f"- Relevant to fashion purchase/wishlist behavior: "
             f"**{cov['relevant']}** ({pct(cov['relevant'], cov['extracted'])}% "
             f"of extracted).\n")

    # Headline opportunity comparison
    L.append("## Prioritized opportunity areas (Q10 — unmet needs)")
    L.append("Ranked by an opportunity score weighting **reach** and "
             "**frustration** equally.\n")
    if rep["opportunity_areas"]:
        L.append("| Rank | Opportunity (blocker) | Dimension | Mentions | "
                 "Reach % | Frustration % | Confidence | Score |")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for i, o in enumerate(rep["opportunity_areas"], 1):
            L.append(f"| {i} | {o['blocker_type']} | {o['dimension']} | "
                     f"{o['mentions']} | {o['reach_pct_of_relevant']} | "
                     f"{o['frustration_rate_pct']} | {o['avg_confidence']} | "
                     f"**{o['opportunity_score']}** |")
    else:
        L.append("_No blocker-tagged relevant items found._")
    L.append("")

    # Q1
    q1 = rep["q1_why_wishlist"]
    L.append("## Q1 — Why do users add products to their wishlist?")
    L.append(f"- Wishlist/save signals detected: **{q1['wishlist_mentions']}**.")
    if q1["top_reasons"]:
        L.append("- Top stated reasons for saving:")
        for reason, c in q1["top_reasons"]:
            L.append(f"  - {reason} ({c})")
    L += _fmt_quotes(q1["quotes"])
    L.append("")

    # Q8
    q8 = rep["q8_intent_vs_bookmark"]
    L.append("## Q8 — Wishlist as genuine intent vs. bookmarking")
    L.append(f"- Of {q8['wishlist_mentions']} wishlist signals: "
             f"**{q8['genuine_intent']} genuine purchase intent**, "
             f"**{q8['bookmarking']} bookmarking**, {q8['unclear']} unclear "
             "(heuristic on stated reason + text).\n")

    # Q2 / opportunity = purchase blockers
    L.append("## Q2 — What prevents wishlisted products from being purchased?")
    L.append("See the prioritized opportunity table above — the ranked blockers "
             "are exactly the purchase blockers, by reach and frustration.\n")

    # Q3
    q3 = rep["q3_post_like_uncertainty"]
    L.append("## Q3 — Uncertainties remaining after a user likes a product")
    L.append(f"- **{q3['mentions']}** mentions "
             f"({q3['share_of_blockers_pct']}% of all blockers) are lingering "
             "uncertainties (fit, styling, quality, trust, social validation).")
    for bt, c in q3["breakdown"]:
        L.append(f"  - {bt}: {c}")
    L += _fmt_quotes(q3["quotes"])
    L.append("")

    # Q4
    q4 = rep["q4_postponement"]
    L.append("## Q4 — What causes users to postpone a purchase?")
    L.append(f"- **{q4['mentions']}** mentions "
             f"({q4['share_of_blockers_pct']}% of blockers) map to postponement "
             "drivers (price/sale-wait, occasion timing, choice overload).")
    for bt, c in q4["breakdown"]:
        L.append(f"  - {bt}: {c}")
    L.append("")

    # Q5
    q5 = rep["q5_comparison"]
    L.append("## Q5 — How do users compare multiple shortlisted products?")
    L.append(f"- Choice-overload / comparison-difficulty mentions: "
             f"**{q5['mentions']}**.")
    L += _fmt_quotes(q5["quotes"])
    L.append("")

    # Q6
    q6 = rep["q6_off_platform_research"]
    L.append("## Q6 — What do users research off-platform before buying?")
    if not q6["captured"]:
        L.append("- _resolution_channel was not populated in this extraction run "
                 "(a known weak spot for the local model). Re-run Stage 2 with "
                 "the Claude backend to fill this cut._")
    else:
        L.append(f"- Off-platform research: **{q6['off_platform_total']}** "
                 f"mentions ({q6['off_platform_pct_of_relevant']}% of relevant).")
        for ch, c in q6["by_channel"]:
            L.append(f"  - {ch}: {c}")
        L += _fmt_quotes(q6["quotes"])
    L.append("")

    # Q7
    q7 = rep["q7_dimension_roles"]
    L.append("## Q7 — Role of fit, size, styling, price, reviews, occasion, social")
    if q7["by_dimension"]:
        L.append("| Dimension | Mentions | Share of blockers % |")
        L.append("| --- | --- | --- |")
        for d in q7["by_dimension"]:
            L.append(f"| {d['dimension']} | {d['mentions']} | {d['share_pct']} |")
    L.append("")

    # Q9
    L.append("## Q9 — How do behaviors differ across user segments?")
    L.append("Concentration = share of the top segment among mentions that have "
             "an inferred segment. High concentration = sharper, more targetable "
             "signal. _segment_signal is model-inferred and often sparse._\n")
    L.append("| Blocker | Mentions | Known-segment coverage % | Top segment | "
             "Concentration % |")
    L.append("| --- | --- | --- | --- | --- |")
    for s in rep["q9_by_segment"]:
        L.append(f"| {s['blocker_type']} | {s['mentions']} | "
                 f"{s['known_segment_coverage_pct']} | {s['top_segment']} | "
                 f"{s['top_segment_concentration_pct']} |")
    L.append("")

    L.append("---")
    L.append("_Generated by discover.py (Stage 4). Backing data: "
             "structured_insights.jsonl. Spot-check categorization in "
             "sample_quotes_by_blocker.json before quoting numbers._")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Stage 4 discovery synthesis.")
    p.add_argument("--in", dest="infile", default="structured_insights.jsonl")
    p.add_argument("--outdir", default=".")
    p.add_argument("--quotes", type=int, default=3,
                   help="Representative quotes per section (default: 3).")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if not os.path.exists(args.infile):
        print(f"Input not found: {args.infile}. Run Stage 2 (extract.py) first.")
        return 1

    records = load_records(args.infile)
    report = build_report(records)

    os.makedirs(args.outdir, exist_ok=True)
    p_json = os.path.join(args.outdir, "discovery_report.json")
    p_md = os.path.join(args.outdir, "discovery_report.md")
    with open(p_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    with open(p_md, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))

    cov = report["coverage"]
    print("=== Stage 4 discovery ===")
    print(f"records={cov['total_records']} extracted={cov['extracted']} "
          f"failed={cov['failed']} relevant={cov['relevant']}")
    print(f"wrote {p_md}")
    print(f"wrote {p_json}")
    if report["opportunity_areas"]:
        top = report["opportunity_areas"][0]
        print(f"Top opportunity: {top['blocker_type']} "
              f"({top['dimension']}) — score {top['opportunity_score']}, "
              f"{top['mentions']} mentions, "
              f"{top['reach_pct_of_relevant']}% reach.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
