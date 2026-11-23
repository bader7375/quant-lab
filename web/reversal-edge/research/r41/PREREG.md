# Round 41: quant upgrades to the Z swing - entry timing, exits, sizing, selection (pre-registered 2026-10-30, before any result)
User request: think out of the box, use quant methods, improve the strategy. Known: stops hurt (round 39), further falls are not
predictable from volume/candles/volatility (round 40), stock choice added little vs random in 2023-26 (round 38).

Baseline: live Z swing (daily -2.62 / weekly -2.08 first touch, ML >= 0.5, market model > 0, market momentum <= -1.18, liquid), buy next
open, hold 40 sessions, no stop, sleeve of at most 5 positions x 5%, highest ML first, 0.40% round trip. Every variant changes ONE thing.

A. Entry timing ("let it finish falling")
 A1 wait for the first up close within 5 sessions after the signal, buy the next open (no up close: no trade).
 A2 scale in: half at the next open, half with a resting buy order 8% below the first price (filled at that price, or at the open if it
    gaps below; unfilled half stays cash). A3 the same with the second half 12% below.
B. Exit ("sell when the stretch is gone, not on a calendar")
 B1 sell at the next open after the daily stretch Z closes >= 0 (at most 60 sessions). B2 the same with Z >= +1.
 B3 Ornstein-Uhlenbeck holding period: hold 2 half-lives of the stock's own mean reversion (AR(1) of log price around its 60-day mean,
    past 250 sessions), between 10 and 60 sessions. B4 hold 60 sessions.
C. Sizing
 C1 equal risk: weight 5% x (median volatility of design-period signals / the stock's 60-day volatility), between 2.5% and 10%.
 C2 deep-zone tilt: 7.5% when market momentum <= -2.53, else 3.75%.
D. Selection and timing
 D1 own mean-reversion strength: keep signals whose rolling 500-session slope of 20-day forward return on stretch Z (known 20 sessions
    later) is below that day's median across liquid stocks (the stock has reverted more strongly in its own past).
 D2 market washout: keep signals on days when at least 10% / 15% / 20% of liquid stocks close at daily Z <= -2.0.
 D3 timing basket: on each signal the sleeve takes, buy an equal-weight basket of the 20 most liquid stocks instead of the signalled
    stock (same days, same hold) - tells whether picking the stock adds anything over timing the market.

Measures: per trade (win rate, average, worst 5%) and the sleeve with daily mark-to-market: return per year (% of account), maximum
drawdown, ratio return / maximum drawdown, daily Sharpe. Eras: DESIGN 2013-19, CONFIRM 2020-26, also 2023-26.
Choice per family: in DESIGN, the variant with the highest ratio among those with sleeve return >= 90% of the baseline's. Adopted only
if in CONFIRM its ratio is higher than the baseline's and its sleeve return >= 90% of the baseline's. Adopted changes are then
combined and the combination is reported (CONFIRM used twice for it: labelled, not a new decision). D3 is a diagnostic: it is
"adopted" only by the same rule. 16 variants in all; with that many tries, single near-misses are treated as noise.

## Addendum (2026-10-30, after the Saudi run, before any US number of this round)
Saudi: no family adopted. The Z-target exit B1 was much better in 2020-26 and 2023-26 but worse in 2013-19 (it sells the long rebounds of
that period early); scale-in A2/A3 cut drawdowns but also returns. Independent check on the US sell-off swing (115 large caps, window
open, 0.10% costs, sleeve 5 x 5%, most stretched first), eras 2005-09 / 2010-17 / 2018-26, variants baseline, A3, B1, B4.
B1 counts as confirmed in the US if its sleeve ratio beats the baseline's in BOTH 2010-17 and 2018-26 with return >= 90% of the
baseline's. Even then it is offered as a tracked option (exit marker in the terminal), not switched on, because Saudi 2013-19 disagrees.
