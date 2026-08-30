# Fashion Wishlist & Purchase-Intent Discovery Report

_AI-powered discovery engine — Myntra. Directional signals for opportunity prioritization, not statistically representative measurements (see data limitations in README)._

## Coverage
- Records analyzed: **1422** (1422 extracted, 0 failed).
- Relevant to fashion purchase/wishlist behavior: **483** (34.0% of extracted).
- Sources (always the eight public channels):
  - App Store reviews: 133 records, 55 relevant (41.4%).
  - Play Store reviews: 440 records, 133 relevant (30.2%).
  - Reddit discussions: 292 records, 171 relevant (58.6%).
  - Fashion and shopping communities: 231 records, 63 relevant (27.3%).
  - Social media conversations: 26 records, 6 relevant (23.1%).
  - YouTube comments: 180 records, 27 relevant (15.0%).
  - Product reviews and Q&A where relevant: 70 records, 23 relevant (32.9%).
  - Other publicly available conversations about online fashion shopping: 50 records, 5 relevant (10.0%).

## Prioritized opportunity areas (Q10 — unmet needs)
Not a sentiment summary. Each area is **identified** (blocker), **quantified** (mentions, reach, frustration), and **compared** on volume vs pain vs wishlist→buy leverage. `wpc_weighted_score` is VOC score × journey weight — **not** a measured conversion lift.

| Rank | Opportunity | Stage | Leverage | Mentions | Reach % | Frustration % | Sources | VOC score | WPC-weighted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | return_hassle | anticipated_ops | medium | 53 | 11.0 | 94.3 | 6 | **82.5** | 53.6 |
| 2 | other | post_purchase_ops | low | 52 | 10.8 | 80.8 | 7 | **75.1** | 26.3 |
| 3 | price | decision_friction | high | 75 | 15.5 | 20.0 | 5 | **60.0** | 60.0 |
| 4 | trust_authenticity | decision_friction | high | 23 | 4.8 | 78.3 | 5 | **54.5** | 54.5 |
| 5 | fit_sizing | decision_friction | high | 27 | 5.6 | 70.4 | 6 | **53.2** | 53.2 |
| 6 | occasion_timing | decision_friction | medium | 3 | 0.6 | 100.0 | 2 | **52.0** | 33.8 |
| 7 | quality_doubt | decision_friction | high | 24 | 5.0 | 70.8 | 5 | **51.4** | 51.4 |
| 8 | payment_friction | decision_friction | medium | 6 | 1.2 | 83.3 | 4 | **45.6** | 29.6 |
| 9 | decision_paralysis_too_many_options | decision_friction | high | 10 | 2.1 | 30.0 | 4 | **21.7** | 21.7 |
| 10 | styling_uncertainty | decision_friction | high | 11 | 2.3 | 9.1 | 3 | **11.9** | 11.9 |

## Q1 — Why do users add products to their wishlist?
- Wishlist/save signals detected: **10**.
- Top stated reasons for saving:
  - wants link to purchase later (4)
  - interested in maxi dress seen in video (1)
  - to win contest voucher (1)
  - to secure low prices during sale (1)
  - to verify fabric composition before buying (1)
  - to hit card discount threshold (1)
  - to keep track of desired luxury items (1)
  > "Cheap Only in Price, Not in Quality  **Plum Smokin’ Vanilla**   Saw rave reviews on the sub, found it listed on Myntra during a sale for peanuts, bought it.   Remarkable perfume..."  — _reddit_ (rating 1)
  > "8:16 mango Red dress link plz❤"  — _youtube_
  > "#MyntraEORSGameZone gets Bigger! We've hidden a treasure on the Myntra app. Look out for it while wish-listing for #MyntraEORS2021   The first to find it, screenshot it, &amp; p..."  — _social_twitter_ (rating 688)

## Q8 — Wishlist as genuine intent vs. bookmarking
- Of 10 wishlist signals: **6 genuine purchase intent**, **1 bookmarking**, 3 unclear (heuristic on stated reason + text).

## Q2 — What prevents wishlisted products from being purchased?
Identify blockers, quantify reach × frustration, then compare by journey stage (decision vs anticipated ops vs post-purchase). wpc_weighted_score is VOC score × leverage weight — not a measured lift.
- **decision_friction**: 179 mentions across 8 areas (top: price).
- **anticipated_ops**: 53 mentions across 1 areas (top: return_hassle).
- **post_purchase_ops**: 52 mentions across 1 areas (top: other).

