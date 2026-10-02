// ------------------------------------------------ Research tab
$("research").innerHTML=`
<h2 style="font-size:18px">How this system was built, and what the evidence says (v6)</h2>
<p>I tested the main short-term reversal ideas from academic papers and trading books on real daily prices: 87 large US stocks (2012–2017, Yahoo prices from the StockNet dataset), Tesla (2010–2026) and the VIX (1990–2026). Every number below is out of sample. Either the model was trained only on earlier years, or it was trained on the 87 stocks and then tested on Tesla, a stock it had never seen. Costs of 10 basis points per round trip are included.</p>
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
function renderSymSelect(){const ks=Object.keys(DS).sort();sel.innerHTML=ks.map(k=>`<option ${k===st.sym?"selected":""}>${esc(k)}</option>`).join("")}
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
