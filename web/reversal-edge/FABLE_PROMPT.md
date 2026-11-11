# Reversal Edge — the Fable edition

You're taking over my Saudi stock research project, and I want your own version of it: the Fable edition. Use all your creativity and your own vision. Question everything: the strategy, the portfolio, how risk is handled, how the daily decision is shown to me. Surprise me. The one thing you may not bend is the honesty of the evidence. I would rather hear "nothing beat the current rule" than see a beautiful backtest that fails with real money.

## Me
- I trade Saudi stocks (Tadawul: Sunday to Thursday, 10:00–15:00 Riyadh, ±10% daily limit). My priority: high reward with low risk.
- Every morning by 07:00 Riyadh I read a daily list. During the day I use a terminal (a Claude artifact) on my phone. I want it visually perfect, and I like creative tools (Z bands and Z touch momentum came from asking for them).
- Talk to me in short, plain sentences, with tables and before/after numbers by period. End with clear yes/no decisions.
- I decide what goes live. Nothing I trade changes without my yes.

## What exists: read before you design
Repo bader7375/quant-lab, branch claude/nice-gates-8aa4yb (not merged to main; base your work on it). Everything is under web/reversal-edge/:
- research/PENDING.md: what is live, what is offered, what was retired. Start here.
- research/daily/README.md: the daily pipeline and its change log.
- research/daily/planbook.py: the live rule replayed exactly. It is the single source for the list, the export and the tests; following it day by day reproduces the tested trades.
- research/daily/top3.py (the list), research/r27/final27.py (the export the terminal reads), research/daily/run.sh (the daily run), research/daily/bootstrap.sh (rebuilds the work folder from Yahoo).
- research/rNN/PREREG.md and RESULTS.md for rounds 27–70. Read rounds 64–70 first.
- The live terminal: https://claude.ai/artifact/HQMRJpu3hpLyj7ahSxSQDn (read it with the Artifact tool; in the repo it is src/index.html v24 plus research/v25 to v32/patch_vNN.py). Its database document ml/latest holds the daily export.
- TradingView Pine scripts: pine/.
- The list also has a US part (SPY/QQQ dip rule, US sell-off swing, US market leaders).

## The live strategy (plan Z) and its verified numbers
Stretch Z of a stock = the average of z10, z20 and z60, where z_k = the sum of its last k daily log returns ÷ (its 60-day volatility measured before those k days × √k).
Buy at the next open after the first close at Z ≤ −2.62 (or the first weekly close ≤ −2.08; weeks end Thursday) if all of these hold:
- ML rank ≥ 50% (ranker C: LightGBM, refit every quarter, walk-forward);
- market model > 0 (a 20-day market forecast, refit every January);
- market momentum ≤ −1.18;
- liquid (at least SAR 3m traded a day);
- latest annual result not a loss.

Sizing: 5% per position, at most 5, most volatile first, hold 40 sessions, no stop. Idle money sits in a SAR money-market fund.

Whole account, idle money at T-bill interest:
- 2013–19: +3.2% a year, worst drawdown 6.1%.
- 2020–26: +4.9% a year, worst drawdown 4.9%.
- 69 trades in 14 years: 71% winners, +9.0% per trade, worst −21.6%.

## What 70 rounds taught us (don't repeat these without a new angle)
- Most of the edge is timing (buying broad fear in sell-offs), not stock choice. There are only 18 sell-off episodes since 2013: small samples, easy to overfit.
- The account is mostly cash (stocks average about 4% of it at 5% positions), so the cash yield is a big part of the return.
- The account buys most trades on the first day of a sell-off, which has the weakest signals. Then its 5 slots stay full for 40 sessions, while later signals did better (round 70).
- Spacing buys at least 3 sessions apart cut the worst drawdown from 6.1% to 3.8% at the same growth. I haven't decided on it yet.
- Dead ends:
  - stop losses of every kind (rounds 39, 63, 69);
  - entering on a bounce or a first green candle (42, 63);
  - split exits, or selling when Z is back at 0 (41, 43, 70);
  - a higher ML bar (70);
  - financial quality (59);
  - meta-labeling (62);
  - Z curve, rebound memory, capitulation volume (61);
  - a Z touch-momentum filter (60);
  - 14 classic TASI bottom signals (47);
  - GP rule search, a CNN chart reader, an online meta-allocator (46);
  - calendar effects (45);
  - more, smaller positions (69);
  - a US direction model for options (44).
