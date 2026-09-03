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

# Display order when grouping fetched reviews by reason.
CATEGORY_ORDER = [
    "Size issue",
    "Fit issue",
    "Fit & Size",
    "Returns & Exchange",
    "Price & Value",
    "Quality",
    "Styling",
    "Trust & Reviews",
    "Choice / Comparison",
    "Occasion & Timing",
    "Social Validation",
    "Payment",
    "Other",
    "Uncategorized",
]


def review_category(record: dict) -> str:
    """Human reason for a review: Size vs Fit when the text supports it, else taxonomy dimension."""
    text = (record.get("text") or "").lower()
    bt = record.get("blocker_type")
    has_size = bool(re.search(
        r"\b(size|sizing|size.?chart|xxl|xxxl)\b|\bsmall\b|\blarge\b|\btoo (small|big|large)\b",
        text,
    ))
    has_fit = bool(re.search(r"\b(fit|tight|loose|baggy|snug|fitting)\b", text))
    if bt == "fit_sizing" or has_size or has_fit:
        if has_size and not has_fit:
            return "Size issue"
        if has_fit and not has_size:
            return "Fit issue"
        return "Fit & Size"
    if bt:
        return BLOCKER_DIMENSION.get(bt, "Other")
    return "Uncategorized"

# Brief source labels (the eight public-VOC channels this engine analyzes).
SOURCE_BRIEF = {
    "app_store_myntra": "App Store reviews",
    "google_play_myntra": "Play Store reviews",
    "reddit": "Reddit discussions",
    "fashion_community": "Fashion and shopping communities",
    "social_twitter": "Social media conversations",
    "youtube": "YouTube comments",
    "product_review": "Product reviews and Q&A where relevant",
    "product_qa": "Product reviews and Q&A where relevant",
    "other_public": "Other publicly available conversations about online fashion shopping",
}
BRIEF_SOURCE_ORDER = [
    "App Store reviews",
    "Play Store reviews",
    "Reddit discussions",
    "Fashion and shopping communities",
    "Social media conversations",
    "YouTube comments",
    "Product reviews and Q&A where relevant",
    "Other publicly available conversations about online fashion shopping",
]

# Blockers that represent lingering *uncertainty* after a user likes an item (Q3).
UNCERTAINTY_BLOCKERS = {
    "fit_sizing", "styling_uncertainty", "quality_doubt", "social_validation",
    "trust_authenticity",
}
# Blockers/behaviors that typically cause *postponement* (Q4).
POSTPONE_BLOCKERS = {
    "price", "occasion_timing", "decision_paralysis_too_many_options",
}

# Journey tag vs the north-star (wishlist → purchase). Not a measured lift.
# decision_friction = sits between "I like this" and "I buy this".
# anticipated_ops = post-purchase pain that can suppress the buy if shoppers expect it.
# post_purchase_ops = loud VOC after the order — weak direct WPC lever.
WPC_META = {
    "fit_sizing": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Size/fit doubt is a classic stall after a product is liked.",
        "questions": ["Q3", "Q7"],
    },
    "styling_uncertainty": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Looks-on-me doubt after shortlisting.",
        "questions": ["Q3", "Q7"],
    },
    "quality_doubt": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Fabric/quality hesitation after interest.",
        "questions": ["Q3", "Q7"],
    },
    "social_validation": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "medium",
        "wpc_note": "Waiting for a second opinion before buying.",
        "questions": ["Q3", "Q7"],
    },
    "trust_authenticity": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Reviews and authenticity checks before checkout.",
        "questions": ["Q3", "Q6", "Q7"],
    },
    "price": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Sale-wait and value doubt postpone the buy. Not a coupon brief.",
        "questions": ["Q4", "Q7"],
    },
    "occasion_timing": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "medium",
        "wpc_note": "No immediate occasion — timing, not forgetting.",
        "questions": ["Q4", "Q7"],
    },
    "decision_paralysis_too_many_options": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "high",
        "wpc_note": "Too many shortlisted items; comparison never resolves.",
        "questions": ["Q5", "Q4"],
    },
    "return_hassle": {
        "wpc_stage": "anticipated_ops",
        "wpc_leverage": "medium",
        "wpc_note": "Loudest post-purchase VOC. Can suppress WPC if a painful return is expected — not a measured lift.",
        "questions": ["Q2", "Q10"],
    },
    "payment_friction": {
        "wpc_stage": "decision_friction",
        "wpc_leverage": "medium",
        "wpc_note": "Checkout/payment friction after the decision is made.",
        "questions": ["Q2"],
    },
    "other": {
        "wpc_stage": "post_purchase_ops",
        "wpc_leverage": "low",
        "wpc_note": "Mostly delivery/cancel/ops. High volume, weak direct wishlist-to-buy lever.",
        "questions": ["Q2"],
    },
}
LEVERAGE_WEIGHT = {"high": 1.0, "medium": 0.65, "low": 0.35}

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

