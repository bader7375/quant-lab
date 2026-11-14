# Round 72 plan (written 2026-11-13 before any result): the user's four momentum helpers for the Saudi stretch-Z swing
Specified by the user (message of 2026-11-13); this file freezes it before running. No change to engine.js or daily/settings.json.

## Strategy under test
First daily close at or below stretch Z -2.62, buy at the next open, hold 40 sessions (sell at the open 40 sessions after entry),
0.40% round-trip cost, liquid stocks (60-day median traded value >= SAR 3m and at least 120 bars of history), Cement excluded
(industry codes 3000-3099), one trade per stock at a time (a touch while that stock's trade is open is not a new event).
Traded value = volume x raw (unadjusted) close (round 71 found the dividend-adjusted value carries a mild look-ahead).
Market momentum ms = the live definition (equal-weight market of liquid stocks, 60-day log return / (daily sd before those 60 days x
sqrt 60)); the market index keeps Cement (Cement is excluded from trading only).

## Eras
Era 1 (untouched early history) 2004-2012 Tadawul 193-stock library: NOT AVAILABLE. The library (a Kaggle file) is not in the repo and
was lost with the machine reset of 2026-10-27; Yahoo's Saudi history starts 2010-03-03. A stand-in is reported instead:
Early 2011-2012 (Yahoo, same panel; first 120-250 bars are warm-up). It is NOT Era 1: anything that needs Era 1 stays provisional
until the library is restored. Era 2 Design 2013-2019; Era 3 2020-2026 with and without the FY2022+ profitable-company filter.
US check: 115 large caps, 2010-2017 and 2018-2026 (same definitions; stretch Z computed the same way on US prices; no traded-value floor
(all large caps); 0.40% round trip; US market momentum from the equal-weight US universe; Yahoo sectors for H3).

## Indicators (point in time at the signal close t)
H1 pulseAcc[t] = M[t] - M[t-3], M = the terminal's Momentum Pulse (engine.js pulseCalc): EMA (alpha 0.5) of the mean over h = 5, 10, 20,
   60 of ln(C[t]/C[t-h]) / (sigma[t] x sqrt h), sigma = Yang-Zhang 20-day daily volatility (engine.js volSuite yz(20), sample variances).
   Filter: pulseAcc < -0.5. Variant H1b: the stretch Z's 10-day component z10[t] <= -2.8.
H2 preMom[t] = ln(C[t-60]/C[t-250]) / (sd60[t-60] x sqrt 190) (sd60 = sd of daily log returns over the 60 days ending t-60) and
   Z250[t] = (ln C[t] - 250-day mean of ln C) / 250-day sd of ln C. Filter: preMom > 0 and Z250 > -2.5.
H3 secZ[t] = mean stretch Z at t of the other liquid stocks of the same industry group (at least 3 others). Filter: secZ <= -1.0;
   variant <= -1.2; contrast row: secZ > -0.5 (the hypothesis says these lose money).
H4 RSI(14)[t] <= 25 (Wilder, as engine.js wilderRSI) and volz[t] > 1.0 (today's log volume vs the mean and sd of the 60 sessions before).
   Entry comparison within 10 sessions after t: immediate (open t+1) vs (a) the open after the first close above the previous day's high,
   (b) the open after the first day the stretch Z rises (zc[k] > zc[k-1]); no trigger in 10 sessions = no trade. Done for the H4 set and
   for the set named in the hypothesis (RSI(14) <= 25 and pulseAcc < -0.5).
Combined: ms <= -1.18 + secZ <= -1.0 + pulseAcc < -0.5 + preMom > 0, with and without ML rank >= 50% (ML exists from 2013).
Capitulation Score = -pulseAcc + preMom (used only as a slot order).

## Event tables (each era, and the US)
Rows: unfiltered (Z <= -2.62), ms <= -1.18 baseline, H1, H1b, H2, H3, H3b, H3 calm contrast, H4, combined, combined + ML; each H inside
ms <= -1.18. Columns: n, win %, average 40-session net %, median %, 5th percentile (P05) %, overlap-adjusted t of the difference kept vs
the rest of the unfiltered set and kept vs the rest of the ms set (regression on a kept dummy, standard errors clustered by 40-session
blocks of the signal date, since trades starting in the same block share most of their holding period).

## 5 x 5% sleeves (T-bill interest on idle money, 0.20% per side, Z first and Core v2 in the remaining room when paired)
2013-19, 2020-26 and 2013-26 on the live rule's signals (daily or weekly touch, ML >= 50%, market model > 0, ms <= -1.18, liquid,
profitable, Cement excluded): V0 ordered by 60-day volatility (live); V1 ordered by the Capitulation Score; VF = V0 + H1 + H2 + H3;
each single filter added to V0; V0 and VF with a 6-ATR close-confirmed catastrophe stop and with a -25% close-confirmed stop, both with
a 40-session cooldown (the stopped slot stays in cash until the trade's 40 sessions would have ended); all standalone and with Core v2.
Reference row: the live rule exactly as traded today (adjusted value, Cement included). Early 2011-12 stand-in: the price-only rule
(Z touch + ms + liquid, Cement excluded) and its H1+H2+H3 version. Reported: growth per year, worst drawdown, Sharpe, Calmar.

## Acceptance rule (the user's, frozen)
A filter is adopted only if all hold:
(1) inside the ms <= -1.18 baseline it raises BOTH the win rate and the average net 40-session return in Era 1 (2004-2012) AND Era 2;
(2) it holds up out of sample in Era 3: win rate and average net return not below the ms baseline's, with and without the profitable
    filter;
(3) added to the live rule, the 5 x 5% sleeve has a higher Sharpe AND a higher Calmar AND a worst drawdown no deeper than V0's, in
    2013-19 and in 2020-26.
Because Era 1 is unavailable, no filter can be adopted in this round; a filter meeting (2), (3) and condition (1) on Era 2 (and on the
2011-12 stand-in) is reported as "provisional, needs Era 1". Slot orders and stops are not filters: they are judged by (3) alone.
Prior evidence, written down before running: round 61 found sudden shocks (z10 far below z60) rebound worse (H1 related); rounds 29 and
62 found weaker stocks rebound better (H2 related); round 71's sector stretch had no effect (H3 related); round 61 found heavy-volume dips
rebound worse and round 63 that waiting for a bounce costs return (H4 related).
