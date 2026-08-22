# Opportunity & Solution Proposal — Wishlist → Purchase Conversion

**Source:** `discovery_report.md` / `discovery_report.json` (Stage 4 of the
discovery engine).
**Backing data:** 445 public reviews/comments collected (Play Store Myntra,
App Store Myntra, YouTube Myntra hauls). **100% extracted (445/445, 0 failed)**
→ **134 relevant** to fashion purchase/wishlist behavior, of which **79 carry an
identified blocker**. AJIO sources were removed so this is a Myntra-only corpus.
(Reddit is wired but was run without credentials.)
**Extraction backend:** Groq `openai/gpt-oss-120b` (cloud, fast). This replaced an
earlier partial local-model run — sentiment and blocker attribution are now far
more reliable (e.g. returns frustration reads 97% here vs a badly under-counted 9%
from the local model).
**Status:** Directional but now well-grounded. Read "Confidence & limitations"
before treating any single number as fact — this prioritizes where to dig and
what to build first, it does not size a business case.

---

## 1. The metric this ladders up to

North-star: **wishlist/consideration → purchase conversion**, plus the
**repeat-purchase / retention** that protects it. Every opportunity below either
(a) removes a reason a considered item never gets bought, or (b) removes a reason
a buyer won't come back.

The data forces one nuance into the open: the loudest, most frequent voice is
**post-purchase operational pain** (returns, delivery, order cancellations), not a
classic pre-purchase wishlist blocker. That still governs the metric — **fear of a
painful return/delivery is itself a first-purchase blocker**, and one bad
experience kills the repeat purchase conversion depends on. The purest
pre-purchase / wishlist signals (price volatility, quality doubt, in-app reviews)
are rarer in review text but strategically sharper.

---

## 2. Opportunity areas, ranked

Two lenses, because they disagree and both matter:

