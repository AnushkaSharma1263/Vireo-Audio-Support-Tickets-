# Submission (form not in pack; answers below follow the brief's questions)
**Tool:** `breach_report.py` (pandas, deterministic). **README:** README.md. **Business goal:** overall first-response breach rate 25% -> ~13% (stretch ~10%) within a quarter; ~Rs 3.8 lakh/yr (~Rs 0.95 lakh/qtr) credits avoided (Rs 4.8 lakh/yr stretch). Source: 1,581 uncovered overnight breaches x Rs 350 in 12 months.
**Evidence it works:** independent SQLite recompute (0 mismatches on 11,200 tickets), unit tests on boundary minute / IST cliff 21:59 vs 22:00 / roster as-of dates, breach-rate cliff at 22:00 IST in the data. Error rate: 0 on rule application; the real risk is the UTC assumption and resolver-as-proxy (not testable from the data).
**Left out and why:** CSAT, refunds, replacement cost, IVR/free-text analysis, forecasting. Not needed to answer the breach question; LLM not used because every field needed is structured.
**Decisions:** listed in README.md.
**AI tools used:** [FILL IN: assistant used, approx cost, what you discarded]. Honest note: do not claim figures here you did not generate yourself.
**Screen recording:** [YOU RECORD]. Script: (1) show the first naive report: morning shift = worst; (2) change: UTC->IST, dedupe; (3) change: attribute by creation shift + coverage flag, which flips the story; (4) thrown away: per-agent league table, LLM classification of notes, CSAT analysis.
