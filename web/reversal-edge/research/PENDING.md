# Open decisions (saved 2026-10-30 at the user's request: "save this, I will come back to it")
LIVE SINCE 2026-11-10 (the user: "Let's go back to previous strategy stretch with ML"): plan Z = the Z score rule (stretch Z touch, ML rank 50%+,
market model positive, market momentum -1.18 or lower, profitable), 5 positions of 5%, most volatile first, hold 40 sessions, no stop; reported
through the plan book (daily/planbook.py kind "Z"). Plan A (below) was live on 2026-11-09 only and made no trade.
14. BUILT 2026-11-13 at the user's request ("build a very advanced indicator to help with taking the trade"): Rebound Edge (round 80,
   r80/RESULTS.md; fable/rebound.py; pine/rebound_edge.pine; the Fable terminal's chart, scanner and Research tab). For a stock with
   stretch Z -1.5 or lower: the expected net result of a buy at the next open (sold at stretch Z 0 or after 40 sessions), with the share
   of wins, the dip, the sessions and a cone. Formula fitted on 23 other markets (214,081 cases), adjusted on Saudi. Verdict by the
   pre-registered marks: DESCRIPTIVE. It separates (Saudi 2013-19 top third +7.7% / bottom third -3.7%; 2020-26, opened once, +8.9% /
   -2.4%) but ranks results no better than market momentum alone (rank correlation 0.437 against 0.437 in 2020-26). NOT a filter for the
   swing's signals. Dead ends added: a chance-of-win indicator (the chance barely moves: 65-77%; trees worse than no-skill); 19 extra
   stock and market readings (volatility, zone age, overnight share, residual, speed, range, close position, crash days, breadth,
   market stretches, co-movement, sell-off age): none adds across markets. The 16:55 scheduled task: the user said NO on 2026-11-13.
   Round 81 (r81/RESULTS.md, 2026-11-14, at the user's request): the swing with and without Rebound Edge, and Rebound Edge alone. No
   rule that uses it beats the swing. Filter (strong edge only): 77 trades against 95, +4.2% / 5.7% against +4.4% / 5.4%; abroad lost
   34 to 28. Rebound Edge alone (terminal version): 12 trades a year, 2020-26 +7.1% / 4.0% against +4.8% / 2.6%, but 2013-19 +3.2% /
   8.5% against +3.9% / 5.4%; abroad 34 to 30 (coin flip). Chart formula alone (no gates): 63% winners, +2.0% a trade. Do not repeat.
13. OFFERED 2026-11-12 (the Fable edition, rounds 76-78; r78/RESULTS.md): the Fable swing - the same gates as the Z score plan; buy at
   the open after the first close at stretch Z -2.5 or lower (daily only) in a sell-off; ONE new position a day (the most volatile), up
   to 12 positions of 2.1% of the account, 4.2% when market momentum is -2.53 or lower; SELL at the open after the first close with
   stretch Z at 0 or higher, or after 40 sessions; a sold stock can be bought again on a new cross. Rule fixed before Saudi 2020-26 was
   opened. CONFIRMED against live by the strict rule: 2013-19 +3.9% a year / drawdown 5.4% against +3.1% / 6.1%; 2020-26 +4.9% / 2.6%
   against +4.6% / 4.9%; 2023-26 +6.0% / 1.7% against +6.3% / 2.7%. 92 trades (about 7 a year, almost only in sell-off years), 83% winners,
   +10.1%, 24 sessions held. NOT better than the ladder (item 12) in both periods; the yearly walk-forward picks the ladder; the plan's
   "sound" mark missed on one count (13 trades against 14 in 2023-26). Stress: passes costs, a day late, idle money at zero; FAILS with
   line -2.25 or two buys a day (drawdown 8-9%). Abroad it beats the live shape in 80% of 64 market-eras. Not blind on 2020-26 for the
   exit (rounds 41, 43, 70 had looked at selling at Z 0 inside the 5-slot plan and did not adopt it; the swing differs by one buy a
   day, small positions and re-entry, and its gain is lower drawdown). Runs on paper in the Fable terminal since the 2026-11-11 close. Waiting for the user.
   The 16:55 scheduled task that would feed the Fable terminal daily (fable/SCHEDULE.md): the user said no on 2026-11-13; not created.
   Round 79 (r79/RESULTS.md, 2026-11-12): 13 ideas / 36 variants to improve the swing (zone by weather, later sales, order of candidates,
   size from volatility or depth, 2 buys a day in a named state, calm-weather dips in an uptrend, liquidity bar, the daily limit, sector
   cap, 10-session swing, no quick re-buy, exposure ceiling, rotation). Tested abroad first, then Saudi 2013-19; 2020-26 NOT opened.
   None passed both. The swing stays as it is. Do not repeat these without a new angle. One lead only: rotation into a deeper stock when
   the book is full won where it acted abroad (17 of 22 market-eras) and never acted on Saudi 2013-19.
12. OFFERED 2026-11-11 (the Fable edition, rounds 71-74; r73/RESULTS.md): the Fable ladder - the same Z score signals, at most ONE new
   position a day (the most volatile signal), up to 12 positions of 2.1% of the account, 4.2% when market momentum is -2.53 or lower;
   hold 40 sessions, no stop; the account can hold up to 50%. Chosen on 23 foreign markets plus the US (it beats the live shape in 75% of 64
   market-eras, in every era, also with 0.8% costs and a day late); pacing 3 sessions apart (item 11) FAILED there (55%: it only invests
   less). On Saudi at equal risk: 2013-19 +5.4% a year / drawdown 6.1% against live +3.1% / 6.1%; 2020-26 +4.5% / 4.5% against +4.7% / 4.9%;
   2023-26 +4.7% / 1.0% against +6.4% / 2.7%. By the strict rule it is NOT confirmed (less growth in 2020-26); the yearly walk-forward
   does not favour it; stress tests 10 of 10. It made money in the three sell-offs where the live rule lost (2014, 2015, 2022) and less
   in the short ones (5 of 15 sell-offs better). Runs on paper in the Fable terminal (fable/README.md). Waiting for the user.
   Also from these rounds: the live numbers move by about 0.2 point a year when the models are refit from scratch (round 71); every
   gate earns its place except the loss filter, which changes 2 trades in 14 years (kept as a guard); buying at the 10:00 open is right
   (round 74: the close and limit orders do not beat it).
11. OFFERED 2026-11-10 (round 70, r70/RESULTS.md): pacing for the Z score plan - at least 3 sessions between two new positions (one buy a
   day, the most volatile signal). Same growth over 2013-26 at 5% (+4.2% vs +4.1% a year) with a 3.8% worst drawdown instead of 6.1%; less
   growth than live in 2020-26 at the same size (+4.2% vs +4.9%), so it did not pass the advance rule; the yearly re-choice supports it.
   At 8% positions (exploratory): +5.6% a year over 2013-26 at the live rule's 6.1% drawdown. Waiting for the user (pacing yes/no, 5% or 8%).
   Round 70 also retired options 1 (ML bar 70%: now worse) and 4 (split exit: no gain in the verified engine).
WAS LIVE 2026-11-09 to 2026-11-10 (round 67, r67/RESULTS.md, the user's choice "Let put A"): plan A - buy only Market returned signals (option 7),
10% of the account each, at most 5, most volatile first, hold 40 sessions, no stop; Z score signals off (they run as the shadow book);
ML leaders / breakouts shown for reference only; idle money in a SAR money-market fund. Switches: daily/settings.json.
Audit 2026-11-10 (round 68, r68/RESULTS.md): numbers confirmed by an independent rebuild; the list now follows daily/planbook.py (the tested
rule replayed: plan book, free slots, repeat signals ignored). Plan A rests on 53 trades in 14 years.
Stop loss for plan A (round 69, r69/RESULTS.md, the user asked for one): 36 stops tested, none improves it (the plan buys the retest of the
market low, so dips after the entry are normal; stops lock them in). More, smaller positions (8 to 20 slots at the same 50%) are not better
either. Plan A stays 5 x 10%, hold 40 sessions, no stop.
Nothing below is switched on. Live rule today: Z swing (daily -2.62 / weekly -2.08, ML >= 50%, market model > 0, market momentum
<= -1.18, profitable company), buy next open, 5% per stock, at most 5, hold 40 sessions, no stop.
Switched on 2026-11-06 at the user's request ("Yes let's switch to scanner C"): the ML score now comes from ranker C (round 58,
r58/RESULTS.md) instead of M0. The rule itself (ML >= 50% and the rest) is unchanged.

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
   Switch added 2026-11-08 at the user's request ("put this in setting to be on and off"); then the user chose two signal sets, both ON
   ("let us keep the off setting called z score and has own signals. and the option 7 is called market returned signals ... both are on"):
   the daily list shows "Z score" (the live rule) and its own "Market returned" section (option 7). daily/settings.json.
   The daily list prints the turn window every day; the terminal's Settings has its own view switch (as the list / on / off).
8. Z swing v2 (rounds 48-50, overnight 2026-11-03): option 7 (shadow turn gate) + option 1 (ML bar 0.7) + option 4 (split exit:
   half held 40 sessions, half sold when stretch Z is back at 0), 5 slots. Passed the combination test and 10 of 12 stress variants
   (costs, slippage, a day late, nearby settings). Same size as live: 2013-19 +2.4% vs +1.8% a year, max drawdown 5.4% vs 6.4%;
   2020-26 +1.5% vs +1.5%, drawdown 3.0% vs 4.4%, 89% vs 63% winners; 2023-26 ratio 0.70 vs 0.33. The gain is mostly lower risk
   (worst sell-off -0.07% vs -2.87% of the account in 2020-26), not more return. Saudi-only: the turn gate failed the US 2018-26 check.
   Round 48: 5 x 10% (instead of 5 x 5%) is the largest size with drawdown <= 15% in both periods; more, smaller slots did not help.
9. Z touch momentum filter for Z swing (round 60, r60/RESULTS.md): take a Z-swing signal only if the stock's 120-session net
   stretch-Z touches are <= -9 (more down-touches than up). Met the pre-registered rule (2020-26 +8.7% vs +6.5% per trade; sleeve
   ratio 0.24 -> 0.34 / 0.23 -> 0.26) but failed half the stress tests and the US check. NOT recommended; listed because it passed.
Saved 2026-11-07 at the user's request ("Let's back to them later. Save them."): options 1, 7 and 8 wait for the user.
   Before deciding on option 8, re-run it with ranker C (its numbers used M0). Option 1 was re-checked with ranker C in round 62:
   sleeve ratio 0.31 / 0.25 / 0.39 vs live 0.24 / 0.23 / 0.22 (2013-19 / 2020-26 / 2023-26).
10. DONE 2026-11-09 (round 66, r66/RESULTS.md, the user's choice): Z score signals most volatile first (60-day volatility) when there are
   more signals than free slots; ML rank 50%+ stays a filter. Volatility + ML blended was tested and lost to volatility alone in every
   era. Market returned keeps the ML order. Switch: daily/settings.json "zscore_order": "volatility" or "ml".
Overnight conclusion (rounds 48-53): the split exit (option 4) is the one Z-swing change that holds across markets (better in 7 of
10 market-eras: Saudi, US, India, GCC). v2's turn gate is strong in Saudi (both periods, stress-tested) but helps in only 5 of 10
market-eras elsewhere, so treat it as a Saudi-specific choice for lower risk. Size: 5 x 10% keeps drawdown under 15%.
