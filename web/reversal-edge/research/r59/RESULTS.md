# Round 59 results: do the signals work better in companies with better financials? (plan in PREREG.md; r59.py, r59.out)
Data: Yahoo annual accounts FY2022-25 for 270 Saudi stocks (1029 stock-years; F-score for 756), each year usable 91 days after the
fiscal year end; share counts corrected for 274 bonus-share / split events. Quarterly data starts 2025 and was not used.
Trades: next open, hold 40 sessions, 0.4% costs, finished trades only (entries up to 2026-09-09). ML sets: 20-session excess vs the
average liquid stock. 95% intervals: bootstrap over entry weeks. Set B has 270 trades, not the 668 first touches counted in the plan,
because a stock already held is not re-entered and unfinished trades are dropped.

## Answer by the pre-registered rule: NOT PROVEN
| last two years (entries 2024-11-06 .. 2026-09-09) | F-score strong (>= 6) | weak (<= 4) | strong - weak (95%) |
|---|---|---|---|
| A Z swing, live filters without the profit filter (49 trades, 9 entry weeks) | 59% win, +3.5% | 45%, +2.5% | +0.9 pts (-16.8 .. +7.7) |
| B price-only stretch-Z dips (270) | 45%, -0.6% | 35%, -5.6% | **+5.0 pts (+0.8 .. +10.0)** |
| C ML ranker C top 10% (1698) | 59%, +1.43% | 51%, +0.33% | **+1.1 pts (+0.4 .. +1.9)** |
| D all liquid stocks (15978) | 47%, +0.27% | 41%, -0.72% | **+1.0 pts (+0.6 .. +1.4)** |

Conditions 1 (B above zero) and 2 (A and C the same way) pass; condition 3 fails: in the earlier piece (entries 2024-04 .. 2024-11)
strong minus weak was -4.0 pts for dips (46 trades) and -1.1 pts (-2.1 .. -0.2) for all stocks. Financial strength paid in
2025-26 but not in 2024, so it is not a stable edge yet. No change to the live rule.

## What did hold
- Profitable vs loss-making, the filter the live rule already has (round 36): Z swing 74% winners +5.8% vs 47% +1.3%
  (+4.5 pts, 95% +1.6 .. +9.8); dips +0.1% vs -6.7%; all stocks +0.9 pts. This period overlaps the round-33 data the filter
  was chosen on, so it supports but does not independently confirm it.
- Other measures, last two years (descriptive; with about 20 comparisons some "significant" results are expected by chance):
  low debt better for dips (-5.2 pts high-low debt) and all stocks (-0.8); cheaper (higher earnings yield) and earnings-up stocks
  better for all stocks (+1.0, +0.6); none of ROE, debt, cheapness, earnings growth or cash-flow quality separated the Z swing trades.
- Exploratory (not in the plan): among the profitable Z swing trades the live rule takes (34), F-score >= 6 68% +4.9%, 5 100% +9.1%,
  <= 4 40% +2.9% (5 trades). Too few and too clustered (22 of 49 signals in the first week of April 2025) to act on.

## Conclusion
Better financials helped the broad market and the price-only dips over the last two years, and the ML top picks of weak
companies lagged. For Z swing itself, the only measure that clearly mattered is the one already in the rule: skip loss-makers.
Re-test when longer history with publication dates is available (see the data-source note of 2026-11-06).