## Q3 — Uncertainties remaining after a user likes a product
- **85** mentions (29.9% of all blockers) are lingering uncertainties (fit, styling, quality, trust, social validation).
  - fit_sizing: 27
  - quality_doubt: 24
  - trust_authenticity: 23
  - styling_uncertainty: 11
  > "Fraud company I order a mac moisturiser which is showing deliver on 27/08/2026 but same was not delivered  , but company has updated in his record order has been delivered . I w..."  — _app_store_myntra_ (rating 1)
  > "They are fakes. I ordered NB in myntra. Returned same day."  — _reddit_ (rating 1)
  > "Online shopping is 90% guessing, 10% hoping you didn’t just buy trash I try to be intentional when I shop—buy things that are sustainable, safe, ethical, actually *worth* the mo..."  — _fashion_community_ (rating 1)

## Q4 — What causes users to postpone a purchase?
- **88** mentions (31.0% of blockers) map to postponement drivers (price/sale-wait, occasion timing, choice overload).
  - price: 75
  - decision_paralysis_too_many_options: 10
  - occasion_timing: 3

## Q5 — How do users compare multiple shortlisted products?
- Choice-overload / comparison-difficulty mentions: **10**.
  > "Need advice on solid cotton shirt brands for men I am tired of looking in myntra for shirts, and a lot of options from different brands. I personally am planning to buy cotton c..."  — _reddit_ (rating 1)
  > "1 or 2? Help me choose my Bday fit!! First is from Savana and second from Newme I am really confused which dress to get for my birthday and which brand to choose....I only have ..."  — _fashion_community_ (rating 1)
  > "This all promotion Haul video  How come she can find simple dress in Myntra?"  — _youtube_

## Q6 — What do users research off-platform before buying?
- Off-platform research: **40** mentions (8.3% of relevant).
  - none_mentioned: 196
  - in_app_reviews: 37
  - external_friends_family: 19
  - external_youtube: 12
  - external_google_search: 7
  - social_media_influencer: 1
  - in_store_trial: 1
  > "Price ku nhi mention karti ho ab"  — _youtube_
  > "Myntra coupon please I'm buying shoes. If anyone have myntra coupon, please share. Thankyou"  — _reddit_ (rating 1)
  > "Joining a Big 4 as manager , what should I wear on my first day ? PS: I have been working from home for so long ! I (female) have been working from home for so long , I feel lik..."  — _fashion_community_ (rating 1)

## Q7 — Role of fit, size, styling, price, reviews, occasion, social
| Dimension | Mentions | Share of blockers % |
| --- | --- | --- |
| Price & Value | 75 | 26.4 |
| Returns & Exchange | 53 | 18.7 |
| Other | 52 | 18.3 |
| Fit & Size | 27 | 9.5 |
| Quality | 24 | 8.5 |
| Trust & Reviews | 23 | 8.1 |
| Styling | 11 | 3.9 |
| Choice / Comparison | 10 | 3.5 |
| Payment | 6 | 2.1 |
| Occasion & Timing | 3 | 1.1 |

## Q9 — How do behaviors differ across user segments?
Age bands are intended profiles. Public VOC has no verified age. voc_mentions size the hypothesized conversion barrier, not the size of that age group.

| Segment | Age | Wishlist behavior | Primary need | Barrier | VOC mentions |
| --- | --- | --- | --- | --- | --- |
| Young Millennials | 25–34 | Save fewer, more considered products | Quality + versatility | Fit, quality & value | 126 |
| Value-Conscious Shoppers | 18–35 | Save and monitor products | Best value | Price/timing | 75 |
| Practical Shoppers | 30–45+ | Small wishlist, highly intentional | Functionality + reliability | Trust + fit | 50 |
| Occasion Shoppers | 20–40 | Wishlist around weddings/events | Complete look | Styling + suitability | 14 |
| Working Professionals | 25–40 | Wishlist around work/occasion needs | Convenience + confidence | Time + decision effort | 13 |
| Gen Z Trend Seekers | 18–24 | Save many trending/socially discovered items | Trend + social validation | Will it actually look good on me? | 11 |
| Fashion Enthusiasts | 18–35 | Large, highly curated wishlist | Discovery + experimentation | Choice overload | 10 |

---
_Generated by discover.py (Stage 4). Backing data: structured_insights.jsonl. Spot-check categorization in sample_quotes_by_blocker.json before quoting numbers._