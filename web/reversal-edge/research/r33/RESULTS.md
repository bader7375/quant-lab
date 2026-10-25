# Round 33 results (plan in PREREG.md)
## A. Stretch Z on weekly and monthly candles (htf.py, htf.out)
Weekly (weeks end Thursday; same formula on weekly bars; DESIGN 2% line -2.08), live filters, hold 40 sessions:
2013-19 85% winners, +24.3% / -10.8%, +19.1% per trade (25/yr); 2020-26 86%, +11.2% (10/yr); 2020-22 91% +12.4%; 2023-26 fewer than 10 trades.
Price only: 2013-19 73% +11.7%, 2020-26 70% +5.9%, 2004-12 (library) 62% +18.4% (daily stretch Z price-only 2004-12: +3.7%). Hold 65: similar or better.
61% of weekly trades coincide with a daily Z swing (same stock within 10 sessions); the others: 2013-19 72% +10.7%, 2020-26 87% +11.2%.
=> ADOPTED as an extra Z-swing trigger (all pre-registered conditions met). Sleeve 5x5% daily+weekly (weekly_port.py): +3.3% -> +3.6%/yr,
Sharpe 0.91 -> 0.97, DD -7% -> -5%; with trend 10x5%: +7.8% -> +8.1%, Sharpe 1.14 -> 1.17. Daily list (top3.py): Z-swing picks 2020-26 71% -> 75% winners, +7.6% -> +9.1%.
Monthly (spliced library+Yahoo closes; line -1.62): 3 qualifying trades a year (12 in 2013-19, all winners; fewer than 10 in 2020-26) -> fails the
5-a-year floor; context view only.
## B1. Dividend record (fin1.py) - NOT adopted
Z swing: steady payers 2013-19 78% +14.4% vs non-payers 91% +24.2%; 2020-26 73% +6.7% vs 69% +7.1% (2023-26 75% vs 54%).
Price-only dips hold 40: steady 2013-19 +2.0% vs non-payers +6.9%; 2020-26 +2.8% vs +1.1%. The ordering flips between periods.
## B2. Yahoo annual accounts FY2022-25, entries 2023-04..2026-10 (fin2.py, descriptive)
Loss-making companies: Z swing 50% winners -0.1% (16 trades) vs profitable 72% +5.3% (36); price-only dips hold 20 35% -3.5% vs 51% +0.6%;
hold 40 37% -2.6% vs 51% +0.7%. High debt/equity (non-financial) weaker in price-only dips (hold 40: 42% -2.1% vs low 62% +2.7%); ROE and
earnings growth: no clear order. One period only -> shown as information (latest accounts per pick, loss-makers flagged), not a filter.
Full statement history (saudiexchange.sa, argaam.com) is blocked by this environment's network policy.
