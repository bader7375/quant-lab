"""v18 -> v19 (round 33): weekly / monthly candles with stretch Z on that timeframe, weekly Z swing in plan / signal card / Core panel,
latest annual accounts in the inspector and plan."""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../v19"))
TFQ = json.load(open("../r33/tf_q.json"))
def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:100], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)

patch("body.html", [
 ('<div class="seg2" role="group" aria-label="Mode"><button id="m-live" class="on">Live</button>',
  '<div class="seg2" role="group" aria-label="Candles"><button id="tf-D" class="on">Daily</button><button id="tf-W">Weekly</button><button id="tf-M">Monthly</button></div>\n          <div class="seg2" role="group" aria-label="Mode"><button id="m-live" class="on">Live</button>'),
 ('        <div class="scrub"><span>scrub</span>', '        <div id="htf-wrap" style="display:none"><div id="htf"></div><div class="legend" id="htf-legend"></div></div>\n        <div class="note" id="htf-note" style="display:none"></div>\n        <div class="scrub"><span>scrub</span>'),
 ('#lwc{position:absolute;inset:0}', '#lwc{position:absolute;inset:0}\n#htf-wrap{position:relative;border:1px solid var(--hair);border-radius:6px;overflow:hidden;background:var(--surface)}#htf{position:absolute;inset:0}#htf-note{margin:8px 2px;font-size:12px;line-height:1.55;color:var(--ink2)}'),
 ("reversal edge v18 · Saudi Core v2 · Z swing + market-momentum gate", "reversal edge v19 · Saudi Core v2 · daily + weekly Z swing"),
])

