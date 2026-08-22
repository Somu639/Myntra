# Phase 3 — Synthesis (the opportunity map)

This is where most teams get sloppy: they collect a pile of quotes and call it insight. Phase 3 is the opposite — **affinity → size → segment → rank**.

**Inputs:** Phase 1 drop-off map (where) + Phase 2 reason inventory and micro-survey volumes (why).  
**North-star:** still wishlist / consideration → purchase conversion on Myntra.

Public VOC (`opportunity_summary.csv`) ranks *stated* post-purchase pain. It is **not** this map. Do not paste VOC opportunity scores into the RICE matrix.

**Not the job of this phase:** invent percentages. Directional sizing is the point; empty cells until Phase 1 warehouse + Phase 2 fieldwork exist.

---

## Output

A **segmented opportunity map**: one row per friction type, sized, cut by category / tenure / wishlist-size, scored on a RICE-like matrix. That is a ranked backlog, not a quote dump.

---

## Four moves (in order)

### 1. Affinity-map into discrete friction types

Every diary line, live-wishlist note, and survey “other” gets clustered into a **friction type**. Starter codebook (freeze after Phase 2 affinity — add types that show up; do not keep unused ones):

| id | Friction type | Typical signal |
| --- | --- | --- |
| `fit_doubt` | Fit doubt | Size/fit risk; “not sure it will look like the photo” |
| `price_wait` | Price-wait | Waiting for a sale; found cheaper elsewhere |
| `comparison_paralysis` | Comparison paralysis | 3+ near-duplicates; cannot pick |
| `occasion_timing` | Occasion timing | No event yet; “for the wedding in December” |
| `social_validation` | Social validation | Asking a friend / haul / “who else bought this” |
| `forgetting` | Forgetting | Zero revisits; item aged out of mind |
| `style_regret` | Style regret | Changed mind on look; no longer needed |
| `trust_seller_returns` | Trust in seller / returns | Authenticity, return hassle, seller quality |

Quotes are evidence *for* a type. They are not the deliverable.

### 2. Quantify (directional, not perfect attribution)

For each friction type, use **Phase 1 volumes + Phase 2 micro-survey shares**:

> What % of **non-converted wishlist items** does this friction *plausibly* explain?

You will not get unique attribution (an item can be fit *and* price). Directional sizing is enough to prioritize, e.g. *“~35% of removed items cite ‘found cheaper elsewhere,’ concentrated in footwear and elect-adjacent accessories.”* That sentence is the **format** of a filled cell — not a number to treat as fact until surveys run.

Primary numerators:

- Remove-without-buy survey codes (Phase 2)
- 14-day reopen “what’s holding you back” codes (Phase 2)
- Phase 1 funnel slices that *match* the type (zero revisits → forgetting; many revisits + no buy → deliberation / comparison; OOS deaths → availability, if you add that type)

Write the concentration note next to the % (category, price band). A national average that hides footwear-vs-ethnic is useless.

### 3. Segment the map

The mix will almost certainly differ. Treat these as **hypotheses to confirm**, not findings:

| Cut | Hypothesis |
| --- | --- |
| **Category** | Occasion-wear → social validation + timing. Basics → price + forgetting. Footwear → fit risk. |
| **User tenure / purchase history** | New users → trust gap. Repeat buyers → price-timing habit. |
| **Wishlist size** | Light wishlisters → genuine intent. Heavy wishlisters → bookmarking — “improving conversion” there may be the **wrong metric**. |

Score and backlog **inside** cells. A high-reach friction on 200-item lists may be a bookmarking problem you should not “fix” with conversion tactics.

### 4. Score on a RICE-like matrix

Turns a list of pains into a ranked backlog:

**Score = (Reach × Frequency × Conversion lift × Confidence) ÷ Effort**

| Factor | Meaning |
| --- | --- |
| **Reach** | % of wishlist volume (non-converted items, or the Phase 1 cell you are ranking) this friction plausibly affects |
| **Frequency** | How often it shows up among those items (micro-survey share or item incidence) |
| **Conversion lift** | Potential relative lift if the friction is reduced (product judgment, triangulated — not a fake A/B) |
| **Confidence** | How well Phase 1 + Phase 2 + surveys agree (low if only 18 interview quotes) |
| **Effort** | Build / ops / policy cost |

Use 1–5 for Frequency, Lift, Confidence, Effort if the raw units differ; keep Reach as a %. Rank by score. Do not rank by how vivid the quote was.

---

## How this sits next to Phases 1–2 and public VOC

| Source | Role here |
| --- | --- |
| Phase 1 | Denominator (wishlist volume, cells) and behavioral proxies (revisits, OOS, price path) |
| Phase 2 diaries / live wishlist | Types that exist (affinity) |
| Phase 2 micro-surveys | Frequency / Reach for those types |
| Public VOC | Seed codes only; biased to loud post-purchase pain |

Do not skip affinity and rank quotes. Do not skip surveys and treat 15–20 sessions as Reach. Do not skip segmentation and average occasion-wear with basics. Non-monetary sketches are [Phase 4](phase4_solutions.md); scoped A/B is [Phase 5](phase5_validate.md).
