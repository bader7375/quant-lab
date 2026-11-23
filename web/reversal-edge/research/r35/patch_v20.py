"""v19 -> v20 (round 35): US index dip rule on SPY / QQQ (signal card, Core panel), research notes."""
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../v20"))
def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:100], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)
USFN = r'''
// ------------------------------------------------ v20 (round 35): US index dip rule - the one US edge that held up out of sample
// SPY / QQQ: RSI(2) closes below 10 while above the 200-day average -> buy at the next open; sell at the next open after the first close above
// the 5-day average, or after 10 sessions. 2000-26: SPY 72% winners +0.41%/trade, QQQ 67% +0.48%; ~8 trades a year, 2-3 days each.
function usIdxNote(d,c){if(!/^(SPY|QQQ)$/i.test(st.sym))return "";const n=c+1,C=d.c,r2=new Array(n).fill(NaN),s5=new Array(n).fill(NaN),s200=new Array(n).fill(NaN);
 let up=NaN,dn=NaN;for(let t=1;t<n;t++){const x=C[t]-C[t-1],u=Math.max(x,0),w=Math.max(-x,0);up=isF(up)?up+(u-up)/2:u;dn=isF(dn)?dn+(w-dn)/2:w;r2[t]=dn===0?100:100-100/(1+up/dn)}
 let a5=0,a200=0;for(let t=0;t<n;t++){a5+=C[t];a200+=C[t];if(t>=5)a5-=C[t-5];if(t>=200)a200-=C[t-200];if(t>=4)s5[t]=a5/5;if(t>=199)s200[t]=a200/200}
 let i=0,S=null;while(i<n){if(isF(r2[i])&&r2[i]<10&&isF(s200[i])&&C[i]>s200[i]){const e=i+1;if(e>=n){S={k:"signal"};break}let k=e;while(k<n&&!(C[k]>s5[k])&&k-e<10)k++;if(k>=n){S={k:"hold",e};break}if(k===n-1){S={k:"sell"};break}i=k+1}else i++}
 const now=S?(S.k==="signal"?"<b>buy signal at this close</b>: buy at the next open; sell at the next open after a close above the 5-day average, at most 10 sessions":S.k==="hold"?`in a trade since ${d.d[S.e]} (session ${c-S.e+1} of 10): sell at the next open after a close above the 5-day average (${fp(s5[c])})`:"<b>exit</b>: it closed above the 5-day average (or reached 10 sessions): sell at the next open")
  :(C[c]>s200[c]?`no signal (RSI(2) ${fmt(r2[c],1)}; a buy needs it below 10 while above the 200-day average, ${fp(s200[c])})`:`off: below the 200-day average (${fp(s200[c])})`);
 return `<div style="margin-top:6px"><b>US index dip rule</b> (round 35, the one US edge that held up): RSI(2) below 10 while above the 200-day average, buy at the next open, sell at the next open after the first close above the 5-day average or after 10 sessions. 2000–26: SPY 72% winners, +0.41% per trade; QQQ 67%, +0.48%; about 8 trades a year, 2–3 days each; in the market only ~8% of days, so it earns less than buy-and-hold in total but with a −14% worst drawdown instead of −55%. Now: ${now}.</div>`}
'''
patch("app3.js", [(" const chips=!mom&&s.setup[c]?topSigns(s,c)", " {const ux=usIdxNote(d,c);if(ux)say+=ux}\n const chips=!mom&&s.setup[c]?topSigns(s,c)")])
s = open("app3.js").read(); open("app3.js", "w").write(s + USFN)
patch("app7.js", [('${isF(MLPF.ms)?` <b>Market momentum ${MLPF.ms.toFixed(2)}</b>: ${msZone(MLPF.ms).txt}.`:""}',
 '${isF(MLPF.ms)?` <b>Market momentum ${MLPF.ms.toFixed(2)}</b>: ${msZone(MLPF.ms).txt}.`:""}${MLPF.us&&MLPF.us.etf?`<br><b>US index dip rule (SPY / QQQ, ${esc(MLPF.us.date)} US close):</b> ${Object.entries(MLPF.us.etf).map(([k,v])=>`${k} ${esc(v.status)} (RSI(2) ${v.rsi2.toFixed(1)}, ${v.above?"above":"below"} the 200-day average)`).join(" · ")}. Buy at the next open on a signal; sell at the next open after a close above the 5-day average or after 10 sessions.<br>`:""}')])
