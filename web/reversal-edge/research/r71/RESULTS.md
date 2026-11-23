# Round 71 results: eight new stretch-style indicators for the Z score plan (plan in PREREG.md)
Scripts and outputs: r71.py (r71.out), r71b.py (addendum B, r71b.out), r71diag.py (S5 diagnostics), valraw.py (traded-value check).
Checks: the stretch formula used here equals the scanner's stretch Z exactly; all 8 indicators recomputed on data cut at 6 random past
closes equal their full-history values (no look-ahead in the indicators themselves).

## Verdict: no indicator helps the plan. Nothing changes in the live rule.
None of the 8 meets the rule fixed in advance; the two follow-ups on the most informative one (addendum B) fail too; the yearly re-choice
among all variants is worse than live (2016-26 +3.1% a year, return / drawdown 0.77, against +5.2%, 1.06).

## Trade level: does the indicator tell good signals from bad ones? (rank correlation, signed so + = the expected direction)
| indicator | Saudi 2013-19 | Saudi 2020-26 | episode-clustered t | within episodes | US 2005-26 (t) |
|---|---|---|---|---|---|
| S1 own stretch (stock minus market) | +0.13 | +0.04 | +1.35 | +0.17 | +0.04 (+0.3) |
| S2 sector stretch | -0.04 | -0.07 | -0.09 | +0.14 | n/a |
| S3 overnight share of the fall | -0.01 | +0.30 | +0.42 | +0.02 | -0.24 (-2.9) |
| S4 panic (volatility 20d / 250d) | +0.17 | -0.14 | -0.09 | +0.10 | +0.05 (+0.4) |
| **S5 liquidity shock** | **+0.29** | **+0.22** | **+5.16** | **+0.20** | +0.13 (+1.1) |
| S6 limit-down closes (5 days) | -0.22 | +0.22 | -0.45 | -0.15 | n/a |
| S7 breadth washout | +0.08 | -0.02 | +0.90 | | +0.05 (+0.4) |
| S8 oil stretch | -0.06 | +0.20 | +0.53 | | -0.21 (-1.8) |
Only S5 passes the trade-level and US conditions. S3 and S8 flip sign between eras or between Saudi and the US.

## Account (plan Z 5 x 5%, growth per year / worst drawdown): filter (U1) or size tilt (U2)
| variant | 2013-19 | 2020-26 | 2013-26 | trades |
|---|---|---|---|---|
| live | +3.2% / 6.1% | +4.5% / 4.9% | +3.9% / 6.1% | 67 |
| S1 filter | +3.9% / 4.0% | +3.4% / 5.3% | +3.6% / 5.3% | 37 |
| S2 filter | +4.8% / 4.1% | +3.7% / 4.9% | +4.2% / 4.9% | 41 |
| S3 size tilt | +4.3% / 6.0% | +4.8% / 4.8% | +4.5% / 6.0% | 67 |
| S5 filter | +2.3% / 5.8% | +3.2% / 4.4% | +2.8% / 5.8% | 37 |
| S5 size tilt | +2.4% / 4.8% | +3.9% / 3.9% | +3.2% / 4.8% | 67 |
| S7 filter | +5.1% / 4.1% | +2.8% / 4.1% | +3.9% / 4.1% | 25 |
| S8 size tilt | +4.6% / 9.0% | +5.1% / 6.1% | +4.8% / 9.0% | 67 |
(all 16 rows in r71.out.) S3's size tilt is better than live in both eras by the account rule, but S3 fails the trade-level rule
(no effect in 2013-19, reversed in the US), so its account gain is not trusted.

## S5 liquidity shock: real information, but not usable by a 5-slot account
S5 = log(5-day average of |return| / value traded, over its 250-day median): the price moving on unusually thin trading.
- Strong at the trade level: favourable half 2013-19 +23.9% vs +14.2% per trade, 2020-26 +12.6% vs +6.4%. With stretch depth,
  volatility and ML rank as controls t +5.8; adding volatility expansion and the sell-off day, t +3.0. Positive in 6 of 8 years and in
  6 of 7 sell-offs with enough trades on both sides. Positive but weak in the US (+0.13).
- Not usable by the account: the account fills its slots on the first day of a sell-off, when liquidity shocks are still small (median
  S5 of trades taken +1.20, of signals not taken +1.73). On the same day, the signal with the higher S5 is hardly better (average
  same-day rank correlation +0.06).
- Addendum B (pre-registered after the diagnostics): S5 as the slot order: 2013-19 +2.6% / 6.6%, 2020-26 +4.3% / 4.9% (worse than
  live); S5 as part of the signal (a touch without a liquidity shock is no signal and blocks nothing): +2.5% / 4.9%, +3.2% / 4.4%,
  38 trades, 61% winners (worse). US: better in 2 of 3 eras, worse in 2018-26.

## Found on the way (not indicator results)
1. The past moves: two old trades of the live rule (4300 on 2021-11-11, 8030 on 2025-12-28) dropped out since round 70 because the
   walk-forward market model's value on those days moved from just above zero to just below after data updates. The live record is
   now 2020-26 +4.5% a year (was +4.9%), 34 trades, +6.7% per trade. The daily list now recomputes the record it quotes on every run
   (planbook.record), so it cannot go stale.
2. Traded value uses the dividend-adjusted close. Each dividend scales a stock's whole past down, so its past value traded shrinks:
   the median adjustment is 0.83 in 2013 and 0.91 in 2019. A stock's liquidity on an old date therefore depends on dividends paid
   later (a mild look-ahead), and old values change after every dividend (the cause of item 1).
   With value traded from the raw close (valraw.py; ML ranks and the market model not refit): 3.1% more liquid stock-days, 26 more
   Z score signals, 69 trades instead of 67, and 2013-19 +3.1% a year with a 7.6% worst drawdown instead of +3.2% / 6.1%; 2020-26
   unchanged. The honest fix is raw value traded everywhere, with the ranker and the market model refit. Offered to the user.
