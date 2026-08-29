# ChatGPT research — Myntra wishlist conversion

**Source:** [ChatGPT share](https://chatgpt.com/share/6a92fd04-47c4-83e8-942a-4d34aad1ce3b)  
**Status:** External PM case study. Example rates in the share (e.g. 12% → 16% WPC) are **illustrative**. They are not Myntra warehouse numbers.

**North-star:** 30-day wishlist purchase conversion — users who add ≥1 item who buy ≥1 wishlisted item within 30 days. Do not optimize wishlist additions.

**Problem (as framed):** high-intent users lack decision support between “I like this” and “I’m confident enough to buy.” Do not assume they forgot the list.

**Hypotheses:** decision uncertainty (fit) · timing · price-wait · choice overload · availability.  
**Segments:** ready-but-hesitating · wait-and-watch · comparison shopper · availability-blocked · passive saver.

**Constraint:** no coupons, cashback, coins, or markdown.

**MVP:** Smart Wishlist (genuine updates + fit/decision support + compare 2–4 saved items).  
**Test:** A/B vs current wishlist. Primary = 30-day WPC. Guardrails = opt-out, returns, incrementality.

Machine-readable chunks: `chatgpt_research.json`. The Reviewer retrieves these against public-VOC quotes.
