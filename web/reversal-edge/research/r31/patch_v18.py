"""v17 -> v18 (round 31): VWAP stretch Z panel, market momentum panel (the dip-buy gate), Z swing gated at market momentum <= -1.18."""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../v18"))
VZQ = json.load(open("../r31/vz_q.json"))
def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:100], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)

patch("app1.js", [("zs:true,zl:false", "zs:true,vz:true,ms:true,zl:false")])

HELPERS = '''
// ------------------------------------------------ v18 (round 31): VWAP stretch Z and market momentum (the dip-buy gate)
// VWAP stretch Z = mean over 10/20/60 days of ln(close / k-day VWAP) in units of the stock's own daily volatility (measured before the window)
// x sqrt((k-1)(2k-1)/(6k)). Line -2.67 = 2% of liquid Saudi stock-days 2013-19; scale = liquid Saudi stocks 2004-2026.
const VZ_LINE=-2.67,VZ_Q=''' + json.dumps(VZQ) + ''';
function vwapZ(d){const n=d.c.length,c=d.c,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);
 for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-.25,Math.min(.25,a-b))}
 for(let i=59;i<n;i++){let s1=0,s2=0,m=0;for(let k=i-59;k<=i;k++)if(isF(rr[k])){s1+=rr[k];s2+=rr[k]*rr[k];m++}if(m>=40)sd[i]=Math.sqrt(Math.max(1e-12,(s2-s1*s1/m)/(m-1)))}
 const pv=new Array(n).fill(0),vv=new Array(n).fill(0);for(let i=0;i<n;i++){const tp=(d.h[i]+d.l[i]+c[i])/3,v=d.v?d.v[i]:NaN;if(isF(tp)&&isF(v)&&v>0){pv[i]=tp*v;vv[i]=v}}
 const zk=K=>{const z=new Array(n).fill(NaN),sc=Math.sqrt((K-1)*(2*K-1)/(6*K));let a=0,b=0;
  for(let i=0;i<n;i++){a+=pv[i];b+=vv[i];if(i>=K){a-=pv[i-K];b-=vv[i-K]}if(i>=K&&b>0&&isF(c[i])&&c[i]>0&&isF(sd[i-K])&&sd[i-K]>0)z[i]=Math.log(c[i]/(a/b))/(sd[i-K]*sc)}return z};
 const x=zk(10),y=zk(20),w=zk(60);for(let i=0;i<n;i++)if(isF(x[i])&&isF(y[i])&&isF(w[i]))out[i]=(x[i]+y[i]+w[i])/3;return out}
function qCdf(Q,z){if(!isF(z))return NaN;if(z<=Q[0][0])return Q[0][1]/2;if(z>=Q[Q.length-1][0])return 1-(1-Q[Q.length-1][1])/2;
 for(let k=1;k<Q.length;k++)if(z<=Q[k][0]){const [x0,p0]=Q[k-1],[x1,p1]=Q[k];return p0+(p1-p0)*(z-x0)/(x1-x0)}return NaN}
function vzRareTxt(z){const p=qCdf(VZ_Q,z);if(!isF(p))return "—";if(p<=.5){const n=Math.round(1/p);return `lower than ${(100*(1-p)).toFixed(p<.02?1:0)}% of days${p<.1?` (about 1 day in ${n})`:""}`}
 const n=Math.round(1/(1-p));return `higher than ${(100*p).toFixed(p>.98?1:0)}% of days${p>.9?` (about 1 day in ${n})`:""}`}
function vzColor(z){return !isF(z)?"inherit":z<=VZ_LINE?"#4dd0e1":z<=-1.5?"#8fdde6":z>=2.66?"#ffb74d":z>=2?"#ffd08a":"inherit"}
// market momentum = equal-weight Saudi market 60-day log return / (its daily sd measured before those 60 days x sqrt 60), from the daily ML export.
// Round 31: dip buys worked when it was at or below -1.18 (the whole market falling); above it single-stock dips tended to keep falling.
const MS_GATE=-1.18,MS_DEEP=-2.53;let MS_MAP=null,MS_SRC=null;
function msMap(){const h=typeof MLPF!=="undefined"&&MLPF&&MLPF.ms_hist;if(!h||!h.d)return null;
 if(MS_SRC!==h){MS_SRC=h;MS_MAP=new Map();for(let k=0;k<h.d.length;k++){const q=String(h.d[k]);MS_MAP.set(`${q.slice(0,4)}-${q.slice(4,6)}-${q.slice(6,8)}`,h.v[k])}}return MS_MAP}
function msOn(sym){try{return saudiSym(sym)}catch(e){return false}}   // saudiSym is a const in app6 (not hoisted)
function msAt(t){const m=msMap();if(!m)return NaN;const v=m.get(t);return isF(v)?v:NaN}
function msZone(v){return !isF(v)?null:v<=MS_DEEP?{k:"deep",txt:"deep mean-reversion zone (dip buys worked best)",col:"#4fd1a5"}:v<=MS_GATE?{k:"mr",txt:"mean-reversion zone (dip buys allowed)",col:"#8fd19e"}:{k:"mom",txt:"momentum zone: the market is not falling, avoid dip buys",col:"#e6a667"}}
'''
patch("app2.js", [
 ('function zcColor(z){return !isF(z)?"inherit":z<=ZC_LINE?"#4f96f0":z<=-1.5?"#7fb2f0":z>=3?"#e66767":z>=2?"#f0a0a0":"inherit"}\n',
  'function zcColor(z){return !isF(z)?"inherit":z<=ZC_LINE?"#4f96f0":z<=-1.5?"#7fb2f0":z>=3?"#e66767":z>=2?"#f0a0a0":"inherit"}\n' + HELPERS),
 ('["zs","Stretch Z (10/20/60d)"],', '["zs","Stretch Z (10/20/60d)"],["vz","VWAP stretch Z"],["ms","Market momentum (dip-buy gate)"],'),
 ('A.zs=L(A.zsArr);', 'A.zs=L(A.zsArr);A.vzArr=vwapZ(d);A.vz=L(A.vzArr);A.msArr=msOn(st.sym)?d.d.map(msAt):d.d.map(()=>NaN);A.ms=L(A.msArr);'),
 ('''[-3.5,"rgba(79,150,240,.5)","−3.5"]])SER.zs.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}''',
  '''[-3.5,"rgba(79,150,240,.5)","−3.5"]])SER.zs.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}
 if(UI.pn.vz){P.vz=pane++;SER.vz=chart.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:0},lineWidth:2,priceLineVisible:false,title:"VWAP Z",topLineColor:"#ffb74d",topFillColor1:"rgba(255,183,77,.12)",topFillColor2:"rgba(255,183,77,0)",bottomLineColor:"#4dd0e1",bottomFillColor1:"rgba(77,208,225,0)",bottomFillColor2:"rgba(77,208,225,.18)",priceFormat:{type:"price",precision:2,minMove:.01}},P.vz);
  for(const [p,c,t] of [[2.66,"rgba(255,183,77,.7)","+2.7 top 1%"],[VZ_LINE,"rgba(77,208,225,.9)","−2.7 (2%)"]])SER.vz.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}
 if(UI.pn.ms&&msOn(st.sym)){P.ms=pane++;SER.ms=chart.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:MS_GATE},lineWidth:2,priceLineVisible:false,title:"Market momentum",topLineColor:"#e6a667",topFillColor1:"rgba(230,166,103,.10)",topFillColor2:"rgba(230,166,103,0)",bottomLineColor:"#4fd1a5",bottomFillColor1:"rgba(79,209,165,0)",bottomFillColor2:"rgba(79,209,165,.25)",priceFormat:{type:"price",precision:2,minMove:.01}},P.ms);
  for(const [p,c,t] of [[MS_GATE,"rgba(230,166,103,.9)","−1.18 dip buys below"],[MS_DEEP,"rgba(79,209,165,.9)","−2.53 deep"]])SER.ms.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}'''),
 ('const DKEYS=["zs",', 'const DKEYS=["zs","vz","ms",'),
 ('zs=ARR&&ARR.zsArr?ARR.zsArr[i]:NaN;\n', 'zs=ARR&&ARR.zsArr?ARR.zsArr[i]:NaN,vz=ARR&&ARR.vzArr?ARR.vzArr[i]:NaN,mm=ARR&&ARR.msArr?ARR.msArr[i]:NaN,mz=msZone(mm);\n'),
 ('<span class="lk">Z250 ${fmt(zl,2)}</span>', '<span title="price vs its 10/20/60-day VWAP in volatility units; ${esc(vzRareTxt(vz))}"><b>VWAP Z</b> <span style="color:${vzColor(vz)};font-weight:600">${fmt(vz,2)}</span></span>${mz?`<span title="market momentum: ${esc(mz.txt)}">mkt mom <span style="color:${mz.col};font-weight:600">${fmt(mm,2)}</span></span>`:""}<span class="lk">Z250 ${fmt(zl,2)}</span>'),
])
# the chart height counts open panels; the market momentum panel is skipped for non-Saudi stocks
patch("app2.js", [('np=Object.entries(UI.pn).filter(([k,v])=>v&&!(TRM0&&(k==="edge"||k==="rsi"||k==="z"))).length',
                   'np=Object.entries(UI.pn).filter(([k,v])=>v&&!(TRM0&&(k==="edge"||k==="rsi"||k==="z"))&&!(k==="ms"&&!msOn(st.sym))).length')])

