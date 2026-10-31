# Round 30 pre-registration: does the Z swing work on US stocks? (written before results)
Signal: stretch Z (same formula as Saudi) first close <= line; entry next open; exits hold 20 / hold 40 (Saudi choice) on closes, filled next open.
Lines: Saudi -2.62 and the US 2% quantile of 2010-17. Filters (no US ML ranker or market model exist): none; SPY above its 200-day average;
stock above its 200-day average; both. Costs 0.10% round trip (US large caps). Benchmark: random entries in the same stocks on the same days, same exit.
Data: 115 large US stocks 2010-2026 (survivorship: today's leaders) -> DESIGN 2010-17, CONFIRM 2018-26; KDD17 50 stocks 2007-2016 (incl. 2008);
CMIN-US 110 stocks 2018-2021. Verdict "works" if, for the variant chosen on DESIGN (highest expectancy x trades/yr with win >= 60%),
CONFIRM has win >= 60%, payoff >= 1 and beats the random benchmark by >= 1 percentage point per trade, and KDD17 is positive.
