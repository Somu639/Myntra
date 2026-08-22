# Phase 5 — Validate before you scale

Ship the **top 1–2** Phase 3 / Phase 4 bets as **scoped experiments**. Not a platform-wide redesign. Not a stack of widgets.

**North-star (primary metric):** wishlist → purchase conversion **within 30 days** (item-level: user × style × size × color, same grain as Phase 1).

---

## Output

An experiment brief per bet: hypothesis, segment/category cell, treatment, primary metric, guardrails, stop/scale rule. Empty until Phase 3 ranks and Phase 4 sketches exist.

---

## How to run it

**Scope:** A/B on the **specific segment and category where the friction concentrates** — e.g. footwear × new users for fit-doubt, not “all wishlist users.” Platform-wide tests dilute the effect and can harm bookmarking cohorts.

**N bets:** one or two. A third is usually a failure to prioritize.

**Primary:** share of wishlisted items purchased on Myntra within 30 days of add (or of treatment exposure, declared in the brief). Same north-star as Phase 1.

**Guardrails** (watch even if primary moves):

| Guardrail | Why |
| --- | --- |
| **Return rate** | Fit-related fixes can **raise or lower** returns. A conversion win that inflates returns is not a win. |
| **Time-to-first-purchase** | Resurfacing / occasion reminders can pull purchases forward without adding them — or annoy and delay. Track p50 / p90. |

Optional secondary (declare, do not swap in after seeing results): revisit rate, remove-without-buy rate, inspiration-vs-ready-to-buy mix if you ship the list split.

**Constraint still holds:** treatments are non-monetary. A coupon arm is a different program.

---

## Stop / scale

- **Scale** only if primary lifts in the target cell, guardrails hold, and the effect is not a pull-forward that dies at day 31.
- **Kill** if conversion is flat and returns worsen, or if heavy-wishlist (bookmarking) cells were in the mix and the metric was diluted on purpose.
- **Do not** “roll out everywhere because it didn’t hurt.” Phase 3 said the mix differs by category.

---

## How this sits next to earlier phases

| Phase | Role |
| --- | --- |
| 1 | Denominator, cell, 30-day window definition |
| 2–3 | Which friction, how large, where it concentrates |
| 4 | Non-monetary treatment sketch |
| 5 | Prove lift in that cell before platform scale |

Do not A/B a solution for a friction you have not sized. Do not measure success as clicks on the new widget.
