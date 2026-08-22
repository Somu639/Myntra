# Fashion Wishlist & Purchase-Intent Discovery Report

_AI-powered discovery engine — Myntra. Directional signals for opportunity prioritization, not statistically representative measurements (see data limitations in README)._

## Coverage
- Records analyzed: **1011** (1011 extracted, 0 failed).
- Relevant to fashion purchase/wishlist behavior: **359** (35.5% of extracted).

## Prioritized opportunity areas (Q10 — unmet needs)
Ranked by an opportunity score weighting **reach** and **frustration** equally.

| Rank | Opportunity (blocker) | Dimension | Mentions | Reach % | Frustration % | Confidence | Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | return_hassle | Returns & Exchange | 41 | 11.4 | 95.1 | 0.948 | **78.6** |
| 2 | other | Other | 47 | 13.1 | 83.0 | 0.913 | **77.1** |
| 3 | price | Price & Value | 66 | 18.4 | 19.7 | 0.916 | **59.9** |
| 4 | trust_authenticity | Trust & Reviews | 16 | 4.5 | 81.2 | 0.91 | **52.7** |
| 5 | fit_sizing | Fit & Size | 20 | 5.6 | 75.0 | 0.874 | **52.7** |
| 6 | occasion_timing | Occasion & Timing | 1 | 0.3 | 100.0 | 0.96 | **50.8** |
| 7 | quality_doubt | Quality | 18 | 5.0 | 72.2 | 0.893 | **49.7** |
| 8 | payment_friction | Payment | 5 | 1.4 | 80.0 | 0.958 | **43.8** |
| 9 | decision_paralysis_too_many_options | Choice / Comparison | 4 | 1.1 | 50.0 | 0.833 | **28.0** |
| 10 | styling_uncertainty | Styling | 5 | 1.4 | 20.0 | 0.828 | **13.8** |

## Q1 — Why do users add products to their wishlist?
- Wishlist/save signals detected: **7**.
- Top stated reasons for saving:
  - wants link to purchase later (4)
  - interested in maxi dress seen in video (1)
  - to win contest voucher (1)
  - to secure low prices during sale (1)
  > "8:16 mango Red dress link plz❤"  — _youtube_
  > "#MyntraEORSGameZone gets Bigger! We've hidden a treasure on the Myntra app. Look out for it while wish-listing for #MyntraEORS2021   The first to find it, screenshot it, &amp; p..."  — _social_twitter_ (rating 688)
  > "Mango red dress link not given plz send"  — _youtube_

## Q8 — Wishlist as genuine intent vs. bookmarking
- Of 7 wishlist signals: **5 genuine purchase intent**, **1 bookmarking**, 1 unclear (heuristic on stated reason + text).

## Q2 — What prevents wishlisted products from being purchased?
See the prioritized opportunity table above — the ranked blockers are exactly the purchase blockers, by reach and frustration.

## Q3 — Uncertainties remaining after a user likes a product
- **59** mentions (26.5% of all blockers) are lingering uncertainties (fit, styling, quality, trust, social validation).
  - fit_sizing: 20
  - quality_doubt: 18
  - trust_authenticity: 16
  - styling_uncertainty: 5
  > "Absolute fraud app They censor genuine reviews for some fake rejection reason and ensure they only publish good ones. the products received are always damaged, broken or pre-use..."  — _google_play_myntra_ (rating 1)
  > "ನಿಜ ಬಟ್ಟೆ ಕ್ಟಾಲಿಟಿ ಇತ್ತೀಚೆಗೆ ಸರಿ ಇಲ್ಲ ಮೈಂತ್ರಾ....Viscose Rayan  cotton ಅಂತಾರೆ ಕಳಪೆ ಇರುತ್ತೆ ಬಟ್ಟೆ"  — _youtube_
  > "[Selling] ZARA Cargos size 0 For context, bought this from Myntra on a major sale, but I got the sizing all wrong and it is non-returnable 😭😭😭 for how much I wanna keep it becau..."  — _reddit_ (rating 1)

## Q4 — What causes users to postpone a purchase?
- **71** mentions (31.8% of blockers) map to postponement drivers (price/sale-wait, occasion timing, choice overload).
  - price: 66
  - decision_paralysis_too_many_options: 4
  - occasion_timing: 1

## Q5 — How do users compare multiple shortlisted products?
- Choice-overload / comparison-difficulty mentions: **4**.
  > "Suggest which to buy I wanted to get new earphones as I put my previous ones in the washing machine🥲.  I have an offer on myntra of around 3300 for Realme buds air 6 pro. Or sho..."  — _reddit_ (rating 1)
  > "This all promotion Haul video  How come she can find simple dress in Myntra?"  — _youtube_
  > "I think they are overvaluing brand loyalty here. I don&#x27;t even understand people who can shop using mobile apps, especially clothes. You cannot easily compare, read reviews,..."  — _other_public_

## Q6 — What do users research off-platform before buying?
- Off-platform research: **36** mentions (10.0% of relevant).
  - none_mentioned: 129
  - in_app_reviews: 30
  - external_friends_family: 16
  - external_youtube: 12
  - external_google_search: 7
  - social_media_influencer: 1
  > "Price ku nhi mention karti ho ab"  — _youtube_
  > "Myntra coupon please I'm buying shoes. If anyone have myntra coupon, please share. Thankyou"  — _reddit_ (rating 1)
  > "Can I pull off a crop top + skirt + Gujarati dupatta for Dandiya, or should I just buy a set? Hey everyone! I don’t really have a traditional festive wardrobe yet. I was thinkin..."  — _fashion_community_ (rating 1)

## Q7 — Role of fit, size, styling, price, reviews, occasion, social
| Dimension | Mentions | Share of blockers % |
| --- | --- | --- |
| Price & Value | 66 | 29.6 |
| Other | 47 | 21.1 |
| Returns & Exchange | 41 | 18.4 |
| Fit & Size | 20 | 9.0 |
| Quality | 18 | 8.1 |
| Trust & Reviews | 16 | 7.2 |
| Payment | 5 | 2.2 |
| Styling | 5 | 2.2 |
| Choice / Comparison | 4 | 1.8 |
| Occasion & Timing | 1 | 0.4 |

## Q9 — How do behaviors differ across user segments?
Concentration = share of the top segment among mentions that have an inferred segment. High concentration = sharper, more targetable signal. _segment_signal is model-inferred and often sparse._

| Blocker | Mentions | Known-segment coverage % | Top segment | Concentration % |
| --- | --- | --- | --- | --- |
| price | 66 | 83.3 | budget-conscious shopper | 78.2 |
| other | 47 | 40.4 | time-sensitive shopper | 15.8 |
| return_hassle | 41 | 48.8 | return-focused shopper | 30.0 |
| fit_sizing | 20 | 65.0 | tall shopper | 15.4 |
| quality_doubt | 18 | 66.7 | quality-conscious shopper | 25.0 |
| trust_authenticity | 16 | 50.0 | skeptical shopper | 12.5 |
| payment_friction | 5 | 20.0 | international shopper | 100.0 |
| styling_uncertainty | 5 | 40.0 | style-conscious shopper | 50.0 |
| decision_paralysis_too_many_options | 4 | 50.0 | first-time buyer | 50.0 |
| occasion_timing | 1 | 100.0 | gift shopper | 100.0 |

---
_Generated by discover.py (Stage 4). Backing data: structured_insights.jsonl. Spot-check categorization in sample_quotes_by_blocker.json before quoting numbers._