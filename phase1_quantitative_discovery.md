# Phase 1 — Quantitative discovery

Cheap and fast. Run this **before** qualitative research so interviews are pointed at where drop-off actually concentrates — not at a generic “wishlist problem.”

**Job of this phase:** describe **where** conversion dies (which categories, price bands, tenure, wishlist-size bands).  
**Not the job of this phase:** explain **why**. That is [Phase 2](phase2_qualitative_discovery.md). Ranking those reasons is [Phase 3](phase3_synthesis.md).

**North-star:** wishlist / consideration → purchase conversion on Myntra.

**Data this phase needs:** first-party product analytics (wishlist item lifecycle, price/stock snapshots, search/browse, cart). Public reviews cannot compute these rates. The existing collect → extract pipeline is a **companion signal** (stated blockers), not a substitute for the funnel.

---

## Output

A **segmented drop-off map**: one row per cut of (category × price band × user tenure × wishlist-size bucket), with the funnel and diagnostic metrics below. Use it to allocate interview / diary-study budget.

---

## Workstreams

### 1. Funnel decomposition of the wishlist

Share of wishlisted items that are:

| Outcome | Definition (item-level, observation window T) |
| --- | --- |
| Never revisited | Added, never opened again, not purchased, still on list or expired |
| Revisited but not purchased | ≥1 item/page reopen, no order containing that SKU/size |
| Purchased on Myntra | Converted on Myntra (AJIO is out of scope for this engine) |
| Removed without purchase | Explicit remove / move, no subsequent purchase of same SKU |

Grain: wishlisted **item** (user × style × size × color), not user. Window: e.g. 7 / 30 / 90 days from add.

### 2. Time-to-purchase (converters only)

Distribution of hours/days from add → paid order for items that convert.

- Front-loaded → decisive buyers; product work is reduce friction at add.
- Long tail → deliberators; product work is re-engagement, price/stock, styling confidence.

Report p50 / p90 and a histogram, cut by category.

### 3. Size / color / stock at add vs intended purchase

Among non-converters who revisit (or who open PDP from wishlist): how often the **saved size/color is OOS or delisted** vs still available.

This is the “would-be conversion that died on availability” rate — distinct from “never came back.”

### 4. Price trajectory (waiting-for-sale test)

For each wishlisted item, compare price at add vs price at convert **or** last revisit / window end.

| Path | Converter | Non-converter |
| --- | --- | --- |
| Dropped | % | % |
| Rose | % | % |
| Flat | % | % |

If non-converters see more *rises* or fewer *drops* than converters, sale-wait is supported. If both groups see the same trajectory, price motion is not the discriminator.

### 5. Wishlist size vs conversion (bookmark vs intent)

User-level: conversion rate of wishlisted items for

- light (5–10 items)
- mid
- power (100+)

If power-wishlisters convert much worse, wishlist is a bookmark dump for that cohort; if similar, size is not the intent proxy.

### 6. Revisit pattern

Count wishlist-page and wishlist-item opens between add and outcome.

- **0 revisits** → forgetting / no trigger (reminders, not PDP content).
- **Many revisits, no buy** → active deliberation (fit, price, styling, comparison).

These are different problems. Do not average them.

### 7. Category cuts

Conversion and the metrics above for **occasion-wear** (ethnic, party, festive) vs **basics** (tees, innerwear, everyday).

Hypothesis to test, not assume: occasion is event-driven and needs styling confidence; basics are habitual and low-risk.

### 8. Search / browse immediately before drop-off

In the session (or 24h) before remove / last-seen-without-purchase: did the user

- search that style’s reviews / PDP again,
- search **competing** products / brands,
- or neither?

Review-seeking vs competitor-seeking vs silence are different interventions.

### 9. Cart abandonment vs wishlist abandonment (baseline)

Same-window conversion of **carted** items vs **wishlisted** items, same user population and categories.

If wishlist ≈ cart, the problem is general purchase hesitation. If wishlist is much worse, the problem is wishlist-specific (bookmarking, no urgency, no checkout prompt).

---

## Required events (warehouse)

Minimum event set (illustrative names):

- `wishlist_add` / `wishlist_remove` (style, size, color, price, in_stock)
- `wishlist_page_view` / `wishlist_item_open`
- `pdp_view` (referrer = wishlist)
- `order_paid` (lines with style/size/color)
- daily (or on-view) **price** and **size-stock** snapshots for wishlisted SKUs
- `search` / `browse` with query and product ids
- `cart_add` / `cart_remove` / `checkout` for the baseline

Cuts on every metric: **category, price band, user tenure, wishlist size bucket**.

---

## What the current public-VOC engine is

`collect.py` → `extract.py` → `discover.py` ranks **stated blockers** in reviews and social (returns, price, fit, trust). That answers a different question: *what people complain about*. It cannot produce the funnel table above.

Use Phase 1’s map to choose **which cells** to interview; use the VOC report to seed **why** hypotheses inside those cells.
