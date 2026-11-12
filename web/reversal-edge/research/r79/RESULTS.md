# Round 79 results: thirteen ideas, 36 variants, nothing beat the swing (plan in PREREG.md)
Scripts and outputs: ideas79.py (every idea as engine switches), feat79.py, world79 (.out, .json, .csv), saudi79 (.out, .json), limit79 (.out, .json).
Saudi 2020-26 was not opened. Round 80 is not run.

## Verdict
- **No idea passed both tests** (abroad AND Saudi 2013-19). By the plan the answer is: nothing beat the swing.
- Abroad one idea passed: a calm-weather layer that buys the dip in a stock that is in an uptrend (6a, 6c). On Saudi 2013-19 it
  added 10-12 trades in 7 years, no growth, and raised the worst drawdown from 5.4% to 5.8%. Failed.
- On Saudi 2013-19 one idea passed: riding the rebound (2c, +4.0% against +3.9%). Abroad it lost in 44 of 64 market-eras. Failed.

## Every variant
Base swing abroad: median return per drawdown 0.203, growth +0.81% a year, drawdown 5.4%, 2213 trades. Base swing on Saudi 2013-19: +3.9% / 5.4%, return per drawdown 0.72, 54 trades, 83% winners, +11.1%.
"Abroad" = market-eras won / lost / unchanged against the base swing (64 counted), and the one-sided sign-test p on the planned count (wins of 64).

