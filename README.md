# Wishlist → purchase research (Myntra)

**Phase 1 is quantitative** — cheap, fast, and run first so later work is
pointed at *where* drop-off concentrates, not at a generic wishlist problem.

| Phase | Job | Output |
| ----- | --- | ------ |
| **1. Quantitative discovery** | Funnel, time-to-purchase, stock, price, wishlist size, revisits, category, search-before-drop, cart baseline | Segmented drop-off map — **where** conversion dies |
| Companion: public VOC | Stated blockers in reviews/social (`collect` → `extract` → `discover`) | Ranked *why* hypotheses inside those cells |

Phase 1 needs **first-party** events. Public reviews cannot compute funnel rates. Spec: [`phase1_quantitative_discovery.md`](phase1_quantitative_discovery.md).

The rest of this README is the **VOC companion** pipeline (flat files, fixed blocker taxonomy).

---

## What you get (the outputs that matter)

The headline deliverable is **`discovery_report.md`** (Stage 4) — a narrative that
answers the product-discovery questions and ranks opportunity areas. It's backed
by four detailed cuts (Stage 3):

### 1. `opportunity_summary.csv` — the headline
One row per blocker type, ranked by an **opportunity score**. Columns:

| Column | What it means |
| ------ | ------------- |
| `blocker_type` | The category of what's stopping the purchase (e.g. `fit_sizing`, `price`, `trust_authenticity`). |
| `mention_count` | How many relevant mentions fell into this blocker. |
| `pct_of_all_relevant` | This blocker's share of all relevant mentions. *(These won't sum to 100% — some relevant mentions have no clear blocker.)* |
| `frustration_rate_pct` | Of those mentions, how many read as *frustrated*. |
| `avg_confidence` | How sure the model was, on average (0-1). Low = treat that row with more caution. |
| `opportunity_score` | Composite 0-100 that weighs **how often** a blocker shows up and **how frustrating** it is **equally**. Sorted highest-first. |

**How to read it:** the top rows are your best interview topics — problems that
are both common *and* painful. A high-frequency but low-frustration row (e.g.
"waiting for a sale") is a different kind of opportunity than a low-frequency but
100%-frustrated one.

### 2. `blocker_by_segment.csv` — is it concentrated or broad?
A crosstab of blocker type (rows) against inferred user segment (columns), plus:

- `top_segment` — the segment where this blocker shows up most.
- `top_segment_share_pct` — how concentrated it is there.

**How to read it:** a blocker that's ~50% spread across several segments is a
broad, general problem. A blocker that's ~100% concentrated in one segment (e.g.
"first-time buyers doubting authenticity") is a sharper, more targetable signal —
great for recruiting a specific interview cohort.

### 3. `resolution_channel_summary.csv` — the off-platform cut
Where users say they go to decide *before* buying. The `off_platform` column
flags YouTube, Google, friends/family, in-store trials, and influencers.

**Why this is its own headline, not a footnote:** every "yes" in that column is a
moment a shopper *left Myntra* to answer a question the app didn't answer.
That is directly a product opportunity (better size guides, real-fit photos,
authenticity proof, in-app reviews). The run prints the total off-platform share
so you can quote it.

### 4. `sample_quotes_by_blocker.json` — spot-check before you trust the numbers
Three real, original quotes per blocker type (highest-confidence, source-diverse),
with source/date/rating. **Read this first.** If the quotes under a blocker don't
actually match the label, don't trust that row's count yet.

---

## How to run it (three stages)

### One-time setup
Use a fresh virtual environment (one dependency ships broken pins that can
corrupt a shared Python install):

```bash
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-collect.txt   # scrapers + Claude (local pipeline only)
```

Copy `.env.example` to `.env` and fill in keys as needed (see below).

### Stage 1 — collect the raw text → `raw_data.jsonl`
```bash
python collect.py
```
Pulls Google Play reviews (Myntra), Apple App Store reviews (Myntra),
Reddit discussions, fashion/shopping community posts, public social posts,
YouTube haul comments, and product reviews/Q&A. Everything is normalized to one
format and de-duplicated. Reddit API credentials are optional — without them
we still collect via public archives (Pullpush + Arctic Shift).

### Stage 2 — extract structured signals → `structured_insights.jsonl`
Sends each item to an LLM in small batches and forces a strict categorization
into the fixed schema (blocker type, wishlist signal, sentiment, segment guess,
resolution channel, confidence). **This is the stage that makes it a discovery
engine rather than a scraper.** Four interchangeable backends:

