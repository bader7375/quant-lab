# Round 71 plan (written 2026-11-13 before any indicator was compared with trade results): new stretch-style indicators
User: "Do a very good research loop to improve the strategy. Another indicator that help the strategy like the idea of stretch Z".
Base = the live Z score plan (plan Z): Z score signals (stretch Z touch, ML 50%+, market model > 0, market momentum <= -1.18, liquid,
profitable), paper book one trade per stock, 5 slots most volatile first, 5% each, hold 40 sessions, no stop, T-bill interest on idle money.

## The indicators (all known at the signal close; direction fixed now)
Stretch formula used below = the scanner's: average over k = 10, 20, 60 of (sum of the last k daily values) / (60-day sd of the values
measured k days earlier x sqrt k).
S1 Own stretch (idiosyncratic): the stretch formula on the stock's residual return r - beta x market (beta: 120 days, measured the day
   before; market: equal-weight liquid stocks). Higher (the fall is more the market's than the stock's own) = better.
   (Consistent with round 64, where high-beta stocks first was the runner-up order.)
S2 Sector stretch: the stretch formula on the stock's sector index (equal-weight liquid stocks of its industry, the stock itself left
   out; at least 3 others). Lower (the whole sector is stretched too) = better.
S3 Overnight share of the fall: over 20 sessions, overnight moves (open vs the previous close) / (overnight + intraday moves), when the
   20-day fall is at least 2%; opens that look missing (open = close on a day that moved) are left out. Lower (the fall came from
   selling during the session, not from overnight news gaps) = better ("tug of war", Lou, Polk & Skouras 2019).
S4 Panic: log(20-day volatility / 250-day volatility). Higher (volatility exploding versus the stock's own normal) = better.
S5 Liquidity shock: log(5-day average of |return| / value traded, over its 250-day median). Higher (prices moving on thin trading)
   = better (Nagel 2012; also in line with round 61, where heavy-volume dips did worse).
S6 Limit-down pressure (Saudi only): number of closes at -9.5% or lower in the 5 sessions up to the signal. More = worse (price limits
   delay price discovery: continuation after limit hits, Kim & Rhee 1997).
S7 Breadth washout (market level): share of liquid stocks with stretch Z <= -2 at the signal close. Higher = better.
S8 Oil stretch (market level): the stretch formula on Brent's daily returns, each US day credited to the next Saudi session. Higher
   (oil not crashing; the sell-off is not an oil-fundamentals story) = better.
Not repeated (already tested): momentum / 52-week high / trend position (round 62: weaker stocks rebound better), Connors 200-day,
Nagel market volatility, 52-week low (43), capitulation volume, Z curve, rebound memory (61), touch momentum (60), beta and
volatility orders (64-66), sell-off session age, pacing, market momentum depth (70).

## Tests
E1 trade level, Saudi, every paper trade 2013-26 with a known 40-session result (about 440): rank correlation of the signed indicator
   with the net result in 2013-19 (DESIGN) and 2020-26 (CONFIRM); pooled slope of the net result on the indicator's percentile with
   standard errors clustered by sell-off episode (signal days more than 20 sessions apart start a new episode; about 18); for the stock
   indicators S1-S6 also the correlation within episodes (stock choice, not timing).
E2 US check, the US sell-off swing trades 2005-26 (115 large caps): the same signed correlation and episode-clustered t, for S1, S3,
   S4, S5, S7, S8 (S2: no US sectors; S6: no US price limits).
E3 account, plan Z: U1 filter = buy only signals on the favourable side of the indicator's 2013-19 median (unknown values kept);
   U2 size tilt = 7.5% on the favourable side, 2.5% on the other (5% when unknown), slots and order unchanged.
   Better than live in an era = growth per year not lower, worst drawdown at most 0.2 points higher, higher return / drawdown (round 70).

## An indicator HELPS only if all hold (fixed now)
(a) E1: the expected sign in both eras and a pooled episode-clustered t of at least 2 (2.5 for the Saudi-only S2 and S6);
(b) E2: the expected sign in the US with t of at least 1 (where a US version exists);
(c) E3: its better use on 2013-19 (U1 or U2, by return / drawdown) is better than live in 2013-19 and again in 2020-26;
(d) stress on 2013-26 (return / drawdown above live under the same stress), 3 of 4: 0.8% costs; the 40th and the 60th percentile as the
    threshold; idle money earning nothing.
Honesty check: each January from 2016 choose among live and all 16 indicator uses by return / drawdown on the years before, hold one year;
2016-26 must be at least as good as live.
If 2 or more indicators help, they are combined once into one stress score (average of their signed percentile ranks) and tested by the
same rule. 8 indicators x 2 uses = 16 variants, all reported. Look-ahead check: every indicator recomputed on data cut at random past
closes must equal its full-history value. Nothing goes live without the user's yes; a helping indicator is also built as a chart tool
(terminal and TradingView).

## Addendum B (written 2026-11-13 after the main results and the S5 diagnostics, before running these variants)
Seen: no indicator passes; S5 (liquidity shock) has a strong trade-level effect (t 5.2, both eras, within episodes, positive in the US,
t 5.8 with stretch depth, volatility and ML as controls) but its filter and tilt did not help the account, because the account fills
its slots on the first day of a sell-off (low S5) and a skipped signal still blocks its stock for 40 sessions (so later, stronger
signals of the same stock are ignored). Same-day choice by S5 is weak (average same-day rank correlation +0.06).
Variants, everything else as plan Z:
B1 slot order by S5 (highest first) instead of volatility.
B2 S5 as part of the signal: a stretch Z touch counts as a signal only if S5 is at or above its 2013-19 median among the paper trades
   (unknown S5: counts); a touch without a liquidity shock starts no paper trade, so it does not block the stock.
Rule as before: better than live in 2013-19 and again in 2020-26 (growth not lower, drawdown at most 0.2 points higher, higher return /
drawdown). Stress for a confirmed variant (2013-26 return / drawdown above live under the same stress), 3 of 4: 0.8% costs; idle money
earning nothing; for B2 the 40th and the 60th percentile (for B1: S5 measured over 10 days instead of 5, and against a 120-day median
instead of 250). US check for B2: the US sell-off swing with the same signal-level filter (threshold = the US 2005-17 median), 5 slots,
default order: return / drawdown better than without it in at least 2 of the 3 US eras (2005-09, 2010-17, 2018-26).
Honesty check: yearly re-choice among live, B1, B2 (2016-26) at least as good as live. Nothing goes live without the user's yes.
