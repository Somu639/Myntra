"""Stage 2 — extract.py

Turns raw scraped text (raw_data.jsonl) into structured discovery signals using
the Claude API. This is the stage that makes the project a *discovery engine*
rather than a scraper: instead of summarizing, we force a strict JSON extraction
of wishlist / purchase-blocker behavior for every item.

For each raw item we ask Claude (claude-sonnet-4-5) to fill a fixed schema:

    relevant            bool
    wishlist_signal     bool
    reason_for_saving   short phrase | null
    blocker_type        enum | null
    blocker_detail      short phrase (paraphrased, not a quote) | null
    resolution_channel  enum | null
    segment_signal      short phrase | null
    sentiment           frustrated | neutral | positive | mixed
    confidence          0.0 - 1.0

Items are processed in small batches (~10) to control cost. Output is written to
structured_insights.jsonl, merged back with the original source / id / date /
rating / text. Malformed responses are retried with backoff; one bad batch never
kills the run — failed items are written with an ``extraction_error`` marker.

Usage
-----
    python extract.py                       # Claude (needs ANTHROPIC_API_KEY)
    python extract.py --limit 20            # only the first 20 items (testing)
    python extract.py --ollama              # local LLM via Ollama, no API key
    python extract.py --ollama --ollama-model qwen2.5:7b
    python extract.py --mock                # offline heuristic stub (plumbing)
    python extract.py --in raw.jsonl --out out.jsonl

Backends: Claude (default, needs ANTHROPIC_API_KEY in env/.env), Ollama
(``--ollama``, needs a local Ollama server + pulled model, no key), or the
offline ``--mock`` heuristic. See README.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-5"
INPUT_FILE = "raw_data.jsonl"
OUTPUT_FILE = "structured_insights.jsonl"
RUN_LOG = "extraction_run.log"

# Local-LLM (Ollama) backend defaults.
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"

# Groq (OpenAI-compatible cloud API — fast open models, needs GROQ_API_KEY).
GROQ_HOST = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"

BATCH_SIZE = 10            # items per Claude call (cost control)
MAX_ITEM_CHARS = 1500      # truncate long items before sending (cost control)
MAX_RETRIES = 8            # per-batch retries (Groq 429s are common on free tier)
BACKOFF_BASE = 2.0         # exponential backoff base (seconds)
SLEEP_BETWEEN_BATCHES = 1.0
MAX_TOKENS = 4096
GROQ_MAX_RETRY_AFTER = 45  # cap Retry-After so a TPM 429 cannot stall 15 min

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
SENTIMENTS = ["frustrated", "neutral", "positive", "mixed"]

INSIGHT_FIELDS = [
    "relevant", "wishlist_signal", "reason_for_saving", "blocker_type",
    "blocker_detail", "resolution_channel", "segment_signal", "sentiment",
    "confidence",
]

SYSTEM_PROMPT = (
    "You are a senior consumer-insights analyst for a fashion e-commerce company "
    "(think Myntra). You read raw customer voice — app reviews, Reddit "
    "posts, YouTube comments — and extract structured behavioral signals about "
    "wishlist usage, purchase decisions, fit/sizing, price, returns, and "
    "comparison shopping.\n\n"
    "You will receive a numbered batch of text items. For EACH item, call the "
    "`record_insights` tool with one result object per item, echoing back its "
    "`index`. Follow these rules strictly:\n"
    "- Judge `relevant` = true only if the item is about wishlist behavior, "
    "purchase decisions, fit/sizing, price, returns, or comparison shopping in "
    "fashion e-commerce. Generic praise ('nice app') is relevant=false.\n"
    "- `wishlist_signal` = true if it describes or implies saving/bookmarking an "
    "item, or the gap between saving and actually buying.\n"
    "- CRITICAL: whenever `relevant` is true AND the text shows ANY friction, "
    "hesitation, complaint, or problem, you MUST pick the single closest "
    "`blocker_type` from the allowed enum — do NOT leave it null out of caution. "
    "Only set `blocker_type` to null when a relevant item genuinely has no "
    "blocker at all (e.g. pure positive wishlist/saving behavior). If the text "
    "clearly describes a problem, `blocker_type` must be a non-null enum value.\n"
    "- Map common cases: wrong/defective item or denied/slow returns/exchange -> "
    "return_hassle; doubts about genuineness or fakes -> trust_authenticity; "
    "wrong/inconsistent size or fit -> fit_sizing; too costly / waiting for a "
    "discount -> price; unsure about fabric/build quality -> quality_doubt; "
    "overwhelmed by choices -> decision_paralysis_too_many_options; checkout / "
    "payment problems -> payment_friction. Use `other` only if none fit.\n"
    "- Infer `segment_signal` (a short phrase on who the user is: e.g. "
    "'budget-conscious shopper', 'ethnicwear buyer', 'first-time buyer') whenever "
    "the text gives any hint; use null only when there is truly no signal.\n"
    "- `blocker_detail` and `reason_for_saving` must be short paraphrases in your "
    "own words — never copy the text verbatim.\n"
    "- Never invent details that aren't supported by the text.\n"
    "- `confidence` reflects how strongly the text supports your extraction.\n"
    "- Return exactly one result per input index, and nothing else."
)

# Tool schema that forces a structured, validated JSON shape out of the model.
EXTRACTION_TOOL = {
    "name": "record_insights",
    "description": "Record structured discovery insights, one object per input item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer",
                                  "description": "The 0-based index of the input item."},
                        "relevant": {"type": "boolean"},
                        "wishlist_signal": {"type": "boolean"},
                        "reason_for_saving": {"type": ["string", "null"]},
                        "blocker_type": {"type": ["string", "null"],
                                         "enum": BLOCKER_TYPES + [None]},
                        "blocker_detail": {"type": ["string", "null"]},
                        "resolution_channel": {"type": ["string", "null"],
                                               "enum": RESOLUTION_CHANNELS + [None]},
                        "segment_signal": {"type": ["string", "null"]},
                        "sentiment": {"type": "string", "enum": SENTIMENTS},
                        "confidence": {"type": "number",
                                       "minimum": 0.0, "maximum": 1.0},
                    },
                    "required": [
                        "index", "relevant", "wishlist_signal", "sentiment",
                        "confidence",
                    ],
                },
            }
        },
        "required": ["results"],
    },
}


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def load_raw_items(path: str) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def item_key(rec: dict) -> tuple[str, str]:
    """Stable identity for a record — matches Stage 1's (source, id) dedup."""
    return (str(rec.get("source")), str(rec.get("id")))