def brief_source(src) -> str:
    return SOURCE_BRIEF.get(str(src or ""), str(src or "Unknown"))


def coverage_by_source(records: list[dict], relevant: list[dict]) -> list[dict]:
    """Always emit the eight brief sources, even if a collector returned zero."""
    totals = Counter(brief_source(r.get("source")) for r in records)
    rels = Counter(brief_source(r.get("source")) for r in relevant)
    rows = []
    for label in BRIEF_SOURCE_ORDER:
        total = totals.get(label, 0)
        rel = rels.get(label, 0)
        rows.append({
            "source": label,
            "records": total,
            "relevant": rel,
            "relevant_pct": pct(rel, total),
        })
    extra = sorted(
        (k for k in totals if k not in BRIEF_SOURCE_ORDER and k != "Unknown"),
    )
    for label in extra:
        total = totals[label]
        rel = rels.get(label, 0)
        rows.append({
            "source": label,
            "records": total,
            "relevant": rel,
            "relevant_pct": pct(rel, total),
        })
    return rows


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
        src_counts = Counter(brief_source(it.get("source")) for it in items)
        meta = WPC_META.get(bt, {
            "wpc_stage": "decision_friction",
            "wpc_leverage": "medium",
            "wpc_note": "",
            "questions": [],
        })
        weight = LEVERAGE_WEIGHT.get(meta["wpc_leverage"], 0.65)
        rows.append({
            "blocker_type": bt,
            "dimension": BLOCKER_DIMENSION.get(bt, bt),
            "mentions": cnt,
            "reach_pct_of_relevant": pct(cnt, total),
            "frustration_rate_pct": round(100 * frust_rate, 1),
            "avg_confidence": round(avg_conf, 3),
            "source_count": len(src_counts),
            "by_source": src_counts.most_common(),
            "wpc_stage": meta["wpc_stage"],
            "wpc_leverage": meta["wpc_leverage"],
            "wpc_note": meta["wpc_note"],
            "questions": meta["questions"],
            "_weight": weight,
        })

    max_cnt = max((r["mentions"] for r in rows), default=0)
    for r in rows:
        freq_norm = r["mentions"] / max_cnt if max_cnt else 0.0
        r["opportunity_score"] = round(
            100 * (0.5 * freq_norm + 0.5 * r["frustration_rate_pct"] / 100), 1)
        r["wpc_weighted_score"] = round(r["opportunity_score"] * r.pop("_weight"), 1)

    def _rank(key):
        order = sorted(rows, key=lambda x: x[key], reverse=True)
        return {id(x): i + 1 for i, x in enumerate(order)}

    vol = _rank("mentions")
    fr = _rank("frustration_rate_pct")
    wp = _rank("wpc_weighted_score")
    for r in rows:
        r["volume_rank"] = vol[id(r)]
        r["frustration_rank"] = fr[id(r)]
        r["wpc_weighted_rank"] = wp[id(r)]
    rows.sort(key=lambda r: r["opportunity_score"], reverse=True)
    return rows