- Kept:
  - the volatility-first slot order (64–66);
  - ranker C (58).
- The market-turn window ("Market returned", plan A, rounds 47–49 and 67–69) is strong in Saudi. But it failed in the US and rests on about 53 trades.
- Second engines for the idle money (trend breakouts, ML leaders) add return but bring 17–25% drawdowns and losing years (67).
- Data:
  - Yahoo only: daily and hourly prices, dividends, annual accounts from FY2022.
  - The exchange's own site and MarketScreener block automated access. Don't try to get around that.
  - The price panel holds only stocks listed today (survivorship bias).

## Your freedom: the Fable part
Be ambitious. A few directions, not orders; drop them if you see further:
- Make the sell-off episode the unit of decision: how much to deploy in this episode, spread over which days, and at what depth.
- Put the idle cash to work without adding much risk: sizing by episode depth, a market basket instead of single names, a barbell.
- Grow the evidence: other markets, hourly bars for entry timing, bootstraps over episodes, shrinkage instead of point estimates.
- Show honest uncertainty: a range on every headline number, and a forward scorecard of live picks against what the backtest expected.
- A terminal that tells the day's story at a glance on a phone: market weather, the plan book, an episode timeline, what-if sizing, "why this stock".
- Or show that a simpler version is better. If the evidence says so, that counts as a win.

## Non-negotiables
1. Evidence:
   - Write PREREG.md before running anything you will judge.
   - DESIGN 2013–19, CONFIRM 2020–26, plus a check on 2023–26.
   - Report every variant, failures included.
   - Stress tests: 0.8% costs, a day late, neighbouring settings, idle money earning nothing.
   - A yearly walk-forward re-choice as the honesty check, and a second market where possible.
   - Signals at the close, trades at the next open, 0.4% round-trip costs.
   - No look-ahead; prove it with truncation tests.
2. Replayable: following your daily output day by day must reproduce your tested trades, as planbook.py does.
3. Never invent prices, picks or results. If data is missing, say so.
4. Don't touch the live system without my yes. That means:
   - daily/settings.json;
   - the live terminal and its ml/latest;
   - the three scheduled tasks (lists at 06:42 and 16:41 Riyadh, data update at 15:48).

   Build alongside it:
   - research rounds as research/r71 onward;
   - your product under web/reversal-edge/fable/;
   - your terminal as a new artifact. A new artifact can't read the old one's database, so propose how yours gets its daily data, and ask me before changing any scheduled task.
5. Plain words. Any technical term gets a one-line meaning.

## Start
1. Get a work folder. If one from earlier sessions is in your scratchpad (daily/, r27/, edge26/), reuse it. Otherwise rebuild it with sh web/reversal-edge/research/daily/bootstrap.sh <your scratchpad folder>; this takes about 35 minutes and downloads the Yahoo history.
2. Reproduce the live numbers above with planbook.py before changing anything. If you can't, find out why first.
3. Write VISION.md (one page): what you think the edge really is, what you will build, and your 3–5 bets ranked by expected value and by overfitting risk. Show it to me, then carry on unless I object.
4. Run your research rounds. Then build the Fable edition: the rule (if anything passes), the daily list, the terminal, and a Pine script if useful.
5. Commit and push as you go. Finish with a short report: a before/after table by period with ranges, what's ready to switch on, and one clear yes/no question for me.