GATED = "with market momentum at or below −1.18 (round 31), first touches like this averaged +6.9% net over 40 sessions in 2020–26 (70% winners, average win +13% vs loss −7%) and +19.9% in 2013–19 (86% winners)"
patch("app3.js", [
 ('''cem=typeof sectorInfo==="function"&&(sectorInfo(st.sym)||{}).g==="Cement",ok=pct0>=.5&&on;''',
  '''cem=typeof sectorInfo==="function"&&(sectorInfo(st.sym)||{}).g==="Cement",msv=msAt(d.d[c]),mok=!(msv>MS_GATE),ok=pct0>=.5&&on&&mok;'''),
 ('''with the ML rank ≥ 50% and the market model positive, "+"first touches like this averaged +6.0% net over 40 sessions in 2020–26 (66% winners, average win +13%, average loss −8%) and +15.9% in 2013–19 (77% winners)"''', 'with the ML rank ≥ 50%, the market model positive and market momentum at or below −1.18 (round 31: the whole market falling), "+"first touches like this averaged +6.9% net over 40 sessions in 2020–26 (70% winners, average win +13% vs loss −7%) and +19.9% in 2013–19 (86% winners)"'),
 (''':`Not a trade: it needs ${[!(pct0>=.5)?"an ML rank of at least 50%":"",!on?"the market model positive":""].filter(Boolean).join(" and ")}.`)}''',
  ''':`Not a trade: it needs ${[!(pct0>=.5)?"an ML rank of at least 50%":"",!on?"the market model positive":"",!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)}: the market is not falling, and dips like this kept falling: 28% winners in 2013–19, 39% in 2020–26)`:""].filter(Boolean).join(" and ")}.`)}'''),
 ('''  if(isF(zs)&&zo){h+=`<div class="sec">stretch Z: how unusual, and what followed</div>''',
  '''  {const vz0=ARR&&ARR.vzArr&&ARR.n===d.d.length?ARR.vzArr[i]:vwapZ(d)[i],mm=msOn(st.sym)?msAt(d.d[i]):NaN,mz=msZone(mm);
   h+=`<div class="sec">VWAP stretch Z and market momentum (round 31)</div><table class="t"><tr><td>VWAP stretch Z (price vs its 10/20/60-day VWAP, in volatility units)</td><td class="n"><b style="color:${vzColor(vz0)}">${fmt(vz0,2)}</b> · ${vzRareTxt(vz0)}</td></tr>${mz?`<tr><td>market momentum (dip-buy gate)</td><td class="n"><b style="color:${mz.col}">${fmt(mm,2)}</b> · ${mz.txt}</td></tr>`:""}</table><div class="note">VWAP Z moves with stretch Z (correlation 0.89) but was the weaker signal in every test era (Z-swing rule: 69% vs 78% winners in 2013–19, 63% vs 67% in 2020–26), so trades use stretch Z. Market momentum at or below −1.18 means the whole market is falling: that is when dip buys worked; above it single-stock dips tended to keep falling.</div>`}
  if(isF(zs)&&zo){h+=`<div class="sec">stretch Z: how unusual, and what followed</div>'''),
])
patch("app6.js", [
 ('''cem=typeof sectorInfo==="function"&&(sectorInfo(sym)||{}).g==="Cement",ok=pct>=.5&&on;''',
  '''cem=typeof sectorInfo==="function"&&(sectorInfo(sym)||{}).g==="Cement",msv=msAt(s.d[i]),mok=!(msv>MS_GATE),ok=pct>=.5&&on&&mok;'''),
 ('''Z swing: first touches with ML rank ≥ 50% and the market model positive averaged +6.0% net over 40 sessions, 66% winners, average win +13% vs average loss −8% (2020–26; 2013–19 +15.9%, 77% winners)''',
  '''Z swing: first touches with ML rank ≥ 50%, the market model positive and market momentum at or below −1.18 averaged +6.9% net over 40 sessions, 70% winners, average win +13% vs average loss −7% (2020–26; 2013–19 +19.9%, 86% winners)'''),
 ('''  if(!on)warn.push("market model negative: the Z rebound is only taken when it is positive");''',
  '''  if(!on)warn.push("market model negative: the Z rebound is only taken when it is positive");
  if(!mok)warn.push(`market momentum ${fmt(msv,2)} is above −1.18 (the market is not falling): such Z-swing entries lost money (2013–19 −9.3% per trade, 28% winners; 2020–26 −0.9%, 39%)`);
  if(!isF(msv))warn.push("market momentum unknown for this date (daily ML data not loaded): check it before buying");'''),
 ('''- Z SWING (round 28, pre-registered;''',
  '''- MARKET MOMENTUM GATE (round 31): market momentum = equal-weight Saudi market 60-day log return / (its daily sd before those 60 days x sqrt 60). Zones: <= -2.53 deep mean-reversion zone, -2.53..-1.18 mean-reversion zone, > -1.18 momentum zone (80% of days). Dips bought in the momentum zone lost about -3.4% per 20-day trade in 2004-12, 2013-19 and 2020-26; confirmed on US data (market falling: +8% to +11% per dip trade, 76-85% winners; not falling: -4.7% to +1.2%). Z swing now also needs market momentum <= -1.18: 2013-19 86% winners, +19.9% per trade; 2020-26 70%, +6.9% (before 78%/+15.9% and 67%/+6.1%); skipped entries 28%/39% winners. Found after the registered test (excess return) failed; one independent confirmation.
- VWAP STRETCH Z (round 31): like stretch Z but price vs its 10/20/60-day VWAP; correlation 0.89 with stretch Z; weaker as a signal in 2004-12, 2013-19 and 2020-26, so chart context only. Stock-level momentum gauges (variance ratio, autocorrelation, efficiency ratio, ADX, 12-1 momentum) did not tell when dips revert.
- Z SWING (round 28, pre-registered;'''),
])
patch("app7.js", [
 ('''its ML rank is ≥ 50% and the market model is positive; no stop; sell at the open 40 sessions later. 2020–26: 66% winners, average win +13% vs loss −8%, +6.0% per trade (2013–19: 77%, +15.9%).''',
  '''its ML rank is ≥ 50%, the market model is positive and <b>market momentum is at or below −1.18</b> (round 31: the whole market is falling); no stop; sell at the open 40 sessions later. 2020–26: 70% winners, average win +13% vs loss −7%, +6.9% per trade (2013–19: 86%, +19.9%); entries skipped by the momentum gate won only 28% / 39% of the time.'''),
 ('''(20-day forecast ${spct(MLPF.pm,1)}). ML sleeve list: ${top10}.''',
  '''(20-day forecast ${spct(MLPF.pm,1)}).${isF(MLPF.ms)?` <b>Market momentum ${MLPF.ms.toFixed(2)}</b>: ${msZone(MLPF.ms).txt}.`:""} ML sleeve list: ${top10}.'''),
])
patch("body.html", [("reversal edge v17 · Saudi Core v2 · Z swing + momentum", "reversal edge v18 · Saudi Core v2 · Z swing + market-momentum gate")])
SEC = '''<h2>v18 (round 31): VWAP stretch Z and a momentum gate for dip buys</h2>
<p>Two ideas, written down before testing: a <b>VWAP version of stretch Z</b>, and a <b>momentum gauge</b> that says when buying dips works and when to avoid it.</p>
<table class="t"><tr><th style="text-align:left">test</th><th>2013–19</th><th>2020–26</th><th>2004–12</th><th>verdict</th></tr>
<tr><td style="text-align:left">Z-swing rule with VWAP stretch Z instead of stretch Z</td><td>69% winners, +10.0%</td><td>63%, +5.1%</td><td>−0.4% (price only)</td><td class="down">weaker: chart panel only</td></tr>
<tr><td style="text-align:left">stock momentum gauges (variance ratio, autocorrelation, efficiency ratio, ADX, 12-month momentum)</td><td colspan="3">no consistent split between good and bad dips</td><td class="down">rejected</td></tr>
<tr><td style="text-align:left">dips bought while the market is NOT falling (market momentum above −1.18)</td><td>−3.5% per 20-day trade, 35% winners</td><td>−3.4%, 33%</td><td>−3.4%, 41%</td><td>avoid</td></tr>
<tr><td style="text-align:left">dips bought while the market is deeply oversold (≤ −2.53)</td><td>+3.7%, 60%</td><td>+5.2%, 74%</td><td>−0.6%, 48%</td><td>trade</td></tr>
<tr><td style="text-align:left"><b>Z swing with market momentum ≤ −1.18</b></td><td><b>86% winners, +19.9%</b> (was 78%, +15.9%)</td><td><b>70%, +6.9%</b> (was 67%, +6.1%)</td><td></td><td class="up"><b>adopted</b></td></tr></table>
<p><b>Market momentum</b> is the whole Saudi market's 60-day move in units of its own volatility (equal weight). Below −1.18 the market is falling and stock dips tend to snap back with it; above −1.18 (80% of days) a stock falling on its own usually has a reason, and its dip kept falling. The registered test (return above the market) failed; the absolute-return pattern was found afterwards, so it was checked on data never used for this question: <b>US stocks</b>, where dips bought with the market falling made +8% to +11% per trade (76–85% winners) against −4.7% to +1.2% when it was not, in all three US data sets. Gating the Z swing kept the return of the 5 × 5% sleeve (+3.3% a year) with a smaller drawdown (−7% vs −10%); the worst gated trade lost 23% (was 35%). Trend breakouts are not gated: they happen in the momentum zone. Caveat: sell-offs cluster, so the number of independent episodes is far smaller than the trade counts.</p>
'''
s = open("app5.js").read(); a = "<h2>v17 (round 29): momentum to help the Z swing</h2>"; assert s.count(a) == 1
open("app5.js", "w").write(s.replace(a, SEC + a))
print("patched")
patch("app6.js", [("stretch Z first close ≤ −2.62 with ML rank ≥ 50% and the market model positive, hold 40 sessions; 66% winners 2020–26, 77% 2013–19)",
                   "stretch Z first close ≤ −2.62 with ML rank ≥ 50%, the market model positive and market momentum ≤ −1.18, hold 40 sessions; 70% winners 2020–26, 86% 2013–19)")])