def load_done_keys(path: str) -> set[tuple[str, str]]:
    """(source, id) pairs already SUCCESSFULLY extracted, so re-runs resume.

    Keyed on (source, id) to match Stage 1 (two sources can share an id). Rows
    that failed extraction (``extraction_error`` present, or ``relevant`` is
    None) are deliberately NOT counted as done, so a normal resume retries them.
    """
    done: set[tuple[str, str]] = set()
    if not os.path.exists(path):
        return done
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
                continue
            if rec.get("extraction_error") or rec.get("relevant") is None:
                continue  # failed row — leave it eligible for retry
            done.add(item_key(rec))
    return done


def chunked(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ---------------------------------------------------------------------------
# Validation / normalization of a single insight object
# ---------------------------------------------------------------------------

def _clean_enum(value, allowed):
    if value in allowed:
        return value
    return None


def normalize_insight(raw: dict) -> dict:
    """Coerce a raw model result into the canonical, validated shape."""
    def as_bool(v):
        return bool(v) if isinstance(v, bool) else bool(v) if v in (0, 1) else False

    def as_str_or_none(v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    sentiment = raw.get("sentiment")
    if sentiment not in SENTIMENTS:
        sentiment = "neutral"

    conf = raw.get("confidence")
    try:
        conf = float(conf)
        conf = min(1.0, max(0.0, conf))
    except (TypeError, ValueError):
        conf = 0.0

    return {
        "relevant": as_bool(raw.get("relevant")),
        "wishlist_signal": as_bool(raw.get("wishlist_signal")),
        "reason_for_saving": as_str_or_none(raw.get("reason_for_saving")),
        "blocker_type": _clean_enum(raw.get("blocker_type"), BLOCKER_TYPES),
        "blocker_detail": as_str_or_none(raw.get("blocker_detail")),
        "resolution_channel": _clean_enum(
            raw.get("resolution_channel"), RESOLUTION_CHANNELS),
        "segment_signal": as_str_or_none(raw.get("segment_signal")),
        "sentiment": sentiment,
        "confidence": round(conf, 3),
    }


def error_insight() -> dict:
    """Placeholder insight written when extraction fails for an item."""
    return {
        "relevant": None,
        "wishlist_signal": None,
        "reason_for_saving": None,
        "blocker_type": None,
        "blocker_detail": None,
        "resolution_channel": None,
        "segment_signal": None,
        "sentiment": None,
        "confidence": 0.0,
    }


# ---------------------------------------------------------------------------
# Batch extraction backends
# ---------------------------------------------------------------------------

def build_user_message(batch: list[dict]) -> str:
    lines = ["Here is the batch of items to analyze. "
             "Return one result per index.\n"]
    for idx, item in enumerate(batch):
        text = (item.get("text") or "")[:MAX_ITEM_CHARS]
        source = item.get("source", "unknown")
        lines.append(f"[{idx}] (source={source})\n{text}\n")
    return "\n".join(lines)


class ClaudeExtractor:
    """Calls the real Claude API with forced tool use + retries."""

    def __init__(self, model: str, api_key: str):
        import anthropic  # imported lazily so --mock works without the SDK
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_batch(self, batch: list[dict]) -> dict[int, dict]:
        """Return {index: normalized_insight} for this batch, with retries."""
        user_msg = build_user_message(batch)

        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=[EXTRACTION_TOOL],
                    tool_choice={"type": "tool", "name": "record_insights"},
                    messages=[{"role": "user", "content": user_msg}],
                )
                results = self._parse_tool_results(resp)
                mapped = self._map_results(results, len(batch))
                if mapped is not None:
                    return mapped
                last_err = "response missing / malformed results"
            except self._retryable_errors() as exc:
                last_err = f"{type(exc).__name__}: {exc}"
            except Exception as exc:  # noqa: BLE001 - unknown, treat as retryable
                last_err = f"{type(exc).__name__}: {exc}"

            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                print(f"    retry {attempt}/{MAX_RETRIES - 1} after error "
                      f"({last_err}); waiting {wait:.1f}s")
                time.sleep(wait)

        print(f"    batch failed after {MAX_RETRIES} attempts: {last_err}")
        return {}

    def _retryable_errors(self):
        a = self._anthropic
        return (
            getattr(a, "APIError", Exception),
            getattr(a, "APIConnectionError", Exception),
            getattr(a, "RateLimitError", Exception),
            getattr(a, "APIStatusError", Exception),
        )

    @staticmethod
    def _parse_tool_results(resp) -> list | None:
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                data = block.input
                if isinstance(data, dict) and isinstance(data.get("results"), list):
                    return data["results"]
        return None

    @staticmethod
    def _map_results(results, batch_len: int) -> dict[int, dict] | None:
        return map_results(results, batch_len)


class OllamaExtractor:
    """Local-LLM backend via Ollama's HTTP API — no cloud, no API key.

    Uses Ollama structured outputs (the ``format`` field carries a JSON schema),
    so the local model must return JSON matching the same shape Claude's tool
    call produces. Same retry / validation path as the Claude backend.

    Requires a running Ollama server (https://ollama.com) and a pulled model.
    """

    def __init__(self, model: str, host: str):
        import requests  # part of requirements; imported lazily
        self._requests = requests
        self.model = model
        self.host = host.rstrip("/")
        self._schema = EXTRACTION_TOOL["input_schema"]

    def extract_batch(self, batch: list[dict]) -> dict[int, dict]:
        user_msg = build_user_message(batch)
        payload = {
            "model": self.model,
            "stream": False,
            "format": self._schema,          # enforce structured JSON output
            "options": {"temperature": 0},   # deterministic extraction
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        }

        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._requests.post(
                    f"{self.host}/api/chat", json=payload,
                    timeout=300,
                )
                resp.raise_for_status()
                content = resp.json().get("message", {}).get("content", "")
                results = self._parse_content(content)
                mapped = map_results(results, len(batch))
                if mapped is not None:
                    return mapped
                last_err = "response missing / malformed results"
            except Exception as exc:  # noqa: BLE001 - treat all as retryable
                last_err = f"{type(exc).__name__}: {exc}"

            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                print(f"    retry {attempt}/{MAX_RETRIES - 1} after error "
                      f"({last_err}); waiting {wait:.1f}s")
                time.sleep(wait)

        print(f"    batch failed after {MAX_RETRIES} attempts: {last_err}")
        return {}

    @staticmethod
    def _parse_content(content) -> list | None:
        if not content:
            return None
        if isinstance(content, dict):
            data = content
        else:
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return None
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
        if isinstance(data, list):  # some models return the bare array
            return data
        return None


GROQ_JSON_INSTRUCTION = (
    "\n\nOUTPUT FORMAT: ignore any mention of tools above. Respond with a single "
    "JSON object (no prose, no markdown) of the exact shape:\n"
    '{"results": [{"index": <int>, "relevant": <bool>, "wishlist_signal": <bool>, '
    '"reason_for_saving": <string|null>, "blocker_type": <enum|null>, '
    '"blocker_detail": <string|null>, "resolution_channel": <enum|null>, '
    '"segment_signal": <string|null>, "sentiment": <enum>, '
    '"confidence": <float 0..1>}]}\n'
    f"blocker_type enum: {BLOCKER_TYPES + [None]}.\n"
    f"resolution_channel enum: {RESOLUTION_CHANNELS + [None]}.\n"
    f"sentiment enum: {SENTIMENTS}.\n"
    "Return exactly one object per input index, echoing its `index`."
)


class GroqExtractor:
    """Cloud backend via Groq's OpenAI-compatible chat API (fast open models).

    Uses JSON-object response format instead of tool use, then validates the
    same way as the other backends. Needs GROQ_API_KEY. Retries with backoff,
    so transient 429s (free-tier rate limits) don't kill the run.
    """

    def __init__(self, model: str, api_key: str, host: str = GROQ_HOST):
        import requests  # part of requirements; imported lazily
        self._requests = requests
        self.model = model
        self.host = host.rstrip("/")
        self.api_key = api_key

    def extract_batch(self, batch: list[dict]) -> dict[int, dict]:
        user_msg = build_user_message(batch)
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + GROQ_JSON_INSTRUCTION},
                {"role": "user", "content": user_msg},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "User-Agent": "Mozilla/5.0"}

        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._requests.post(
                    f"{self.host}/chat/completions",
                    json=payload, headers=headers, timeout=120,
                )
                if resp.status_code == 429:  # rate limited — honor Retry-After
                    raw_wait = float(resp.headers.get("retry-after", BACKOFF_BASE ** attempt))
                    wait = min(raw_wait, GROQ_MAX_RETRY_AFTER)
                    print(f"    rate limited; waiting {wait:.1f}s "
                          f"(server asked {raw_wait:.0f}s, capped)")
                    time.sleep(wait)
                    last_err = "429 rate limited"
                    continue
                if resp.status_code == 400:
                    last_err = f"400 Bad Request: {resp.text[:300]}"
                    print(f"    {last_err}")
                    wait = BACKOFF_BASE ** attempt
                    if attempt < MAX_RETRIES:
                        time.sleep(wait)
                    continue
                resp.raise_for_status()
                content = (resp.json().get("choices", [{}])[0]
                           .get("message", {}).get("content", ""))
                results = self._parse_content(content)
                mapped = map_results(results, len(batch))
                if mapped is not None:
                    return mapped
                last_err = "response missing / malformed results"
            except Exception as exc:  # noqa: BLE001 - treat all as retryable
                last_err = f"{type(exc).__name__}: {exc}"

            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                print(f"    retry {attempt}/{MAX_RETRIES - 1} after error "
                      f"({last_err}); waiting {wait:.1f}s")
                time.sleep(wait)

        print(f"    batch failed after {MAX_RETRIES} attempts: {last_err}")
        return {}

    @staticmethod
    def _parse_content(content) -> list | None:
        if not content:
            return None
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
        if isinstance(data, list):
            return data
        return None


