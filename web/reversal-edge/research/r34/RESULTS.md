# Round 34 results: the current Saudi strategy on US stocks (plan in PREREG.md; us34.py, us34.out)
US lines (2010-17 2% quantiles of us100): daily stretch Z -1.67, weekly -1.13 (Saudi -2.62 / -2.08). US market momentum <= -1.18 on 5-7% of days.
Rule C (daily or weekly first touch + market momentum <= -1.18, hold 40), us100:
  2010-17: 206 trades, 69% winners, +3.6% | random stocks same days +3.5% (edge +0.1) | SPY +2.4%
  2018-26: 389 trades, 76% winners, +11.8% | random +9.9% (edge +1.9) | SPY +10.0%   (2023-26: 93%, +21.1% vs random +16.8%)
  KDD17 2007-09: 37% winners, -4.3% (random -4.7%, SPY -8.0%); 2010-16: 68%, +2.5% (random +2.3%). CMIN-US 2018-21: 80%, +13.4% (random +13.5%).
Without the gate (round 30 style): us100 64-66% winners, +3.7% / +4.8%, edge vs random +0.1 / +0.8.
SPY alone on the first day market momentum crosses -1.18, hold 40: 2010-17 95% winners +5.0% (20 times), 2018-26 70% +3.7% (20),
2007-09 0% -18.5% (7 times: the 2008 crash kept going).
VERDICT: fails (2010-17 edge over random +0.1 < +1.0; CMIN-US edge -0.1). In the US the market-momentum gate is what makes money: random
stocks bought on the same days earn almost as much; picking the stretched stock adds about 0-2 points. The gate failed in 2008 - in the
Saudi strategy the market model guards against that, and there is no US market model.