| idea | abroad won / lost / unchanged | p (plan) | median return per drawdown | trades abroad | Saudi 2013-19 growth / drawdown (ratio) | Saudi trades, winners, average | Saudi trades changed | passed |
|---|---|---|---|---|---|---|---|---|
| 1a storm -2.5 / deep -2.0 | 34 / 29 / 1 | 0.354 | 0.200 | 2417 | +3.2% / 9.3% (0.35) | 62, 76%, +8.0% | 78 | no |
| 1b storm -3.0 / deep -2.5 | 33 / 31 / 0 | 0.450 | 0.215 | 1647 | +3.8% / 5.4% (0.70) | 53, 79%, +10.7% | 37 | no |
| 1c storm -3.0 / deep -2.0 | 37 / 27 / 0 | 0.130 | 0.235 | 1845 | +3.1% / 9.1% (0.34) | 61, 72%, +7.3% | 113 | no |
| 2b target falls with time (+0.5 to -1.0) | 33 / 31 / 0 | 0.450 | 0.191 | 2229 | +3.5% / 5.4% (0.65) | 54, 78%, +10.1% | 0 | no |
| 2c ride the rebound (sell 0.5 under the peak stretch) | 20 / 44 / 0 | 0.999 | 0.166 | 2150 | +4.0% / 5.4% (0.75) | 54, 83%, +12.1% | 0 | Saudi |
| 2d deep buys sell at +1 | 34 / 29 / 1 | 0.266 | 0.163 | 2177 | +4.5% / 5.8% (0.79) | 52, 83%, +13.8% | 2 | no |
| 2e no sale at 0 while the market is deep | 22 / 23 / 19 | 0.734 | 0.189 | 2163 | +3.6% / 5.8% (0.63) | 52, 77%, +10.8% | 2 | no |
| 3a largest stock-specific fall first | 32 / 31 / 1 | 0.550 | 0.184 | 2221 | +3.2% / 5.1% (0.64) | 51, 78%, +9.0% | 55 | no |
| 3b smallest stock-specific fall first | 29 / 34 / 1 | 0.809 | 0.169 | 2209 | +3.0% / 6.0% (0.50) | 50, 82%, +8.9% | 62 | no |
| 3c fastest fall first | 39 / 24 / 1 | 0.052 | 0.187 | 2224 | +3.2% / 5.3% (0.60) | 51, 82%, +9.5% | 59 | no |
| 3d slowest fall first | 33 / 30 / 1 | 0.450 | 0.207 | 2218 | +3.0% / 5.1% (0.59) | 51, 80%, +8.8% | 53 | no |
| 3e rarest stretch first | 29 / 34 / 1 | 0.809 | 0.171 | 2210 | +2.8% / 5.3% (0.52) | 50, 78%, +7.8% | 68 | no |
| 4a equal risk (less in volatile stocks) | 35 / 29 / 0 | 0.266 | 0.203 | 2213 | +3.4% / 4.9% (0.69) | 54, 83%, +11.1% | 0 | no |
| 4b more in volatile stocks | 22 / 42 / 0 | 0.996 | 0.186 | 2195 | +4.5% / 6.1% (0.74) | 53, 83%, +11.1% | 1 | no |
| 4c more in the deeper stock | 27 / 37 / 0 | 0.916 | 0.206 | 2206 | +4.2% / 5.6% (0.75) | 54, 83%, +11.1% | 0 | no |
| 4d smooth market-depth size (1x to 3x) | 26 / 38 / 0 | 0.948 | 0.183 | 2162 | +4.6% / 8.0% (0.57) | 51, 82%, +10.9% | 3 | no |
| 4e half size in the first 5 sessions | 33 / 31 / 0 | 0.450 | 0.218 | 2213 | +3.8% / 5.4% (0.71) | 54, 83%, +11.1% | 0 | no |
| 5a two buys a day in deep weather | 26 / 35 / 3 | 0.948 | 0.173 | 2376 | +4.2% / 8.9% (0.47) | 66, 83%, +10.0% | 24 | no |
| 5b two buys a day when the market is turning | 26 / 14 / 24 | 0.870 | 0.196 | 2270 | +3.9% / 5.7% (0.69) | 60, 82%, +10.4% | 10 | no |
| 5c two buys on a panic day | 24 / 36 / 4 | 0.984 | 0.153 | 2376 | +4.3% / 7.5% (0.57) | 67, 82%, +10.4% | 29 | no |
| 6a calm dips: stock and market in an uptrend | 43 / 20 / 1 | 0.004 | 0.210 | 3199 | +3.9% / 5.8% (0.67) | 64, 81%, +9.3% | 14 | abroad |
| 6b calm dips: market in an uptrend | 36 / 28 / 0 | 0.191 | 0.207 | 3758 | +3.9% / 5.8% (0.67) | 66, 80%, +8.8% | 16 | no |
| 6c calm dips: stock in an uptrend | 44 / 20 / 0 | 0.002 | 0.206 | 3762 | +3.9% / 5.8% (0.68) | 66, 80%, +9.0% | 16 | abroad |
| 7a seasoned stocks only (500 sessions) | 8 / 20 / 36 | 0.998 | 0.195 | 2112 | +3.8% / 5.4% (0.70) | 52, 83%, +11.1% | 2 | no |
| 10a fast swing (10-session stretch only) | 22 / 42 / 0 | 0.996 | 0.096 | 2791 | +1.8% / 4.2% (0.42) | 39, 74%, +4.8% | 79 | no |
| 10b also sell on a sharp short bounce | 25 / 39 / 0 | 0.970 | 0.172 | 2309 | +3.3% / 5.4% (0.62) | 54, 76%, +8.8% | 0 | no |
| 10c plus fast candidates (10-session stretch -3.0) | 34 / 30 / 0 | 0.354 | 0.177 | 2595 | +3.8% / 6.3% (0.61) | 61, 80%, +9.7% | 43 | no |
| 11a no re-buy for 20 sessions | 7 / 20 / 37 | 1.000 | 0.190 | 2168 | +3.9% / 5.4% (0.72) | 54, 83%, +11.1% | 0 | no |
| 12a exposure ceiling by market depth | 10 / 10 / 44 | 1.000 | 0.206 | 2190 | +3.8% / 5.4% (0.70) | 52, 83%, +10.9% | 2 | no |
| 13a rotate out a holding at -1.0 or higher | 17 / 5 / 42 | 0.992 | 0.206 | 2250 | +3.9% / 5.4% (0.72) | 54, 83%, +11.1% | 0 | no |
| 13b rotate out a holding at -0.5 or higher | 10 / 5 / 49 | 1.000 | 0.206 | 2230 | +3.9% / 5.4% (0.72) | 54, 83%, +11.1% | 0 | no |
| 7b liquidity bar SAR 1 million | Saudi only |  |  |  | +3.9% / 5.4% (0.72) | 54, 83%, +11.1% | 0 | no |
| 7b the same with 0.8% costs (shown, not judged) | Saudi only |  |  |  | +3.8% / 5.4% (0.69) | 54, 83%, +11.1% | 0 | no |
| 8a a limit-down cross waits for a normal close | Saudi only |  |  |  | +4.5% / 6.5% (0.69) | 57, 84%, +12.3% | 37 | no |
| 8b skip limit-down crosses | Saudi only |  |  |  | +3.8% / 5.4% (0.70) | 52, 87%, +11.2% | 22 | no |
| 8c limit-down crosses first | Saudi only |  |  |  | +3.8% / 5.6% (0.67) | 52, 83%, +11.0% | 22 | no |
| 9a at most 3 positions in one industry | Saudi only |  |  |  | +3.3% / 5.4% (0.62) | 50, 80%, +10.0% | 6 | no |

