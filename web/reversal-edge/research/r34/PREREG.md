# Round 34 pre-registration: the current Saudi strategy on US stocks (written 2026-10-25, before running anything below)
Known beforehand (disclosed): round 30 - US Z swing without the newer filters won 64-67% of trades but matched random entries in the same
stocks; round 31 - the market-momentum split was checked on US broad dips (first stretch Z <= -2.0, hold 20): dips with the market falling did
much better (us100 +10.4% vs +0.5%). So the US data has been seen for that split, not for the rules below.

Data: us100 (115 large caps, 2010-2026, survivorship-biased: today's leaders), KDD17 (50 stocks 2007-16), CMIN-US (~110 stocks 2018-21).
Eras as in round 30: US DESIGN 2010-17, US CHECK 2018-26. Costs 0.10% round trip. Signal at the close, entry next open.
What transfers: stretch Z (daily and weekly), market momentum (each set's own equal-weight market, same formula, gate -1.18). There is no US
ML rank or market model, so those two filters are absent.
Lines: daily US line = 2010-17 2% quantile of us100 stretch Z (round 30: -1.68); weekly US line = 2010-17 2% quantile of us100 weekly
stretch Z (weeks ending Friday).
Rules (hold 40 sessions, no stop): A daily first touch + market momentum <= -1.18; B weekly first touch + market momentum <= -1.18; C = A or B.
Benchmarks on the SAME signal days and hold: (i) random stocks from the same set (20 draws per trade, averaged); (ii) SPY.
Plus "market timing alone": SPY bought on the first day market momentum crosses to <= -1.18, hold 40.
The strategy "works on US stocks" only if, for C on us100, in BOTH 2010-17 and 2018-26: win rate >= 60%, edge over random stocks >= +1.0 point
per trade, and edge over SPY >= 0; and on KDD17 and CMIN-US the edge over random is >= 0. Otherwise the answer is: in the US the gain comes
from buying after market sell-offs, not from picking the stretched stock.
