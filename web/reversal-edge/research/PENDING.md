# Open decisions (saved 2026-10-30 at the user's request: "save this, I will come back to it")
Nothing below is switched on. Live rule today: Z swing (daily -2.62 / weekly -2.08, ML >= 50%, market model > 0, market momentum
<= -1.18, profitable company), buy next open, 5% per stock, at most 5, hold 40 sessions, no stop.

1. ML bar 50% -> 70% (round 38, r38/RESULTS.md). Passed the pre-registered rule. Per trade 2020-26: 74% win, +8.7% vs 72%, +7.6%;
   2023-26 +6.4% vs +4.6%. In the 5-position account: about the same return per year, fewer trades (29 vs 43 in 2020-26), higher win rate.
2. 12% stop order (round 39, r39/RESULTS.md). Rule answer: no stop (missed by 0.1 pt on the worst-5% trade). With it: account return
   +2.2% vs +1.7% a year and drawdown 5.2% vs 5.6% in 2020-26, but win rate 65% vs 72%, average trade +5.5% vs +7.6%.
3. Sell when stretch Z is back at 0 (round 41, r41/RESULTS.md). Not adopted (regime-dependent). 2020-26: 86% win vs 72%, worst-5%
   trade -6.0% vs -12.3%, account drawdown 4.4% vs 5.6%; 2013-19: average +12.1% vs +19.5% (sells long rebounds early).
   Suggested: show it in the scanner / signal card as an optional "low-risk exit" and track both exits live.
Related findings: further falls after the buy are not predictable from volume / candles / volatility (round 40); scale-in halves
drawdowns but lowers returns (round 41); recently (2023-26) the edge is mostly timing (buying in sell-offs), not stock choice.
Also tested afterwards (round 42, r42/RESULTS.md): buying on the first green candle (big volume / strong close) with the stop under it -
not adopted; the stop is hit in about half the trades and the wait for the candle lowers returns in 2020-26.
4. Split exit (round 43 context, r43/RESULTS.md): half of each position held 40 sessions, half sold when stretch Z is back at 0.
   Return about +2.3% of the account a year in 2013-19, 2020-26 and 2023-26 alike; ratio return / drawdown 0.45 / 0.51 / 0.85 vs
   0.55 / 0.31 / 0.26 for the live rule. The robust choice (best worst period); a mix of two tested exits, not a new discovery.
Round 43 (book rules: Connors close entry, RSI(2) entry and exits, 200-day filter; Turtle Soup; Bulkowski dead-cat; Nagel volatility;
George-Hwang 52-week low): nothing beats the live rule in both periods.
5. Position size (round 45, r45/RESULTS.md): Kelly says 5% per Z-swing position is too small. 10% positions (still at most 5):
   about double the Z swing's contribution (+5.9% / +3.6% a year in 2013-19 / 2020-26) with a worst drawdown of about -10%.
6. Idle money (round 45): the Z swing is invested only ~5% of the time. Core v2 (ML ranking + trend breakouts, in the terminal's
   Core panel) made +11% / +20% a year (2013-19 / 2020-26, Sharpe 0.91 / 1.39, worst drawdown -23% / -19%); with the Z swing on top
   +12.5% / +20.2%. A bigger decision (much more market exposure), so not switched on.
7. Buy only after TASI turns (round 47, r47/RESULTS.md): take a Z-swing signal only if the TASI proxy (equal-weight liquid stocks) has
   bounced at least 4% off its 20-day low in the last 20 sessions (after being 10%+ below its 1-year high). Passed the pre-registered
   rule and its robustness checks. Per trade 2020-26: 86% win, +11.8%, worst-5% -5.6% vs 72%, +7.7%, -11.9%; account ratio
   0.55 vs 0.25 (2013-19: 0.39 vs 0.23). Caveats: designed after seeing the first test; only 3 of 5 sell-offs with both kinds of
   trades favour it; failed in the 2005-09 US bear market (4% bounces were bear rallies). On 2026-11-02 it is ON (bounce on 10-26).
Round 47 also found: none of 14 classic TASI bottom signals (Lowry, Zweig, Desmond, Connors RSI(2), Williams VIX Fix, breadth
washouts, VIX, oil) beats simply being in the live sell-off window as a market timer.
   Note (round 49): option 7 works only as a "shadow book" - run the live rule on paper and actually buy only its trades that start
   after the turn (a stock the paper book bought before the turn stays blocked for its 40 sessions). Gating the signals instead
   (letting pre-turn signalers be bought on a later signal) is much weaker (2020-26 ratio 0.37 vs 0.34, 2023-26 worse).
8. Z swing v2 (rounds 48-50, overnight 2026-11-03): option 7 (shadow turn gate) + option 1 (ML bar 0.7) + option 4 (split exit:
   half held 40 sessions, half sold when stretch Z is back at 0), 5 slots. Passed the combination test and 10 of 12 stress variants
   (costs, slippage, a day late, nearby settings). Same size as live: 2013-19 +2.4% vs +1.8% a year, max drawdown 5.4% vs 6.4%;
   2020-26 +1.5% vs +1.5%, drawdown 3.0% vs 4.4%, 89% vs 63% winners; 2023-26 ratio 0.70 vs 0.33. The gain is mostly lower risk
   (worst sell-off -0.07% vs -2.87% of the account in 2020-26), not more return. Saudi-only: the turn gate failed the US 2018-26 check.
   Round 48: 5 x 10% (instead of 5 x 5%) is the largest size with drawdown <= 15% in both periods; more, smaller slots did not help.
Overnight conclusion (rounds 48-53): the split exit (option 4) is the one Z-swing change that holds across markets (better in 7 of
10 market-eras: Saudi, US, India, GCC). v2's turn gate is strong in Saudi (both periods, stress-tested) but helps in only 5 of 10
market-eras elsewhere, so treat it as a Saudi-specific choice for lower risk. Size: 5 x 10% keeps drawdown under 15%.