patch("app6.js", [("- WEEKLY Z SWING (round 33, pre-registered):", "- US EDGE SEARCH (round 35, pre-registered): index timing on S&P 500 1950-99 (choose) / 2000-26 (confirm) + NASDAQ, Nikkei, DAX, FTSE, Hang Seng checks, and a walk-forward US stock ranker. Only the INDEX RSI(2) dip in an uptrend passed: RSI(2) < 10 above the 200-day average, exit on a close above the 5-day average or 10 days; S&P 2000-26 +0.21%/trade over drift (t 2.2), SPY 72% winners +0.41%, QQQ 67% +0.48% (next-open execution), ~8 trades/yr, in market ~8% of days, CAGR +4.7% vs +8.2% buy-and-hold, DD -14% vs -55%. Failed: turn of the month (strong 1950-99, weak in the US since 2000), index dips with crash guards, VIX spikes, 200-day trend filter, the US stock ranker (survivorship-driven: its us100 edge vanished in KDD17 and CMIN-US), and RSI(2) on single stocks.\n- WEEKLY Z SWING (round 33, pre-registered):")])
patch("body.html", [("reversal edge v19 · Saudi Core v2 · daily + weekly Z swing", "reversal edge v20 · Saudi Z swing + US index dip")])
SEC = '''<h2>v20 (round 35): searching for a US edge</h2>
<p>Two searches, written down before testing. <b>Timing the US market</b> on the S&amp;P 500 from 1950 (rules chosen on 1950–99, checked on 2000–26 and on NASDAQ, Nikkei, DAX, FTSE and Hang Seng), and <b>picking US stocks</b> with a walk-forward ML ranker like the Saudi one.</p>
<table class="t"><tr><th style="text-align:left">idea</th><th>chosen on 1950–99</th><th>S&amp;P 2000–26</th><th>other markets</th><th>verdict</th></tr>
<tr><td style="text-align:left"><b>index RSI(2) &lt; 10 above the 200-day average</b>, exit on a close above the 5-day average</td><td>+0.06%/trade over drift</td><td><b>+0.21% (t 2.2)</b>, SPY +0.32, QQQ +0.35</td><td>positive on 4 of 6</td><td class="up"><b>adopted</b></td></tr>
<tr><td style="text-align:left">turn of the month (last day to day 3)</td><td>very strong (t 6.5)</td><td>weak (t 0.9)</td><td>positive on 6 of 6</td><td class="down">faded in the US</td></tr>
<tr><td style="text-align:left">index dip with a crash guard / VIX spike / 200-day trend filter</td><td colspan="3">no consistent edge</td><td class="down">rejected</td></tr>
<tr><td style="text-align:left">US stock ML ranker (us100)</td><td colspan="2">+11% a year over the average stock, but driven by today's winners (survivorship)</td><td>KDD17 and CMIN-US: no edge</td><td class="down">rejected</td></tr>
<tr><td style="text-align:left">RSI(2) dip on single US stocks</td><td colspan="3">mixed: below the stock's own drift in 2018–26, nothing in KDD17</td><td class="down">rejected</td></tr></table>
<p><b>The rule:</b> on SPY or QQQ, when RSI(2) closes below 10 while the ETF is above its 200-day average, buy at the next open; sell at the next open after the first close above the 5-day average, or after 10 sessions. 2000–26: SPY 72% winners, +0.41% per trade; QQQ 67%, +0.48%; about 8 trades a year each, 2–3 days per trade. It is a small edge: in the market only about 8% of days, SPY made +4.7% a year (cash otherwise) against +8.2% for buy-and-hold, with a −14% worst drawdown instead of −55%. Weakest decade: the 2010s (+0.17% per trade). The daily list now carries a US section (and runs on Fridays for it); open SPY or QQQ on the chart to see the rule's state.</p>
'''
s = open("app5.js").read(); a = "<h2>v19 (round 33)"; assert s.count(a) == 1; open("app5.js", "w").write(s.replace(a, SEC + a))
print("patched v20")
