# Fashion Wishlist & Purchase-Intent Discovery Report

_AI-powered discovery engine — Myntra. Directional signals for opportunity prioritization, not statistically representative measurements (see data limitations in README)._

## Coverage
- Records analyzed: **1422** (1422 extracted, 0 failed).
- Relevant to fashion purchase/wishlist behavior: **483** (34.0% of extracted).

## Prioritized opportunity areas (Q10 — unmet needs)
Ranked by an opportunity score weighting **reach** and **frustration** equally.

| Rank | Opportunity (blocker) | Dimension | Mentions | Reach % | Frustration % | Confidence | Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | return_hassle | Returns & Exchange | 53 | 11.0 | 94.3 | 0.951 | **82.5** |
| 2 | other | Other | 52 | 10.8 | 80.8 | 0.916 | **75.1** |
| 3 | price | Price & Value | 75 | 15.5 | 20.0 | 0.917 | **60.0** |
| 4 | trust_authenticity | Trust & Reviews | 23 | 4.8 | 78.3 | 0.924 | **54.5** |
| 5 | fit_sizing | Fit & Size | 27 | 5.6 | 70.4 | 0.894 | **53.2** |
| 6 | occasion_timing | Occasion & Timing | 3 | 0.6 | 100.0 | 0.94 | **52.0** |
| 7 | quality_doubt | Quality | 24 | 5.0 | 70.8 | 0.901 | **51.4** |
| 8 | payment_friction | Payment | 6 | 1.2 | 83.3 | 0.957 | **45.6** |
| 9 | decision_paralysis_too_many_options | Choice / Comparison | 10 | 2.1 | 30.0 | 0.888 | **21.7** |
| 10 | styling_uncertainty | Styling | 11 | 2.3 | 9.1 | 0.867 | **11.9** |

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
See the prioritized opportunity table above — the ranked blockers are exactly the purchase blockers, by reach and frustration.

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
Concentration = share of the top segment among mentions that have an inferred segment. High concentration = sharper, more targetable signal. _segment_signal is model-inferred and often sparse._

| Blocker | Mentions | Known-segment coverage % | Top segment | Concentration % |
| --- | --- | --- | --- | --- |
| price | 75 | 85.3 | budget-conscious shopper | 71.9 |
| return_hassle | 53 | 52.8 | return-focused shopper | 21.4 |
| other | 52 | 42.3 | time-sensitive shopper | 13.6 |
| fit_sizing | 27 | 66.7 | tall shopper | 11.1 |
| quality_doubt | 24 | 75.0 | quality-conscious shopper | 22.2 |
| trust_authenticity | 23 | 60.9 | gift buyer | 14.3 |
| styling_uncertainty | 11 | 72.7 | style-conscious shopper | 12.5 |
| decision_paralysis_too_many_options | 10 | 80.0 | first-time buyer | 12.5 |
| payment_friction | 6 | 33.3 | international shopper | 50.0 |
| occasion_timing | 3 | 100.0 | gift shopper | 33.3 |

---
_Generated by discover.py (Stage 4). Backing data: structured_insights.jsonl. Spot-check categorization in sample_quotes_by_blocker.json before quoting numbers._