"""Pack discovery_report + quotes + rag_review into frontend JS/JSON."""

from __future__ import annotations

import json
from pathlib import Path

from discover import BRIEF_SOURCE_ORDER, build_report, brief_source, load_records
from rag import build_review_file

ROOT = Path(__file__).resolve().parent
FRONT = ROOT / "frontend"
SOURCE_LABELS = {
    "app_store_myntra": "App Store reviews",
    "google_play_myntra": "Play Store reviews",
    "reddit": "Reddit discussions",
    "fashion_community": "Fashion and shopping communities",
    "social_twitter": "Social media conversations",
    "youtube": "YouTube comments",
    "product_review": "Product reviews and Q&A where relevant",
    "product_qa": "Product reviews and Q&A where relevant",
    "other_public": "Other publicly available conversations about online fashion shopping",
    "chatgpt_research": "ChatGPT research",
}

SECTIONS = [
    {"id": "intent", "label": "Intent", "ids": ["q1", "q8"]},
    {"id": "path", "label": "Purchase path", "ids": ["q2", "q3", "q4", "q5"]},
    {"id": "research", "label": "Research", "ids": ["q6", "q7"]},
    {"id": "who", "label": "Who & opportunity", "ids": ["q9", "q10"]},
]
SECTION_FOR = {qid: s["label"] for s in SECTIONS for qid in s["ids"]}

QUESTIONS = [
    {"id": "q1", "key": "q1_why_wishlist", "short": "Why wishlist", "icon": "favorite",
     "section": "Intent", "lens": "INTENT DELAY",
     "question": "Why do users add fashion products to their wishlist?"},
    {"id": "q2", "key": "q2_purchase_blockers", "short": "Purchase blockers", "icon": "block",
     "section": "Purchase path", "lens": "FRICTION POINTS",
     "question": "What prevents wishlisted products from eventually being purchased?"},
    {"id": "q3", "key": "q3_post_like_uncertainty", "short": "Uncertainty", "icon": "help",
     "section": "Purchase path", "lens": "CONFIDENCE",
     "question": "What uncertainties remain after users have identified a product they like?"},
    {"id": "q4", "key": "q4_postponement", "short": "Postpone", "icon": "schedule",
     "section": "Purchase path", "lens": "TIMING",
     "question": "What causes users to postpone a purchase?"},
    {"id": "q5", "key": "q5_comparison", "short": "Compare", "icon": "compare_arrows",
     "section": "Purchase path", "lens": "COMPETITION",
     "question": "How do users compare multiple shortlisted products?"},
    {"id": "q6", "key": "q6_off_platform_research", "short": "Off-platform", "icon": "travel_explore",
     "section": "Research", "lens": "OUTSIDE THE APP",
     "question": "What information do users seek outside Myntra before purchasing?"},
    {"id": "q7", "key": "q7_dimension_roles", "short": "Dimensions", "icon": "category",
     "section": "Research", "lens": "MIX",
     "question": "What role do fit, size, styling, price, reviews, occasion and social validation play?"},
    {"id": "q8", "key": "q8_intent_vs_bookmark", "short": "Intent vs bookmark", "icon": "bookmark",
     "section": "Intent", "lens": "INTENT",
     "question": "When do users use the wishlist as genuine purchase intent versus bookmarking?"},
    {"id": "q9", "key": "q9_by_segment", "short": "Segments", "icon": "groups",
     "section": "Who & opportunity", "lens": "WHO",
     "question": "How do these behaviors differ across user segments?"},
    {"id": "q10", "key": "opportunity_areas", "short": "Unmet needs", "icon": "target",
     "section": "Who & opportunity", "lens": "OPPORTUNITY",
     "question": "What unmet needs emerge consistently across user conversations?"},
]


def _label(src) -> str:
    return SOURCE_LABELS.get(str(src or ""), str(src or "Unknown"))


def _quotes(items) -> list[dict]:
    out = []
    for q in items or []:
        if isinstance(q, dict):
            out.append({
                "text": q.get("text") or "",
                "source": _label(q.get("source")),
                "rating": q.get("rating"),
                "blocker": q.get("blocker_type"),
            })
    return out[:3]


