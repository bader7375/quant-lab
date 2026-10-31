# Round 45: portfolio-level ideas from the quant literature (pre-registered 2026-10-31, before any result)
User: "run whatever you want and tell me". Saudi panel 2013-2026; DESIGN 2013-19, CONFIRM 2020-26.

## 1. Idle money (Faber 2007; Moskowitz-Ooi-Pedersen 2012; Carver) - port45.py
The Z swing (5 x 5%, hold 40, live rule) is invested only part of the time. Alternatives for the rest of the money, each held with
the Z swing taking priority (core weight = 1 - Z exposure): (a) cash (T-bill rate), (b) the equal-weight liquid Saudi market,
(c) the market only while its equal-weight index is above its 200-day average (Faber), (d) the market only while its 12-month
return is positive (time-series momentum), (e) Core v2 (ML ranking + trend breakouts, round 27). Costs 0.20% per side on turnover.
Measures: CAGR, Sharpe, maximum drawdown per era. A home for idle money is recommended if, in BOTH eras, the combination
(i) has a higher CAGR than the Z swing alone, (ii) a higher Sharpe than the same core without the Z swing, and (iii) a maximum
drawdown no more than 5 points worse than that core alone. Among those, the highest DESIGN Sharpe.
## 2. Adaptive exit (bandit) - adapt45.py
For every Z-swing signal both exits are computed (hold 40; sell at the next open after stretch Z closes >= 0, at most 60 sessions).
At each entry the rule uses the exit whose last N completed outcomes (exited before that day) had the higher average return
(N = 20; N = 40 as a check; hold 40 until 10 outcomes exist). Compared on the 5 x 5% sleeve with hold 40, Z exit and the 50/50
split. Adopted if its ratio return / drawdown beats the split's in BOTH eras with return >= 90% of the split's.
## 3. Kelly sizing (Thorp) - port45.py
Scale k of the 5 x 5% sleeve (position = 5% x k, total at most 100%) that maximises the DESIGN log growth of the account; reported
in CONFIRM at k*/4, k*/2, k* vs k = 1 (growth, CAGR, maximum drawdown). Advice, not a rule change.
## 4. Saudi calendar (Bialkowski-Etebari-Wisniewski 2012 and others) - cal45.py
Umm al-Qura calendar (hijridate). Equal-weight liquid market daily return inside vs outside: Ramadan; the 5 sessions before each
Eid holiday; the first 9 days of Dhu al-Hijjah; turn of the month (last session + first 3 sessions). An effect counts if it has the
same sign and |t| >= 2 in BOTH eras.
## 5. Overfitting audit (Bailey & Lopez de Prado; Harvey-Liu-Zhu) - audit45.py
Deflated Sharpe ratio of the live Z sleeve 2013-26 with N = 200 trials (variants tried since round 28) and the variance of
Sharpe across the variants of rounds 41-43. Rank correlation of DESIGN vs CONFIRM ratios across the variants of rounds 39-43
(does doing well in 2013-19 predict 2020-26?), and the share of families whose DESIGN pick fell below the CONFIRM median.
