def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:100], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)
patch("app7.js", [
 ('''Signals cluster in sell-offs, so keep it small and separate: added to the Core it raised return by about 1.3% a year but deepened the worst drawdown by about 4 points.''',
  '''Signals cluster in sell-offs, so keep it small and separate: added to the Core it raised return by about 1.3% a year but deepened the worst drawdown by about 4 points.<br>
 <b>Z swing + momentum (round 29, the low-drawdown way to run the Z swing):</b> pair it with the trend-breakout sleeve at half size (10 slots × 5%). The two are nearly uncorrelated (daily correlation +0.11): the Z swing buys fear after sell-offs, trend breakouts ride uptrends and their trailing stops keep them out of crashes. 2013–2026: <b>+8.4% a year, Sharpe 1.14, worst drawdown −12%</b> (2013–19 Sharpe 1.03, 2020–26 1.24), against Z swing alone Sharpe 0.82 and putting the same money into more Z swing Sharpe 0.54 (drawdown −26%). Core v2 still earns more (+15.8%, Sharpe 1.20) with a deeper drawdown (−19%).'''),
])
patch("app6.js", [('''- STRETCH Z (round 27):''', '''- ROUND 29 (momentum to help the Z swing; pre-registered): momentum FILTERS hurt (dips only in 12-1 winners: 59% winners 2020-26; near 52-week high: 45-54%; dips in stocks above SMA200 or in rising sectors almost never reach the extreme line). Momentum EXITS were not adopted: a fade exit (after 20 sessions, first close below the 10-day average) was better in 2020-26 (74% winners, +6.9%, half the hold) but worse in 2013-19; handing winners to a trailing stop or extending to 60 sessions raised profit per trade but lowered profit per day. Momentum SLEEVES: 12-1 momentum, 52-week-high and the ML sleeve move with the Z swing (daily correlation +0.51..+0.65); trend breakouts do not (+0.11). Z swing 5x5% + trend breakouts 10x5%: +8.4%/yr, Sharpe 1.14, DD -12% (2013-19 1.03, 2020-26 1.24) vs Z swing alone 0.82 and Z swing at 3x size 0.54 (DD -26%).
- STRETCH Z (round 27):''')])
s = open("app5.js").read(); a = '<h2>v16 (round 28): a high-win-rate Saudi swing signal — Z swing</h2>'; assert s.count(a) == 1
sec = '''<h2>v17 (round 29): momentum to help the Z swing</h2>
<p>Three ways momentum could help, written down before testing and chosen on 2013–19: as a <b>filter</b> on Z-swing entries, as an <b>exit</b>, or as a separate <b>sleeve</b> that earns when the Z swing is idle.</p>
<table class="t"><tr><th style="text-align:left">idea</th><th>2013–19</th><th>2020–26</th><th>verdict</th></tr>
<tr><td style="text-align:left">filter: only dips in 12-month winners</td><td>77% winners, +15.0%</td><td>59% winners, +4.1%</td><td class="down">hurts</td></tr>
<tr><td style="text-align:left">filter: dip within 10% of the 52-week high</td><td>45%, +1.6%</td><td>54%, +3.2%</td><td class="down">hurts</td></tr>
<tr><td style="text-align:left">exit: after 20 sessions, sell on the first close below the 10-day average</td><td>69%, +9.4% (21 days)</td><td>74%, +6.9% (23 days)</td><td>not adopted (worse 2013–19); watch</td></tr>
<tr><td style="text-align:left">exit: at session 40 hand winners to a 3-ATR trailing stop</td><td>71%, +17.2% (70 days)</td><td>61%, +6.0%</td><td class="down">less profit per day</td></tr>
<tr><td style="text-align:left"><b>sleeve: trend breakouts at half size next to the Z swing</b></td><td>Sharpe 1.03, DD −12%</td><td>Sharpe 1.24, DD −12%</td><td class="up"><b>adopted</b></td></tr></table>
<p>Why the trend sleeve: 12-month momentum, 52-week-high and ML portfolios all move with the Z swing (daily correlation +0.51 to +0.65: they are long the same market), while trend breakouts barely do (+0.11). The Z swing buys after sell-offs; trend breakouts buy in uptrends and their trailing stops step aside in sell-offs. Together (Z swing 5 × 5% + trend breakouts 10 × 5%): <b>+8.4% a year, Sharpe 1.14, worst drawdown −12%</b>; the Z swing alone has Sharpe 0.82, and the same money put into more Z swing gives Sharpe 0.54 with a −26% drawdown. Worst years of the pair: 2022 −1%, 2024 −2% (market −22% in 2022 and 2025). Core v2 (ML + trend) still earns more (+15.8%, Sharpe 1.20, −19%).</p>
'''
open("app5.js", "w").write(s.replace(a, sec + a))
b = open("body.html").read(); x = '<span>reversal edge v16 · Saudi Core v2 · Z swing</span>'; assert b.count(x) == 1
open("body.html", "w").write(b.replace(x, '<span>reversal edge v17 · Saudi Core v2 · Z swing + momentum</span>'))
print("ok")
