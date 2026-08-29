"""Pack discovery_report + quotes + rag_review into frontend JS/JSON."""

from __future__ import annotations

import json
from pathlib import Path

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
    "product_review": "Product reviews and Q&A",
    "product_qa": "Product reviews and Q&A",
    "other_public": "Other public conversations",
    "chatgpt_research": "ChatGPT research",
}

QUESTIONS = [
    {"id": "q1", "key": "q1_why_wishlist", "short": "Why wishlist", "icon": "favorite",
     "lens": "INTENT DELAY",
     "question": "Why do users add fashion products to their wishlist?"},
    {"id": "q2", "key": "q2_purchase_blockers", "short": "Purchase blockers", "icon": "block",
     "lens": "FRICTION POINTS",
     "question": "What prevents wishlisted products from eventually being purchased?"},
    {"id": "q3", "key": "q3_post_like_uncertainty", "short": "Uncertainty", "icon": "help",
     "lens": "CONFIDENCE",
     "question": "What uncertainties remain after users have identified a product they like?"},
    {"id": "q4", "key": "q4_postponement", "short": "Postpone", "icon": "schedule",
     "lens": "TIMING",
     "question": "What causes users to postpone a purchase?"},
    {"id": "q5", "key": "q5_comparison", "short": "Compare", "icon": "compare_arrows",
     "lens": "COMPETITION",
     "question": "How do users compare multiple shortlisted products?"},
    {"id": "q6", "key": "q6_off_platform_research", "short": "Off-platform", "icon": "travel_explore",
     "lens": "OUTSIDE THE APP",
     "question": "What information do users seek outside Myntra before purchasing?"},
    {"id": "q7", "key": "q7_dimension_roles", "short": "Dimensions", "icon": "category",
     "lens": "MIX",
     "question": "What role do fit, size, styling, price, reviews, occasion and social validation play?"},
    {"id": "q8", "key": "q8_intent_vs_bookmark", "short": "Intent vs bookmark", "icon": "bookmark",
     "lens": "INTENT",
     "question": "When do users use the wishlist as genuine purchase intent versus bookmarking?"},
    {"id": "q9", "key": "q9_by_segment", "short": "Segments", "icon": "groups",
     "lens": "WHO",
     "question": "How do these behaviors differ across user segments?"},
    {"id": "q10", "key": "opportunity_areas", "short": "Unmet needs", "icon": "target",
     "lens": "OPPORTUNITY",
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


def main() -> None:
    report = json.loads((ROOT / "discovery_report.json").read_text(encoding="utf-8"))
    quotes_by = {}
    qp = ROOT / "sample_quotes_by_blocker.json"
    if qp.exists():
        quotes_by = json.loads(qp.read_text(encoding="utf-8"))

    lab = {"coverage": report.get("coverage") or {}, "questions": []}
    for spec in QUESTIONS:
        payload = report.get(spec["key"])
        entry = {**spec, "payload": payload}
        if spec["id"] in ("q2", "q10") and isinstance(payload, list) and payload:
            top = payload[0].get("blocker_type")
            entry["spot_quotes"] = _quotes(quotes_by.get(top))
        elif isinstance(payload, dict):
            entry["spot_quotes"] = _quotes(payload.get("quotes"))
        else:
            entry["spot_quotes"] = []
        lab["questions"].append(entry)

    (FRONT / "lab_data.js").write_text(
        "window.LAB_DATA = " + json.dumps(lab, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    review = build_review_file()
    (FRONT / "rag_review.json").write_text(
        json.dumps(review, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote frontend/lab_data.js and frontend/rag_review.json")


if __name__ == "__main__":
    main()
