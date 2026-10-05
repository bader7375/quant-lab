// ------------------------------------------------ Research tab
$("research").innerHTML=`
<h2 style="font-size:18px">How this system was built, and what the evidence says (v13)</h2>
<p>I tested the main short-term reversal ideas from academic papers and trading books on real daily prices: 87 large US stocks (2012–2017, Yahoo prices from the StockNet dataset), Tesla (2010–2026) and the VIX (1990–2026). Every number below is out of sample. Either the model was trained only on earlier years, or it was trained on the 87 stocks and then tested on Tesla, a stock it had never seen. Costs of 10 basis points per round trip are included.</p>
<h2>v13: 193 Tadawul stocks, 2002–2020</h2>
<p><b>Data:</b> the Tadawul file (199 stocks; 193 with 300+ days), 2001-12-31 to 2020-03-05. Prices are already adjusted for corporate actions as of 2020.</p>
<ul><li>Removed: 1,165 zero-price rows, 2 spike glitches, and flat no-trade rows.</li>
<li>Al Rajhi and Aramco were used to design the v12 rule, so every decision test below uses the other 191 stocks.</li>
<li>Only companies still listed in 2020 are included (survivorship).</li></ul>
<p><b>The v12 Saudi rule passed on fresh stocks</b> (test written down first):</p>
<table class="t"><tr><th>191 stocks, real engine</th><th>momentum mode</th><th>dip-buy mode</th><th>auto</th><th>buy &amp; hold</th></tr>
<tr><td>mean Sharpe</td><td><b>0.31</b></td><td>−0.04</td><td>0.16</td><td>0.22</td></tr><tr><td>stocks with Sharpe &gt; 0</td><td>72%</td><td>40%</td><td></td><td></td></tr></table>
<ul><li>Momentum beat dip-buying on 75% of stocks, in every sector (Materials 90%, Consumer Staples 94%, Financials 76%) and every liquidity group.</li>
<li>Momentum entries beat random days by <b>+0.42%</b> (2002–07), <b>+0.20%</b> (2008–13) and <b>+0.17%</b> (2014–20) per trade, all significant. The edge is shrinking as the market matures.</li></ul>
<p><b>Behaviour:</b></p>
<ul><li>89–94% of stocks trend day to day in every period. The effect is strongest in the most liquid names.</li>
<li><b>Limit-up close:</b> the next morning opens +2.6% to +3.4% higher, then fades 0.5–1.3% by the close. Buying that open loses; holders can sell into it.</li>
<li><b>Limit-down close:</b> the next morning opens 2.3–3.8% lower.</li>
<li><b>Gap-down opens</b> (&lt; −2%) rebounded about +1% open-to-close in every liquidity group and both periods (t 12–18). Gap-up opens faded −0.7% after 2013. Daily data can't prove these open prices were fillable, so it's shown as a day-trade idea only.</li>
<li><b>Weekly momentum:</b> last week's top fifth beat last week's bottom fifth by +0.30% the next week (t 2.4). One-month to one-year rankings showed nothing.</li>
<li><b>Lead-lag:</b> after TASI rises more than 1%, the average stock gains +0.28% the next day (t 4.2). Big caps lead small caps.</li>
<li><b>Calendar:</b> the day before a long holiday averaged +0.51% (t 3.3, n 39). Ramadan showed no reliable effect for the average stock. The earlier Ramadan finding came from three large names only, so it's withdrawn.</li></ul>
<p><b>Tested and not adopted</b> (each had to help in both halves and on the post-2020 Al Rajhi, Aramco and TASI data):</p>
<ul><li>Momentum only in a TASI uptrend: helped before 2013, hurt after.</li>
<li>Skipping signals on more than 2× normal volume: helped in both halves (+0.1 Sharpe) but hurt Al Rajhi and Aramco after 2020.</li>
<li>Selling at the next open after a limit-up close.</li>
<li>Pullback-turn entries: better on only 42% and 49% of stocks.</li></ul>
<p><b>Built in:</b> all 193 stocks are in the Data tab library. The "Update data with Claude" button starts a Claude Code session on your account that downloads newer prices and writes them into the terminal. Older history is rescaled automatically for bonus shares and splits.</p>
<h2>v12: the Saudi market</h2>
<p><b>Data:</b> Al Rajhi Bank (1120, 2013–2026), Saudi Aramco (2222, Dec 2019 – Dec 2025) and the TASI index (2001–2026). The Al Rajhi file contained 17 corrupt rows from an unadjusted feed (prices about 2.46× too high, no volume), mostly in 2013. Aramco had 35 flat holiday rows. The importer now drops such rows and reads volumes written as "5.05M".</p>
<p><b>Character:</b> Saudi stocks trend from one day to the next, the opposite of US stocks.</p>
<table class="t"><tr><th></th><th>lag-1 autocorrelation</th><th>CAGR</th><th>max drawdown</th></tr>
<tr><td>Al Rajhi</td><td>+0.03 to +0.14 by period</td><td>10.3%</td><td>−45%</td></tr><tr><td>Aramco</td><td>+0.07 / +0.17</td><td>1.1%</td><td>−29%</td></tr><tr><td>TASI</td><td>+0.03 to +0.14</td><td>6.0%</td><td>−80%</td></tr></table>
<p><b>Dip-buying has little or no edge here.</b> After RSI(2) &lt; 10, the next 5 and 10 days were normal (t ≈ 0) on all three. The engine's dip trades made Sharpe 0.14 on Al Rajhi and 0.03 on Aramco.</p>
<p><b>Momentum works.</b> Buying the open after RSI(2) &gt; 90 and selling on a close below the 5-day average, compared with random days:</p>
<ul><li><b>Al Rajhi:</b> +0.49% per trade (2013–19) and +0.56% (2020–26). As a system: Sharpe 0.94, 11.0% a year, max drawdown −13%, vs buy &amp; hold 0.56, 10.5%, −45%.</li>
<li><b>TASI:</b> +0.81%, +0.29%, +0.27% per trade across periods.</li>
<li><b>Aramco:</b> +0.16%, not significant. As a system: Sharpe 0.36 vs buy &amp; hold 0.12.</li></ul>
<p>The default "auto" mode missed this: Saudi stocks' autocorrelation (about +0.06) sits just under the 0.08 switch. So v12 runs Saudi symbols in momentum mode (Settings → Saudi stocks).</p>
<p><b>Calendar:</b></p>
<ul><li><b>Ramadan:</b> +0.13% to +0.17% a day vs about 0 in other months, on all three (t 1.5–2.1). Shown as a note, not a rule.</li>
<li><b>Weekdays:</b> Sunday weak and Tuesday strong, but none is reliable (|t| ≤ 2).</li></ul>
<p><b>Shorts:</b> too few signals to judge, and retail short selling in Saudi is restricted.</p>
<p><b>Limits:</b> this is two stocks. Upload 20–30 Saudi stocks to confirm that momentum mode suits the market broadly. Your Aramco file ends on 2025-12-31.</p>
<h2>v11: short trades (optional, off by default)</h2>
<p><b>The rule.</b> Sell an overbought bounce: RSI(2) above 90 with a top-third short score, only while the stock is below its 200-day average. When you choose a market file, the market must also be below its 200-day average. The order is a limit sell 0.5 ATR above the close, valid for the next session. Cover on the first close below the previous day's low or after the max hold. Every short has a 3-ATR stop and uses half a slot.</p>
<p><b>What the tests found</b> (written down before testing, same protocol as v9):</p>
<table class="t"><tr><th>short rule</th><th>6 long histories, test Sharpe</th><th>87 stocks Sharpe</th><th>verdict</th></tr>
<tr><td>Plain mirror (sell RSI(2) &gt; 90)</td><td>−0.30</td><td>−0.91</td><td>loses; a squeeze blew up a test account</td></tr>
<tr><td>Only below the 200-day average</td><td>−0.13</td><td>−0.45</td><td>loses</td></tr>
<tr><td>Only when the Pulse is negative</td><td>−0.04</td><td>−0.74</td><td>loses</td></tr>
<tr><td>Below 200-day + 3-ATR stop</td><td>−0.14</td><td>−0.38</td><td>loses</td></tr>
<tr><td>+ market below its 200-day average</td><td>−0.08</td><td>−0.67</td><td>loses in bull periods</td></tr></table>
<p>On fresh stocks, shorts paid only in bear markets: +1.1% per short on 2007–2012 stocks (2008 inside), and +3.8% on 18 shorts in the 2020 crash with the market filter. China lost (−6.9% on 5 shorts).</p>
<p>Inside the full long + short book (half size, stop, downtrend only), Sharpe changed by −0.06 to +0.07. That's roughly nothing in normal markets and a small help in crashes.</p>
<p><b>Hedging instead</b> (short the index while long trades are open) lowered Sharpe on all four data sets, because much of the dip-buy profit comes from the market bouncing too.</p>
<p><b>Use shorts as a bear-market tool.</b> Turn them on when your market file is below its 200-day average, keep the stop, and keep them small. Short losses are open-ended.</p>
<p><b>Bug fixed in v11.</b> When a held stock did not trade on a given day (TASI vs US holidays), its value was miscounted while sizing a new trade. Long trades were capped by cash so the effect was small: the 6-market Sharpe went 0.77 → 0.76, drawdown −15.0% → −14.5%. All single-market and same-calendar results are unchanged.</p>
<h2>v9: whole-system stress test</h2>
<p><b>Method.</b> I tested the full engine, the same code that runs in this page, on two kinds of data:</p>
<ul><li><b>Development data:</b> your 6 long histories (before 2013 = design, 2013+ = test) and the 87 StockNet stocks.</li>
<li><b>Lockbox:</b> 432 stocks the system had never seen, run once after the changes were frozen. These were KDD17 (47 US stocks, 2007–2012/16), CMIN-US (106 US large caps, 2018–2021) and CMIN-CN (279 China CSI 300 stocks, 2018–2021, with T+1 and 10bp costs).</li></ul>
<p>I wrote the candidate list and the acceptance rule before running them. A change had to improve Sharpe in the design period, the test period, the 6-market portfolio and the 87-stock portfolio. It also could not worsen drawdown by more than 20%, and had to win on at least 4 of 6 markets.</p>
<p><b>Is the edge real?</b> I replaced the signals with random entry days at the same frequency, keeping the same exits:</p>
<ul><li>The real system beat all 20 random runs on the long histories (Sharpe 0.53 vs 0.28 average), on the 87 stocks (1.23 vs 0.72) and on KDD17 (0.45 vs −0.09).</li>
<li>Per reversal trade on US stocks, the edge over random entries was:</li></ul>
<table class="t"><tr><th>period</th><th>real</th><th>random</th><th>edge per trade</th></tr>
<tr><td>1990–2007</td><td>+3.01%</td><td>+0.45%</td><td>+2.56% ± 0.86</td></tr><tr><td>2008–2012</td><td>+1.28%</td><td>+0.54%</td><td>+0.74% ± 0.62</td></tr>
<tr><td>2013–2017</td><td>+1.16%</td><td>+0.33%</td><td>+0.82% ± 0.26</td></tr><tr><td>2018–2021</td><td>+1.06%</td><td>+0.59%</td><td>+0.47% ± 0.43</td></tr><tr><td>2022–2026</td><td>+2.28%</td><td>+0.37%</td><td>+1.90% ± 1.29</td></tr></table>
<p>The edge is real in every period but smaller since 2008. In the 2018–2021 US bull market, random entries made twice as many trades and so a higher portfolio Sharpe. In China the reversal signal had <b>no edge</b> over random (0.73% vs 0.81% per trade), so do not use it there without more testing.</p>
<p><b>Robustness of v8</b> (plateaus, not spikes, are what you want):</p>
<ul><li>RSI(2) trigger 5–20, limit depth 0–1 ATR, max hold 10–20 and the exit rule all gave similar results. Nothing hinges on one exact value.</li>
<li>Price stops hurt in every test.</li>
<li>Costs matter. At 5 / 10 / 20bp per side, the 87-stock Sharpe was 1.23 / 1.02 / 0.59. Use limit orders and liquid stocks.</li></ul>
<table class="t"><tr><th>candidate</th><th>development result</th><th>decision</th></tr>
<tr><td>Fixed research weights (no per-stock refit)</td><td>better on all 6 markets, both periods, both portfolios</td><td><b>adopted</b></td></tr>
<tr><td>Refit with n0 = 1000</td><td>passed, but fixed weights are simpler and as good</td><td>not needed</td></tr>
<tr><td>Exit on RSI(2) &gt; 70</td><td>passed alone; no gain on top of fixed weights. Lockbox: mixed.</td><td>kept as an option</td></tr>
<tr><td>Exit at the next open</td><td>higher Sharpe, but 6-market drawdown −16% → −22%. Lockbox: worse on US 2018–21 and China.</td><td>rejected</td></tr>
<tr><td>Momentum only if autocorrelation is significant</td><td>worse in the test period</td><td>rejected</td></tr>
<tr><td>Inverse-volatility position size</td><td>lower drawdowns, slightly lower Sharpe on single markets</td><td>rejected</td></tr>
<tr><td>Limit order valid 2 days</td><td>worse on 4 of 4 measures</td><td>rejected</td></tr></table>
<p><b>Lockbox</b> (10-slot portfolios, never seen before; v8 → v9, with equal-weight buy &amp; hold):</p>
<ul><li>KDD17: Sharpe 0.45 → 0.45, drawdown −14.8% → −13.0% (buy &amp; hold 0.27, −46%)</li>
<li>CMIN-US: 0.65 → 0.67 (buy &amp; hold 1.19)</li>
<li>CMIN-CN: 0.66 → 0.72 (buy &amp; hold 1.69)</li></ul>
<p>v9 met the rule, but the gain is small. The honest expectation for a diversified portfolio on new data is a <b>Sharpe of about 0.45–0.7</b> (KDD17 95% interval 0.09–0.90), not the 1.3 seen on the 87 development stocks. Those 87 trained the score weights, so they flatter it. The fresh sets are today's big companies looked at backwards (survivorship bias), which flatters buy &amp; hold, and the period matters.</p>
<p><b>Your six markets, v8 → v9 Sharpe (all years):</b> AAPL 0.71 → 0.87, AMZN 0.58 → 0.64, F 0.34 → 0.45, MSFT 0.53 → 0.54, TASI 0.63 → 0.71, TSLA 0.37 → 0.40.</p>
<p><b>Bug fixed in v9.</b> In a portfolio mixing TASI with US stocks, a limit order was dropped when the next calendar day was a US-only trading day. Fixing it raised the 6-market Sharpe from 0.63 to 0.72.</p>
<p><b>What the tests say about the options:</b></p>
<ul><li><b>Others half size</b> lowered drawdowns on every data set with the same or better Sharpe: fresh portfolios −13%/−21%/−17% → −9%/−14%/−13%, single stocks about −30%. Total return is lower. It's the best choice if drawdowns bother you.</li>
<li><b>Reversal only</b> beat "auto" on all three fresh stock sets (KDD17 0.45 → 0.56). Momentum mode helps index-like markets such as TASI and F, but on individual stocks its trades lost money.</li>
<li><b>Idle cash in an index fund</b> roughly doubles return (CMIN-US 9.5% → 25.6% a year), but drawdowns become index-sized (−21% → −39%). That's more money, not better risk-adjusted money.</li>
<li><b>More slots</b> (more stocks at once) give a smoother ride and lower drawdowns, but each trade is smaller.</li></ul>
<h2>v8: the A+ grade</h2>
<p><b>Definition.</b> An A+ setup is a top-third reversal setup that also closed in the bottom 13% of the day's range (internal bar strength ≤ 0.13) <i>and</i> has a Momentum Pulse below −0.5σ. The two thresholds are the medians of the setups before 2013. Both conditions were chosen from 14 candidates because they held in both periods. A 200-day-average filter, VIX change, volatility of volatility and longer trends did not.</p>
<p><b>Per trade it is clearly better.</b> In the engine's own backtest, A+ trades averaged roughly twice the return of the other top-third trades on every long history:</p>
<table class="t"><tr><th></th><th>A+</th><th>other top-third</th></tr>
<tr><td>TSLA</td><td>+5.3% (8 trades, 88% won)</td><td>+2.6% (33, 76%)</td></tr><tr><td>MSFT</td><td>+2.4% (33, 76%)</td><td>+1.6% (93, 72%)</td></tr>
<tr><td>AMZN</td><td>+6.7% (15, 93%)</td><td>+2.6% (55, 76%)</td></tr><tr><td>AAPL</td><td>+3.3% (16, 75%)</td><td>+1.7% (29, 72%)</td></tr>
<tr><td>F</td><td>+2.3% (45, 67%)</td><td>+0.8% (115, 71%)</td></tr><tr><td>TASI</td><td>+1.6% (8, 75%)</td><td>−1.1% (20, 50%)</td></tr></table>
<p><b>But as a filter it makes less money.</b> The other top-third trades are still profitable, so skipping them halves total return. On the 6-market portfolio, "A+ only" made +428% (Sharpe 0.58) against +952% (Sharpe 0.63). <b>Putting the two signs into the score did not help either.</b> A refit with 11 signs scored slightly worse out of sample than the current 9 weights, so the score is unchanged.</p>
<p><b>How to use it: position size</b> (Settings → position size):</p>
<ul><li><b>A+ double size:</b> on the 6-market portfolio, total +952% → +1,521% and CAGR 4.3% → 5.1%, with the same Sharpe (0.63) and a deeper max drawdown (−16.5% → −18.9%). This is more money, not better risk-adjusted money.</li>
<li><b>Others half size:</b> on single markets, Sharpe stays the same or improves on all six (TSLA 0.37 → 0.43, TASI 0.63 → 0.67) and drawdowns shrink sharply (F −54% → −31%, TSLA −34% → −17%, TASI −18% → −9%). Total return is lower.</li>
<li>A+ setups are taken first when several stocks signal on the same day.</li></ul>
<h2>Momentum Pulse (the pane under the chart)</h2>
<p>The pulse measures momentum over 5, 10, 20 and 60 days. Each one is the return divided by the move this stock's own volatility would normally produce over that period (Yang-Zhang, 20 days), so +2σ means "a big move for this stock". The thick line is their smoothed average. The ribbon spans the four horizons: teal or red when all four agree, violet when they disagree, and brighter when the path was straight (Kaufman efficiency ratio). Bars show acceleration (the line now vs 3 days ago). The dotted amber lines are this stock's own 5% and 95% momentum levels over the last two years. Amber glowing dots mark exhaustion (momentum at a 2-year extreme and turning), triangles mark thrusts (crossing ±1σ with all horizons agreeing), and dashed violet lines mark divergences on both panes (price makes a new low or high that momentum does not confirm).</p>
<p><b>What I tested, and what I found.</b> The design sample was the six long series before 2013; the test was 2013 onward plus the 87 stocks. The results contradict some trading folklore, so the advice follows the evidence:</p>
<ul>
<li><b>"Avoid mean reversion in a downtrend" is false on stocks.</b> Reversal setups taken while the pulse showed a strong down-trend did <i>better</i>: +1.70% per trade in the test against +1.09% in no-trend conditions (design: +2.11% vs +1.61%). A strong, straight decline into an oversold close is capitulation. The pulse calls it that and does not warn you off.</li>
<li><b>What really says "avoid mean reversion" is the market's character.</b> When a market keeps moving the same way from day to day (500-day autocorrelation above 0.08, as TASI does), dip-buying fails and the system switches to momentum. The pulse shows "AVOID MEAN REVERSION" there.</li>
<li><b>Chasing strength on a reverting stock is bad.</b> After a strong up-trend state, the next 10 days were 0.31% below the stock's average (t = −2.4).</li>
<li><b>Momentum entries work in momentum markets, not single US stocks.</b> On TASI, the up-trend state was +1.44% over 10 days before 2013 (t = 2.3) but only +0.07% after. That is weak, so treat it as a tilt, not a signal.</li>
<li><b>Exhaustion, thrusts and divergences had no reliable edge</b> (|t| &lt; 1 in both samples). They are shown because they describe what is happening, and the inspector shows how each one worked on the loaded stock. The engine never trades on them.</li>
</ul>
<h2>What works</h2>
<p><b>1. A short-term oversold trigger with a quick exit.</b> Buy when the 2-day RSI closes below 10 (Connors &amp; Alvarez). Sell on the first close back above the 5-day average, at a 3-ATR stop, or after 10 days. This was profitable on 80% of the 87 stocks and in both Tesla periods (2011–17: +0.56% per trade; 2018–26: +0.23%, about 70% winners). In a portfolio of the 87 stocks, 2015–2017, it earned a Sharpe ratio around 1.6–1.7, against 0.96 for buy &amp; hold. The exit matters more than the entry: holding a fixed 5 days instead cut the Sharpe ratio to about 0.5.</p>
<p><b>2. Not every setup is equal.</b> Within RSI(2) setups, nine signs pointed the same way in all three samples (87 stocks, Tesla 2011–17, Tesla 2018–26). They are combined into the <b>Reversal Edge Score</b>, with weights fitted on the 87 stocks by non-negative least squares on trade returns:</p>
<ul>
<li><b>Market fear (VIX rank)</b>, weight 1.95. Reversal profits are pay for providing liquidity, and they are highest when the market is scared (Nagel 2012, "Evaporating Liquidity"). In the 87 stocks, a stretched stock bounced +0.85% more over 5 days when the VIX was in its top 20%, and it <i>underperformed</i> by 0.23% when the VIX was calm.</li>
<li><b>News-like gap</b>, counts against the trade, weight 2.16. Moves with news tend to drift, while moves without news reverse (Chan 2003). A big opening gap is the best daily-data proxy for news.</li>
<li><b>Rising volatility</b> (5-day above 60-day), weight 1.59, and <b>high volatility rank</b>. Stress periods pay the most. Recent work finds volatility, more than volume, drives reversals (Bogousslavsky, LeBaron &amp; Pontiff 2024).</li>
<li><b>Down streak</b>, weight 0.93. Consecutive lower closes.</li>
<li><b>Relative volume</b>, weight 0.84, and <b>range expansion</b>, weight 0.76. Price drops on heavy volume reverse more (Campbell, Grossman &amp; Wang 1993; Conrad, Hameed &amp; Niden 1994). In the 87 stocks, stretched drops on above-normal volume bounced about +0.5% more over 5 days (t≈3); drops on low volume showed no bounce at all.</li>
<li><b>Lower wick</b>, counts against the trade, weight 0.77. A long lower wick ("hammer") means the bounce already happened during the day.</li>
</ul>
<p>The score transferred to Tesla without any Tesla training. The top third of setups averaged <b>+1.64%</b> per trade (2011–17) and <b>+1.12%</b> (2018–26); the bottom third −0.09% and −0.46%. On the 87 stocks, walk-forward, the top third beat the bottom third in every year. Its probabilities are calibrated: it predicted 61% / 66% / 70% winners by third, and the actual rates were 61% / 65% / 71% (87 stocks) and 66% / 68% / 72% (Tesla).</p>
<h2>Round 2 (v6): fixing the failures on Ford and TASI</h2>
<p>Tested on new files the system had never seen, v5 failed twice. Ford (1978–2026) roughly broke even (−1% a year). TASI (2002–2026) lost money in every period. I searched the literature on the reasons, then tested every candidate fix. I designed on data before 2013 and judged only on 2013–2026 plus the 87 stocks: 92 series in all.</p>
<ul>
<li><b>Saudi stocks and TASI move with momentum, not reversal.</b> Their daily returns are positively autocorrelated, most of all in volatile periods (studies of the Saudi market from MPRA and the <i>Review of Accounting and Finance</i>). TASI's own 500-day lag-1 autocorrelation is about +0.12; US stocks sit near 0. Buying strength (RSI(2) above 90, sell on a close below the 5-day average) earned <b>Sharpe 2.0 on TASI before 2013 and 1.4 after</b> (10.4% a year while in the market 32% of the time), against 0.19 for holding it. The same rule lost money on MSFT, AMZN and Ford. So v6 checks each market's character every day. Above +0.08 it trades momentum setups; otherwise it trades reversal setups (the <b>Auto</b> mode).</li>
<li><b>Stops hurt mean reversion.</b> The literature finds this repeatedly. Removing the 3-ATR stop raised the average trade from +0.45% to +0.62% (t 7.6 → 10.4). Wide 4–6 ATR stops still cost about 0.15% a trade and did not reduce the worst loss, which comes from gaps. v6 uses a 10-day time limit and no price stop by default; a stop is still available in Settings.</li>
<li><b>Buy at a discount.</b> A limit order 0.5 ATR under the signal close, valid for the next day only, fills on about half the setups, but those trades averaged <b>+1.13%</b> instead of +0.62% (t 10.9).</li>
<li><b>Exit on strength.</b> Selling on the first close above the previous day's high beat the 5-day-average exit: +1.18% a trade and 0.27% per day held, against 0.13% per day for v5.</li>
<li><b>What did not help:</b> the 200-day trend filter, a filter on the stock's own short-window autocorrelation, and a "recent results" filter. All were inconsistent out of sample.</li>
</ul>
<p><b>v6 on your six files</b> (default settings, 100% of equity per trade, costs included):</p>
<ul>
<li>Ford: +546% total, Sharpe 0.34 (v5: −38%, Sharpe 0.02).</li>
<li>TASI: +195%, Sharpe 0.63, worst drawdown −18% (v5: −42%; buy &amp; hold drew down −80%).</li>
<li>AAPL: Sharpe 0.71, drawdown −14% (v5: 0.59, −25%).</li>
<li>MSFT: Sharpe 0.53, drawdown −28% (v5: 0.48, −34%).</li>
<li>AMZN: Sharpe 0.58, drawdown −23% (v5: 0.62, −35%).</li>
<li>TSLA got worse (Sharpe 0.37 vs 0.61). Its v5 result relied on the 3-ATR stop and the 5-day exit, a combination that did not hold up across the other 91 series.</li>
</ul>
<p>Average Sharpe across the six rose from 0.36 to 0.53. The momentum rule was validated mainly on one market (TASI) plus the published evidence, so treat momentum mode with more caution than reversal mode.</p>
<h2>The full system on Tesla (in this terminal, 2011–2026)</h2>
<p>Trading RSI(2) setups in the top third of the score, 100% of equity per trade, with the 5-day-average exit, a 3-ATR stop and costs: <b>+375% total (11.1% a year)</b>, Sharpe 0.61, maximum drawdown −37%, 91 trades, 71% won, in the market about 6% of the time. Trading every setup instead: +247%, Sharpe 0.44, drawdown −61%, 206 trades. Fewer, better trades made more money with less pain. Buy &amp; hold made far more on Tesla (about 43% a year) but fell 74% on the way.</p>
<h2>What does not work (so the system does not use it)</h2>
<ul>
<li><b>Shorting stocks that rose.</b> It lost money in every test, and badly on Tesla. The system buys drops only; shorting stays available, with a warning.</li>
<li><b>Candlestick patterns</b> (hammer, engulfing, key reversal) as signals on their own: no reliable edge.</li>
<li><b>Deeper z-score stretch</b> and <b>the 200-day trend filter</b>: they helped on some samples and hurt on others, so they are shown for context but not scored. A deep z-score of −2 or lower actually lost money on Tesla.</li>
<li><b>The earlier 22-feature machine-learning model</b> on the Kalman fair value: about 0.57 AUC on Tesla with no calibrated edge. It was replaced.</li>
</ul>
<h2>The adaptive zones</h2>
<p>Each stock has its own "normal" stretch. The zones on the chart are the stock's own percentiles of its 20-day z-score over the last three years (2.5%, 10%, 25%, 75%, 90%, 97.5%), recomputed every day from past data only. The inspector shows, for each zone, how often price got back to its 20-day mean within 10 days, and the average 5-day move, using only outcomes known before the bar you are looking at.</p>
<h2>Volatility</h2>
<p>The Volatility tab follows the professional toolkit:</p>
<ul>
<li>Five realised-volatility estimators: close-to-close, Parkinson (1980), Garman–Klass (1980), Rogers–Satchell (1991) and Yang–Zhang (2000). Yang–Zhang is the most efficient estimator that handles both overnight gaps and drift.</li>
<li>A GARCH(1,1) model (Bollerslev 1986) fitted by maximum likelihood every 250 days, with its forecast term structure, persistence and shock half-life.</li>
<li>A HAR forecast (Corsi 2009) on an OHLC daily-variance proxy.</li>
<li>A volatility cone (Burghardt &amp; Lane 1990).</li>
<li>Fat-tail statistics (skew, kurtosis, Hill tail index, VaR and expected shortfall), volatility clustering and the leverage effect.</li>
<li>An out-of-sample check of which forecast was most accurate on your stock.</li>
</ul>
<h2>Honest limits</h2>
<ul>
<li>The edge is real but modest and noisy: a few tenths of a percent per trade on average, more in the top third.</li>
<li>Tesla buy &amp; hold made about 43% a year from 2011 to 2026; no strategy that is in the market 10–20% of the time beats that in total return. Its value is in risk-adjusted return, smaller drawdowns, and capital that is free between trades.</li>
<li>The 87-stock sample covers a bull market (2013–2017). Past results do not guarantee future ones. Practise in bar replay, compare your journal with the system, and size small. This is research software, not financial advice.</li>
</ul>
<h2>References</h2>
<ol class="ref">
<li>Nagel, S. (2012). Evaporating Liquidity. <i>Review of Financial Studies</i> 25(7). <a href="https://www.nber.org/papers/w17653" target="_blank" rel="noopener">NBER w17653</a></li>
<li>Campbell, J., Grossman, S. &amp; Wang, J. (1993). Trading Volume and Serial Correlation in Stock Returns. <i>Quarterly Journal of Economics</i> 108(4). <a href="https://dash.harvard.edu/bitstream/1/3128710/2/campbell_trading.pdf" target="_blank" rel="noopener">PDF</a></li>
<li>Conrad, J., Hameed, A. &amp; Niden, C. (1994). Volume and Autocovariances in Short-Horizon Individual Security Returns. <i>Journal of Finance</i> 49(4).</li>
<li>Gervais, S., Kaniel, R. &amp; Mingelgrin, D. (2001). The High-Volume Return Premium. <i>Journal of Finance</i> 56(3). <a href="https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9901.pdf" target="_blank" rel="noopener">PDF</a></li>
<li>Chan, W. (2003). Stock Price Reaction to News and No-News: Drift and Reversal after Headlines. <i>Journal of Financial Economics</i> 70(2).</li>
<li>Bogousslavsky, V., LeBaron, B. &amp; Pontiff, J. (2024). A Century of Market Reversals: Resurrecting Volatility. <a href="https://abfer.org/component/edocman/main-annual-conference/a-century-of-market-reversals-resurrecting-volatility" target="_blank" rel="noopener">ABFER 2024</a></li>
<li>Lehmann, B. (1990). Fads, Martingales, and Market Efficiency. <i>QJE</i> 105(1); Jegadeesh, N. (1990). Evidence of Predictable Behavior of Security Returns. <i>Journal of Finance</i> 45(3).</li>
<li>Connors, L. &amp; Alvarez, C. (2008). <i>Short Term Trading Strategies That Work</i> (RSI(2), 5-day-average exit).</li>
<li>Pagonidis, A. (2013). The IBS Effect: Mean Reversion in Equity ETFs; replication: <a href="https://arxiv.org/abs/2306.12434" target="_blank" rel="noopener">arXiv 2306.12434</a></li>
<li>Avellaneda, M. &amp; Lee, J. (2010). Statistical Arbitrage in the US Equities Market. <i>Quantitative Finance</i> 10(7).</li>
<li>Yang, D. &amp; Zhang, Q. (2000). Drift-Independent Volatility Estimation Based on High, Low, Open and Close Prices. <i>Journal of Business</i> 73(3).</li>
<li>Parkinson, M. (1980); Garman, M. &amp; Klass, M. (1980); Rogers, L. &amp; Satchell, S. (1991): range-based volatility estimators.</li>
<li>Bollerslev, T. (1986). Generalized Autoregressive Conditional Heteroskedasticity. <i>Journal of Econometrics</i> 31(3).</li>
<li>Corsi, F. (2009). A Simple Approximate Long-Memory Model of Realized Volatility. <i>Journal of Financial Econometrics</i> 7(2).</li>
<li>Burghardt, G. &amp; Lane, M. (1990). How to Tell if Options Are Cheap. <i>Journal of Portfolio Management</i> 16(2). <a href="https://www.m-x.ca/f_publications_en/cone_vol_en.pdf" target="_blank" rel="noopener">volatility cones</a></li>
<li>López de Prado, M. (2018). <i>Advances in Financial Machine Learning</i> (walk-forward testing, triple-barrier labels).</li>
<li>Data: <a href="https://github.com/yumoxu/stocknet-dataset" target="_blank" rel="noopener">StockNet price data</a> (87 stocks); <a href="https://github.com/datasets/finance-vix" target="_blank" rel="noopener">datasets/finance-vix</a> (CBOE VIX).</li>
</ol>`;

