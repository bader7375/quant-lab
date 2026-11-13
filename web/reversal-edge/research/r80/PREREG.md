# Round 80 plan: Rebound Odds, an indicator for taking the trade (written 2026-11-13, before any run)

## What the user asked for
One task: a very advanced indicator that helps with taking the trade, in the family of the stretch Z.

## What I will build
**Rebound Odds**: for a stretched stock, the chance (0 to 100) that a buy at the next open ends in profit, read from what
happened after the same kind of situation in other markets. With it come three numbers and one picture from the same cases:
the typical gain, the typical dip on the way, the typical number of sessions, and a cone (where such cases stood 1 to 40
sessions later). The stretch Z says how far a stock has fallen. Rebound Odds says what usually followed.

Words:
- **case**: a liquid stock on a day its stretch Z closed at -1.5 or lower.
- **the trade**: buy at the next open; sell at the open after the first close with stretch Z at 0 or higher, or after 40
  sessions (the swing's sale). Net of 0.4% costs. **win** = net result above 0. **dip** = the lowest close against the buy price.
- **odds**: the model's chance of a win. **odds band**: cases grouped by their odds (ten groups of equal size in the fitting data).

## How it is made (fixed now)
1. **Fit on other markets only.** 23 foreign markets and 117 US large caps (the round 72 panel). No Saudi case enters any fit.
2. **Two frozen copies.** M19: fitted on cases whose trade ended by 2019-12-31; every test below uses M19. Mlive: the same
   recipe refitted on all cases to date; the product uses it. I report how far the two differ.
3. **The formula** is a logistic regression (odds = 1 / (1 + exp(-score)), score = a weighted sum), so it can be written in
   TradingView. Every market weighs the same in the fit.
4. **Base inputs**: stretch Z, market momentum, and their product.
5. **Candidate extra inputs**, all from the daily open, high, low, close of the stock and the market average, known at the close:
   relative volatility (log of the stock's 60-session volatility over the market average's); zone age (sessions since the stretch
   first closed at -1.5 or lower in this run, capped at 30, log); market momentum's change over 5 sessions; sell-off age (sessions
   since the buy window opened, capped at 60, log); overnight stretch (the part of the 10-session move made between a close and
   the next open, in the same units as the stretch); fall from the 250-session high (in units of yearly volatility); residual
   stretch (the 20-session move the market does not explain); speed (10-session stretch minus 60-session stretch); range
   expansion (log of the average daily range of the last 5 sessions over the last 60); close position (where in the day's range
   the last 3 closes sat, 0 = the low, 1 = the high); crash days (sessions in the last 5 that closed 9.5% or more down);
   stretch Z squared; market momentum squared.
6. **Choosing the extras**: forward steps, on M19's data only. At each step the candidate that most lowers the average
   out-of-market error (log loss, each market scored by a model fitted on the other 23) is added, if it lowers it in at least 17
   of the 24 markets and by at least 0.0005. At most 5 extras.
7. **Ceiling check**: a boosted-tree model with every input, scored the same out-of-market way. If the formula gets less than
   80% of the trees' gain over a no-skill forecast, I say so and report both; the product still uses the formula (it must run on a chart).
8. **Companion tables** (gain, dip, sessions, cone) are averages and quantiles of the other markets' cases by odds band.
9. **Saudi adjustment**: fitted on Saudi 2013-19 only: saudi score = a + b x score, plus c for a stock that passes the live gates
   (ML rank 50%+, market model positive, not loss-making). c is kept only if its 5%-95% range from resampling months excludes 0.

## The tests and the wall
- **Step 1, abroad**: out-of-market scores (each market by the model of the other 23), M19 data.
- **Step 2, Saudi 2013-19**: M19 scores. No Saudi data is in M19, so this is a test, and the Saudi adjustment is fitted here.
- **Step 3, Saudi 2020-26, opened once**, after steps 1-2 and after the formula, tables and adjustment are frozen and committed.
  If step 2 fails, step 3 is not run.

## Pass marks (each on Saudi 2013-19, then on 2020-26; ranges resample months, 5th percentile)
1. **It separates.** Cases in the top third of odds made more than cases in the bottom third (average net result), 5th percentile above 0.
2. **It beats what you already have.** Its rank correlation with the net result is above that of the stretch Z alone AND of
   market momentum alone, each difference with a 5th percentile above 0.
3. **It is honest about its number** (2020-26 only, after the Saudi adjustment): in every odds band with 100 or more cases the
   share of wins is within 10 points of the stated odds.
Words for the verdict: **USEFUL** = 1, 2 and 3 pass. **DESCRIPTIVE** = 1 passes, 2 fails (it restates weather and stretch as a
chance; still shown, labelled so). **NOT VALID** = 1 fails: not shipped.

## Reported without a pass mark
- Inside the swing's own trades and candidates (first closes at -2.5 or lower in storm or deep weather with the gates): do higher
  odds go with better results? Round 62 (meta-labeling) was a dead end, and I expect little here. Rebound Odds is NOT a filter for
  the swing's signals and I will not test it as one in this round.