def map_results(results, batch_len: int) -> dict[int, dict] | None:
    """Map a list of raw model results to {index: normalized_insight}."""
    if not results:
        return None
    mapped: dict[int, dict] = {}
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            continue
        idx = r.get("index", i)
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = i
        if 0 <= idx < batch_len:
            mapped[idx] = normalize_insight(r)
    # Require at least one valid mapping; missing ones are filled by caller.
    return mapped or None


class MockExtractor:
    """Offline heuristic backend so the pipeline runs without an API key.

    NOT a substitute for the model — just enough signal to exercise the
    plumbing (batching, merging, resume, output shape) end to end.
    """

    def extract_batch(self, batch: list[dict]) -> dict[int, dict]:
        out: dict[int, dict] = {}
        for idx, item in enumerate(batch):
            text = (item.get("text") or "").lower()
            rating = item.get("rating")

            wishlist = any(k in text for k in
                           ("wishlist", "wish list", "save", "saved", "bookmark"))
            blocker = None
            if any(k in text for k in ("size", "fit", "large", "small", "tight")):
                blocker = "fit_sizing"
            elif any(k in text for k in ("price", "expensive", "costly", "cheap")):
                blocker = "price"
            elif any(k in text for k in ("return", "refund", "exchange")):
                blocker = "return_hassle"
            elif any(k in text for k in ("quality", "fake", "genuine", "original")):
                blocker = "quality_doubt"

            relevant = wishlist or blocker is not None
            if isinstance(rating, (int, float)):
                sentiment = ("positive" if rating >= 4 else
                             "frustrated" if rating <= 2 else "neutral")
            else:
                sentiment = "frustrated" if blocker else "neutral"

            out[idx] = normalize_insight({
                "relevant": relevant,
                "wishlist_signal": wishlist,
                "reason_for_saving": "buy later" if wishlist else None,
                "blocker_type": blocker,
                "blocker_detail": (f"mentions {blocker.replace('_', ' ')}"
                                   if blocker else None),
                "resolution_channel": None,
                "segment_signal": None,
                "sentiment": sentiment,
                "confidence": 0.3,  # low: this is a heuristic stub
            })
        return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def merge_record(item: dict, insight: dict, model: str, error: str | None) -> dict:
    record = {
        "id": item.get("id"),
        "source": item.get("source"),
        "date": item.get("date"),
        "rating": item.get("rating"),
        "text": item.get("text"),
        "meta": item.get("meta", {}),
    }
    record.update(insight)
    record["model"] = model
    record["extracted_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        record["extraction_error"] = error
    return record


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def resolve_api_key() -> str | None:
    _load_env()
    return os.getenv("ANTHROPIC_API_KEY")


def resolve_groq_key() -> str | None:
    _load_env()
    return os.getenv("GROQ_API_KEY")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage 2 structured insight extractor.")
    p.add_argument("--in", dest="infile", default=INPUT_FILE,
                   help=f"Input JSONL (default: {INPUT_FILE}).")
    p.add_argument("--out", dest="outfile", default=OUTPUT_FILE,
                   help=f"Output JSONL (default: {OUTPUT_FILE}).")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Claude model (default: {DEFAULT_MODEL}).")
    p.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                   help=f"Items per Claude call (default: {BATCH_SIZE}).")
    p.add_argument("--limit", type=int, default=None,
                   help="Only process the first N new items (testing).")
    p.add_argument("--backend", choices=["claude", "groq", "ollama", "mock"],
                   default=None,
                   help="Extraction backend (default: claude; --groq/--mock/"
                        "--ollama are shortcuts).")
    p.add_argument("--mock", action="store_true",
                   help="Shortcut for --backend mock (offline heuristic).")
    p.add_argument("--ollama", action="store_true",
                   help="Shortcut for --backend ollama (local LLM, no API key).")
    p.add_argument("--groq", action="store_true",
                   help="Shortcut for --backend groq (needs GROQ_API_KEY).")
    p.add_argument("--groq-model", default=GROQ_MODEL,
                   help=f"Groq model (default: {GROQ_MODEL}).")
    p.add_argument("--ollama-model", default=OLLAMA_MODEL,
                   help=f"Ollama model tag (default: {OLLAMA_MODEL}). "
                        f"Try qwen2.5:7b or llama3.1:8b for better quality.")
    p.add_argument("--ollama-host", default=OLLAMA_HOST,
                   help=f"Ollama server URL (default: {OLLAMA_HOST}).")
    p.add_argument("--no-resume", action="store_true",
                   help="Re-extract everything, ignoring existing output.")
    return p.parse_args(argv)