```bash
# 1) Claude (cloud) — needs ANTHROPIC_API_KEY in env/.env
python extract.py
python extract.py --limit 20            # cheap first pass to sanity-check

# 2) Groq (cloud, fast open models) — needs GROQ_API_KEY in env/.env
python extract.py --groq                          # default openai/gpt-oss-120b
python extract.py --groq --groq-model openai/gpt-oss-20b
#   Free-tier is rate-limited; the run auto-backs-off on 429s and finishes.

# 3) Local LLM via Ollama (no API key, runs on your machine)
python extract.py --ollama                        # default model qwen2.5:3b*
python extract.py --ollama --ollama-model qwen2.5:7b
#   * requires a running Ollama server + a pulled model, e.g.:
#       ollama serve            (usually auto-starts after install)
#       ollama pull qwen2.5:3b

# 4) Offline heuristic stub (no model at all — plumbing test only)
python extract.py --mock
```

Backend quality (observed): **Claude ≈ Groq (gpt-oss-120b) > Ollama (7B > 3B) >
mock**. The cloud backends nail sentiment and blocker attribution; local models
are cheaper/private but weaker at the harder judgments (segment inference, subtle
blockers) and much slower — smaller batches (`--batch-size 5`) help them stay
reliable. Each output row records which backend produced it in its `model` field.

> Note: Groq keys start with `gsk_` and go in `.env` as `GROQ_API_KEY=...`
> (Anthropic keys start with `sk-ant-` and go in `ANTHROPIC_API_KEY`).

### Stage 3 — aggregate into the CSV cuts
```bash
python aggregate.py
```
Reads Stage 2 output, keeps only relevant items, and writes the four CSV/JSON
files. It also prints a **coverage report** first — see below.

### Stage 4 — synthesize the discovery report
```bash
python discover.py
```
Reads Stage 2 output and writes `discovery_report.md` (PM-facing) and
`discovery_report.json` (machine-readable). This is the layer that makes it a
*discovery engine*: it answers the product-discovery questions directly and ends
with a **prioritized opportunity comparison**, instead of just tabulating cuts:

1. Why do users add products to their wishlist?
2. What prevents wishlisted products from being purchased?
3. What uncertainties remain after a user likes a product?
4. What causes users to postpone a purchase?
5. How do users compare multiple shortlisted products?
6. What information do users seek outside Myntra before buying?
7. What role do fit, size, styling, price, reviews, occasion, and social play?
8. Wishlist as genuine purchase intent vs. a bookmarking mechanism?
9. How do these behaviors differ across user segments?
10. What unmet needs / opportunity areas emerge consistently?

Each answer is quantified from the fixed taxonomy where the data allows, and the
report honestly flags any question the current extraction couldn't populate
(e.g. off-platform research is thin when a weaker local model leaves
`resolution_channel` empty — re-run Stage 2 with Claude to fill it).

---

## Coverage & completeness (so you know what you're standing on)

You should never wonder how much data actually made it through:

- **Stage 2** logs every run to `extraction_run.log` (a line per run with counts
  of processed / extracted / failed items and any failed batch numbers). Failed
  batches are retried with backoff; anything still failing is written with an
  `extraction_error` marker rather than silently dropped, and the run ends with a
  visible WARNING.
- **Stage 3** prints a coverage report at the top of every run: total records,
  how many extracted successfully, how many **failed**, how many were relevant,
  and how many relevant items had no clear blocker. Failed items are excluded
  from the analysis and the exclusion is stated out loud.

If the failure rate is high, treat the numbers as provisional and re-run Stage 2
(it resumes and only reprocesses missing items).

---

## Data limitations (read before quoting any number)

These outputs are **directional signals to prioritize who to interview**, not
statistically representative measurements of the user base. Specifically:

- **The source data is self-selected toward strong opinions.** People who leave
  app reviews, Reddit posts, and YouTube comments skew toward the delighted and
  the angry. Quiet, satisfied shoppers are underrepresented. Frequencies here
  reflect *who chose to speak up*, not the true population.
- **`segment_signal` is model-inferred, not verified.** The segment attached to
  each mention is Claude's guess from the text, not a confirmed attribute of a
  real account. Use the segment crosstab to *form hypotheses about who to
  recruit*, then verify segment in the actual interviews — don't report it as
  fact.
- **Categorization is a model judgment.** Always spot-check
  `sample_quotes_by_blocker.json` before trusting a row's count, and lean on the
  `avg_confidence` column.
- **v1 covers store reviews, Reddit, fashion communities, social posts,
  YouTube, and product reviews/Q&A.** That is enough to prioritize; it is not
  an exhaustive listen.