def _blockers(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("blockers") or payload.get("rows") or []
    return []


def _pack_questions(report: dict, quotes_by: dict) -> list[dict]:
    out = []
    for spec in QUESTIONS:
        payload = report.get(spec["key"])
        entry = {**spec, "payload": payload}
        blockers = _blockers(payload)
        if spec["id"] in ("q2", "q10") and blockers:
            top = blockers[0].get("blocker_type")
            entry["spot_quotes"] = _quotes(quotes_by.get(top))
        elif isinstance(payload, dict):
            entry["spot_quotes"] = _quotes(payload.get("quotes"))
        else:
            entry["spot_quotes"] = []
        out.append(entry)
    return out


def _reviews_by_source(records: list[dict], n: int = 100) -> dict:
    buckets: dict[str, list] = {label: [] for label in BRIEF_SOURCE_ORDER}
    for r in records:
        label = brief_source(r.get("source"))
        if label not in buckets:
            continue
        if len(buckets[label]) >= n:
            continue
        if not (r.get("text") or "").strip():
            continue
        buckets[label].append({
            "text": (r.get("text") or "")[:360],
            "source": label,
            "rating": r.get("rating"),
            "blocker": r.get("blocker_type"),
            "sentiment": r.get("sentiment"),
        })
    return buckets


def main() -> None:
    report = json.loads((ROOT / "discovery_report.json").read_text(encoding="utf-8"))
    quotes_by = {}
    qp = ROOT / "sample_quotes_by_blocker.json"
    if qp.exists():
        quotes_by = json.loads(qp.read_text(encoding="utf-8"))
    insights = []
    ip = ROOT / "structured_insights.jsonl"
    if ip.exists():
        insights = load_records(str(ip))

    packed_all = _pack_questions(report, quotes_by)
    by_platform = {"All platforms": {q["id"]: q["payload"] for q in packed_all}}
    quotes_by_platform = {"All platforms": {q["id"]: q["spot_quotes"] for q in packed_all}}
    for label in BRIEF_SOURCE_ORDER:
        subset = [r for r in insights if brief_source(r.get("source")) == label]
        packed = _pack_questions(build_report(subset), quotes_by) if subset else []
        by_platform[label] = {q["id"]: q["payload"] for q in packed}
        quotes_by_platform[label] = {q["id"]: q.get("spot_quotes") or [] for q in packed}

    lab = {
        "coverage": report.get("coverage") or {},
        "sections": SECTIONS,
        "platforms": BRIEF_SOURCE_ORDER,
        "questions": packed_all,
        "by_platform": by_platform,
        "quotes_by_platform": quotes_by_platform,
        "reviews_by_source": _reviews_by_source(insights),
    }

    (FRONT / "lab_data.js").write_text(
        "window.LAB_DATA = " + json.dumps(lab, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    (FRONT / "segments_data.js").write_text(
        "window.SEGMENTS_DATA = " + json.dumps(report.get("intent_segments") or report.get("q9_by_segment") or report.get("age_segments") or {}, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    home = {
        "north_star": report.get("north_star"),
        "workflow": report.get("workflow") or {},
        "coverage": report.get("coverage") or {},
        "questions": [{"id": q["id"], "short": q["short"], "question": q["question"]} for q in QUESTIONS],
        "comparison": report.get("opportunity_comparison") or {},
        "areas": report.get("opportunity_areas") or [],
        "intents": report.get("intent_segments") or {},
    }
    (FRONT / "home_data.js").write_text(
        "window.HOME_DATA = " + json.dumps(home, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    (FRONT / "library_data.js").write_text(
        "window.LIBRARY_DATA = " + json.dumps({
            "coverage": report.get("coverage") or {},
            "comparison": report.get("opportunity_comparison") or {},
            "areas": report.get("opportunity_areas") or [],
            "intents": report.get("intent_segments") or {},
        }, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    review = build_review_file()
    (FRONT / "rag_review.json").write_text(
        json.dumps(review, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote frontend/lab_data.js, home_data.js, library_data.js, segments_data.js, rag_review.json")


if __name__ == "__main__":
    main()