def q2_purchase_blockers(areas: list[dict]) -> dict:
    stages = ["decision_friction", "anticipated_ops", "post_purchase_ops"]
    by_stage = []
    for stage in stages:
        items = [r for r in areas if r.get("wpc_stage") == stage]
        by_stage.append({
            "stage": stage,
            "mentions": sum(r["mentions"] for r in items),
            "areas": len(items),
            "top": items[0]["blocker_type"] if items else None,
        })
    return {
        "metric": "Wishlist → purchase conversion. Public VOC cannot compute the rate.",
        "method": (
            "Identify blockers, quantify reach × frustration, then compare by "
            "journey stage (decision vs anticipated ops vs post-purchase). "
            "wpc_weighted_score is VOC score × leverage weight — not a measured lift."
        ),
        "by_stage": by_stage,
        "blockers": areas,
    }


def opportunity_comparison(areas: list[dict]) -> dict:
    def _top(key):
        row = max(areas, key=lambda r: r.get(key) or 0, default=None)
        if not row:
            return None
        return {"blocker_type": row["blocker_type"], "value": row.get(key)}

    return {
        "lenses": [
            {"id": "volume", "label": "How often it shows up in relevant conversations"},
            {"id": "frustration", "label": "How painful those mentions read"},
            {"id": "wpc_weighted", "label": "VOC score × journey leverage (not a measured WPC lift)"},
            {"id": "source_spread", "label": "How many of the eight sources mention it"},
        ],
        "note": (
            "Sentiment is one input (frustration rate), not the output. "
            "Compare areas on volume, pain, source spread, and whether the "
            "friction sits on the wishlist→buy path."
        ),
        "top_by_volume": _top("mentions"),
        "top_by_frustration": _top("frustration_rate_pct"),
        "top_by_wpc_weighted": _top("wpc_weighted_score"),
        "rows": areas,
    }


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


