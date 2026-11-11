# Round 72 plan (written 2026-11-11 before any foreign result): the sell-off episode in other markets

## Why
The Saudi history holds 18 sell-offs since 2013 and they have been searched 70 times. "Confirm on 2020-26" no longer confirms much:
every idea was shaped by people (and models) who had already seen those years. Round 70 left one open offer, pacing the buys, which
was found on the whole Saudi history. This round asks the question where Saudi data played no part: the same price rule in other
stock markets, hundreds of sell-offs instead of 18. The world designs; Saudi confirms (round 73).

## Data
Yahoo daily bars, today's large caps of 23 markets (r72/world.py: India, Qatar, Dubai, Kuwait, Egypt, Turkey, China A, Taiwan, Korea,
Japan, Hong Kong, Indonesia, Brazil, South Africa, UK, Germany, France, Switzerland, Australia, Canada, Mexico, Malaysia, Thailand; Abu
Dhabi is not on Yahoo) plus the 115 US large caps the daily pipeline already downloads. Same cleaning for all (r72/wpanel.py): adjusted prices; a
stock's history before an unadjusted one-day jump above 60% is dropped; eligible = 250 sessions of history and traded on 80% of the
last 60 sessions; a market needs 10 eligible stocks. Today's large caps only: survivorship bias, as in Saudi. It lifts every variant
alike, so comparisons between variants are safer than levels.

## The rule in every market (nothing is fitted there)
Saudi's price rule with Saudi's lines: first daily close at stretch Z <= -2.62 or first weekly close <= -2.08, while market momentum
(equal-weight eligible stocks of that market) <= -1.18; buy next open, hold 40 sessions, 0.4% round-trip costs. No ML, no market model,
no accounts filter (they exist only for Saudi). One 40-session paper trade per stock at a time. Idle money earns nothing here (sleeves
are compared, not accounts). Trades from 2001.
Market-eras: 2001-09, 2010-19, 2020-26 for each market; a market-era counts if the base account took at least 10 trades in it.
Measure: return per year / worst drawdown of the account ("ratio"; nearly size-free when idle money earns nothing), plus growth and
drawdown themselves, at a total budget of 25% of the account.

## Variants (19, all reported)
- A0 base shape (as live): 5 slots x 5%, any number of buys on one day, most volatile first.
- P(S, p), 9 shapes: S slots in {5, 8, 12} at 25% / S each; at least p sessions between two buys, p in {1, 3, 5} (p = 1: one buy a day).
- B3(5, p), p in {1, 3, 5}: as P(5, p), but a buy day's 5% is split equally over that day's (up to) 3 most volatile signals.
- M(5, 0) and M(5, 3): no stock signals. A buy = 5% split over the 10 most traded eligible stocks, at the open after any close with
  market momentum <= -1.18, hold 40 sessions; 5 at once; unpaced / 3 sessions apart. (Is the stock signal worth anything over the market?)
- O-low and O-deep: A0 with the least volatile first / the deepest stretch Z first. (Is "most volatile first" general?)
- H30 and H60: A0 held 30 / 60 sessions (context for the fixed 40; not a candidate).

## Hypotheses and pass marks (fixed now)
"Beats" = higher ratio in a market-era. Share = share of counted market-eras. Sign test one-sided against 50%.
- H1 pacing (the Saudi offer): P(5, 3) beats A0 in at least 60% of market-eras with sign-test p <= 0.05. Also shown: P(5, 3)'s growth
  as a share of A0's at the same size, and its drawdown.
- Shape pick: among the 9 P shapes, the one that beats A0 in the most market-eras (tie: higher median ratio). It goes to Saudi in round 73
  together with P(5, 3). If no P shape reaches 60%, the conclusion is "pacing is not general" and round 73 tests nothing new on Saudi.
- H2 first day is the weakest: per market-era, average trade of signals on the episode's first signal day against signals 3 or more
  sessions later (both need 5 trades). Pass: later is higher in at least 60% of market-eras and the pooled difference, resampled by
  episode, is above zero in 95% of draws.
- H3 most volatile first: A0 beats O-low in at least 60% of market-eras (p <= 0.05).
- H4 stock signal against the market basket: P(5, 3) against M(5, 3), and A0 against M(5, 0). Reported, no pass mark: it tells what the edge is.
- H5 split tranche: B3(5, p) beats P(5, p) in at least 60% of market-eras for at least two of the three p.
- H6 depth: slope of the trade result on market momentum at the signal, pooled, resampled by episode. If deeper is clearly better
  (95% of draws), round 73 may test exactly one Saudi variant: double size at or below -2.53 (the list's existing "deep zone" line).
Caveats written now: market-eras are not independent (2008 and 2020 hit every market at once), so the sign tests overstate; results are
also shown by era and by region (Gulf, emerging, developed), and a claim needs the same sign in at least 2 of the 3 eras.
Saudi (price-only and live) is shown in the same table for reference and plays no part in the pick.
Detail fixed before the run: "higher ratio" is used when both variants grow in a market-era; if either loses money there, the one
with the higher growth beats (a ratio of two negative numbers can rank a bigger loss first).
