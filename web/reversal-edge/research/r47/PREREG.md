# Round 47: TASI reversal (pre-registered 2026-11-03, before any result of this round)
User request: "another round focusing on TASI reversal; read books, every source available".

Question: can we tell, at the close, that a TASI sell-off is ending (washout) or has turned (confirmation)? Does that improve:
- what we already do (the Z swing, which buys stretched stocks inside sell-off windows), or
- a plain "buy the market at the turn" trade?

## Data (mk47.py, mk47us.py)
- **Index:** Yahoo has no TASI history (today's value only); stooq, Argaam and the Saudi Exchange site are blocked or denied. TASI is therefore proxied by an equal-weight index of the liquid Saudi stocks: eligible, 60-day median value traded at least SAR 3m, about 100-200 stocks.
  - Weekly-return correlation with the cap-weighted MSCI Saudi ETF (KSA), 2016-26: 0.71 equal-weight, 0.76 liquidity-weighted.
  - The equal-weight basket is what our strategies trade, so it is the main series.
- **Breadth** (all measured on liquid stocks):
  - share of advancers;
  - share of value traded in advancers (Lowry's 90% days use volume);
  - shares below the 20-, 50- and 200-day averages;
  - shares at a 20-day or 52-week low;
  - share with stretch Z at or below -2.
- **Index measures:** RSI(2), stretch Z, drawdown from the 1-year high, Williams VIX Fix, value traded vs its 1-year median, 5-day return in units of its 1-year spread.
- **Outside the market:** US VIX and Brent, each the last close before the Saudi close.
- **Data-gap days:** 54 days where bars exist for under 60% of the usual stocks (Yahoo gaps, e.g. Feb-Mar 2015) get no measures.
- **US replication:** the same measures on the US 100 large caps. The trade is SPY from the next open, and VIX is same-day.

## Signals (each fixed from its source; none tuned)
An episode is the first day a signal is true after at least 20 sessions without it.

Washout family (W): "the fall is extreme"
- W1 Lowry 90% down day: at least 90% of value traded is in declining stocks.
- W2 Breadth washout (Vialoux, under 14% of stocks above their 200-day average): share below the 200-day average at least 86%.
- W3 New-low spike (Sentimentrader / Advisor Perspectives, over 35% at 52-week lows): share at a 52-week low at least 35%.
- W4 Index stretch: index stretch Z at or below -2.62 (our stock line applied to the index).
- W5 Index RSI(2) below 5 (Connors & Alvarez).
- W6 Williams VIX Fix spike: WVF (22-day high close vs close) above its 20-day mean + 2 standard deviations (Williams / Moody).
- W7 High-volume decline (Campbell, Grossman & Wang 1993: index falls on high volume reverse):
  - 5-day index return at most -2 x its trailing 1-year spread; and
  - 5-day value traded at least 1.5 x its 1-year median.
- W8 Global fear (Nagel 2012; AllianceBernstein): US VIX at least 30.

Turn family (T): "buyers are back"
- T1 Desmond (2002 Dow Award): a 90% up day (at least 90% of value in advancers) within 10 sessions after a 90% down day.
- T2 Zweig breadth thrust: the 10-day EMA of advancers/(advancers+decliners) goes from below 0.40 to above 0.615 within 10 sessions.
- T3 Zweig 4% rule, daily version:
  - the index closes at least 4% above its lowest close of the last 20 sessions; and
  - within those 20 sessions it was at least 10% below its 1-year high.
- T4 Fear retreat: US VIX at least 25 at some point in the last 10 sessions, and now at most 0.8 x its 10-day high.
- T5 Oil turn: Brent's 10-day return at least +10% while Brent is at most 0.8 x its 1-year high.
- T6 Desmond's alternative: two consecutive days with at least 80% of value in advancers.

## Step 1: does the signal precede a better market? (t47.py)
Return measured: the equal-weight liquid basket bought at the next open, over 20 sessions (10 and 40 also reported).

Two comparisons:
- **A:** vs the average of all days in the same era.
- **B:** vs the average of all sell-off-window days (market momentum <= -1.18, the window the Z swing already trades in). This asks whether the signal adds anything to what the live rule already knows.

Periods: DESIGN is Saudi 2012-19 (1-year measures start in 2012). CONFIRM is Saudi 2020-26. The US 2005-26 is the independent replication; its eras 2005-09, 2010-17 and 2018-26 are reported.

A signal SURVIVES only if all three hold:
1. **DESIGN:** at least 8 episodes, excess A > 0 with t >= 2.0 across episodes, and excess B > 0.
2. **CONFIRM:** excess A > 0 and excess B > 0.
3. **US 2005-26:** excess A > 0 with t >= 2.0 and excess B > 0.

With 14 signals, about one false pass on DESIGN is expected by luck; the CONFIRM and US requirements are the guard.

## Step 2: use, only for survivors (the highest DESIGN t in each family, at most one W and one T)
Comparisons use the live Z swing sleeve: 5 x 5%, hold 40, DESIGN 2013-19 (the ML filter starts in 2013), CONFIRM 2020-26.
- **2a Gate:** take a Z-swing signal only if the survivor fired in the last 10 sessions (including today).
- **2b Delayed entry** (T family only): Z-swing signals from the last 10 sessions are bought at the next open after the survivor fires, if the stock's stretch Z is still at or below -1.
- 2a or 2b is adopted (as a candidate offered to the user) only if, in both DESIGN and CONFIRM, the sleeve ratio (return per year / max drawdown) is higher than the live rule's and the return is at least 90% of it.
- **2c Turn trade:**
  - On each survivor episode, put 25% of the account in the liquid equal-weight basket for 40 sessions.
  - Simulated next to the Z swing (two sleeves).
  - Adopted as a candidate only if Z + turn has a higher return AND a higher ratio than Z alone in both DESIGN and CONFIRM.

If nothing survives Step 1, Step 2 is not run, and the round reports what the TASI proxy says about reversals.

## Addendum B (pre-registered 2026-11-03 after Step 1, before this test) - g47.py
Step 1 result: no signal survived; the best TASI timer found is the sell-off window the live rule already uses. Over the next 20
sessions, a window day averaged +4.0% (2012-19) and +1.9% (2020-26), against +0.6% / +0.5% for all days.

Question: inside the window, does the market's state at the Z-swing signal tell a better entry?

Gates on the live Z swing (5 x 5%, hold 40), measured at the signal close:
- G1 deep window: market momentum <= -2.53.
- G2 momentum turning: market momentum at least 0.5 above its lowest value of the last 10 sessions.
- G3 breadth turning: the 10-day EMA of advancers / (advancers + decliners) at least 0.50.
- G4 turn confirmed: the Zweig breadth thrust (T2) or the 4%-off-the-low rule (T3) was true in the last 20 sessions.

Each gate's complement (the trades it removes) is reported too.

A gate is adopted as a candidate (offered to the user, not switched on) only if all three hold:
1. **DESIGN 2013-19:** sleeve ratio higher than the live rule's, with return at least 90% of it.
2. **CONFIRM 2020-26:** the same.
3. **US sell-off swing:** the gated trades' average return is higher than all trades' average in both 2010-17 and 2018-26.

Exploratory, cannot adopt: the near-miss T2 (Zweig thrust) as a turn trade. On each episode, 25% of the account goes into the liquid basket for 40 sessions, next to the Z swing.

## Addendum C (pre-registered 2026-11-03 after addendum B, before these checks) - c47.py
G4 passed addendum B's bar, but it was designed after Step 1 had shown T2 and T3. These checks decide whether G4 is offered as robust or as fragile.
- C1 Lookback: in the last 10, 30 or 40 sessions instead of 20. G4 is "fragile" if the ratio gain over the live rule disappears for 2 of the 3 lookbacks in either era.
- C2 T2 alone and T3 alone, lookback 20 (reported).
- C3 Luck test: 2,000 random subsets of the live trades, each the size of the G4 set, per era. The p-value is the share of random subsets whose per-trade average (and whose sleeve ratio) is at least G4's. G4 is "fragile" if either p-value is above 0.10 in either era.
- C4 Sell-off by sell-off: trades are grouped by the sell-off window spell they came from. Count the spells where after-the-turn trades beat before-the-turn trades (spells with both kinds only).
- C5 Wait for the turn (delayed entry):
  - A Z-swing signal without G4 waits up to 20 sessions.
  - It is bought at the next open after the first day G4 is on, if the stock's stretch Z is still at or below -1.
  - Signals already under G4 are bought as usual.
  - C5 is preferred over the plain G4 gate only if its sleeve ratio is higher than G4's in DESIGN and CONFIRM, with return at least 90% of G4's.
- C6 Size: G4 and the live rule at 10% positions (round 45), reported.