// ------------------------------------------------ wiring
function renderLive(){renderSigbar();if(!draft.show)defaultLevels();else ticketChanged(false);if(st.tab==="mine")drawMine();
 if(REPLAY){const d=DS[REPLAY.sym];$("rp-date").textContent=d?`${d.d[REPLAY.idx]} · bar ${REPLAY.idx-REPLAY.startIdx>=0?"+":""}${REPLAY.idx-REPLAY.startIdx}`:""}}
function focusDate(sym,date){if(REPLAY&&REPLAY.sym!==sym)exitReplay();if(sym!==st.sym){st.sym=sym;sel.value=sym;symChanged()}show("chart");const i=idxOf(date);if(i<0)return;
 chart.timeScale().setVisibleLogicalRange({from:i-110,to:i+30});st.pinned=true;st.cursor=i;syncScrub();inspector(i);renderLegend()}
function renderSymSelect(){const ks=Object.keys(DS).sort();sel.innerHTML=ks.map(k=>`<option value="${esc(k)}" ${k===st.sym?"selected":""}>${esc(nameOf(k))}</option>`).join("")}
function symChanged(){if(REPLAY&&REPLAY.sym!==st.sym)exitReplay();UI.sym=st.sym;saveUI();st.cursor=null;st.pinned=false;hoverIdx=null;draft.show=false;
 if(chart){refreshOverlays();showRange();inspector(cur())}renderLive()}
