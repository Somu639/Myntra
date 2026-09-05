"""Myntra Discovery Engine — Streamlit dashboard.

Myntra-themed research console: sidebar navigation, Discovery Lab, and
ranked purchase-blocker opportunities from public reviews.

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

from discover import load_records

ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
REPORT_PATH = ROOT / "discovery_report.json"
INSIGHTS_PATH = ROOT / "structured_insights.jsonl"
QUOTES_PATH = ROOT / "sample_quotes_by_blocker.json"
PROPOSAL_PATH = ROOT / "opportunity_proposal.md"
PHASE1_PATH = ROOT / "phase1_metrics.json"

DISCOVERY_QUESTIONS = [
    {
        "id": "q1",
        "icon": "💾",
        "short_title": "Why wishlist",
        "question": "Why do users add fashion products to their wishlist?",
        "key": "q1_why_wishlist",
        "lens": "Stated reasons for saving, from wishlist_signal items",
    },
    {
        "id": "q2",
        "icon": "🚫",
        "short_title": "Purchase blockers",
        "question": "What prevents wishlisted products from eventually being purchased?",
        "key": "q2_purchase_blockers",
        "lens": "Identify blockers, quantify reach × frustration, split by wishlist→buy stage",
    },
    {
        "id": "q3",
        "icon": "❓",
        "short_title": "Uncertainty",
        "question": "What uncertainties remain after users have identified a product they like?",
        "key": "q3_post_like_uncertainty",
        "lens": "Fit, styling, quality, trust, social validation",
    },
    {
        "id": "q4",
        "icon": "⏸️",
        "short_title": "Postpone",
        "question": "What causes users to postpone a purchase?",
        "key": "q4_postponement",
        "lens": "Price/sale-wait, occasion timing, choice overload",
    },
    {
        "id": "q5",
        "icon": "⚖️",
        "short_title": "Compare",
        "question": "How do users compare multiple shortlisted products?",
        "key": "q5_comparison",
        "lens": "Choice-overload / comparison-difficulty mentions",
    },
    {
        "id": "q6",
        "icon": "🔎",
        "short_title": "Off-platform",
        "question": "What information do users seek outside Myntra before purchasing?",
        "key": "q6_off_platform_research",
        "lens": "resolution_channel — in-app reviews vs YouTube vs none",
    },
    {
        "id": "q7",
        "icon": "📐",
        "short_title": "Dimensions",
        "question": "What role do fit, size, styling, price, reviews, occasion and social validation play?",
        "key": "q7_dimension_roles",
        "lens": "Share of identified blockers by dimension",
    },
    {
        "id": "q8",
        "icon": "📌",
        "short_title": "Intent vs bookmark",
        "question": "When do users use the wishlist as genuine purchase intent versus bookmarking?",
        "key": "q8_intent_vs_bookmark",
        "lens": "Heuristic on reason_for_saving + review text",
    },
    {
        "id": "q9",
        "icon": "👥",
        "short_title": "Segments",
        "question": "How do these behaviors differ across user segments?",
        "key": "q9_by_segment",
        "lens": "Purchase-intent segments with survey max weightage; VOC sizes related blockers",
    },
    {
        "id": "q10",
        "icon": "🎯",
        "short_title": "Unmet needs",
        "question": "What unmet needs emerge consistently across user conversations?",
        "key": "opportunity_areas",
        "lens": "Compare unmet needs: volume vs pain vs WPC leverage vs source spread",
    },
]

QUESTION_SECTIONS = [
    ("Intent", ["q1", "q8"]),
    ("Purchase path", ["q2", "q3", "q4", "q5"]),
    ("Research", ["q6", "q7"]),
    ("Who & opportunity", ["q9", "q10"]),
]
SECTION_FOR_Q = {qid: name for name, ids in QUESTION_SECTIONS for qid in ids}

FETCH_COUNTS = [10, 25, 50, 100]
PLATFORM_COLLECTORS = {
    "App Store reviews": ["ios"],
    "Play Store reviews": ["play"],
    "Reddit discussions": ["reddit"],
    "Fashion and shopping communities": ["communities"],
    "Social media conversations": ["social"],
    "YouTube comments": ["youtube"],
    "Product reviews and Q&A where relevant": ["product"],
    "Other publicly available conversations about online fashion shopping": ["social"],
}

# Friendly names for the Raw Data source filter (always shown, in this order).
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
SOURCE_FILTER_OPTIONS = [
    "App Store reviews",
    "Play Store reviews",
    "Reddit discussions",
    "Fashion and shopping communities",
    "Social media conversations",
    "YouTube comments",
    "Product reviews and Q&A where relevant",
    "Other publicly available conversations about online fashion shopping",
]


def source_label(src: str | None) -> str:
    key = str(src or "").strip()
    return SOURCE_LABELS.get(key, key or "Unknown")


NAV_PAGES = [
    "Home",
    "Discovery Lab",
    "Search and Library",
    "Segments",
    "Raw Data",
    "Reviewer",
    "AI Roadmap",
]
NAV_ICONS = {
    "Home": "🏠",
    "Discovery Lab": "🔬",
    "Search and Library": "📚",
    "Segments": "👥",
    "Raw Data": "📋",
    "Reviewer": "🔎",
    "AI Roadmap": "🤖",
}


def inject_myntra_css() -> None:
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&display=swap" rel="stylesheet"/>
        <style>
          .stApp {
            background-color: #F5F5F6;
            font-family: 'Assistant', sans-serif;
            color: #282C3F;
          }
          section[data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #EAEAEC;
          }
          section[data-testid="stSidebar"] .stRadio > label { display: none; }
          div[data-testid="stRadio"] label,
          div[data-testid="stRadio"] [role="radiogroup"] label,
          div[data-testid="stPills"] button {
            pointer-events: auto !important;
            cursor: pointer !important;
          }
          h1.aura-brand-title,
          [data-testid="stMarkdownContainer"] h1.aura-brand-title {
            font-family: 'Assistant', sans-serif !important;
            font-size: 2.15rem !important;
            font-weight: 800 !important;
            color: #FF3F6C !important;
            letter-spacing: -0.02em !important;
            line-height: 1.05 !important;
            margin: 0 0 8px 0 !important;
          }
          h1.home-main-heading,
          [data-testid="stMarkdownContainer"] h1.home-main-heading {
            font-family: 'Assistant', sans-serif !important;
            font-size: 3rem !important;
            font-weight: 800 !important;
            color: #FF3F6C !important;
            letter-spacing: -0.02em !important;
            line-height: 1.08 !important;
            margin: 0 0 12px 0 !important;
          }
          .aura-brand-sub {
            font-family: 'Assistant', sans-serif;
            font-size: 0.7rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #535766;
            margin-top: 0;
          }
          header[data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #EAEAEC;
          }
          div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #EAEAEC;
            border-radius: 4px;
            box-shadow: none;
          }
          .stButton>button {
            border-radius: 2px;
            font-family: 'Assistant', sans-serif;
            font-weight: 700;
            background: #FF3F6C;
            color: #ffffff;
            border: none;
            pointer-events: auto !important;
            cursor: pointer !important;
            position: relative;
            z-index: 2;
          }
          .stButton>button:hover { background: #E3365B; color: #ffffff; }
          .home-hero-sub {
            font-family: 'Assistant', sans-serif;
            font-size: 1.05rem;
            color: #535766;
            margin: 0;
            max-width: 720px;
            line-height: 1.55;
          }
          .home-card {
            background: #ffffff;
            border: 1px solid #EAEAEC;
            border-radius: 4px;
            padding: 18px 20px;
            margin-bottom: 10px;
          }
          .home-card h4 {
            font-family: 'Assistant', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            color: #FF3F6C;
            margin: 0 0 6px 0;
          }
          .home-card p { font-size: 0.9rem; color: #535766; margin: 0; line-height: 1.5; }
          .home-pipeline-step {
            background: #ffffff;
            border-left: 4px solid #FF3F6C;
            border-radius: 0 4px 4px 0;
            padding: 12px 16px;
            margin-bottom: 10px;
          }
          .home-pipeline-step strong {
            color: #FF3F6C;
            font-family: 'Assistant', sans-serif;
          }
          .home-nav-row {
            padding: 10px 0;
            border-bottom: 1px solid #EAEAEC;
          }
          .home-nav-row:last-child { border-bottom: none; }
          .home-nav-label { font-weight: 700; color: #FF3F6C; }
          .quote-card {
            background: #ffffff;
            border: 1px solid #EAEAEC;
            border-left: 3px solid #FF3F6C;
            border-radius: 4px;
            padding: 12px 16px;
            margin-bottom: 8px;
            font-size: 0.92rem;
            color: #282C3F;
          }
          .quote-meta { color: #94969F; font-size: 0.75rem; margin-top: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _file_stamp(path: Path) -> tuple[float, int]:
    """mtime + size so Streamlit cache invalidates when JSONL grows."""
    if not path.exists():
        return (0.0, 0)
    st_ = path.stat()
    return (st_.st_mtime, st_.st_size)


@st.cache_data(show_spinner=False)
def load_report(stamp: tuple[float, int]) -> dict:
    if not REPORT_PATH.exists():
        return {}
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_insights(stamp: tuple[float, int]) -> list[dict]:
    if not INSIGHTS_PATH.exists():
        return []
    return load_records(str(INSIGHTS_PATH))


@st.cache_data(show_spinner=False)
def load_quotes(stamp: tuple[float, int]) -> dict:
    if not QUOTES_PATH.exists():
        return {}
    return json.loads(QUOTES_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_phase1(stamp: tuple[float, int]) -> dict:
    if not PHASE1_PATH.exists():
        return {}
    return json.loads(PHASE1_PATH.read_text(encoding="utf-8"))


def blocker_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("blockers") or payload.get("rows") or []
    return []


def quote_block(text: str, source: str = "", rating=None) -> None:
    meta = source
    if rating is not None:
        meta = f"{source} · rating {rating}" if source else f"rating {rating}"
    st.markdown(
        f'<div class="quote-card">{text}'
        f'<div class="quote-meta">{meta}</div></div>',
        unsafe_allow_html=True,
    )


def page_home(report: dict, records: list[dict]) -> None:
    cov = report.get("coverage", {})
    st.markdown(
        """
        <h1 class="home-main-heading">Myntra Discovery Engine</h1>
        <p class="home-hero-sub">
          Analyze public conversations across eight sources, answer ten
          wishlist→purchase questions, then <strong>identify, quantify, and
          compare</strong> opportunity areas that could move conversion.
          This is not a review summary or a sentiment dashboard.
          Public VOC cannot compute funnel rates — do not treat scores as lifts.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records analyzed", cov.get("total_records") or len(records) or "—")
    c2.metric("Relevant to WPC", cov.get("relevant") or "—")
    areas = report.get("opportunity_areas") or []
    top = areas[0] if areas else {}
    c3.metric("Top VOC opportunity", top.get("dimension") or "—", f"score {top.get('opportunity_score')}" if top else None)
    intents = report.get("intent_segments") or report.get("q9_by_segment") or {}
    max_w = intents.get("maximum_weightage_pct")
    at_max = " · ".join(
        p.get("name") or ""
        for p in (intents.get("personas") or [])
        if p.get("max_weightage_pct") == max_w
    )
    c4.metric("Maximum survey weightage", f"{max_w}%" if max_w is not None else "—", at_max or None)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### Workflow")
        for title, body in (
            ("1 · Collect eight public sources", "App Store, Play Store, Reddit, fashion communities, social, YouTube, product Q&A, other public fashion-shopping talk."),
            ("2 · Extract structured codes", "Wishlist signal, reason for saving, blocker type, resolution channel, segment — not star-rating averages."),
            ("3 · Answer ten discovery questions", "Why save, what blocks the buy, leftover uncertainty, postpone, compare, off-platform research, dimension mix, intent vs bookmark, segments, unmet needs."),
            ("4 · Compare opportunity areas", "Volume × frustration × source spread × whether the friction sits on the wishlist→buy path. Sentiment is an input, not the deliverable."),
        ):
            st.markdown(
                f'<div class="home-pipeline-step"><strong>{title}</strong><br/>{body}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("#### Ten questions this engine answers")
        for q in DISCOVERY_QUESTIONS:
            st.markdown(f"**{q['id'].upper()}.** {q['question']}")
    with right:
        st.markdown("#### Sources analyzed")
        src_rows = cov.get("by_source") or []
        if src_rows:
            st.dataframe(
                pd.DataFrame(src_rows).rename(columns={
                    "source": "source",
                    "records": "records",
                    "relevant": "relevant",
                    "relevant_pct": "relevant %",
                }),
                hide_index=True,
                use_container_width=True,
            )
        else:
            for label in SOURCE_FILTER_OPTIONS:
                st.markdown(f'<div class="home-card"><h4>{label}</h4></div>', unsafe_allow_html=True)

    cmp = report.get("opportunity_comparison") or {}
    rows = cmp.get("rows") or report.get("opportunity_areas") or []
    if rows:
        st.markdown("#### Opportunity areas compared (north-star: wishlist → purchase)")
        st.caption(cmp.get("note") or "Intent cut with survey max weightage. Weightage is not a funnel rate.")
        show = pd.DataFrame(rows)
        cols = [c for c in (
            "blocker_type", "dimension", "purchase_intent", "intent_rank",
            "survey_weightage_pct", "mentions", "reach_pct_of_relevant",
            "frustration_rate_pct", "source_count", "opportunity_score",
        ) if c in show.columns]
        st.dataframe(show[cols].rename(columns={
            "purchase_intent": "intent",
            "survey_weightage_pct": "max weightage %",
            "opportunity_score": "VOC score",
        }), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Where to go in this dashboard")
    nav_guide = [
        ("Discovery Lab", "The ten questions with quantified cuts and verbatim quotes."),
        ("Search and Library", "Compare opportunity areas across volume, pain, and WPC leverage."),
        ("Reviewer", "RAG over VOC + ChatGPT research, and fetch reviews from any of the eight platforms."),
        ("Segments", "Purchase-intent segments with survey max weightage (75%)."),
        ("Raw Data", "Browse extracted conversations by the eight sources."),
        ("AI Roadmap", "Prioritized solutions from opportunity_proposal.md."),
    ]
    cols = st.columns(2)
    for i, (label, desc) in enumerate(nav_guide):
        with cols[i % 2]:
            st.markdown(
                f'<div class="home-nav-row"><span class="home-nav-label">{label}</span> — {desc}</div>',
                unsafe_allow_html=True,
            )


def _fetch_platform_reviews(platform: str, limit: int = 25) -> tuple[list[dict], str]:
    """Live-collect from one public platform. Falls back to an error string."""
    from collect import COLLECTORS, Writer

    keys = PLATFORM_COLLECTORS.get(platform) or []
    if not keys:
        return [], f"No collector mapped for {platform}."
    limit = max(5, min(int(limit or 25), 100))
    tmp = ROOT / f".lab_fetch_{keys[0]}.jsonl"
    writer = Writer(str(tmp))
    try:
        for name in keys:
            COLLECTORS[name](writer, limit)
    except Exception as exc:
        writer.close()
        return [], f"Fetch failed: {exc}"
    writer.close()
    rows = []
    if tmp.exists():
        for line in tmp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if source_label(rec.get("source")) == platform or platform.startswith("Other"):
                rows.append(rec)
            elif source_label(rec.get("source")) in PLATFORM_COLLECTORS:
                # social collector also writes other_public
                if keys == ["social"]:
                    rows.append(rec)
    if not rows and tmp.exists():
        for line in tmp.read_text(encoding="utf-8").splitlines()[-limit:]:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows[-limit:], f"Fetched {len(rows[-limit:])} reviews from {platform}."


def page_discovery_lab(report: dict, quotes: dict, records: list[dict]) -> None:
    from discover import build_report

    st.markdown("### Discovery Lab")
    st.caption(
        "Pick a section and a question. Choose a platform and how many reviews to fetch. "
        "The answer table recuts to that platform. Counts come from structured extraction, not summaries."
    )

    section_names = [name for name, _ in QUESTION_SECTIONS]
    if "lab_section" not in st.session_state:
        st.session_state["lab_section"] = "Purchase path"
    c1, c2, c3, c4, c5 = st.columns([1.1, 2.2, 2.0, 0.9, 1.0])
    section = c1.selectbox("Section", section_names, key="lab_section")
    qids = dict(QUESTION_SECTIONS)[section]
    q_specs = [q for q in DISCOVERY_QUESTIONS if q["id"] in qids]
    q_labels = [f"{q['icon']} {q['short_title']} — {q['question']}" for q in q_specs]
    picked_q = c2.selectbox("Question", q_labels, key=f"lab_question_{section}")
    spec = q_specs[q_labels.index(picked_q)]
    platforms = ["All platforms"] + SOURCE_FILTER_OPTIONS
    platform = c3.selectbox("Platform", platforms, key="lab_platform")
    how_many = c4.selectbox("How many reviews", FETCH_COUNTS, index=1, key="lab_fetch_n")
    fetch_clicked = c5.button("Fetch reviews", use_container_width=True, key="lab_fetch")

    if fetch_clicked:
        target = platform if platform != "All platforms" else "Play Store reviews"
        with st.spinner(f"Fetching {how_many} reviews from {target}…"):
            try:
                fetched, note = _fetch_platform_reviews(target, limit=int(how_many))
            except Exception as exc:
                fetched, note = [], f"Collector not available here ({exc}). Showing saved reviews from this corpus."
        st.session_state["lab_fetched"] = fetched[: int(how_many)]
        st.session_state["lab_fetch_note"] = note
        st.session_state["lab_fetch_platform"] = target
        st.session_state["lab_fetch_n_used"] = int(how_many)

    view = report
    view_records = records
    if platform != "All platforms":
        view_records = [r for r in records if source_label(r.get("source")) == platform]
        view = build_report(view_records) if view_records else {}
    payload = view.get(spec["key"], {})

    cov = view.get("coverage") or {}
    st.caption(
        f"{platform}: {cov.get('relevant', len([r for r in view_records if r.get('relevant')]))} relevant "
        f"/ {cov.get('total_records', len(view_records))} records in this cut."
    )

    fetched = st.session_state.get("lab_fetched") or []
    n_show = int(st.session_state.get("lab_fetch_n_used") or how_many)
    if fetched or st.session_state.get("lab_fetch_note"):
        st.markdown(f"##### Reviews from {st.session_state.get('lab_fetch_platform') or platform} ({n_show} requested)")
        st.caption(st.session_state.get("lab_fetch_note") or "")
        if fetched:
            for rec in fetched[:n_show]:
                quote_block(rec.get("text") or "", source_label(rec.get("source")), rec.get("rating"))
        else:
            want_plat = st.session_state.get("lab_fetch_platform") or platform
            saved = [
                r for r in records
                if (want_plat == "All platforms" or source_label(r.get("source")) == want_plat)
                and (r.get("text") or "").strip()
            ][:n_show]
            if saved:
                st.info("Live fetch did not return new items. Showing saved reviews from this corpus.")
                for rec in saved:
                    quote_block(rec.get("text") or "", source_label(rec.get("source")), rec.get("rating"))
            else:
                st.warning("No reviews on disk for that platform yet. Run `python collect.py --sources …` locally.")

    st.markdown(f"#### {spec['question']}")
    st.caption(spec["lens"])

    if spec["id"] == "q1":
        st.metric("Wishlist signals", payload.get("wishlist_mentions", 0))
        reasons = payload.get("top_reasons") or []
        if reasons:
            st.dataframe(
                pd.DataFrame(reasons, columns=["reason", "count"]),
                hide_index=True, use_container_width=True,
            )
        for q in payload.get("quotes") or []:
            quote_block(q.get("text", ""), q.get("source", ""), q.get("rating"))

    elif spec["id"] in ("q2", "q10"):
        if spec["id"] == "q2" and isinstance(payload, dict):
            st.caption(payload.get("method") or "")
            stages = payload.get("by_stage") or []
            if stages:
                st.dataframe(pd.DataFrame(stages), hide_index=True, use_container_width=True)
        rows = blocker_rows(payload)
        if rows:
            df = pd.DataFrame(rows)
            want = [
                "blocker_type", "dimension", "wpc_stage", "wpc_leverage",
                "mentions", "reach_pct_of_relevant", "frustration_rate_pct",
                "source_count", "opportunity_score", "wpc_weighted_score",
            ]
            show = df[[c for c in want if c in df.columns]].rename(columns={
                "blocker_type": "blocker",
                "reach_pct_of_relevant": "reach %",
                "frustration_rate_pct": "frustration %",
                "opportunity_score": "VOC score",
                "wpc_weighted_score": "WPC-weighted",
                "source_count": "sources",
            })
            st.dataframe(show, hide_index=True, use_container_width=True)
            if "VOC score" in show.columns:
                st.bar_chart(show.set_index("dimension")["VOC score"], color="#FF3F6C")
            st.caption("WPC-weighted = VOC score × journey leverage. Not a measured conversion lift.")

    elif spec["id"] in ("q3", "q4", "q5"):
        st.metric("Mentions", payload.get("mentions", 0))
        st.caption(f"{payload.get('share_of_blockers_pct', 0)}% of identified blockers")
        br = payload.get("breakdown") or []
        if br:
            st.dataframe(pd.DataFrame(br, columns=["blocker", "count"]),
                         hide_index=True, use_container_width=True)
        for q in payload.get("quotes") or []:
            quote_block(q.get("text", ""), q.get("source", ""), q.get("rating"))

    elif spec["id"] == "q6":
        st.metric("Off-platform mentions", payload.get("off_platform_total", 0))
        ch = payload.get("by_channel") or []
        if ch:
            df = pd.DataFrame(ch, columns=["channel", "mentions"])
            st.bar_chart(df.set_index("channel"), color="#FF3F6C")
            st.dataframe(df, hide_index=True, use_container_width=True)
        for q in payload.get("quotes") or []:
            quote_block(q.get("text", ""), q.get("source", ""), q.get("rating"))

    elif spec["id"] == "q7":
        dims = payload.get("by_dimension") or []
        if dims:
            df = pd.DataFrame(dims)
            st.bar_chart(df.set_index("dimension")["share_pct"], color="#FF3F6C")
            st.dataframe(df, hide_index=True, use_container_width=True)

    elif spec["id"] == "q8":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wishlist mentions", payload.get("wishlist_mentions", 0))
        c2.metric("Genuine intent", payload.get("genuine_intent", 0))
        c3.metric("Bookmarking", payload.get("bookmarking", 0))
        c4.metric("Unclear", payload.get("unclear", 0))
        st.info("Wishlist talk is rare in app reviews. Treat this cut as under-sampled; recruit interviews.")

    elif spec["id"] == "q9":
        if isinstance(payload, dict):
            st.caption(payload.get("note") or "")
            max_w = payload.get("maximum_weightage_pct")
            if max_w is not None:
                st.metric("Maximum survey weightage", f"{max_w}%")
            personas = payload.get("personas") or []
            if personas:
                st.dataframe(
                    pd.DataFrame([{
                        "rank": p.get("rank"),
                        "intent": p.get("name"),
                        "when": p.get("horizon"),
                        "max weightage %": p.get("max_weightage_pct"),
                        "primary need": p.get("primary_need"),
                        "main barrier": p.get("main_barrier"),
                        "VOC mentions": p.get("voc_mentions"),
                    } for p in personas]),
                    hide_index=True,
                    use_container_width=True,
                )
        else:
            rows = payload if isinstance(payload, list) else []
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Spot-check quotes for the top blocker when looking at opportunities
    if spec["id"] in ("q2", "q10") and quotes:
        st.markdown("##### Sample quotes (spot-check categorization)")
        rows = blocker_rows(payload)
        top_bt = (rows[0].get("blocker_type") if rows else None)
        shown = 0
        for item in quotes.get(top_bt) or []:
            if platform != "All platforms" and source_label(item.get("source")) != platform:
                continue
            quote_block(item.get("text", ""), item.get("source", ""), item.get("rating"))
            shown += 1
            if shown >= 3:
                break
        if not shown:
            for rec in view_records:
                if rec.get("blocker_type") == top_bt and rec.get("text"):
                    quote_block(rec.get("text") or "", source_label(rec.get("source")), rec.get("rating"))
                    shown += 1
                    if shown >= 3:
                        break


def page_library(report: dict, records: list[dict]) -> None:
    st.markdown("### Search and Library")
    st.caption(
        "Compare opportunity areas that could influence wishlist→purchase conversion. "
        "Sentiment is an input to frustration rate, not the product."
    )
    cov = report.get("coverage", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Corpus", cov.get("total_records", 0))
    c2.metric("Relevant", cov.get("relevant", 0))
    c3.metric("Failed extraction", cov.get("failed", 0))

    tab_opp, tab_src, tab_sent = st.tabs(["Opportunity comparison", "Sources", "Sentiment (input)"])
    with tab_opp:
        cmp = report.get("opportunity_comparison") or {}
        st.caption(cmp.get("note") or "")
        tops = st.columns(3)
        hit_v = cmp.get("top_by_volume") or {}
        hit_f = cmp.get("top_by_frustration") or {}
        intents = report.get("intent_segments") or {}
        max_w = intents.get("maximum_weightage_pct")
        at_max = " · ".join(
            p.get("name") or ""
            for p in (intents.get("personas") or [])
            if p.get("max_weightage_pct") == max_w
        )
        tops[0].metric("Highest volume", hit_v.get("blocker_type") or "—", str(hit_v.get("value") or ""))
        tops[1].metric("Highest frustration", hit_f.get("blocker_type") or "—", str(hit_f.get("value") or ""))
        tops[2].metric("Maximum survey weightage", f"{max_w}%" if max_w is not None else "—", at_max or None)
        rows = cmp.get("rows") or report.get("opportunity_areas") or []
        if rows:
            df = pd.DataFrame(rows)
            if "survey_weightage_pct" in df.columns:
                st.bar_chart(
                    df.set_index("dimension")[["mentions", "survey_weightage_pct"]],
                    color=["#FF3F6C", "#282C3F"],
                )
            show_cols = [c for c in (
                "blocker_type", "purchase_intent", "intent_rank", "survey_weightage_pct",
                "mentions", "frustration_rate_pct", "source_count", "opportunity_score",
            ) if c in df.columns]
            st.dataframe(df[show_cols].rename(columns={
                "purchase_intent": "intent",
                "survey_weightage_pct": "max weightage %",
                "opportunity_score": "VOC score",
            }), hide_index=True, use_container_width=True)
    with tab_src:
        src_rows = cov.get("by_source") or []
        if src_rows:
            df = pd.DataFrame(src_rows)
            st.bar_chart(df.set_index("source")["relevant"], color="#E3365B")
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            counts = Counter(source_label(r.get("source")) for r in records)
            if counts:
                st.bar_chart(pd.Series(counts), color="#E3365B")
    with tab_sent:
        relevant = [r for r in records if r.get("relevant") is True]
        counts = Counter(r.get("sentiment") or "unknown" for r in relevant)
        if counts:
            st.caption("Used only to compute frustration rate inside opportunity score.")
            st.bar_chart(pd.Series(counts), color="#FF3F6C")


def page_segments(report: dict) -> None:
    st.markdown("### Segments")
    data = report.get("intent_segments") or report.get("q9_by_segment") or report.get("age_segments") or {}
    st.caption(
        data.get("note")
        or "Purchase-intent segments. Survey weightage is not a funnel rate."
    )
    personas = data.get("personas") or []
    if not personas:
        st.info("No intent-segment table. Re-run `python discover.py`.")
        return

    max_w = data.get("maximum_weightage_pct")
    c1, c2, c3 = st.columns(3)
    c1.metric("Maximum weightage", f"{max_w}%" if max_w is not None else "—")
    c2.metric("Intent segments", len(personas))
    c3.metric("Cut", "Intent (not age)")
    if data.get("weightage_source"):
        st.caption(data["weightage_source"])

    st.markdown("#### Intent segments")
    st.dataframe(
        pd.DataFrame([{
            "rank": p.get("rank"),
            "intent": p.get("name"),
            "when": p.get("horizon"),
            "max weightage %": p.get("max_weightage_pct"),
            "impact": p.get("impact"),
            "primary need": p.get("primary_need"),
            "main barrier": p.get("main_barrier"),
            "VOC mentions (related blockers)": p.get("voc_mentions"),
        } for p in personas]),
        hide_index=True,
        use_container_width=True,
    )
    wdf = pd.DataFrame(personas).set_index("name")["max_weightage_pct"]
    st.bar_chart(wdf, color="#FF3F6C")
    st.caption("Bar length is survey max weightage (%), not VOC volume and not a conversion lift.")

    for p in personas:
        tag = f"{p.get('horizon') or ''} · {p.get('impact') or ''}".strip(" ·")
        with st.expander(f"#{p.get('rank')} {p.get('name')} · {p.get('max_weightage_pct')}% max weightage · {tag}"):
            st.markdown(f"**Primary need:** {p.get('primary_need')}")
            st.markdown(f"**Main conversion barrier:** {p.get('main_barrier')}")
            ev = p.get("survey_evidence") or []
            if ev:
                st.markdown("**Survey evidence**")
                for line in ev:
                    st.markdown(f"- {line}")
            if p.get("conversion_hypothesis"):
                st.caption(p["conversion_hypothesis"])
            sols = p.get("ai_solutions") or []
            if sols:
                st.markdown("**AI solutions (proposed)**")
                for line in sols:
                    st.markdown(f"- {line}")
            match = p.get("voc_match") or []
            if match:
                st.markdown("**Related public-VOC blockers**")
                st.dataframe(pd.DataFrame(match), hide_index=True, use_container_width=True)

    inferred = (report.get("q9_by_segment") or {}).get("inferred_blockers") or []
    if inferred:
        st.markdown("#### Older cut — free-text `segment_signal` (directional)")
        st.dataframe(pd.DataFrame(inferred), hide_index=True, use_container_width=True)


def page_raw(records: list[dict]) -> None:
    st.markdown("### Raw Data")
    if not records:
        st.info("No structured_insights.jsonl found.")
        return
    blockers = sorted({str(r.get("blocker_type") or "") for r in records if r.get("blocker_type")})
    sentiments = sorted({str(r.get("sentiment") or "") for r in records if r.get("sentiment")})

    c1, c2, c3, c4 = st.columns(4)
    src = c1.multiselect("Source", SOURCE_FILTER_OPTIONS)
    bt = c2.multiselect("Blocker", blockers)
    sent = c3.multiselect("Sentiment", sentiments)
    only_rel = c4.checkbox("Relevant only", value=False)
    q = st.text_input("Search text")

    rows = records
    if only_rel:
        rows = [r for r in rows if r.get("relevant") is True]
    if src:
        rows = [r for r in rows if source_label(r.get("source")) in src]
    if bt:
        rows = [r for r in rows if r.get("blocker_type") in bt]
    if sent:
        rows = [r for r in rows if r.get("sentiment") in sent]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in (r.get("text") or "").lower()]

    st.caption(f"{len(rows)} rows")
    preview = [{
        "source": source_label(r.get("source")),
        "rating": r.get("rating"),
        "sentiment": r.get("sentiment"),
        "blocker_type": r.get("blocker_type"),
        "segment_signal": r.get("segment_signal"),
        "text": (r.get("text") or "")[:280],
    } for r in rows[:400]]
    st.dataframe(pd.DataFrame(preview), hide_index=True, use_container_width=True)


def page_phase1(spec: dict) -> None:
    st.markdown("### Phase 1 · Quantitative discovery")
    st.caption(spec.get("purpose") or "")
    st.info(
        spec.get("status_note")
        or "Needs first-party wishlist analytics. Public VOC cannot fill this table."
    )
    st.markdown(f"**North-star:** {spec.get('north_star', '')}")
    st.markdown(f"**Output of this phase:** {spec.get('output', '')}")
    cuts = spec.get("cuts") or []
    if cuts:
        st.markdown("**Cuts on every metric:** " + " · ".join(cuts))

    for i, ws in enumerate(spec.get("workstreams") or [], start=1):
        st.markdown(
            f'<div class="home-pipeline-step"><strong>{i} · {ws.get("title", "")}</strong>'
            f'<br/>{ws.get("job", "")}'
            f'<br/><span style="color:#535766">{ws.get("grain", "")}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Drop-off map (schema — empty until warehouse data)")
    st.dataframe(
        pd.DataFrame(
            columns=[
                "category",
                "price_band",
                "user_tenure",
                "wishlist_size_bucket",
                "never_revisited_pct",
                "revisited_not_purchased_pct",
                "purchased_pct",
                "removed_pct",
                "p50_hours_to_purchase",
                "oos_death_pct",
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "This table is the Phase 1 deliverable. Do not interview until the densest cells are filled."
    )


def page_reviewer(records: list[dict] | None = None) -> None:
    from rag import load_chatgpt, load_voc, retrieve, build_review_file

    records = records or []
    st.markdown("### Reviewer · RAG")
    st.caption(
        "Retrieve public-VOC quotes and ChatGPT wishlist-conversion research, then ground an answer. "
        "The ChatGPT share is a PM case study — its example funnel rates are not Myntra measurements. "
        "Fetch reviews from any of the eight public platforms below."
    )

    st.markdown("#### Fetch reviews")
    fc1, fc2, fc3 = st.columns([2.4, 1.0, 1.1])
    fetch_platform = fc1.selectbox("Platform", SOURCE_FILTER_OPTIONS, key="reviewer_platform")
    fetch_n = fc2.selectbox("How many reviews", FETCH_COUNTS, index=1, key="reviewer_fetch_n")
    fetch_clicked = fc3.button("Fetch reviews", use_container_width=True, key="reviewer_fetch")
    if fetch_clicked:
        with st.spinner(f"Fetching {fetch_n} reviews from {fetch_platform}…"):
            try:
                fetched, note = _fetch_platform_reviews(fetch_platform, limit=int(fetch_n))
            except Exception as exc:
                fetched, note = [], f"Collector not available here ({exc}). Showing saved reviews from this corpus."
        st.session_state["reviewer_fetched"] = fetched[: int(fetch_n)]
        st.session_state["reviewer_fetch_note"] = note
        st.session_state["reviewer_fetch_platform"] = fetch_platform
        st.session_state["reviewer_fetch_n_used"] = int(fetch_n)

    fetched = st.session_state.get("reviewer_fetched") or []
    n_show = int(st.session_state.get("reviewer_fetch_n_used") or fetch_n)
    if fetched or st.session_state.get("reviewer_fetch_note"):
        st.markdown(f"##### Reviews from {st.session_state.get('reviewer_fetch_platform') or fetch_platform} ({n_show} requested)")
        st.caption(st.session_state.get("reviewer_fetch_note") or "")
        if fetched:
            for rec in fetched[:n_show]:
                quote_block(rec.get("text") or "", source_label(rec.get("source")), rec.get("rating"))
        else:
            saved = [
                r for r in records
                if source_label(r.get("source")) == (st.session_state.get("reviewer_fetch_platform") or fetch_platform)
                and (r.get("text") or "").strip()
            ][:n_show]
            if saved:
                st.info("Live fetch did not return new items. Showing saved reviews from this corpus.")
                for rec in saved:
                    quote_block(rec.get("text") or "", source_label(rec.get("source")), rec.get("rating"))
            else:
                st.warning("No reviews on disk for that platform yet. Run `python collect.py --sources …` locally.")

    review_path = ROOT / "rag_review.json"
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else build_review_file()
    research = load_chatgpt()
    st.markdown(f"**Research:** [{research.get('title', 'ChatGPT share')}]({research.get('url', '')})")
    st.info(research.get("problem_statement") or "")
    st.markdown(f"**North-star (from research):** {research.get('north_star', '')}")

    st.markdown("#### ChatGPT hypotheses vs this corpus")
    tri = review.get("triangulation") or []
    if tri:
        st.dataframe(pd.DataFrame(tri), hide_index=True, use_container_width=True)
        st.caption("sized_in_voc = that blocker exists in public reviews. not_in_public_voc = ChatGPT hypothesis with no matching VOC row (e.g. OOS).")

    q = st.text_input("Ask the corpus", placeholder="Why don't people buy from the wishlist?")
    if q:
        hits = retrieve(q, load_voc(), research.get("chunks") or [])
        left, right = st.columns(2)
        with left:
            st.markdown("**Retrieved VOC**")
            if not hits["voc"]:
                st.write("No overlapping quotes.")
            for h in hits["voc"]:
                quote_block(h.get("text", ""), source_label(h.get("source")), None)
                st.caption(f"{h.get('blocker_type') or '—'} · score {h.get('score')}")
        with right:
            st.markdown("**Retrieved ChatGPT research**")
            for h in hits["chatgpt"]:
                st.markdown(f"**{h.get('title')}** — {h.get('kind')}")
                st.write(h.get("text"))
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key and (hits["voc"] or hits["chatgpt"]):
            if st.button("Synthesize with Groq"):
                try:
                    import requests
                    ctx = json.dumps({"voc": hits["voc"], "chatgpt": hits["chatgpt"]}, ensure_ascii=False)[:8000]
                    prompt = (
                        "You are reviewing Myntra wishlist→purchase research. "
                        "Use ONLY the retrieved VOC quotes and ChatGPT chunks. "
                        "Do not invent funnel percentages. Cite which side each claim comes from.\n\n"
                        f"Question: {q}\n\nEvidence:\n{ctx}"
                    )
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                        json={
                            "model": "openai/gpt-oss-120b",
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                        },
                        timeout=60,
                    )
                    resp.raise_for_status()
                    st.markdown(resp.json()["choices"][0]["message"]["content"])
                except Exception as exc:
                    st.error(f"Groq synthesize failed: {exc}")


def page_roadmap() -> None:
    st.markdown("### AI Roadmap")
    st.caption("Prioritized solutions from opportunity_proposal.md — evidence → solution, not a sized business case.")
    if not PROPOSAL_PATH.exists():
        st.info("opportunity_proposal.md not found.")
        return
    st.markdown(PROPOSAL_PATH.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(
        page_title="Myntra Discovery Engine",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_myntra_css()
    st.sidebar.markdown(
        """
        <h1 class="aura-brand-title">Myntra</h1>
        <p class="aura-brand-sub">Discovery Engine</p>
        """,
        unsafe_allow_html=True,
    )

    if "nav_choice" not in st.session_state:
        st.session_state["nav_choice"] = "Home"

    display = [f"{NAV_ICONS[p]} {p}" for p in NAV_PAGES]
    mapping = dict(zip(display, NAV_PAGES))
    current = st.session_state["nav_choice"]
    idx = NAV_PAGES.index(current) if current in NAV_PAGES else 0
    picked = st.sidebar.radio("Go to", display, index=idx, label_visibility="collapsed")
    page = mapping[picked]
    st.session_state["nav_choice"] = page

    report = load_report(_file_stamp(REPORT_PATH))
    records = load_insights(_file_stamp(INSIGHTS_PATH))
    quotes = load_quotes(_file_stamp(QUOTES_PATH))

    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    st.sidebar.markdown("---")
    if groq_ok:
        st.sidebar.success("LLM: Groq key present")
    else:
        st.sidebar.warning("No GROQ_API_KEY — viewing saved extraction only")
    st.sidebar.caption("Eight sources · ten questions · compare opportunities")

    if page == "Home":
        page_home(report, records)
    elif page == "Discovery Lab":
        page_discovery_lab(report, quotes, records)
    elif page == "Search and Library":
        page_library(report, records)
    elif page == "Segments":
        page_segments(report)
    elif page == "Raw Data":
        page_raw(records)
    elif page == "Reviewer":
        page_reviewer(records)
    else:
        page_roadmap()


if __name__ == "__main__":
    main()