**By opportunity score** (reach × frustration, equal weight — the engine's rank):

| # | Opportunity | Mentions | Reach | Frustration | Score |
| - | ----------- | -------- | ----- | ----------- | ----- |
| 1 | Returns & Exchange friction | 24 | 17.9% | 95.8% | **97.9** |
| 2 | Operational: delivery / order-cancel / support (`other`) | 21 | 15.7% | 95.2% | **91.3** |
| 3 | Quality doubt | 9 | 6.7% | 100% | **68.8** |
| 4 | Trust & authenticity | 5 | 3.7% | 100% | **60.4** |
| 5 | Price & value | 11 | 8.2% | 45.5% | **45.7** |
| — | payment (4), fit (2), occasion (1), styling (1), choice-overload (1) | small-n | — | — | 2–54 |

**By volume** (how many real users raised it): Returns **24** › Operational **21**
› Price **11** › Quality **9** › Trust **5** › Payment **4**.

> How to read this: the score deliberately rewards intensity, so rare-but-furious
> items (quality, trust) rank above price. For **sizing**, trust the volume
> lens; for **severity**, trust the score. Returns + Operational together are
> **~57% of all identified blockers** — the dominant theme by both lenses.

---

## 3. The opportunities in detail (evidence → solution)

### Opportunity 1 — De-risk Returns & Exchange (highest priority)
**Evidence:** 24 mentions, **30.4% of all identified blockers**, 96% frustrated.
The pattern is remarkably consistent: **return pickup never happens on schedule**,
**refunds routed to wallet instead of bank**, **exchanges sent in the wrong size**,
and **an automated "call me" bot that answers in the wrong language**.

> "The order arrives fast but the return process takes years… no one comes for
> return pickups and the 'call me' option gives useless automated replies… in
> Hindi when I chose English." — Play Store (Myntra)
> "I requested an exchange for a bigger size and was sent an even smaller one… at
> least three times the return pickup didn't happen on the scheduled date." —
> App Store (Myntra)

**Why it hits the metric:** a shopper who fears "if it's wrong, I'm stuck" won't
convert a borderline wishlist item; a shopper burned once won't re-buy.

**Proposed solutions (small → large):**
1. **Return/exchange status transparency** — real-time state + proactive comms
   (pickup ETA, "quality-check passed", "refund initiated to *bank*"). *(S)*
2. **Refund-destination clarity** — default refunds to original payment method and
   state it upfront; the wallet-vs-bank surprise is a recurring trust breaker. *(S–M)*
3. **Fix exchange size/verification** — audit the doorstep exchange flow that ships
   wrong sizes / fails verification. *(M, ops + app)*
4. **"Easy returns" confidence badge on PDP/wishlist** — surface the return window
   + plain-language guarantee at the moment of hesitation. Turns the #1 fear into a
   conversion nudge. *(S–M)*

### Opportunity 2 — Operational reliability (delivery, cancellations, support)
**Evidence:** 21 mentions in the `other` bucket, 95% frustrated. Decomposes into
**late/undelivered orders**, **automatic order cancellations for "technical
issues"** with token compensation, and **unresponsive support**.

> "My order was confirmed and shipped, then cancelled automatically citing a
> 'technical issue'… offered a ₹100 coupon that doesn't address it." — Play Store
> "Before taking the order they make it user friendly… after that delivery will
> be very late." — App Store (Myntra)

**Why it hits the metric:** these are the experiences that make a user uninstall —
the ultimate retention/repeat-purchase killer, and word-of-mouth damage that
suppresses new conversion.

**Proposed solutions:** proactive delivery-delay comms with a real revised ETA;
kill silent auto-cancellations (or make resolution meaningful, not a ₹100 coupon);
a working human-escalation path. *(M — largely ops, but app surfaces the trust.)*
*Recommend a follow-up pass to split this bucket into delivery vs cancellation vs
support so each gets an owner.*

### Opportunity 3 — Quality doubt / item-not-as-described
**Evidence:** 9 mentions, 100% frustrated — damaged/pre-used items, fabric worse
than the listed "viscose/rayon/cotton", "product doesn't match description". One
user alleges **genuine reviews are censored** so only good ones show.

**Why it hits the metric:** the expectation gap is what turns a wishlist add into a
return (feeding Opportunity 1) and erodes trust in the PDP.

**Proposed solutions:** truer PDP media (real-fit photos, fabric close-ups,
verified-buyer photo reviews); **protect review integrity** — over-curated reviews
directly undercut the in-app reviews channel users rely on (see Q6 below). *(M)*

### Opportunity 4 — Price & value (including platform fees)
**Evidence:** 11 mentions (46% frustrated), concentrated in **budget-conscious
shoppers** (71% segment concentration). Myntra-specific complaints cluster on
**platform fees** and items feeling costlier than other apps.

> "He takes ₹23 platform fee, item cost higher than other apps." — Play Store
> (Myntra)

**Why it hits the metric:** surprise fees at checkout and a sense that list
prices move against the shopper both add last-step friction on considered items.

**Proposed solutions:**
1. **Transparent fee display** before the last step (no surprise platform fee). *(S)*
2. **Wishlist price-drop alerts** — turn saved items into a re-engagement +
   conversion loop. *(M)*
3. **"Price changed since you saved" transparency** on the wishlist, if internal
   event data confirms save→buy drop-off when price moves. *(M–L)*

### Opportunity 5 & the long tail — Trust, payment, fit/occasion/styling
- **Trust & authenticity (5):** low frequency but maximal intensity — 100%
  frustrated (fakes/scams). Overlaps heavily with returns + quality; partly
  addressed by review integrity + PDP proof.
- **Payment (4):** international cards not accepted; extra amount charged at
  delivery; delayed refunds after cancellation. Cheap wins where they fit. *(S)*
- **Fit / occasion / styling (2 / 1 / 1):** almost entirely from **YouTube haul
  comments**, not app reviews — a hint that fit/styling doubt lives *off-platform*
  (see Q6), where app reviews can't see it. Under-sampled here; a Reddit pull and
  more haul videos would firm this up.

---

## 4. What users research off-platform (Q6 — flagged as its own cut)

- **In-app reviews are the dominant pre-purchase research channel: 17 mentions.**
  Users lean on reviews to decide — which is exactly why the "censored reviews"
  complaint in Opportunity 3 is dangerous: it poisons the channel that drives
  conversion.
- **YouTube off-platform tags: 0 in this Myntra-only cut** — but fit/styling
  blockers still came from haul comments, so the gap is real even when
  `resolution_channel` is sparse.
- **Implication:** the biggest off-platform gap is **fit / fabric / styling
  confidence** that Myntra PDPs don't yet answer. Richer PDP media +
  verified-buyer photo/video reviews keep that decision on-platform.

---

## 5. How behaviors differ by segment (Q9)

Segment signal is model-inferred but now has 50–80% coverage on the top blockers:

| Blocker | Top segment | Concentration |
| ------- | ----------- | ------------- |
| Price | budget-conscious shopper | 71% |
| Returns | return-focused shopper | 50% |
| Quality doubt | quality-conscious shopper | 43% |
| Payment | international shopper | 100% (n=1 known) |

Reads: **price pain concentrates in budget-conscious shoppers** (a clean
target for fee transparency), **quality doubt in quality-conscious shoppers**,
and **returns pain is still the volume leader** — reinforcing it as the
universal fix.

---

## 6. Prioritization

| Opportunity | Volume | Severity | Metric leverage | Effort | Call |
| ----------- | ------ | -------- | --------------- | ------ | ---- |
| 1. Returns transparency + refund clarity + confidence badge | High | High | High | S–M | **Do now** |
| 2. Operational: delivery comms / stop silent cancels / escalation | High | High | High (retention) | M | **Do now (ops-led)** |
| 4. Wishlist price-drop / price + fee transparency | Med | Med | High (direct to metric) | S–M | **Fast-follow** |
| 3. Truer PDP media + protect review integrity | Med | High | Med–High | M | Fast-follow |
| 5. Payment (intl cards / extra doorstep charge) | Low | Med | Med | S | Quick wins where cheap |
| Trust / fit / styling | Low (under-sampled) | High | Med | M | Validate with more data first |

**Recommended sequence:**
1. Ship low-risk quick wins now: **returns-confidence badge**, **refund-to-bank
   clarity**, **transparent fee display**.
2. Launch the **returns + delivery reliability** fixes (biggest volume of pain,
   biggest retention leverage).
3. In parallel, run the **wishlist price-volatility study**; if confirmed, build
   **price-drop alerts + save-time price transparency**.
4. Improve **PDP media + protect review integrity** to close the off-platform
   fit/quality gap.

---

## 7. Confidence & limitations (please read)

- **Full, high-quality extraction this run:** 445/445 items extracted, 0 failures,
  with a 120B model — so blocker attribution and sentiment are trustworthy at the
  aggregate level. Spot-check `sample_quotes_by_blocker.json` before quoting any
  single number.
- **Self-selected sample.** Reviews skew to the delighted and the angry, not the
  population. Treat frequencies as *severity/priority signals for interview
  recruiting*, not market sizing.
- **Wishlist behavior is under-sampled (0 explicit signals in this Myntra-only
  cut).** The previous wishlist quotes were AJIO reviews and were removed.
  *Why users wishlist* and *intent vs bookmarking* need **behavioral/event data
  + user interviews**, not app reviews. This is the biggest remaining gap.
- **The `other` bucket is large (21) and needs decomposition** into delivery vs
  auto-cancellation vs support before it gets an owner.
- **Segment signal is model-inferred**, not verified — directional only.
- **Source mix is still narrow:** Reddit is wired but **skipped (no credentials)**,
  and YouTube fit/styling signal is thin. Adding Reddit + more haul videos would
  firm up the pre-purchase fit/styling/comparison questions that app reviews can't
  see.

---

## 8. Immediate next steps
1. **Recruit interviews** from the returns / wrong-item / cancelled-order cohorts —
   this run gives you the exact users to target.
2. **Instrument** the returns funnel, delivery-SLA adherence, and wishlist-SKU
   price changes to convert these hypotheses into measured effects.
3. **Ship** the quick wins (returns-confidence badge, refund-to-bank clarity, fee
   transparency) while the above runs.
4. **Close the data gaps:** add Reddit credentials + more haul videos and re-run
   the pipeline to strengthen the pre-purchase wishlist/fit/styling signal.