HTF = r'''
// ------------------------------------------------ v19 (round 33): weekly and monthly candles, stretch Z on that timeframe
// Weekly bars end on Thursday (the old Sat-Wed week falls in the same buckets); monthly = calendar months; each bar is drawn at its last session.
// Weekly stretch Z = the same formula on weekly bars (bar returns clipped at +-60%). Weekly Z swing: first weekly close <= -2.08 with ML rank >= 50%,
// market model positive and market momentum <= -1.18 -> 2013-19 85% winners +19.1% per trade, 2020-26 86% +11.2% (hold 40 sessions).
// Monthly (line -1.62) fires about 3 times a year: context only. Scales = liquid Saudi stocks 2013-2026.
UI.tf=["D","W","M"].includes(UI.tf)?UI.tf:"D";
const TF_LINE={W:-2.08,M:-1.62},TF_TOP={W:2.86,M:2.45},TF_NAME={W:"weekly",M:"monthly"},TF_Q=''' + json.dumps(TFQ) + r''';
let htf=null,HTF={};
function weekKey(t){const dt=new Date(t+"T00:00:00Z");dt.setUTCDate(dt.getUTCDate()+((4-dt.getUTCDay()+7)%7));return dt.toISOString().slice(0,10)}
function riyadhToday(){return new Date(Date.now()+3*36e5).toISOString().slice(0,10)}
function aggBars(d,tf,upto){const key=tf==="M"?(t=>t.slice(0,7)):weekKey,b={d:[],o:[],h:[],l:[],c:[],v:[],k:[]};let k0=null;const n=upto==null?d.d.length:upto+1;
 for(let i=0;i<n;i++){const c=d.c[i];if(!isF(c))continue;const k=key(d.d[i]),o=isF(d.o[i])?d.o[i]:c,h=isF(d.h[i])?d.h[i]:c,l=isF(d.l[i])?d.l[i]:c,v=d.v&&isF(d.v[i])?d.v[i]:0;
  if(k!==k0){k0=k;b.k.push(k);b.d.push(d.d[i]);b.o.push(o);b.h.push(h);b.l.push(l);b.c.push(c);b.v.push(v)}
  else{const j=b.d.length-1;b.d[j]=d.d[i];b.h[j]=Math.max(b.h[j],h);b.l[j]=Math.min(b.l[j],l);b.c[j]=c;b.v[j]+=v}}
 return b}
function barDone(b,tf){const j=b.d.length-1;if(j<0)return false;const t=riyadhToday();return tf==="W"?(b.d[j]===b.k[j]||t>b.k[j]):t.slice(0,7)>b.k[j]}
function weeklyZ(s,i){if(!s||!s.d||!s.c)return null;const b=aggBars(s,"W",i),n=b.d.length;if(n<125)return null;const z=stretchZ(b.c,.6),j=n-1;
 const done=i<s.d.length-1?weekKey(s.d[i+1])!==b.k[j]:barDone(b,"W");
 return {z:z[j],prev:z[j-1],done,end:b.d[j],first:done&&isF(z[j])&&isF(z[j-1])&&z[j]<=TF_LINE.W&&z[j-1]>TF_LINE.W}}
function drawHTF(){if(htf){htf.remove();htf=null}if(UI.tf==="D")return;const d=D(),lg=$("htf-legend");if(!d){if(lg)lg.innerHTML="";return}
 const tf=UI.tf,b=aggBars(d,tf),n=b.d.length,sa=msOn(st.sym);if(n<3){lg.innerHTML="";return}
 const zs=stretchZ(b.c,.6),vz=vwapZ(b,.6),ms=sa?b.d.map(msAt):b.d.map(()=>NaN),sma=new Array(n).fill(NaN),done=barDone(b,tf),line=TF_LINE[tf];
 for(let i=19;i<n;i++){let m=0;for(let k=i-19;k<=i;k++)m+=b.c[k];sma[i]=m/20}
 $("htf-wrap").style.height=(470+(sa?3:2)*115)+"px";
 htf=LW.createChart($("htf"),{autoSize:true,layout:{background:{type:"solid",color:C.surface},textColor:C.muted,fontFamily:"'JetBrains Mono',ui-monospace,monospace",fontSize:11,attributionLogo:true,panes:{separatorColor:C.axis,separatorHoverColor:"rgba(57,135,229,.3)",enableResize:true}},
  grid:{vertLines:{color:"#222220"},horzLines:{color:"#222220"}},crosshair:{mode:LW.CrosshairMode.Normal,vertLine:{labelBackgroundColor:"#2a2a28"},horzLine:{labelBackgroundColor:"#2a2a28"}},
  rightPriceScale:{borderColor:C.axis},timeScale:{borderColor:C.axis,rightOffset:4,barSpacing:tf==="M"?10:7,minBarSpacing:.4}});
 const L=a=>b.d.map((t,i)=>isF(a[i])?{time:t,value:a[i]}:{time:t}),dg=pdig(b.c[n-1]);
 const cs=htf.addSeries(LW.CandlestickSeries,{upColor:TV.up,downColor:TV.down,borderUpColor:TV.up,borderDownColor:TV.down,wickUpColor:TV.up,wickDownColor:TV.down,priceFormat:{type:"price",precision:dg,minMove:Math.pow(10,-dg)}},0);
 cs.setData(b.d.map((t,i)=>({time:t,open:b.o[i],high:b.h[i],low:b.l[i],close:b.c[i]})));
 const vs=htf.addSeries(LW.HistogramSeries,{priceScaleId:"vol",priceFormat:{type:"volume"},lastValueVisible:false,priceLineVisible:false},0);vs.priceScale().applyOptions({scaleMargins:{top:.84,bottom:0}});
 vs.setData(b.d.map((t,i)=>({time:t,value:b.v[i],color:b.c[i]>=b.o[i]?TV.upV:TV.downV})));
 htf.addSeries(LW.LineSeries,{color:"#ffffff",lineWidth:1.5,lastValueVisible:true,priceLineVisible:false,crosshairMarkerVisible:false,title:"20-bar mean"},0).setData(L(sma));
 const zS=htf.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:0},lineWidth:2,priceLineVisible:false,title:`Stretch Z (${TF_NAME[tf]})`,topLineColor:"#e66767",topFillColor1:"rgba(230,103,103,.12)",topFillColor2:"rgba(230,103,103,0)",bottomLineColor:"#4f96f0",bottomFillColor1:"rgba(57,135,229,0)",bottomFillColor2:"rgba(57,135,229,.18)",priceFormat:{type:"price",precision:2,minMove:.01}},1);zS.setData(L(zs));
 for(const [p,c,t] of [[TF_TOP[tf],"rgba(230,103,103,.7)",`+${TF_TOP[tf].toFixed(1)} top 1%`],[line,"rgba(79,150,240,.9)",`${line.toFixed(2)} extreme`]])zS.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t});
 htf.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:0},lineWidth:2,priceLineVisible:false,title:`VWAP Z (${TF_NAME[tf]}, untested)`,topLineColor:"#ffb74d",topFillColor1:"rgba(255,183,77,.12)",topFillColor2:"rgba(255,183,77,0)",bottomLineColor:"#4dd0e1",bottomFillColor1:"rgba(77,208,225,0)",bottomFillColor2:"rgba(77,208,225,.18)",priceFormat:{type:"price",precision:2,minMove:.01}},2).setData(L(vz));
 if(sa){const mS=htf.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:MS_GATE},lineWidth:2,priceLineVisible:false,title:"Market momentum (bar end)",topLineColor:"#e6a667",topFillColor1:"rgba(230,166,103,.10)",topFillColor2:"rgba(230,166,103,0)",bottomLineColor:"#4fd1a5",bottomFillColor1:"rgba(79,209,165,0)",bottomFillColor2:"rgba(79,209,165,.25)",priceFormat:{type:"price",precision:2,minMove:.01}},3);mS.setData(L(ms));
  for(const [p,c,t] of [[MS_GATE,"rgba(230,166,103,.9)","−1.18 dip buys below"],[MS_DEEP,"rgba(79,209,165,.9)","−2.53 deep"]])mS.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}
 const panes=htf.panes();if(panes.length>1){panes[0].setStretchFactor(3.4);for(let i=1;i<panes.length;i++)panes[i].setStretchFactor(1)}
 const mk=[];for(let i=1;i<n;i++)if(isF(zs[i])&&isF(zs[i-1])&&zs[i]<=line&&zs[i-1]>line)mk.push({time:b.d[i],position:"belowBar",shape:"arrowUp",color:"#4f96f0",text:i===n-1&&!done?"forming":tf==="W"?"W-Z":"M-Z"});
 LW.createSeriesMarkers(cs,mk);HTF={b,zs,vz,ms,done,tf};
 htf.timeScale().setVisibleLogicalRange({from:Math.max(0,n-(tf==="W"?260:n)),to:n+3});
 htf.subscribeCrosshairMove(p=>htfLegend(p&&p.point&&p.logical!=null?Math.round(p.logical):null));htfLegend(null);htfNote()}
function htfLegend(i0){const H=HTF,el=$("htf-legend");if(!H.b||!el)return;const b=H.b,n=b.d.length,i=i0==null||i0<0||i0>=n?n-1:i0,ch=i>0?b.c[i]/b.c[i-1]-1:NaN;
 const zs=H.zs[i],vz=H.vz[i],mm=H.ms[i],mz=msZone(mm),p=qCdf(TF_Q[H.tf],zs),part=i===n-1&&!H.done,nm=TF_NAME[H.tf];
 const rare=!isF(p)?"":p<=.5?`lower than ${(100*(1-p)).toFixed(p<.02?1:0)}% of ${nm} bars`:`higher than ${(100*p).toFixed(p>.98?1:0)}% of ${nm} bars`;
 el.innerHTML=`<div class="l1"><b>${esc(st.sym)}</b><span class="lk">${H.tf==="W"?"1W":"1M"}</span><span class="lk">${H.tf==="W"?"week to":"month to"} ${b.d[i]}${part?" (still forming)":""}</span><span><span class="lk">O</span> ${fp(b.o[i])}</span><span><span class="lk">H</span> ${fp(b.h[i])}</span><span><span class="lk">L</span> ${fp(b.l[i])}</span><span><span class="lk">C</span> ${fp(b.c[i])}</span><span class="${cl(ch)}">${spct(ch,2)}</span></div>
  <div class="l2"><span title="${esc(rare)}"><b>Stretch Z (${nm})</b> <span style="color:${!isF(zs)?"inherit":zs<=TF_LINE[H.tf]?"#4f96f0":zs<=-1?"#7fb2f0":zs>=2?"#e66767":"inherit"};font-weight:600">${fmt(zs,2)}</span></span><span class="lk">${esc(rare)}</span><span><b>VWAP Z</b> ${fmt(vz,2)}</span>${mz?`<span>mkt mom <span style="color:${mz.col};font-weight:600">${fmt(mm,2)}</span></span>`:""}</div>`}
function htfNote(){const el=$("htf-note");if(!el)return;
 el.innerHTML=UI.tf==="W"?`<b>Weekly candles</b> (weeks end on Thursday; the last candle is still forming until the week's final session). Blue arrows: first weekly close at or below the weekly extreme line (−2.08, 2% of weeks in 2013–19). <b>Weekly Z swing</b> (round 33): with the ML rank ≥ 50%, the market model positive and market momentum ≤ −1.18 on that Thursday, buying at the next open and selling 40 sessions later won 85% of trades in 2013–19 (+19.1% per trade) and 86% in 2020–26 (+11.2%); price only in 2004–12, +18.4%. About 6 in 10 of these trades coincide with a daily Z swing on the same stock; they share the 5 Z-swing slots. VWAP Z on this view uses 10/20/60 weekly bars and has no tested line.`
  :`<b>Monthly candles</b>. Blue arrows: first monthly close at or below −1.62 (2% of months in 2013–19). Too rare to trade (about 3 qualifying signals a year), so read it as context: where the stock stands against its own long history. VWAP Z on this view uses 10/20/60 monthly bars and has no tested line.`}
function setTF(tf){UI.tf=tf;saveUI();["D","W","M"].forEach(k=>{const e=$("tf-"+k);if(e)e.classList.toggle("on",k===tf)});const hd=tf!=="D";
 for(const id of ["lwc-wrap","ov","pn"]){const e=$(id);if(e)e.style.display=hd?"none":""}const sc=document.querySelector(".scrub");if(sc)sc.style.display=hd?"none":"";
 $("htf-wrap").style.display=hd?"":"none";$("htf-note").style.display=hd?"":"none";if(hd)drawHTF();else{if(htf){htf.remove();htf=null}if(chart)refreshOverlays()}}
["D","W","M"].forEach(k=>{const e=$("tf-"+k);if(e)e.addEventListener("click",()=>setTF(k))});
setTF(UI.tf);
'''
patch("app2.js", [
 ("function stretchZ(c){const n=c.length,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);\n for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-.25,Math.min(.25,a-b))}",
  "function stretchZ(c,clip=.25){const n=c.length,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);\n for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-clip,Math.min(clip,a-b))}"),
 ("function vwapZ(d){const n=d.c.length,c=d.c,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);\n for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-.25,Math.min(.25,a-b))}",
  "function vwapZ(d,clip=.25){const n=d.c.length,c=d.c,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);\n for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-clip,Math.min(clip,a-b))}"),
 ("function refreshOverlays(range){\n if(!chart)return;", "function refreshOverlays(range){\n if(UI.tf&&UI.tf!==\"D\"){try{drawHTF()}catch(e){console.error(e)}}\n if(!chart)return;"),
])
s = open("app2.js").read(); open("app2.js", "w").write(s + HTF)

