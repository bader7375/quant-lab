# Round 28 pre-registration: high-win-rate Saudi swing signals (written 2026-10-24, before any round-28 result)

User goal: win rate above 60%, high reward / low risk, holding weeks. Data: clean panel (round-27 fix) through 2026-10-22.
Costs 0.40% round trip; signal at the close, entry at the next open; stops/targets judged on CLOSES and executed at the next open
(no intraday fills assumed); liquid stocks only (60-day median value >= SAR 3m).

## Targets (all must hold in DESIGN 2013-19 AND CONFIRM 2020-26; CONFIRM halves 2020-22 / 2023-26 each >= 55% win)
- win rate (net > 0 after costs) >= 60%
- payoff ratio = average win / |average loss| >= 1.0 (no "many small wins, few huge losses" designs)
- expectancy >= +2.0% net per trade; at least 20 trades a year on average; median holding 10-40 sessions
- as a sleeve next to Core v2: portfolio Sharpe not lower by more than 0.05 and worst drawdown not worse by more than 3 points.

## Entry families (signal at close t)
E1 Z rebound: stretch Z first close <= L (L in -2.0, -2.3, -2.62), ML rank >= m (0.5, 0.7), market model > 0.
E2 Uptrend pullback: close > SMA200, SMA50 > SMA200, stretch Z <= -1.5, ML >= 0.7, market model > 0.
E3 ML-leader pullback: ML rank top 10%, 5-day return <= -3%, market model > 0.
E4 Trend breakout: close at 55-day high above SMA200, ML >= 0.7, market model > 0 (current rule).
E5 Squeeze breakout: 20-day range in the lowest 20% of its own 250-day history, close at the 20-day high, above SMA200, ML >= 0.7, market model > 0.
E6 Strong-sector pullback: own sector index above its 50-day average with positive 20-day return; stock stretch Z <= -1.5; ML >= 0.5; market model > 0.
## Exit designs
X1 hold 20 sessions; X2 hold 40; X3 target +k ATR / stop -m ATR (k 3,4,6; m 2,3), cap 40; X4 trailing (highest close - 3 ATR), cap 60;
X5 initial stop 2.5 ATR, after +2 ATR move stop to entry, then trail 3 ATR, cap 40.
## Meta-label filter
Walk-forward yearly LightGBM classifier on all E1-E6 candidates (entry-day stock + market features + family id) predicting a win under
the chosen exit. Probability threshold chosen on DESIGN (maximise expectancy with win >= 62%); judged on CONFIRM.
## Selection
Only DESIGN numbers choose (family x exit x threshold): among combinations meeting all targets on DESIGN, take the highest DESIGN
expectancy x trades per year. CONFIRM is then reported once. Price-only versions (no ML, market filter = equal-weight market above its
200-day average) are also checked on DEEP 2004-12 for the sign of the expectancy. Every combination tried is logged.
