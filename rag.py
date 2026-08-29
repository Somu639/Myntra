"""Retrieve-then-ground: VOC quotes + ChatGPT research chunks.

Used by the Reviewer. No embeddings service — token overlap is enough
to surface evidence. Optional Groq call synthesizes; retrieval always works offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSIGHTS = ROOT / "structured_insights.jsonl"
CHATGPT = ROOT / "chatgpt_research.json"
REPORT = ROOT / "discovery_report.json"

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "it",
    "this", "that", "with", "from", "are", "was", "be", "as", "at", "by",
    "not", "but", "they", "you", "i", "we", "my", "their",
}


def _tok(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(w) > 2 and w not in _STOP
    }


def _score(q: set[str], doc: str) -> float:
    if not q:
        return 0.0
    d = _tok(doc)
    if not d:
        return 0.0
    return len(q & d) / (len(q) ** 0.5)


def load_chatgpt() -> dict:
    if not CHATGPT.exists():
        return {}
    return json.loads(CHATGPT.read_text(encoding="utf-8"))


def load_voc(limit: int = 800) -> list[dict]:
    from discover import load_records

    rows = []
    if not INSIGHTS.exists():
        return rows
    for r in load_records(str(INSIGHTS)):
        if r.get("relevant") is not True:
            continue
        rows.append(r)
        if len(rows) >= limit:
            break
    return rows


def retrieve(query: str, voc: list[dict], chunks: list[dict], k_voc: int = 5, k_gpt: int = 4) -> dict:
    q = _tok(query)
    voc_scored = []
    for r in voc:
        blob = " ".join(str(r.get(k) or "") for k in ("text", "blocker_type", "blocker_detail"))
        s = _score(q, blob)
        if r.get("blocker_type") and r["blocker_type"] in query.lower().replace(" ", "_"):
            s += 0.4
        if s > 0:
            voc_scored.append((s, r))
    voc_scored.sort(key=lambda x: x[0], reverse=True)

    gpt_scored = []
    for c in chunks:
        s = _score(q, f"{c.get('title', '')} {c.get('text', '')}")
        if s > 0:
            gpt_scored.append((s, c))
    gpt_scored.sort(key=lambda x: x[0], reverse=True)

    return {
        "query": query,
        "voc": [
            {
                "score": round(s, 3),
                "text": (r.get("text") or "")[:420],
                "source": r.get("source"),
                "blocker_type": r.get("blocker_type"),
                "sentiment": r.get("sentiment"),
            }
            for s, r in voc_scored[:k_voc]
        ],
        "chatgpt": [
            {"score": round(s, 3), "id": c.get("id"), "title": c.get("title"), "text": c.get("text"), "kind": c.get("kind")}
            for s, c in gpt_scored[:k_gpt]
        ],
    }


def _voc_quotes(limit_per: int = 3) -> list[dict]:
    qp = ROOT / "sample_quotes_by_blocker.json"
    if not qp.exists():
        return []
    quotes = json.loads(qp.read_text(encoding="utf-8"))
    out = []
    for bt, items in quotes.items():
        for q in (items or [])[:limit_per]:
            if not isinstance(q, dict):
                continue
            out.append({
                "text": (q.get("text") or "")[:400],
                "source": q.get("source"),
                "blocker_type": bt or q.get("blocker_type"),
                "rating": q.get("rating"),
            })
    return out


def triangulate(report: dict, research: dict) -> list[dict]:
    """Map ChatGPT hypotheses to VOC opportunity rows. No invented funnel %."""
    opp = {row.get("blocker_type"): row for row in (report.get("opportunity_areas") or [])}
    rows = []
    for c in research.get("chunks") or []:
        if c.get("kind") != "hypothesis":
            continue
        bt = c.get("voc_blocker")
        ev = opp.get(bt) if bt else None
        rows.append({
            "chatgpt": c.get("title"),
            "claim": c.get("text"),
            "voc_blocker": bt or "—",
            "voc_mentions": None if not ev else ev.get("mentions"),
            "voc_score": None if not ev else ev.get("opportunity_score"),
            "voc_frustration_pct": None if not ev else ev.get("frustration_rate_pct"),
            "status": "sized_in_voc" if ev else "not_in_public_voc",
        })
    return rows


def build_review_file() -> dict:
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    research = load_chatgpt()
    out = {
        "source_url": research.get("url"),
        "title": research.get("title"),
        "note": research.get("note"),
        "north_star": research.get("north_star"),
        "problem_statement": research.get("problem_statement"),
        "triangulation": triangulate(report, research),
        "chunks": research.get("chunks") or [],
        "voc_coverage": report.get("coverage") or {},
        "voc_top": (report.get("opportunity_areas") or [])[:8],
        "voc_quotes": _voc_quotes(),
    }
    (ROOT / "rag_review.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out


if __name__ == "__main__":
    review = build_review_file()
    print(f"wrote rag_review.json ({len(review.get('chunks') or [])} chunks, "
          f"{len(review.get('triangulation') or [])} hypothesis rows)")
