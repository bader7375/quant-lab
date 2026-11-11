# Round 71 plan (written 2026-11-11, before any result): reproduce the live rule, put honest ranges on it, ask if a simpler rule is as good

First round of the Fable edition. Nothing here changes what is traded.

## 1. Reproduce (no judgement, just a check)
- Rebuild the work folder from Yahoo (bootstrap.sh) and rerun the live account with `daily/planbook.py`.
- Expected (round 70): 2013-19 +3.2% a year, worst drawdown 6.1%; 2020-26 +4.9%, 4.9%; 69 trades, 71% winners, +9.0% per trade, worst -21.6%.
- If the numbers differ, find out why before anything else (Yahoo re-adjusts old prices when dividends are paid; the panel has one more day).
- `fable/engine.py` (a generic copy of the engine, so other markets can use the same code) must give the same signals, paper trades,
  taken trades and account curve as planbook on the Saudi panel. Any difference is a bug to fix before round 72.

## 2. No look-ahead (truncation tests)
- Cut the price panel at 40 random past closes. Rebuild stretch Z, weekly Z, market momentum, volatility, the liquid flag and the
  signals from the cut data. Every value at the cut must equal the full-history value.
- Rebuild the ranker's input features (feats27.build) on data cut at 5 past closes and compare the last row with the full build.
- Read the training cut-offs of the ranker and the market model from the code and state them.

## 3. Honest ranges (the method is fixed here and used in every later round)
- Episode = one market sell-off: sessions with market momentum at or below -1.18, joined when the gap between two such sessions is
  20 sessions or less. An episode's block = from its first session to the session before the next episode starts (so the block
  carries the quiet time after it, when the account earns interest).
- Bootstrap: draw whole blocks with replacement until the history is as long as the real one; 2,000 draws; the same draws for every
  rule being compared. Report the 5th to 95th percentile ("range") of growth per year and of the worst drawdown, and for a comparison
  the share of draws in which rule A beats rule B.
- Reported for the live rule over 2013-26 and for each era. With 7 to 10 episodes per era the era ranges will be wide; that is the point.
- Second view, per trade: the average trade with a range from resampling episodes (not trades: trades of one sell-off move together).

## 4. Simplicity test: does every gate earn its place?
The live rule has five gates on top of the Z touch. Each is switched off alone, and all three model/accounts gates together:
- S1 no ML rank bar; S2 no market model; S3 no loss filter; S4 no weekly signals (daily touches only); S5 no daily signals (weekly only);
- S6 "price only": no ML, no market model, no loss filter (Z touch + market momentum + liquid). This is the rule a chart script can compute.
Same account as live: 5 slots x 5%, most volatile first, hold 40, 0.4% costs, T-bill interest on idle money.

Rule (fixed now): a gate is "not earning its place" if the account without it is at least as good as live in 2013-19 AND in 2020-26 AND
in 2023-26: growth per year not lower than live by more than 0.1 point, worst drawdown not higher by more than 0.2 point; and the same
holds over 2013-26 with 0.8% costs. Only then would I propose to drop it (simpler is better). Anything else: the gate stays.
The market-momentum gate and the liquid filter are not tested (rounds 31 and 27; without them the rule is a different strategy).
Every variant is reported with its bootstrap range, failures included.

## 5. Not judged in this round
The anatomy of the 18 sell-offs (how the account's money was spent inside each) is described for the record; it was already seen in
round 70 and is the starting point of round 72, where the question goes to other markets first.