def load_intent_segments() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("intent_segments.json", "age_segments.json"):
        path = os.path.join(here, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    return {"note": "", "segments": []}


def q_intent_segments(areas: list[dict]) -> dict:
    """Size each purchase-intent's hypothesized VOC blockers. Survey weightage is separate."""
    spec = load_intent_segments()
    by_bt = {r.get("blocker_type"): r for r in areas}
    personas = []
    for seg in spec.get("segments") or []:
        matched = []
        mentions = 0
        best_score = 0.0
        for bt in seg.get("voc_blockers") or []:
            row = by_bt.get(bt)
            if not row:
                matched.append({"blocker_type": bt, "mentions": 0, "opportunity_score": None})
                continue
            matched.append({
                "blocker_type": bt,
                "dimension": row.get("dimension"),
                "mentions": row.get("mentions"),
                "opportunity_score": row.get("opportunity_score"),
                "wpc_weighted_score": row.get("wpc_weighted_score"),
            })
            mentions += row.get("mentions") or 0
            best_score = max(best_score, row.get("opportunity_score") or 0)
        personas.append({
            **seg,
            "voc_mentions": mentions,
            "top_voc_score": best_score or None,
            "voc_match": matched,
        })
    personas.sort(key=lambda r: (r.get("rank") or 99, -(r.get("max_weightage_pct") or 0)))
    weights = [p.get("max_weightage_pct") for p in personas if p.get("max_weightage_pct") is not None]
    max_w = spec.get("maximum_weightage_pct")
    if max_w is None and weights:
        max_w = max(weights)
    return {
        "cut": spec.get("cut") or "intent",
        "note": spec.get("note") or "",
        "weightage_source": spec.get("weightage_source") or "",
        "maximum_weightage_pct": max_w,
        "personas": personas,
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
    areas = opportunity_areas(relevant)
    intent_seg = q_intent_segments(areas)

    return {
        "north_star": "Wishlist / consideration → purchase conversion on Myntra",
        "workflow": {
            "not": "Review summarization or sentiment scoring as the deliverable",
            "is": (
                "Identify stated blockers across eight public sources, quantify "
                "reach and frustration, and compare opportunity areas by whether "
                "they sit on the wishlist→buy path."
            ),
            "sources": BRIEF_SOURCE_ORDER,
        },
        "coverage": {
            "total_records": total,
            "extracted": total - failed,
            "failed": failed,
            "relevant": len(relevant),
            "not_relevant": (total - failed) - len(relevant),
            "by_source": coverage_by_source(records, relevant),
        },
        "opportunity_areas": areas,
        "opportunity_comparison": opportunity_comparison(areas),
        "q1_why_wishlist": q_reasons_for_saving(relevant),
        "q2_purchase_blockers": q2_purchase_blockers(areas),
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
        "q9_by_segment": {
            "note": (
                "Primary cut is purchase intent (size/fit, reviews, comparison, returns), not age. "
                "max_weightage_pct is survey share of pre-purchase checks — not a funnel rate. "
                "voc_mentions size related public-review blockers in this corpus. "
                "inferred_blockers is the older free-text segment_signal table."
            ),
            **intent_seg,
            "inferred_blockers": q_segments(relevant),
        },
        "intent_segments": intent_seg,
        "age_segments": intent_seg,
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
             f"of extracted).")
    L.append("- Sources (always the eight public channels):")
    for s in cov.get("by_source") or []:
        L.append(f"  - {s['source']}: {s['records']} records, "
                 f"{s['relevant']} relevant ({s['relevant_pct']}%).")
    L.append("")

    # Headline opportunity comparison
    L.append("## Prioritized opportunity areas (Q10 — unmet needs)")
    L.append("Not a sentiment summary. Each area is **identified** (blocker), "
             "**quantified** (mentions, reach, frustration), and **compared** "
             "on volume vs pain vs wishlist→buy leverage. "
             "`wpc_weighted_score` is VOC score × journey weight — "
             "**not** a measured conversion lift.\n")
    if rep["opportunity_areas"]:
        L.append("| Rank | Opportunity | Stage | Leverage | Mentions | "
                 "Reach % | Frustration % | Sources | VOC score | WPC-weighted |")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for i, o in enumerate(rep["opportunity_areas"], 1):
            L.append(
                f"| {i} | {o['blocker_type']} | {o.get('wpc_stage', '')} | "
                f"{o.get('wpc_leverage', '')} | {o['mentions']} | "
                f"{o['reach_pct_of_relevant']} | {o['frustration_rate_pct']} | "
                f"{o.get('source_count', '')} | **{o['opportunity_score']}** | "
                f"{o.get('wpc_weighted_score', '')} |"
            )
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
    q2 = rep["q2_purchase_blockers"]
    L.append("## Q2 — What prevents wishlisted products from being purchased?")
    L.append(q2.get("method") or "")
    for stg in q2.get("by_stage") or []:
        L.append(f"- **{stg['stage']}**: {stg['mentions']} mentions "
                 f"across {stg['areas']} areas"
                 + (f" (top: {stg['top']})" if stg.get("top") else "")
                 + ".")
    L.append("")

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
    q9 = rep.get("q9_by_segment") or {}
    L.append("## Q9 — How do behaviors differ across user segments?")
    L.append(q9.get("note") or "")
    max_w = q9.get("maximum_weightage_pct")
    if max_w is not None:
        L.append(f"- **Maximum survey weightage:** {max_w}% (Size & Fit, and Wishlist comparison).")
    L.append("")
    L.append("| Rank | Intent | When | Max weightage % | Barrier | VOC mentions |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for s in q9.get("personas") or []:
        L.append(
            f"| {s.get('rank')} | {s.get('name')} | {s.get('horizon')} | "
            f"{s.get('max_weightage_pct')} | {s.get('main_barrier')} | "
            f"{s.get('voc_mentions')} |"
        )
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