Bottom line: use this to decide **which blockers and which segments deserve the
next round of user interviews** — then let the interviews produce the
defensible, representative findings.

---

## Reddit & Claude credentials

**Reddit (Stage 1, optional):**
1. Go to <https://www.reddit.com/prefs/apps>, click **create another app**,
   choose type **script**, set redirect URI to `http://localhost:8080`.
2. Copy the **client id** (under the app name) and the **secret** into `.env`:
   ```
   REDDIT_CLIENT_ID=...
   REDDIT_CLIENT_SECRET=...
   REDDIT_USER_AGENT=myntra-voc-collector/0.1 by u/yourname
   ```
   No username/password needed for read-only search.

**Claude (Stage 2, required for real runs):** get a key at
<https://console.anthropic.com/> and set `ANTHROPIC_API_KEY` in `.env`.

---

## Configuration knobs

- **Stage 1** (`collect.py`): app IDs, subreddits, search terms, and YouTube
  video URLs live in the config block at the top. Swap the placeholder YouTube
  URLs for real fashion-haul videos before a full run.
- **Stage 2** (`extract.py`): `--model`, `--batch-size`, `--limit`, `--mock`,
  `--no-resume`.
- **Stage 3** (`aggregate.py`): `--top-segments` (crosstab width), `--quotes`
  (samples per blocker).
- **Stage 4** (`discover.py`): `--quotes` (quotes per section), `--in`/`--outdir`.

## Deploy

**Frontend (Railway)** — Stitch UI in `frontend/`, served by nginx (`Dockerfile` + `railway.json`).
1. Push this repo to GitHub (already `Somu639/Myntra`).
2. In [Railway](https://railway.app/new) → **Deploy from GitHub** → select `Somu639/Myntra`.
3. Railpack uses the **staticfile** provider (`Staticfile` → `frontend/`) and Caddy. Generate a public URL in Settings → Networking.
   If the service still tries to run `python`, clear any custom **Start Command** in Settings → Deploy.

**Backend (Streamlit Community Cloud)** — live analyzer (`streamlit_app.py`) on the committed insights/report files.
1. Open [Deploy this repo on Streamlit](https://share.streamlit.io/deploy?repository=Somu639/Myntra&branch=master&mainModule=streamlit_app.py).
2. Main file: `streamlit_app.py`. Python: 3.12 (`runtime.txt`).
3. After it is live, paste the `*.streamlit.app` URL into `frontend/config.js` as `window.STREAMLIT_BACKEND_URL` so the pink **Open Streamlit backend** button jumps there.

Local Streamlit: `streamlit run streamlit_app.py`

**Reviewer (RAG):** `Reviewer` in Streamlit and `frontend/reviewer.html` retrieve public-VOC quotes against the ChatGPT wishlist-conversion share ([source](https://chatgpt.com/share/6a92fd04-47c4-83e8-942a-4d34aad1ce3b)). Chunks live in `chatgpt_research.json`. Example funnel rates in that share are **illustrative** — not warehouse measurements. Rebuild the static pack with `python build_frontend_data.py`.

---

## Files

| File | Role |
| ---- | ---- |
| `phase1_quantitative_discovery.md` | Phase 1 spec — funnel metrics and drop-off map |
| `phase1_metrics.json` | Same spec, machine-readable for the dashboard |
| `extract.py` | Stage 2 — LLM structured extraction (Claude / Groq / Ollama / mock) |
| `aggregate.py` | Stage 3 — CSV cuts |
| `discover.py` | Stage 4 — discovery report + opportunity ranking |
| `raw_data.jsonl` | Stage 1 output |
| `structured_insights.jsonl` | Stage 2 output |
| `extraction_run.log` | Stage 2 coverage log |
| `opportunity_summary.csv` | Stage 3 — headline ranking |
| `blocker_by_segment.csv` | Stage 3 — concentration crosstab |
| `resolution_channel_summary.csv` | Stage 3 — off-platform behavior |
| `sample_quotes_by_blocker.json` | Stage 3 — spot-check quotes |
| `discovery_report.md` | Stage 4 — PM-facing discovery narrative (headline) |
| `discovery_report.json` | Stage 4 — machine-readable findings |
| `chatgpt_research.json` | ChatGPT share chunked for the Reviewer (external PM research) |
| `rag.py` | Token-overlap retrieve + ChatGPT↔VOC triangulation |
| `rag_review.json` | Reviewer pack (hypotheses vs this corpus) |
| `frontend/lab_data.js` | Discovery Lab question payloads (generated) |
| `frontend/reviewer.html` | Static Reviewer · RAG |