Holm-adjusted p over the 31 variants run abroad: 6c 0.06, 6a 0.12, every other 1.00. So even the one pass abroad is not safe from luck.

## What each idea taught
1. **A zone that widens in deep weather**: abroad a wash. In Saudi a -2.0 line in deep weather buys too early: drawdown 9.1-9.3%.
2. **A smarter sale**: later sales earned more on Saudi 2013-19 (+4.0% to +4.5%) and less abroad (31% to 55% of market-eras). The same
   split as in round 77: Saudi 2013-19 liked long holds, the other markets and Saudi since 2020 did not. Selling at stretch Z 0 stays.
3. **Which candidate first**: none of five orders beat "most volatile first". Fastest-fall-first came nearest abroad (39 of 64, lower
   drawdown) with a lower median return per drawdown, and lost on Saudi (+3.2%).
4. **Size from the numbers**: more in volatile or deeper stocks, or a smooth 1x-3x depth size, raise growth and drawdown together
   (Saudi +4.2% to +4.6% with 5.6% to 8.0% drawdown). That is leverage, not edge. Equal-risk sizing lowers both.
5. **Two buys a day in a named state** (deep weather, market turning, panic day): more trades, drawdown 5.7% to 8.9% on Saudi. One buy a day stays.
6. **Calm-weather dips in an uptrend**: the only pass abroad (won 43-44 of 64; 45% to 70% more trades, the same growth and drawdown).
   Saudi 2013-19: 10-12 extra trades in 7 years, same growth, drawdown 5.8%, one calm trade lost 25.8%. The gates leave too few
   calm dips in Saudi for this to matter, and those few did not pay.
7. **Universe**: seasoned-only changes little and loses abroad. A SAR 1 million liquidity bar adds NO trade: the ML rank exists only
   for stocks above the 3 million bar, so the gate blocks the added names.
8. **The daily limit**: my guess was wrong. In China, Qatar and Taiwan a cross on a limit-down close was a better buy (+12.6% to
   +17.3% a trade against +7.0% to +7.5%). On Saudi 2013-19 (82 such crosses among candidates) waiting for a normal close gave
   +4.5% with a 6.5% drawdown; skipping them gave +3.8% / 5.4% and a mildest worst trade (-12.0% against -19.7%); buying them first
   gave +3.8% / 5.6%. Nothing clear enough to adopt.
9. **Sector cap** (3 an industry): lost on Saudi (+3.3%). In a sell-off the industries fall together; the cap only removes good trades.
10. **Two speeds of the stretch**: a 10-session swing is much worse (abroad 0.096 return per drawdown, Saudi +1.8%). Selling on a short
    sharp bounce cuts winners. The average of the three horizons is doing real work.
11. **No quick return to a sold stock**: rarely matters; where it did abroad it lost (7 won, 20 lost). Re-entry on a new cross stays.
12. **Money follows depth** (a lower ceiling in shallow storms): rarely binds; a wash abroad (10 won, 10 lost), slightly worse on Saudi.
13. **Rotate into the deeper stock** when the book is full: by the plan's count it failed (the book is rarely full: 42 of 64
    market-eras unchanged). Where it acted abroad it won 17 and lost 5. On Saudi 2013-19 it never acted. A lead for later, not a result:
    I did not plan the won/lost-only count, so it cannot carry a decision.

## Notes on method
- The plan counted wins out of all 64 market-eras. For ideas that seldom act, "unchanged" then counts against them. I show the
  won / lost / unchanged split so this is visible, and I did not change the pass mark after seeing the results.
- Stack step: only 6a and 6c passed abroad and 6a is 6c plus a market condition, so there was nothing to stack.
- Every idea was also run on Saudi 2013-19, including those that failed abroad (stated in addendum 1 before the run).
- Engine: `fable/swingbook.py` got optional switches. With all of them off it gives the round 78 trade list and curve exactly,
  and the day-by-day replay (replay78.py) is still exact.

## What this means
- The swing sits on a plateau: line, sale, order, pace and size were each pushed in several directions and none held up in both places.
- More trades cannot be bought with a rule change. The only real lever for more reward is position size, and it buys drawdown one for one.
- 31 variants abroad and 36 on Saudi 2013-19 were looked at. Any later claim built on these same data must count that.
