# Round 69 results: a stop loss for plan A (plan in PREREG.md; r69.py, chk69.py, r69b.py, r69c.py and their .out files)

## Verdict: no stop improves plan A. Nothing changes in the live rule.
36 stops were tested on the plan account (51 trades), on every signal inside a turn window (298 trades) and on every paper trade (442).
- By the pre-registered rule no stop is "good": none met all three conditions even in 2013-19 (growth kept, drawdown not worse, and on
  the 298 signals the average trade kept with a better worst-5% trade).
- Honesty check: a yearly re-choice from the menu (it picked the 4-ATR trailing stop every year) made 2016-26 +8.7% a year with a 7.8%
  drawdown, against +8.6% and 6.3% without a stop: worse.
- Insurance rule: among the 13 stops that cost at most 0.2 points of growth, the best "worst trade" on the 298 signals is -20.4%
  (15% stop order) against -21.6% without a stop, and that stop raises the 2013-19 drawdown from 9.8% to 13.2%. No stop in the menu cuts
  the worst trade by more than about one point, so none is recommended as insurance either.

## Selected rows (account growth per year / worst drawdown; trades taken; average and worst-5% trade on the 298 signals)
| stop | 2013-19 | 2020-26 | trades, winners | 298 signals: average, worst 5% | stopped |
|---|---|---|---|---|---|
| none | +6.8% / 9.8% | +6.3% / 6.3% | 51, 78% | +17.4%, -9.9% | - |
| 10% on close | +7.3% / 13.9% | +5.8% / 6.9% | 69, 61% | +12.7%, -15.6% | 27% |
| 15% on close | +6.9% / 10.9% | +6.6% / 6.8% | 58, 78% | +14.6%, -18.0% | 14% |
| 20% on close | +7.0% / 9.8% | +6.6% / 6.8% | 53, 79% | +16.4%, -17.4% | 5% |
| 25% on close | +6.8% / 9.8% | +6.3% / 6.3% | 51, 78% | +16.9%, -11.6% | 3% |
| 10% stop order | +5.9% / 14.2% | +6.0% / 6.9% | 80, 55% | +8.1%, -12.0% | 42% |
| 15% stop order | +6.6% / 13.2% | +6.1% / 6.9% | 64, 69% | +13.7%, -15.4% | 18% |
| 4 ATR on close | +7.6% / 9.8% | +6.3% / 6.3% | 54, 80% | +15.6%, -18.1% | 10% |
| under the 10-day low, 3% room | +6.1% / 13.9% | +5.7% / 6.3% | 103, 53% | +5.8%, -12.5% | 58% |
| time stop, session 20, below -5% | +6.6% / 9.8% | +6.0% / 6.3% | 54, 74% | +14.7%, -11.3% | 16% |
| market below its 20-day low | +4.3% / 17.7% | +3.5% / 7.2% | 139, 46% | +2.5%, -12.5% | 74% |
| breakeven after +10% | +6.7% / 9.8% | +6.3% / 6.3% | 53, 77% | +14.2%, -9.5% | 15% |
| trailing 4 ATR | +8.0% / 10.0% | +6.3% / 6.3% | 58, 76% | +14.6%, -16.7% | 17% |
(all 36 rows and the per-era tables: r69.out)

## Why stops fail here
- Plan A buys the retest: at 78% of its signals the market index closes within 1% of its own 20-session low (the first bounce has
  failed and stocks are falling again). Lower prices right after the entry are the normal case, not the failure.
- How far trades fall before they end (no stop): the median plan trade closes 6.4% below its entry at some point; a tenth close more
  than 16.6% below. Of the trades that were 10% or more under water, 56-59% still ended as winners (average final result +3.9% /
  +4.8%); a 10% stop turns them into about -11%. Even trades that closed 25% under water ended at -7.3% on average when held, against
  about -28% when sold at the next open (8 cases among the 298 signals; the stock opens lower after such a close).
- A stop order does not cap the loss: with a 15% stop the worst exits were at -18% to -20%, because the open was already below the stop.
- The stops that looked good on the account (trailing 4 ATR, 4 ATR, 20% order) gained from re-buying: the freed slot took another
  signal of the same sell-off. With the freed slot left empty (r69b.py, exploratory) every stop is worse than no stop: 4 ATR
  +6.2% / 11.8% in 2013-19, trailing 4 ATR +5.1% / 14.4%, 15% on close +5.4% / 13.2%, against +6.8% / 9.8%.
- The plan account's worst periods without a stop: -9.8% (8 days in December 2014, back at the high 13 days later), -9.6% (October
  2015 to January 2016, 268 days to recover), -6.3% (March 2020, 10 days to recover). No stop in the menu made either of the two
  worst periods shallower by more than a point without making the other one deeper.
Caveat: the data holds only stocks that still trade today, so it cannot show a stock that never comes back; that is the one case
where a stop would help, and its size cannot be measured here. The plan's protection against it is the position size (10%), the
5-slot cap (at most 50% in stocks), the liquidity floor and the loss filter.

## Addendum A: more, smaller positions (r69c.py): not better
| positions | 2013-19 | 2020-26 | 2013-26 | trades |
|---|---|---|---|---|
| 5 x 10% (plan A) | +6.8% / 9.8% | +6.3% / 6.3% | +6.5% / 9.8% | 51 |
| 8 x 6.25% | +5.5% / 13.0% | +6.5% / 5.9% | +6.0% / 13.0% | 78 |
| 10 x 5% | +4.6% / 13.5% | +6.1% / 5.9% | +5.4% / 13.5% | 92 |
| 15 x 3.33% | +4.8% / 11.0% | +5.7% / 6.9% | +5.2% / 11.0% | 122 |
| 20 x 2.5% | +4.7% / 10.2% | +5.5% / 5.1% | +5.1% / 10.2% | 148 |
No variant is better by the rule in either era; the yearly re-choice picks 5 x 10% from 2017 on. Plan A's sizes stay.
