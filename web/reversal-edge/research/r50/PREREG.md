# Round 50: stress tests of the Z swing v2 candidate (pre-registered 2026-11-03, before any result of this round)
Candidate from round 49 addendum A (Saudi-only: it failed the US check in 2018-26):
- **Shadow book:** run the live Z swing as a shadow book (daily -2.62 / weekly -2.08 first touch, market model > 0, market momentum <= -1.18, liquid, ML >= 0.7 instead of 0.5).
- **Turn rule:** actually buy only the shadow trades whose signal day is within 20 sessions after a TASI turn. A turn is the TASI proxy closing 4%+ above its 20-day low after being 10%+ below its 1-year high.
- **Split exit:** half of each position is held 40 sessions; the other half is sold at the open after stretch Z is back at 0 (max 60).
- **Account:** two sub-sleeves of 5 slots each.

Compared with the live rule at the same size: v2 at 5 slots x 2 x 2.5% vs live 5 x 5%.

## Stress variants (r50.py), each run for both v2 and live where it applies
1. Costs 0.60% and 0.80% round trip (base 0.40%).
2. Adverse slippage: buy at the open +0.5% and sell at the open -0.5%.
3. One day late: buy at the second open after the signal.
4. Nearby settings for v2 (live unchanged):
   - ML bar 0.65 / 0.75;
   - turn lookback 10 / 30;
   - bounce 3% / 5%;
   - Z-exit level -0.25 / +0.25.
5. (Dropped before running: the 2026-10-30 ML ranks were overwritten by the daily refit, so no second ML run is available.)

## Pass rule
v2 is called ROBUST if, in at least 80% of the variants in groups 1-4, it keeps BOTH:
- ratio (return per year / max drawdown) higher than live in DESIGN 2013-19 and in CONFIRM 2020-26; and
- return >= 90% of live in both eras.

Otherwise it is FRAGILE.

Also reported (no decision):
- year-by-year P&L of v2 and live;
- a cluster bootstrap over sell-off spells (2,000 draws), giving the probability that v2's ratio beats live's in each era;
- worst trades;
- longest losing streak;
- the worst drawdown period.