- Calm weather: what odds it gives stretched stocks there, and what happened.
- By market abroad, by year, and the 2023-26 check on Saudi.

## Honesty rules that apply
Signals at the close, the buy at the next open, 0.4% costs. No look-ahead: features use data up to that close; a cut-data check
recomputes the odds at 30 past closes from data cut there. Overlapping cases move together, so every range resamples whole months.
Saudi 2020-26 has been opened in rounds 73 and 78; a third look is worth less. Today's stocks only.

## Amendment 1 (2026-11-13, after step 1 abroad, before any Saudi run)
What step 1 showed on the other markets (trades ended by 2019; select80.out, and two scratch looks, explore80.py):
- **The chance of a win hardly moves.** Across tenths of the win formula it runs from 65% to 77% (AUC 0.54). Boosted trees with
  every input did WORSE than a no-skill forecast out-of-market. And the win formula ranks results worse than market momentum
  alone (rank correlation 0.145 against 0.203). A "chance of a win" indicator would say little.
- **The size of the result does move.** A formula for the expected net result from stretch Z, market momentum and their product
  cuts the out-of-market error by 2.4% (better in 20 of 23 markets), ranks results better than market momentum alone (0.222
  against 0.205) and is honest by tenths (stated -0.2% to +7.5%, realized +0.6% to +8.9%).
- **No extra input holds up.** 19 candidates (stock: volatility, zone age, overnight share, fall from the high, residual, speed,
  range, close position, crash days; market: its own 10- and 20-session stretch, its fall from the high, breadth, volatility
  expansion, co-movement, momentum change, sell-off age; squares). Three lower the squared error a hair in 17-18 markets and
  LOWER the rank correlation. Boosted trees are worse than the three-input formula (1.6% against 2.4-2.6%).
So the indicator changes, before Saudi is touched:
1. **Name and headline: Rebound Edge** = the expected net result of the trade, in %. The chance of a win becomes a companion.
2. **Formula**: linear, inputs stretch Z, market momentum, their product; fitted on the net result clipped at the 1st and 99th
   percentile of the fitting cases; every market weighs the same. An extra input would be added only if it lowered the
   out-of-market squared error in 17 markets AND raised the rank correlation; none does, so there are none.
3. **Companions in units of the stock's own volatility**: the dip and the cone are stored by edge band as multiples of the
   stock's 20-session normal swing (60-session daily volatility x sqrt(20)), and turned into % with each stock's own volatility.
   Win share and sessions come from the band.
4. **Saudi adjustment**: saudi edge = a + b x edge + c for a stock that passes the live gates; fitted on Saudi 2013-19 only
   (clipped net result); c kept only if its 5%-95% range excludes 0.
5. **Pass marks** 1 and 2 stand as written (they were already about the net result). Mark 3 becomes, on 2020-26 after the Saudi
   adjustment: (a) the realized average result rises from the bottom to the middle to the top third of stated edge;
   (b) the share of wins in every edge band with 100 or more cases is within 10 points of the band's stated share;
   (c) the worst dip was deeper than the stated "bad dip" (the 1-in-10 dip) in 5% to 20% of cases.
The ceiling check (item 7) is answered: the trees do not beat the formula. Everything else in the plan stands.

## Amendment 2 (2026-11-13, after the Saudi 2013-19 step, before 2020-26 is opened)
What Saudi 2013-19 showed (saudi80_design.out, first run):
- Mark 1 passes with M19 (no Saudi data in it): top third of edge +7.7% a trade, bottom third -3.7%.
- **Mark 2 fails** with M19: its lead over stretch Z alone (+0.077) and over market momentum alone (+0.041) is positive, but both
  5th percentiles are below zero (-0.023, -0.008). So the chart formula can be at best DESCRIPTIVE. That stands whatever follows.
- The Saudi adjustment: saudi edge = -5.1% + 1.44 x edge, +4.0% for a stock that passes the live gates (range +0.4% to +6.9%: kept).
- The companion tables of the other markets do not fit Saudi's weak states: in the lowest band Saudi won 51% of the time where
  the table says 66%, and the dip was deeper than the "1-in-10 dip" in 32% of cases. In the strong bands they fit.
Two things are therefore fixed now, before 2020-26 is opened:
1. **Saudi companion tables.** Win share, sessions, dip and cone for Saudi come from Saudi cases grouped in ten bands of the
   Saudi-adjusted edge, each pulled toward the other markets' band with the same edge (weight 300 cases, as for the edge map).
   For the tests they are built from cases whose trade ended by 2019-12-31. Mark 3 is tested against these tables.
2. **A second, clearly separate verdict for the terminal version** (Saudi-adjusted edge, which knows the gates). On 2013-19 it is
   fitted, so only 2020-26 can test it: marks 1 and 2 with the adjusted edge, and mark 3. If all pass it is called
   **USEFUL IN THE TERMINAL (one test period)**; else it carries the chart formula's word. The chart formula's verdict follows
   the plan unchanged.
After the confirm step the product's Saudi adjustment and tables are refitted by the same recipe on all Saudi cases to date
(as M19 becomes the live copy). The report shows the tested and the refitted numbers side by side.