print("patched 2")
# Momentum Pulse: for Saudi stocks the old "momentum market -> avoid mean reversion" advice contradicted the Z swing; use the market momentum gate instead
patch("app2.js", [
 ('''function pulseAdvice(s,i){const P=s.pulse,st0=P.state[i],momMkt=s.mode[i]===-1,div=recentDiv(P,i);let a,tone;
 if(momMkt){''',
  '''function pulseAdvice(s,i){const P=s.pulse,st0=P.state[i],momMkt=s.mode[i]===-1,div=recentDiv(P,i);let a,tone;
 const mv=msOn(st.sym)&&s.d?msAt(s.d[i]):NaN;
 if(isF(mv)){const okz=mv<=MS_GATE;   // v18 (round 31): Saudi stocks use the market momentum gate
  a=okz?`Market momentum ${mv.toFixed(2)}: the whole market is falling, the zone where deep dips rebounded. Short dips (RSI(2)) still don't pay on Saudi stocks: buy only a Z-swing signal (stretch Z first close ≤ −2.62).`
       :`Market momentum ${mv.toFixed(2)}: the market is not falling, so a stock dropping on its own has tended to keep falling. Avoid buying dips; trend breakouts are the trade here.`;tone=okz?"good":"bad";
  if(st0===2)a+=" Up-move at a 2-year momentum extreme and turning: a warning, no proven edge on its own."}
 else if(momMkt){'''),
 ('''${s.mode[i]===-1?'<span class="st" style="color:#a77bea;border-color:#a77bea">AVOID MEAN REVERSION</span>':""}`}''',
  '''${(()=>{const mv=msOn(st.sym)&&s.d?msAt(s.d[i]):NaN;if(isF(mv))return mv<=MS_GATE?`<span class="st" style="color:#4fd1a5;border-color:#4fd1a5">DIP BUYS OK · MKT MOM ${mv.toFixed(2)}</span>`:`<span class="st" style="color:#e6a667;border-color:#e6a667">AVOID DIP BUYS · MKT MOM ${mv.toFixed(2)}</span>`;
   return s.mode[i]===-1?'<span class="st" style="color:#a77bea;border-color:#a77bea">AVOID MEAN REVERSION</span>':""})()}`}'''),
])
print("patched 3")
