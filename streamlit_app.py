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
PHASE2_PATH = ROOT / "phase2_methods.json"
PHASE3_PATH = ROOT / "phase3_opportunity_map.json"
PHASE4_PATH = ROOT / "phase4_solutions.json"
PHASE5_PATH = ROOT / "phase5_experiments.json"

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
        "lens": "Ranked blocker types by opportunity score (reach × frustration)",
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
        "lens": "Model-inferred segment_signal concentration per blocker",
    },
    {
        "id": "q10",
        "icon": "🎯",
        "short_title": "Unmet needs",
        "question": "What unmet needs emerge consistently across user conversations?",
        "key": "opportunity_areas",
        "lens": "Prioritized opportunity areas — the headline ranking",
    },
]

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
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Phase 4",
    "Phase 5",
    "Discovery Lab",
    "Search and Library",
    "Segments",
    "Raw Data",
    "AI Roadmap",
]
NAV_ICONS = {
    "Home": "🏠",
    "Phase 1": "📊",
    "Phase 2": "🎙️",
    "Phase 3": "🗺️",
    "Phase 4": "💡",
    "Phase 5": "🧪",
    "Discovery Lab": "🔬",
    "Search and Library": "📚",
    "Segments": "👥",
    "Raw Data": "📋",
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


@st.cache_data(show_spinner=False)
def load_phase2(stamp: tuple[float, int]) -> dict:
    if not PHASE2_PATH.exists():
        return {}
    return json.loads(PHASE2_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_phase3(stamp: tuple[float, int]) -> dict:
    if not PHASE3_PATH.exists():
        return {}
    return json.loads(PHASE3_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_phase4(stamp: tuple[float, int]) -> dict:
    if not PHASE4_PATH.exists():
        return {}
    return json.loads(PHASE4_PATH.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_phase5(stamp: tuple[float, int]) -> dict:
    if not PHASE5_PATH.exists():
        return {}
    return json.loads(PHASE5_PATH.read_text(encoding="utf-8"))


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
          Phased wishlist research for Myntra. <strong>Phase 1</strong> where,
          <strong>2</strong> why, <strong>3</strong> ranked map,
          <strong>4</strong> non-monetary sketches,
          <strong>5</strong> scoped A/B — then scale.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("#### What this analyzer is for")
        st.markdown(
            "**Phase 1** maps where. **Phase 2** is why. **Phase 3** sizes and ranks frictions. "
            "**Phase 4** sketches non-monetary solutions (no coupons) on the ranked mix — including "
            "splitting inspiration vs ready-to-buy so moodboarders do not dilute the metric. "
            "**Phase 5** A/Bs the top 1–2 bets in the concentrating cell, with return-rate and "
            "time-to-first-purchase guardrails. Public reviews cannot fill funnel rates. The collect → "
            "extract pipeline is a **companion** that seeds codes, not this backlog."
        )
        st.markdown("#### Research structure")
        for title, body in (
            ("Phase 1 · Quantitative discovery", "Wishlist funnel, time-to-purchase, OOS, price trajectory, wishlist size, revisits, category, search-before-drop, cart baseline. Output: where to spend interview budget."),
            ("Phase 2 · Qualitative why", "Diaries (in the moment), live wishlist item-by-item, micro-surveys at remove / 14-day reopen, off-platform ask, comparison shadowing. Output: reason inventory + frequency check."),
            ("Phase 3 · Opportunity map", "Affinity → directional % of non-converted items → segment by category / tenure / wishlist size → RICE-like rank. Quotes are evidence, not the deliverable."),
            ("Phase 4 · Non-monetary solutions", "Illustrative directions per friction (fit, compare, trust, occasion, forgetting, bookmarking split). Not a build list until Phase 3 ranks. No discounts."),
            ("Phase 5 · Validate before scale", "Top 1–2 bets, A/B in the concentrating cell. Primary: wishlist→purchase in 30 days. Guardrails: returns, time-to-first-purchase."),
            ("Companion · Public VOC", "Play Store, App Store, Reddit, communities, social, YouTube, product Q&A → stated blockers. Seeds codes; does not replace diaries or this map."),
        ):
            st.markdown(
                f'<div class="home-pipeline-step"><strong>{title}</strong><br/>{body}</div>',
                unsafe_allow_html=True,
            )
    with right:
        st.markdown("#### Where reviews are fetched from")
        for label, note in (
            ("Google Play — Myntra", "Public Android reviews. No API key."),
            ("Apple App Store — Myntra", "iTunes RSS fallback when the scraper is empty."),
            ("YouTube hauls", "Comments on Myntra try-on / honest-review videos."),
            ("Reddit discussions", "Public archive + Arctic Shift. PRAW comments if credentials exist."),
            ("Fashion & shopping communities", "IndianFashionAddicts, FFA, MFA, onlineshopping, and related subs."),
            ("Social + other public", "Public Twitter syndication and Hacker News threads."),
            ("Product reviews & Q&A", "Sitejabber reviews and HN comments about Myntra."),
        ):
            st.markdown(
                f'<div class="home-card"><h4>{label}</h4><p>{note}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### Where to go in this dashboard")
    nav_guide = [
        ("Phase 1", "Nine quantitative workstreams and the drop-off map this phase owes."),
        ("Phase 2", "Diaries, live wishlist, micro-surveys, off-platform ask, comparison shadowing."),
        ("Phase 3", "Friction types, directional sizing, segment hypotheses, RICE-like backlog (empty until fieldwork)."),
        ("Phase 4", "Non-monetary sketches per friction — illustrative, not a roadmap until the map is filled."),
        ("Phase 5", "Top 1–2 scoped A/Bs; 30-day conversion; return-rate and time-to-purchase guardrails."),
        ("Discovery Lab", "Public-VOC companion: ten stated-blocker questions and quotes."),
        ("Search and Library", "Opportunity ranking, blocker mix, and corpus charts."),
        ("Segments", "Who feels which blocker — model-inferred concentration."),
        ("Raw Data", "Browse extracted reviews and filter by source / blocker / sentiment."),
        ("AI Roadmap", "Prioritized solutions from opportunity_proposal.md."),
    ]
    cols = st.columns(2)
    for i, (label, desc) in enumerate(nav_guide):
        with cols[i % 2]:
            st.markdown(
                f'<div class="home-nav-row"><span class="home-nav-label">{label}</span> — {desc}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records in session", cov.get("total_records") or len(records) or "—")
    c2.metric("Extracted", cov.get("extracted") or "—")
    c3.metric("Relevant", cov.get("relevant") or "—")
    c4.metric("Research questions", "10 structured")
    if not cov.get("relevant"):
        st.info("No discovery report yet. Run `python discover.py` after Stage 2 extraction.")


def page_discovery_lab(report: dict, quotes: dict) -> None:
    st.markdown("### Discovery Lab")
    st.caption("Ten product-discovery questions. Answers are counted from structured extraction, not summaries.")
    labels = [f"{q['icon']} {q['short_title']}" for q in DISCOVERY_QUESTIONS]
    picked = st.radio("Question", labels, horizontal=True, label_visibility="collapsed")
    spec = DISCOVERY_QUESTIONS[labels.index(picked)]
    payload = report.get(spec["key"], {})

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
        rows = payload if isinstance(payload, list) else []
        if rows:
            df = pd.DataFrame(rows)
            show = df[["blocker_type", "dimension", "mentions",
                       "reach_pct_of_relevant", "frustration_rate_pct",
                       "opportunity_score"]].rename(columns={
                "blocker_type": "blocker",
                "reach_pct_of_relevant": "reach %",
                "frustration_rate_pct": "frustration %",
                "opportunity_score": "score",
            })
            st.dataframe(show, hide_index=True, use_container_width=True)
            st.bar_chart(show.set_index("dimension")["score"], color="#FF3F6C")

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
        rows = payload if isinstance(payload, list) else []
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Spot-check quotes for the top blocker when looking at opportunities
    if spec["id"] in ("q2", "q10") and quotes:
        st.markdown("##### Sample quotes (spot-check categorization)")
        top_bt = (payload[0].get("blocker_type") if payload else None)
        for item in (quotes.get(top_bt) or [])[:3]:
            quote_block(item.get("text", ""), item.get("source", ""), item.get("rating"))


def page_library(report: dict, records: list[dict]) -> None:
    st.markdown("### Search and Library")
    cov = report.get("coverage", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Corpus", cov.get("total_records", 0))
    c2.metric("Relevant", cov.get("relevant", 0))
    c3.metric("Failed extraction", cov.get("failed", 0))

    tab_opp, tab_sent, tab_src = st.tabs(["Opportunities", "Sentiment", "Sources"])
    with tab_opp:
        rows = report.get("opportunity_areas") or []
        if rows:
            df = pd.DataFrame(rows)
            st.bar_chart(
                df.set_index("dimension")[["mentions", "frustration_rate_pct"]],
                color=["#FF3F6C", "#282C3F"],
            )
            st.dataframe(df, hide_index=True, use_container_width=True)
    with tab_sent:
        relevant = [r for r in records if r.get("relevant") is True]
        counts = Counter(r.get("sentiment") or "unknown" for r in relevant)
        if counts:
            st.bar_chart(pd.Series(counts), color="#FF3F6C")
    with tab_src:
        counts = Counter(source_label(r.get("source")) for r in records)
        if counts:
            st.bar_chart(pd.Series(counts), color="#E3365B")


def page_segments(report: dict) -> None:
    st.markdown("### Segments")
    st.caption("segment_signal is model-inferred free text — directional, not verified personas.")
    rows = report.get("q9_by_segment") or []
    if not rows:
        st.info("No segment table. Re-run `python discover.py`.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)
    known = df[df["top_segment"] != "(unknown)"]
    if not known.empty:
        st.bar_chart(
            known.set_index("blocker_type")["top_segment_concentration_pct"],
            color="#FF3F6C",
        )


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


def page_phase2(spec: dict) -> None:
    st.markdown("### Phase 2 · Qualitative discovery (the why)")
    if not spec:
        st.info("phase2_methods.json not found.")
        return
    st.caption(spec.get("purpose") or "")
    st.info(spec.get("status_note") or "")
    st.markdown(f"**North-star:** {spec.get('north_star', '')}")
    st.markdown(f"**Recruit:** {spec.get('recruit_rule', '')}")
    st.markdown(f"**Output of this phase:** {spec.get('output', '')}")

    for i, m in enumerate(spec.get("methods") or [], start=1):
        st.markdown(
            f'<div class="home-pipeline-step"><strong>{i} · {m.get("title", "")}</strong>'
            f'<br/>{m.get("job", "")}'
            f'<br/><span style="color:#535766">{m.get("sample", "")}'
            f' — {m.get("bias_it_avoids", "")}</span></div>',
            unsafe_allow_html=True,
        )

    triggers = spec.get("survey_triggers") or []
    if triggers:
        st.markdown("#### Micro-surveys (frequency check — empty until in-app)")
        st.dataframe(pd.DataFrame(triggers), hide_index=True, use_container_width=True)

    listen = spec.get("off_platform_listen_for") or []
    if listen:
        st.markdown("**Off-platform — listen for:** " + " · ".join(listen))

    st.caption(
        "Interviews list reasons. Micro-surveys rank them. Do not treat 15–20 sessions as a frequency study."
    )


def page_phase3(spec: dict) -> None:
    st.markdown("### Phase 3 · Synthesis (the opportunity map)")
    if not spec:
        st.info("phase3_opportunity_map.json not found.")
        return
    st.caption(spec.get("purpose") or "")
    st.info(spec.get("status_note") or "")
    st.markdown(f"**North-star:** {spec.get('north_star', '')}")
    st.markdown(f"**Output of this phase:** {spec.get('output', '')}")
    st.markdown(f"**Score:** `{spec.get('formula', '')}`")

    for i, step in enumerate(spec.get("steps") or [], start=1):
        st.markdown(
            f'<div class="home-pipeline-step"><strong>{i} · {step.get("title", "")}</strong>'
            f'<br/>{step.get("job", "")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Starter friction codebook (freeze after Phase 2 affinity)")
    types = spec.get("friction_types") or []
    if types:
        st.dataframe(
            pd.DataFrame(
                [{"id": t.get("id"), "friction_type": t.get("label"), "typical_signal": t.get("signal")} for t in types]
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Segment the map (hypotheses — not findings)")
    hyps = spec.get("segment_hypotheses") or []
    if hyps:
        st.dataframe(pd.DataFrame(hyps), hide_index=True, use_container_width=True)

    cols = spec.get("map_columns") or [
        "friction_type",
        "reach_pct_nonconverted",
        "frequency",
        "conversion_lift",
        "confidence",
        "effort",
        "rice_score",
        "concentration_note",
    ]
    empty_rows = [{c: t.get("label") if c == "friction_type" else None for c in cols} for t in types]
    st.markdown("#### Opportunity map (empty until Phase 1 + Phase 2 data)")
    st.dataframe(pd.DataFrame(empty_rows or [{c: None for c in cols}]), hide_index=True, use_container_width=True)
    example = spec.get("sizing_format_example") or ""
    if example:
        st.caption(example)
    st.caption(
        "Do not rank by quote vividness. Do not paste public-VOC opportunity_score into rice_score."
    )


def page_phase4(spec: dict) -> None:
    st.markdown("### Phase 4 · Solution ideation (non-monetary)")
    if not spec:
        st.info("phase4_solutions.json not found.")
        return
    st.caption(spec.get("purpose") or "")
    st.info(spec.get("status_note") or "")
    st.markdown(f"**North-star:** {spec.get('north_star', '')}")
    st.markdown(f"**Constraint:** {spec.get('constraint', '')}")
    st.markdown(f"**Output of this phase:** {spec.get('output', '')}")
    lever = spec.get("biggest_lever_hypothesis") or ""
    if lever:
        st.warning(lever)

    for d in spec.get("directions") or []:
        ideas = d.get("ideas") or []
        body = "<br/>".join(f"· {idea}" for idea in ideas)
        st.markdown(
            f'<div class="home-pipeline-step"><strong>{d.get("friction", "")}</strong>'
            f'<br/>{body}</div>',
            unsafe_allow_html=True,
        )
    st.caption(
        "Illustrative only. Ideate on top-ranked Phase 3 rows, bound to a cell. Phase 5 picks 1–2 bets."
    )


def page_phase5(spec: dict) -> None:
    st.markdown("### Phase 5 · Validate before you scale")
    if not spec:
        st.info("phase5_experiments.json not found.")
        return
    st.caption(spec.get("purpose") or "")
    st.info(spec.get("status_note") or "")
    st.markdown(f"**North-star / primary:** {spec.get('north_star', '')}")
    st.markdown(f"**Output of this phase:** {spec.get('output', '')}")
    st.markdown(f"**Max bets:** {spec.get('max_bets', 2)}")

    primary = spec.get("primary_metric") or {}
    if primary:
        st.markdown(
            f"**{primary.get('name', '')}:** {primary.get('definition', '')} "
            f"Grain: `{primary.get('grain', '')}`."
        )

    guards = spec.get("guardrails") or []
    for g in guards:
        st.markdown(
            f'<div class="home-pipeline-step"><strong>Guardrail · {g.get("label", "")}</strong>'
            f'<br/>{g.get("why", "")}</div>',
            unsafe_allow_html=True,
        )

    rules = spec.get("rules") or []
    if rules:
        st.markdown("**Rules:**")
        for r in rules:
            st.markdown(f"- {r}")

    cols = spec.get("brief_columns") or []
    n = int(spec.get("max_bets") or 2)
    empty = [{c: f"bet_{i}" if c == "bet_id" else None for c in cols} for i in range(1, n + 1)]
    st.markdown("#### Experiment briefs (empty until Phase 3 ranks)")
    st.dataframe(pd.DataFrame(empty or [{c: None for c in cols}]), hide_index=True, use_container_width=True)
    st.caption(
        "A/B in the concentrating cell. Do not measure success as widget clicks. Do not invent lift."
    )


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
    phase1 = load_phase1(_file_stamp(PHASE1_PATH))
    phase2 = load_phase2(_file_stamp(PHASE2_PATH))
    phase3 = load_phase3(_file_stamp(PHASE3_PATH))
    phase4 = load_phase4(_file_stamp(PHASE4_PATH))
    phase5 = load_phase5(_file_stamp(PHASE5_PATH))

    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    st.sidebar.markdown("---")
    if groq_ok:
        st.sidebar.success("LLM: Groq key present")
    else:
        st.sidebar.warning("No GROQ_API_KEY — viewing saved extraction only")
    st.sidebar.caption("1 where · 2 why · 3 map · 4 bets · 5 A/B · VOC")

    if page == "Home":
        page_home(report, records)
    elif page == "Phase 1":
        page_phase1(phase1)
    elif page == "Phase 2":
        page_phase2(phase2)
    elif page == "Phase 3":
        page_phase3(phase3)
    elif page == "Phase 4":
        page_phase4(phase4)
    elif page == "Phase 5":
        page_phase5(phase5)
    elif page == "Discovery Lab":
        page_discovery_lab(report, quotes)
    elif page == "Search and Library":
        page_library(report, records)
    elif page == "Segments":
        page_segments(report)
    elif page == "Raw Data":
        page_raw(records)
    else:
        page_roadmap()


if __name__ == "__main__":
    main()