FINROW = r'''${(()=>{const f=typeof MLPF!=="undefined"&&MLPF&&MLPF.fin?MLPF.fin[st.sym]:null;if(!f)return "";const m=v=>(v/1e6).toLocaleString(undefined,{maximumFractionDigits:0});return `<tr><td>latest annual accounts (FY${String(f.fy).slice(0,4)}, Yahoo)</td><td class="n">${f.ni>0?`profit SAR ${m(f.ni)}m`:`<b class="down">loss SAR ${m(f.ni)}m</b>`}${f.roe!=null?` · ROE ${(100*f.roe).toFixed(0)}%`:""}${f.de!=null?` · debt/equity ${f.de.toFixed(2)}`:""}${f.grew!=null?` · earnings ${f.grew?"up":"down"} on the year`:""}</td></tr>`})()}'''
WKROW = r'''${(()=>{const w=msOn(st.sym)?weeklyZ(s,i):null;return w&&isF(w.z)?`<tr><td>weekly stretch Z (week to ${w.end}${w.done?"":", still forming"})</td><td class="n"><b style="color:${w.z<=TF_LINE.W?"#4f96f0":"inherit"}">${fmt(w.z,2)}</b> · weekly line −2.08${w.first?" · <b>first weekly touch</b>":""}</td></tr>`:""})()}'''
patch("app3.js", [
 (':""}</table><div class="note">VWAP Z moves with stretch Z', ':""}' + WKROW + FINROW + '</table><div class="note">VWAP Z moves with stretch Z'),
 ("above it single-stock dips tended to keep falling.</div>`}", "above it single-stock dips tended to keep falling. Accounts: in 2023–26 (the only years Yahoo serves) dips in loss-making companies won 35–50% of the time against 51–72% for profitable ones: a caution, not a tested rule.</div>`}"),
 ("const ms=momStats(s,c),z=s.z250?s.z250[c]:NaN;let hi=-Infinity;for(let k=Math.max(0,c-53);k<=c;k++)hi=Math.max(hi,d.c[k]);",
  "const ms=momStats(s,c),z=s.z250?s.z250[c]:NaN;let hi=-Infinity;for(let k=Math.max(0,c-53);k<=c;k++)hi=Math.max(hi,d.c[k]);const WZc=msOn(st.sym)&&!(s.zcx&&s.zcx[c])?weeklyZ(s,c):null;"),
 ("  else say=`No trend signal. A breakout needs",
  r'''  else if(WZc&&WZc.first){const pct0=typeof MLPF!=="undefined"&&MLPF&&MLPF.ranks?MLPF.ranks[st.sym]:NaN,on=typeof MLPF!=="undefined"&&MLPF&&MLPF.pm>0,msv=msAt(d.d[c]),mok=!(msv>MS_GATE),ok=pct0>=.5&&on&&mok;
   cls=ok?"long":"";lab=ok?"Weekly Z swing":"Weekly Z extreme";
   say=`<b>Weekly stretch Z reached its extreme</b> (${fmt(WZc.z,2)} for the week to ${WZc.end}; the weekly line is −2.08, 2% of weeks). `+(ok?"<b>Weekly Z swing</b> (round 33): with the ML rank ≥ 50%, the market model positive and market momentum at or below −1.18, buying at the next open and selling 40 sessions later won 85% of trades in 2013–19 (+19.1% per trade) and 86% in 2020–26 (+11.2%). Plan: 5% of the account, no stop, sell at the open 40 sessions later; it shares the 5 Z-swing slots.":`Not a trade: it needs ${[!(pct0>=.5)?"an ML rank of at least 50%":"",!on?"the market model positive":"",!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)})`:""].filter(Boolean).join(" and ")}.`)}
  else say=`No trend signal. A breakout needs'''),
])
patch("app6.js", [
 ('function planFor(sym){const s=SY(sym);if(!s)return null;const i=s.d.length-1;if(i<s.first)return {sym,s,i,kind:"warm",rank:9};',
  'function planFor(sym){const s=SY(sym);if(!s)return null;const i=s.d.length-1;if(i<s.first)return {sym,s,i,kind:"warm",rank:9};const WZ=saudiSym(sym)&&!(s.zcx&&s.zcx[i])?weeklyZ(s,i):null;'),
 (' else if(s.zcx&&s.zcx[i]&&saudiSym(sym)&&!isIndex){const pct=', ' else if(((s.zcx&&s.zcx[i])||(WZ&&WZ.first))&&saudiSym(sym)&&!isIndex){const wko=!(s.zcx&&s.zcx[i]),pct='),
 ('action:ok?"Z-swing buy (5%, hold 40 sessions)":"skip: stretch-Z extreme without the filters"', 'action:ok?(wko?"Weekly Z-swing buy (5%, hold 40 sessions)":"Z-swing buy (5%, hold 40 sessions)"):(wko?"skip: weekly stretch-Z extreme without the filters":"skip: stretch-Z extreme without the filters")'),
 ('  good.push(`stretch Z touched the extreme line today (${s.zc[i].toFixed(2)}, ${zcRareTxt(s.zc[i])}). Z swing: first touches',
  '  good.push((wko?`weekly stretch Z first closed at or below −2.08 this week (${WZ.z.toFixed(2)}, week to ${WZ.end}). Weekly Z swing (round 33): 85% winners in 2013–19 (+19.1% per trade), 86% in 2020–26 (+11.2%). Daily rule for reference — `:`stretch Z touched the extreme line today (${s.zc[i].toFixed(2)}, ${zcRareTxt(s.zc[i])}). `)+`Z swing: first touches'),
 ('  if(!isF(msv))warn.push("market momentum unknown for this date (daily ML data not loaded): check it before buying");',
  '  if(!isF(msv))warn.push("market momentum unknown for this date (daily ML data not loaded): check it before buying");\n  {const f=MLPF&&MLPF.fin?MLPF.fin[sym]:null;if(f&&f.ni<=0)warn.push(`loss-making company (FY${String(f.fy).slice(0,4)}): in 2023–26 dips in loss-makers won 35–50% of the time vs 51–72% for profitable ones (one period only)`)}'),
 ('- MARKET MOMENTUM GATE (round 31):', '''- WEEKLY Z SWING (round 33, pre-registered): stretch Z on weekly candles (weeks end Thursday; same formula on weekly bars), first weekly close <= -2.08 (2% of weeks), ML >= 50%, market model > 0, market momentum <= -1.18, buy next open, hold 40 sessions: 2013-19 85% winners +19.1%/trade (25/yr), 2020-26 86% +11.2% (10/yr), price only 2004-12 +18.4%. 61% overlap with daily Z swing; adding it to the 5x5% sleeve: +3.3% -> +3.6%/yr, Sharpe 0.91 -> 0.97, DD -7% -> -5%. Monthly stretch Z (line -1.62) fires about 3 times a year: context only.
- FINANCIAL STRENGTH (round 33): steady dividend payers did not give better swings (Z swing 2013-19 78% vs 91% for non-payers; 2020-26 73% vs 69%; flips by period). Yahoo accounts exist only for FY2022-25: in 2023-26 dips in loss-making companies won 35-50% vs 51-72% for profitable ones, and high debt/equity was weaker; one period only, shown as a caution.
- MARKET MOMENTUM GATE (round 31):'''),
])
patch("app7.js", [
 ("entries skipped by the momentum gate won only 28% / 39% of the time.", "entries skipped by the momentum gate won only 28% / 39% of the time. <b>Weekly Z swing</b> (round 33): the same rule on weekly candles (weekly stretch Z first closing at or below −2.08 on a Thursday) won 85% / 86% of trades in 2013–19 / 2020–26 and shares the 5 Z-swing slots."),
 ('.join(", "):"none"}.`:""}${Array.isArray(MLPF.zactive)', '.join(", "):"none"}.`:""}${Array.isArray(MLPF.zwx)&&MLPF.wk_done?` Weekly stretch-Z extremes this week: ${MLPF.zwx.length?MLPF.zwx.map(z=>`${esc(nameOf(z.sym))} (weekly Z ${z.zw.toFixed(2)}, ML ${Math.round(100*z.pct)}%${z.ok?\', <span class="up">weekly Z-swing buy</span>\':\', no trade\'})`).join(", "):"none"}.`:""}${Array.isArray(MLPF.zactive)'),
 ("${esc(nameOf(z.sym))} since ${esc(z.signal)}", '${esc(nameOf(z.sym))}${z.tf==="W"?" (weekly)":""} since ${esc(z.signal)}'),
 ('if(d.id==="latest"){MLPF=d.data();try{drawML()}catch(e){};', 'if(d.id==="latest"){MLPF=d.data();try{drawML()}catch(e){};try{if(UI.tf&&UI.tf!=="D")drawHTF()}catch(e){};'),
])
SEC = '''<h2>v19 (round 33): weekly and monthly candles, and do financially strong companies swing better?</h2>
<p><b>Stretch Z on weekly candles works.</b> Same formula on weekly bars (weeks end Thursday); the weekly extreme line is −2.08 (2% of weeks in 2013–19). With the Z-swing filters (ML rank ≥ 50%, market model positive, market momentum ≤ −1.18), buying at the next open and selling 40 sessions later:</p>
<table class="t"><tr><th style="text-align:left">signal</th><th>2013–19</th><th>2020–26</th><th>2004–12 (price only)</th></tr>
<tr><td style="text-align:left">daily Z swing (round 31)</td><td>86% winners, +19.9%</td><td>70%, +6.9%</td><td>+3.7%</td></tr>
<tr><td style="text-align:left"><b>weekly Z swing</b></td><td><b>85%, +19.1%</b> (25 a year)</td><td><b>86%, +11.2%</b> (10 a year)</td><td><b>+18.4%</b></td></tr>
<tr><td style="text-align:left">monthly (line −1.62)</td><td colspan="3">about 3 qualifying signals a year: too rare to trade, context only</td></tr></table>
<p>About 6 in 10 weekly trades coincide with a daily Z swing on the same stock; the rest (2013–19 72% winners, 2020–26 87%) are new. Added to the 5 × 5% Z-swing sleeve: +3.3% → +3.6% a year, Sharpe 0.91 → 0.97, worst drawdown −7% → −5%. The weekly signal is now part of the daily list and the plan. Use the <b>Daily / Weekly / Monthly</b> buttons above the chart.</p>
<p><b>Financially strong companies?</b> Full financial statements are not reachable from this environment; Yahoo serves only FY2022–25. Over the full history the test used dividends: <b>steady dividend payers did not give better swings</b> (Z swing 2013–19: 78% winners vs 91% for non-payers; 2020–26: 73% vs 69%; plain dips flipped between periods). With the four years of accounts (2023–26 entries only): dips in <b>loss-making</b> companies won 35–50% of the time against 51–72% for profitable ones, and highly indebted companies were weaker. One period cannot confirm a rule, so the terminal and the daily list show each pick's latest accounts and flag loss-makers, without filtering them out.</p>
'''
s = open("app5.js").read(); a = "<h2>v18 (round 31)"; assert s.count(a) == 1; open("app5.js", "w").write(s.replace(a, SEC + a))
print("patched v19")
# the Momentum Pulse glow is drawn with a radial gradient; skip it when the (hidden) daily chart has no size
patch("app2.js", [("if(Math.abs(o.st)===2){const g=ctx.createRadialGradient(", "if(Math.abs(o.st)===2&&isF(x)&&isF(y)&&isF(r)){const g=ctx.createRadialGradient(")])
print("patched v19 b")