function afterDataChange(newSym){if(REPLAY&&!DS[REPLAY.sym]){REPLAY=null;saveReplay();syncMode()}
 if(!DS[st.sym])st.sym=Object.keys(DS)[0]||null;renderSymSelect();renderDS();symChanged();if(Object.keys(DS).length)runNow();else{RES=null;$("snap").textContent="No data yet: upload price history in the Data tab."}}
function show(t){st.tab=t;document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.t===t));
 ["data","chart","scan","mine","vol","model","perf","trades","about"].forEach(k=>$("t-"+k).hidden=k!==t);
 if(t!=="chart"){setClickMode(null);stopPlay()}
 if(t==="chart"){if(!chart)buildChart(false);renderLive();inspector(st.cursor!=null?Math.min(st.cursor,cur()):cur())}
 if(t==="scan")drawScan();
 if(t==="mine")drawMine();
 if(t==="model"||t==="perf"||t==="vol"){const id={model:"cards",perf:"pk",vol:"v-est"}[t];if(!window.Plotly)clr(id,'<div class="empty">Loading charts…</div>');
  needPlotly().then(()=>{if(st.tab!==t)return;if(t==="model"){drawModel();drawEdge()}else if(t==="perf")drawPerf();else drawVol()}).catch(e=>clr(id,`<div class="empty">${esc(e.message)}</div>`))}
 if(t==="trades")drawTrades()}
document.querySelectorAll("#tabs button").forEach(b=>b.addEventListener("click",()=>show(b.dataset.t)));
sel.addEventListener("change",()=>{st.sym=sel.value;symChanged();if(!["chart","data","about","scan"].includes(st.tab))show(st.tab)});
document.querySelectorAll("#rng button").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll("#rng button").forEach(x=>x.classList.remove("on"));b.classList.add("on");st.n=+b.dataset.n;showRange();if(st.tab==="vol"&&window.Plotly)drawVol()}));

// boot
st.sym=REPLAY&&DS[REPLAY.sym]?REPLAY.sym:(UI.sym&&DS[UI.sym]?UI.sym:Object.keys(DS)[0]||null);
if(REPLAY&&!DS[REPLAY.sym]){REPLAY=null;saveReplay()}
renderSymSelect();renderDS();syncMode();renderLive();
await loadFear();
if(Object.keys(DS).length)runNow();else await loadSample();