def resolve_backend(args) -> str:
    if args.backend:
        return args.backend
    if args.mock:
        return "mock"
    if args.ollama:
        return "ollama"
    if args.groq:
        return "groq"
    return "claude"


def main(argv=None) -> int:
    args = parse_args(argv)

    if not os.path.exists(args.infile):
        print(f"Input file not found: {args.infile}. Run Stage 1 (collect.py) first.")
        return 1

    backend = resolve_backend(args)
    items = load_raw_items(args.infile)
    done = set() if args.no_resume else load_done_keys(args.outfile)
    pending = [it for it in items if item_key(it) not in done]
    if args.limit is not None:
        pending = pending[:args.limit]

    print(f"=== Stage 2 extract — backend={backend} ===")
    print(f"loaded {len(items)} raw items; {len(done)} already done; "
          f"{len(pending)} to process (batch_size={args.batch_size})")

    if not pending:
        print("Nothing to do.")
        return 0

    if backend == "mock":
        extractor = MockExtractor()
        model_label = "mock-heuristic"  # never mislabel stub data as the model
    elif backend == "ollama":
        model_label = f"ollama:{args.ollama_model}"
        try:
            extractor = OllamaExtractor(args.ollama_model, args.ollama_host)
        except ImportError:
            print("ERROR: requests not installed — run `pip install requests`.")
            return 1
        print(f"    using Ollama model '{args.ollama_model}' at "
              f"{args.ollama_host}")
    elif backend == "groq":
        model_label = f"groq:{args.groq_model}"
        groq_key = resolve_groq_key()
        if not groq_key:
            print("ERROR: GROQ_API_KEY is not set. Add it to .env "
                  "(GROQ_API_KEY=gsk_...), or use --ollama / --mock.")
            return 1
        try:
            extractor = GroqExtractor(args.groq_model, groq_key)
        except ImportError:
            print("ERROR: requests not installed — run `pip install requests`.")
            return 1
        print(f"    using Groq model '{args.groq_model}'")
    else:  # claude
        model_label = args.model
        api_key = resolve_api_key()
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY is not set. Set it (or use a .env "
                  "file), or run with --ollama (local LLM) or --mock.")
            return 1
        try:
            extractor = ClaudeExtractor(args.model, api_key)
        except ImportError:
            print("ERROR: anthropic SDK not installed — run "
                  "`pip install anthropic` (or use --ollama / --mock).")
            return 1

    kept = errors = 0
    failed_batches: list[int] = []
    batches = list(chunked(pending, args.batch_size))
    # --no-resume is a full re-extraction, so truncate to avoid duplicate rows.
    # Normal resume appends; retried failed items produce a newer row that Stage
    # 3 de-duplicates (keep-last per source+id).
    out_mode = "w" if args.no_resume else "a"
    with open(args.outfile, out_mode, encoding="utf-8") as out_fh:
        for bnum, batch in enumerate(batches, start=1):
            print(f"[batch {bnum}/{len(batches)}] {len(batch)} items ...")
            mapped = extractor.extract_batch(batch)
            if not mapped:
                failed_batches.append(bnum)

            for idx, item in enumerate(batch):
                insight = mapped.get(idx)
                if insight is None:
                    record = merge_record(item, error_insight(), model_label,
                                          error="extraction_failed")
                    errors += 1
                else:
                    record = merge_record(item, insight, model_label, error=None)
                    kept += 1
                out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_fh.flush()

            if bnum < len(batches):
                time.sleep(SLEEP_BETWEEN_BATCHES)

    _write_run_log(args, model_label, len(pending), kept, errors, failed_batches)

    print("\n=== Done ===")
    print(f"extracted={kept}  failed={errors}  failed_batches={len(failed_batches)}")
    if failed_batches:
        print(f"WARNING: {errors} items could not be extracted "
              f"(batches {failed_batches}). They are written with "
              f"extraction_error='extraction_failed'. See {RUN_LOG}.")
    print(f"Appended to {args.outfile}")
    return 0


def _write_run_log(args, model_label, processed, kept, errors, failed_batches):
    """Persist a coverage line so failed batches are never silently lost."""
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model_label,
        "mock": args.mock,
        "infile": args.infile,
        "outfile": args.outfile,
        "batch_size": args.batch_size,
        "processed": processed,
        "extracted": kept,
        "failed_items": errors,
        "failed_batches": failed_batches,
    }
    try:
        with open(RUN_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"(could not write run log {RUN_LOG}: {exc})")


if __name__ == "__main__":
    sys.exit(main())
