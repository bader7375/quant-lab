# Round 62 results: meta-labeling for Z swing (plan in PREREG.md; r62.py, r62.out)
Walk-forward LightGBM win-probability model, refit every January 2013-2026 on 4,836 stretch-Z dips (60 features: the ranker's
42 stock features, the Z family, momentum, market state, ML rank, sector), purged so no training trade overlaps the test year.

## Verdict: does not pass. Nothing changes in the live rule.
| | DESIGN 2013-19 | CONFIRM 2020-26 | 2023-26 |
|---|---|---|---|
| AUC on Z swing signals (0.5 = coin flip) | 0.562 | 0.624 | 0.412 (52 trades) |
| U1 filter (p >= DESIGN median): kept vs dropped per trade | +19.7% vs +18.5% (gap +1.2) | +7.9% vs +3.5% (gap +4.4, 22 dropped) | +4.6% vs +3.6% |
| sleeve ratio: live / option 1 (ML >= 70%) | 0.24 / 0.31 | 0.23 / 0.25 | 0.22 / 0.39 |
| U1 filter | 0.32 | 0.24 (below option 1) | 0.31 |
| U2 priority (highest p first when slots are full) | 0.23 (DD 7.8% vs 6.5%) | 0.37 | 0.45 |
| U3 sizing (2.5%-7.5% by p) | 0.18 | 0.24 | 0.21 |
U1 misses the +2-point gap in DESIGN and loses to option 1 in CONFIRM; U2 is best in CONFIRM and 2023-26 but slightly worse than
live in DESIGN with a deeper drawdown; U3 is worse. The model leans mostly on the market model (18% of split gain) and market
momentum (15%), which the Z-swing gates already use, so inside the gated signals it adds little.

## Momentum does not favor the Z-swing long
Inside the Z swing signals, the 40-session result is NEGATIVELY related to momentum in almost every measure and period
(rank correlation with the trade result, DESIGN / CONFIRM / 2023-26): 60-day return -0.05 / -0.18 / -0.25; distance above the
50-day average -0.08 / -0.18 / -0.19; 12-1 momentum +0.02 / -0.21 / -0.19; 52-week-high proximity -0.10 / -0.18 / -0.05.
The weaker the stock going into the signal, the better the rebound. (Across all dips without the gates the sign is positive,
because there momentum mostly tells whether the whole market is falling - which the market-momentum gate already handles.)
Together with rounds 42 and 57 (waiting for a green candle or for VWAP loses money), momentum confirmation should not be added.

## Paper-track idea (not a rule)
U2 (when more signals than free slots, take the highest win probability first) was strong in 2020-26 and 2023-26. It can be logged
on live signals for a few months before any decision; it changes nothing unless the user adopts it.
