// ------------------------------------------------ chart (TradingView Lightweight Charts)
// Adaptive z-zones: shaded bands between this stock's own z-score percentiles, drawn by a custom series.
class ZoneView{
 constructor(){this.d=null}
 renderer(){const me=this;return {draw(target,pc){const d=me.d;if(!d||!d.visibleRange)return;
  target.useBitmapCoordinateSpace(({context:ctx,horizontalPixelRatio:hr,verticalPixelRatio:vr})=>{
   const bars=d.bars,from=Math.max(0,d.visibleRange.from-1),to=Math.min(bars.length,d.visibleRange.to+1),half=d.barSpacing/2;
   const bands=[[0,1,"rgba(57,135,229,.30)"],[1,2,"rgba(57,135,229,.12)"],[3,4,"rgba(230,103,103,.12)"],[4,5,"rgba(230,103,103,.30)"]];
   for(const [a,b,col] of bands){ctx.fillStyle=col;let seg=[];
    const flush=()=>{if(seg.length>0){ctx.beginPath();seg.forEach((p,k)=>{const x=(k===0?p.x-half:p.x)*hr,y=pc(p.q[b])*vr;k?ctx.lineTo(x,y):ctx.moveTo(x,y)});const L=seg[seg.length-1];ctx.lineTo((L.x+half)*hr,pc(L.q[b])*vr);ctx.lineTo((L.x+half)*hr,pc(L.q[a])*vr);
     for(let k=seg.length-1;k>=0;k--){const p=seg[k];ctx.lineTo((k===0?p.x-half:p.x)*hr,pc(p.q[a])*vr)}ctx.closePath();ctx.fill()}seg=[]};
    for(let i=from;i<to;i++){const bb=bars[i],q=bb.originalData.q;if(q&&isF(q[a])&&isF(q[b])&&pc(q[a])!=null&&pc(q[b])!=null)seg.push({x:bb.x,q});else flush()}flush()}
   for(const [k,col] of [[0,"rgba(79,150,240,.75)"],[5,"rgba(240,110,110,.75)"]]){ctx.strokeStyle=col;ctx.lineWidth=Math.max(1,hr);ctx.setLineDash([4*hr,3*hr]);ctx.beginPath();let pen=false;
    for(let i=from;i<to;i++){const bb=bars[i],q=bb.originalData.q;const y=q&&isF(q[k])?pc(q[k]):null;if(y==null){pen=false;continue}const x=bb.x*hr;pen?ctx.lineTo(x,y*vr):ctx.moveTo(x,y*vr);pen=true}ctx.stroke()}
   ctx.setLineDash([])})}}}
 update(data){this.d=data}
 priceValueBuilder(row){return [row.q[1],row.q[4],row.q[2]]}
 isWhitespace(row){return !row.q}
 defaultOptions(){return Object.assign({},LW.customSeriesDefaultOptions,{lastValueVisible:false,priceLineVisible:false})}
}
// ------------------------------------------------ Momentum Pulse pane (custom renderer)
// Colours validated for colour-blind separation on the dark surface: teal up, red down, amber exhaustion (glow dots), violet divergence (dashed, labelled).
const PC={up:[38,166,154],dn:[239,83,80],ex:[217,154,30],dv:[167,123,234],mid:[120,120,115]};
const prgb=(c,a)=>`rgba(${c[0]},${c[1]},${c[2]},${a})`;
const mix=(a,b,t)=>[0,1,2].map(k=>Math.round(a[k]+(b[k]-a[k])*t));
class PulseView{
 constructor(){this.d=null}
 renderer(){const me=this;return {draw(target,pc){const d=me.d;if(!d||!d.visibleRange)return;
  target.useBitmapCoordinateSpace(({context:ctx,horizontalPixelRatio:hr,verticalPixelRatio:vr,bitmapSize})=>{
   const bars=d.bars,from=Math.max(1,d.visibleRange.from-1),to=Math.min(bars.length,d.visibleRange.to+1),hw=Math.max(1,d.barSpacing*hr/2),H=bitmapSize.height,W=bitmapSize.width;
   const Y=v=>{const y=pc(v);return y==null?null:y*vr},X=i=>bars[i].x*hr,od=i=>bars[i].originalData;
   // 1 regime columns
   for(let i=from;i<to;i++){const o=od(i);if(!o||!o.st)continue;const col=o.st===1?prgb(PC.up,.09):o.st===-1?prgb(PC.dn,.09):prgb(PC.ex,.13);ctx.fillStyle=col;ctx.fillRect(X(i)-hw,0,hw*2,H)}
   // 2 guides: zero, ±1, ±2, and the stock's own 95th/5th percentile extremes
   ctx.lineWidth=Math.max(1,hr);for(const [v,dash,a] of [[0,[],.55],[1,[4,4],.25],[-1,[4,4],.25],[2,[1,4],.3],[-2,[1,4],.3]]){const y=Y(v);if(y==null)continue;ctx.setLineDash(dash.map(x=>x*hr));ctx.strokeStyle=`rgba(195,194,183,${a})`;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}
   ctx.setLineDash([2*hr,3*hr]);ctx.strokeStyle=prgb(PC.ex,.55);for(const key of ["q95","q05"]){ctx.beginPath();let pen=false;for(let i=from;i<to;i++){const o=od(i),y=o&&isF(o[key])?Y(o[key]):null;if(y==null){pen=false;continue}pen?ctx.lineTo(X(i),y):ctx.moveTo(X(i),y);pen=true}ctx.stroke()}ctx.setLineDash([]);
   // 3 acceleration histogram (momentum of momentum)
   const y0=Y(0);if(y0!=null)for(let i=from;i<to;i++){const o=od(i);if(!o||!isF(o.acc))continue;const y=Y(o.acc);if(y==null)continue;ctx.fillStyle=o.acc>=0?prgb(PC.up,.28):prgb(PC.dn,.28);const w=Math.max(1,hw*1.1);ctx.fillRect(X(i)-w/2,Math.min(y,y0),w,Math.abs(y-y0))}
   // 4 multi-horizon ribbon (5/10/20/60-day momentum), colour by agreement, opacity by path efficiency
   for(let i=from;i<to-1;i++){const a=od(i),b=od(i+1);if(!a||!b||!isF(a.lo)||!isF(b.lo))continue;const ya=Y(a.lo),yb=Y(b.lo),za=Y(a.hi),zb=Y(b.hi);if([ya,yb,za,zb].some(v=>v==null))continue;
    const base=a.al===4?PC.up:a.al===-4?PC.dn:PC.dv,al=Math.abs(a.al)===4?.12+.42*Math.min(1,Math.max(0,a.er||0)):.10;ctx.fillStyle=prgb(base,al);
    ctx.beginPath();ctx.moveTo(X(i),za);ctx.lineTo(X(i+1),zb);ctx.lineTo(X(i+1),yb);ctx.lineTo(X(i),ya);ctx.closePath();ctx.fill()}
   // 5 composite line with diverging colour and a soft glow
   ctx.lineWidth=2.4*hr;ctx.lineCap="round";ctx.shadowBlur=7*hr;
   for(let i=from;i<to-1;i++){const a=od(i),b=od(i+1);if(!a||!b||!isF(a.M)||!isF(b.M))continue;const ya=Y(a.M),yb=Y(b.M);if(ya==null||yb==null)continue;
    const m=(a.M+b.M)/2,t=Math.min(1,Math.abs(m)/2.2),c=mix(PC.mid,m>=0?PC.up:PC.dn,t);ctx.strokeStyle=prgb(c,1);ctx.shadowColor=prgb(c,.55);ctx.beginPath();ctx.moveTo(X(i),ya);ctx.lineTo(X(i+1),yb);ctx.stroke()}
   ctx.shadowBlur=0;
   // 6 thrusts (triangles) and exhaustion (glowing amber dots)
   for(let i=from;i<to;i++){const o=od(i);if(!o)continue;const y=isF(o.M)?Y(o.M):null;if(y==null)continue;const x=X(i),r=Math.max(4*hr,hw*.9);
    if(o.th){ctx.fillStyle=rgba(o.th>0?PC.up:PC.dn,1);ctx.strokeStyle="#1a1a19";ctx.lineWidth=1.5*hr;ctx.beginPath();const yy=o.th>0?y+r*2.2:y-r*2.2;ctx.moveTo(x,o.th>0?yy-r:yy+r);ctx.lineTo(x-r,o.th>0?yy+r*.7:yy-r*.7);ctx.lineTo(x+r,o.th>0?yy+r*.7:yy-r*.7);ctx.closePath();ctx.fill();ctx.stroke()}
    if(Math.abs(o.st)===2){const g=ctx.createRadialGradient(x,y,0,x,y,r*3);g.addColorStop(0,prgb(PC.ex,.95));g.addColorStop(.35,prgb(PC.ex,.55));g.addColorStop(1,prgb(PC.ex,0));ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r*3,0,Math.PI*2);ctx.fill();
     ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(x,y,r*.45,0,Math.PI*2);ctx.fill()}}
   // 7 divergences: dashed violet line between the two momentum pivots, labelled
   ctx.font=`${11*hr}px "JetBrains Mono",monospace`;
   for(let i=from;i<Math.min(bars.length,to+70);i++){const o=od(i);if(!o||!o.dv)continue;const i0=i-o.dv.b0,i1=i-o.dv.b1;if(i0<0||i1<0||i1<from-1)continue;const y0=Y(o.dv.M0),y1=Y(o.dv.M1);if(y0==null||y1==null)continue;
    const col=prgb(PC.dv,1);ctx.strokeStyle=col;ctx.lineWidth=2*hr;ctx.setLineDash([5*hr,3*hr]);ctx.beginPath();ctx.moveTo(X(i0),y0);ctx.lineTo(X(i1),y1);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=col;for(const [xx,yy] of [[X(i0),y0],[X(i1),y1]]){ctx.beginPath();ctx.arc(xx,yy,3.2*hr,0,Math.PI*2);ctx.fill()}
    ctx.fillText(o.dv.type>0?"bull div":"bear div",X(i1)+5*hr,y1+(o.dv.type>0?14:-6)*hr)}
  })}}}
 update(data){this.d=data}
 priceValueBuilder(r){return [Math.min(r.lo,-2.2),Math.max(r.hi,2.2),r.M]}
 isWhitespace(r){return !isF(r.M)}
 defaultOptions(){return Object.assign({},LW.customSeriesDefaultOptions,{lastValueVisible:true,priceLineVisible:false,title:"pulse",color:"#c3c2b7"})}
}
// divergence lines on the price pane, between the two price pivots
class PriceDivView{
 constructor(){this.d=null}
 renderer(){const me=this;return {draw(target,pc){const d=me.d;if(!d||!d.visibleRange)return;
  target.useBitmapCoordinateSpace(({context:ctx,horizontalPixelRatio:hr,verticalPixelRatio:vr})=>{const bars=d.bars,from=Math.max(0,d.visibleRange.from),to=Math.min(bars.length,d.visibleRange.to+70);
   ctx.font=`${11*hr}px "JetBrains Mono",monospace`;
   for(let i=from;i<to;i++){const o=bars[i].originalData;if(!o||!o.dv)continue;const i0=i-o.dv.b0,i1=i-o.dv.b1;if(i0<0||i1<0)continue;const y0=pc(o.dv.p0),y1=pc(o.dv.p1);if(y0==null||y1==null)continue;
    ctx.strokeStyle=prgb(PC.dv,.95);ctx.lineWidth=2*hr;ctx.setLineDash([5*hr,3*hr]);ctx.beginPath();ctx.moveTo(bars[i0].x*hr,y0*vr);ctx.lineTo(bars[i1].x*hr,y1*vr);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=prgb(PC.dv,1);ctx.fillText(o.dv.type>0?"bull div":"bear div",bars[i1].x*hr+5*hr,y1*vr+(o.dv.type>0?16:-8)*hr)}})}}}
 update(data){this.d=data}
 priceValueBuilder(r){return [r.dv.p1]}
 isWhitespace(r){return !r.dv}
 defaultOptions(){return Object.assign({},LW.customSeriesDefaultOptions,{lastValueVisible:false,priceLineVisible:false})}
}
const PULSE_STATE={1:"TREND UP",[-1]:"TREND DOWN",2:"EXHAUSTION UP",[-2]:"EXHAUSTION DOWN",0:"NO TREND"};
function pulseAdvice(s,i){const P=s.pulse,st0=P.state[i],momMkt=s.mode[i]===-1,div=recentDiv(P,i);let a,tone;
 if(momMkt){
  if(st0===1){a="Momentum market in an up-trend: favour momentum entries, don't fade strength.";tone="good"}
  else if(st0===-1){a="Momentum market falling: avoid buying dips here; they tend to keep falling.";tone="bad"}
  else if(st0===2){a="Up-move at a 2-year momentum extreme and turning: a warning to tighten, not a proven sell signal.";tone="mid"}
  else if(st0===-2){a="Down-move at a 2-year extreme and turning: possible exhaustion; no proven edge on its own.";tone="mid"}
  else{a="Momentum market without a trend: wait for a strong close (momentum setup).";tone="mid"}
  a="Avoid mean reversion: this market keeps moving the same way day to day. "+a}
 else{
  if(st0===-1){a="Strong down-momentum. In tests on 87 stocks and 6 long histories, reversal setups in this state did better (+1.70% vs +1.09% per trade): capitulation, not a reason to avoid.";tone="good"}
  else if(st0===1){a="Strong up-momentum on a reverting stock: the next 10 days were weaker than average in tests (−0.31%, t −2.4). Don't chase.";tone="bad"}
  else if(st0===2){a="Up-momentum at a 2-year extreme and turning: a warning, no proven edge on its own.";tone="mid"}
  else if(st0===-2){a="Down-momentum at a 2-year extreme and turning: exhaustion often lines up with reversal setups.";tone="mid"}
  else{a="No dominant momentum: mean reversion rules apply normally.";tone="mid"}}
 const own=pulseEvidence(s,i).find(e=>e.k===String(st0));if(own&&own.cnt>=30&&st0!==0){const exp=st0===1?(momMkt?1:-1):st0===-1?(momMkt?-1:1):0;
  if(exp&&Math.sign(own.ex)!==exp)a+=` <i>On this ${momMkt?"market":"stock"} the state has behaved differently: the next 10 days averaged ${spct(own.ex,2)} vs normal (${own.cnt} days). See the inspector.</i>`}
 if(div)a+=` ${div>0?"Bullish":"Bearish"} divergence confirmed in the last 10 bars (shown for context; not a reliable signal in tests).`;
 return {a,tone}}
function recentDiv(P,i){for(let k=i;k>=Math.max(0,i-10);k--)if(P.div[k])return P.div[k];return 0}
function pulseEvidence(s,i){const P=s.pulse,cnt={},sum={};let base=0,nb=0;
 for(let j=0;j+10<=i;j++){const f=P.f10[j];if(!isF(f)||!isF(P.M[j]))continue;base+=f;nb++;const ks=[String(P.state[j])];if(P.thrust[j]===1)ks.push("th");if(P.div[j]===1)ks.push("bd");if(P.div[j]===-1)ks.push("sd");for(const k of ks){cnt[k]=(cnt[k]||0)+1;sum[k]=(sum[k]||0)+f}}
 const b=nb?base/nb:0;return [["1","trend up"],["-1","trend down"],["0","no trend"],["2","exhaustion up"],["-2","exhaustion down"],["th","up-thrust"],["bd","bullish divergence"],["sd","bearish divergence"]].map(([k,n])=>({k,n,cnt:cnt[k]||0,ex:cnt[k]?sum[k]/cnt[k]-b:NaN}))}
function placePulseHud(){const hud=$("pulse-hud");if(!chart||SER.pulsePane==null||!UI.pn.pulse){hud.hidden=true;return}
 try{const el=chart.panes()[SER.pulsePane].getHTMLElement(),r=el.getBoundingClientRect(),w=$("lwc-wrap").getBoundingClientRect();hud.style.top=(r.top-w.top+4)+"px";hud.style.left="8px";hud.hidden=false}catch(e){hud.hidden=true}}
function renderPulseHud(i){const hud=$("pulse-hud"),s=S();if(!s||!s.pulse||!UI.pn.pulse){hud.hidden=true;return}placePulseHud();
 const P=s.pulse,M=P.M[i],st0=P.state[i],al=P.align[i]*(M>=0?1:-1),acc=P.acc[i],col=st0===1?"#26a69a":st0===-1?"#ef5350":Math.abs(st0)===2?"#d99a1e":"#c3c2b7";
 hud.innerHTML=`<b>MOMENTUM PULSE</b> <span style="color:${M>=0?"#26a69a":"#ef5350"}">${isF(M)?(M>=0?"+":"")+M.toFixed(2)+"σ":"—"} ${isF(acc)?(acc>0?"▲ accelerating":"▼ decelerating"):""}</span>
  <span class="pk">horizons</span> ${P.mh.map(a=>isF(a[i])?`<i style="background:${a[i]>=0?"#26a69a":"#ef5350"};opacity:${Math.min(1,.35+Math.abs(a[i])/3)}"></i>`:"<i></i>").join("")} ${Math.abs(al)}/4
  <span class="pk">path</span> ${isF(P.er[i])?Math.round(100*P.er[i])+"%":"—"} <span class="pk">rank</span> ${isF(P.pct[i])?Math.round(100*P.pct[i])+"%":"—"}
  <span class="st" style="color:${col};border-color:${col}">${PULSE_STATE[st0]}</span>${s.mode[i]===-1?'<span class="st" style="color:#a77bea;border-color:#a77bea">AVOID MEAN REVERSION</span>':""}`}

let chart=null,SER={},MK=null,PLINES=[],ARR=null,hoverIdx=null;
const OVL=[["bb","Bollinger Bands (20, 2)","#7aa7e0"],["zones","Stock-specific zones","#3987e5"],["mean","20-day mean","#ffffff"],["exit","5-day average (exit line)","#fab219"],["kalman","Kalman",C.mean.kalman],["trend","Trend",C.mean.trend],["ou","OU (price)",C.mean.ou],["ema20","EMA 20",C.mean.ema20],["factor","Market residual",C.mean.factor],
 ["vol","Volume","#5d6b78"],["setups","Setups","#8a8a85"],["sys","System trades","#4fd1a5"],["signs","Reversal signs","#fab219"],["pdiv","Divergence lines","#a77bea"],["mine","My trades",TV.you]];
const PNS=[["pulse","Momentum Pulse"],["edge","Reversal edge"],["rsi","RSI(2)"],["z","Z-zones"],["vol","Volatility"],["reg","Regime"],["fear","Fear (VIX)"]];
$("ov").innerHTML=`<span class="lab">on price</span>`+OVL.map(([k,n,c])=>`<label><input type="checkbox" data-ov="${k}" ${UI.ov[k]?"checked":""}><span style="color:${c}">■</span>${n}</label>`).join("");
$("pn").innerHTML=`<span class="lab">panels</span>`+PNS.map(([k,n])=>`<label><input type="checkbox" data-pn="${k}" ${UI.pn[k]?"checked":""}>${n}</label>`).join("");
$("ov").addEventListener("change",e=>{const k=e.target.dataset.ov;if(!k)return;UI.ov[k]=e.target.checked;saveUI();applyVisibility();annotate()});
$("pn").addEventListener("change",e=>{const k=e.target.dataset.pn;if(!k)return;UI.pn[k]=e.target.checked;saveUI();buildChart(true)});

function buildArrays(){
 const d=D();if(!d)return null;const s=S(),n=d.d.length,A={n};
 A.candle=d.d.map((t,i)=>({time:t,open:d.o[i],high:d.h[i],low:d.l[i],close:d.c[i]}));
 A.vol=d.d.map((t,i)=>isF(d.v[i])?{time:t,value:d.v[i],color:d.c[i]>=d.o[i]?TV.upV:TV.downV}:{time:t});
 const L=a=>d.d.map((t,i)=>a&&isF(a[i])?{time:t,value:a[i]}:{time:t});
 const lc=d.c.map(Math.log),m20=new Array(n).fill(NaN),s20=new Array(n).fill(NaN),sma5=new Array(n).fill(NaN);
 for(let i=19;i<n;i++){let m=0;for(let k=i-19;k<=i;k++)m+=lc[k];m/=20;let v=0;for(let k=i-19;k<=i;k++)v+=(lc[k]-m)**2;m20[i]=m;s20[i]=Math.sqrt(v/19)}
 for(let i=4;i<n;i++){let m=0;for(let k=i-4;k<=i;k++)m+=d.c[k];sma5[i]=m/5}
 A.atr=new Array(n).fill(NaN);let a=NaN;for(let i=0;i<n;i++){const tr=i?Math.max(d.h[i]-d.l[i],Math.abs(d.h[i]-d.c[i-1]),Math.abs(d.l[i]-d.c[i-1])):d.h[i]-d.l[i];a=isF(a)?a+(tr-a)/14:tr;A.atr[i]=a}
 A.meanArr=m20.map(Math.exp);A.sma5Arr=s?s.sma5:sma5;A.zArr=s?s.z20:lc.map((x,i)=>(x-m20[i])/s20[i]);
 A.mean=L(A.meanArr);A.exit=L(A.sma5Arr);
 A.zones=d.d.map((t,i)=>{if(!s)return {time:t};const q=s.zq.map(z=>isF(z[i])?Math.exp(s.m20[i]+z[i]*s.s20[i]):NaN);return q.every(isF)?{time:t,q}:{time:t}});
 {const U=[],M=[],Lo=[];for(let i=0;i<n;i++){const b=bbAt(d.c,i);U.push(b?b.up:NaN);M.push(b?b.mid:NaN);Lo.push(b?b.lo:NaN)}A.bbu=L(U);A.bbm=L(M);A.bbl=L(Lo)}
 A.kalman=L(s&&s.lv_kalman);A.trend=L(s&&s.lv_trend);A.ou=L(s&&s.lv_ou);A.ema20=L(s&&s.lv_ema20);A.factor=L(s&&s.lv_factor);
 A.edgeH=d.d.map((t,i)=>s&&s.setup[i]&&isF(s.score[i])?{time:t,value:s.score[i],color:THIRD_COL[thirdOf(s.score[i])]}:{time:t});
 A.edgeL=L(s&&s.score);
 A.rsi=L(s?s.rsi2:null);
 A.z=L(A.zArr);for(let k=0;k<6;k++)A["zq"+k]=L(s&&s.zq[k]);
 if(s&&s.pulse){const P=s.pulse;A.pulse=d.d.map((t,i)=>{if(!isF(P.M[i]))return {time:t};const mh=P.mh.map(a=>a[i]),ok=mh.every(isF);
   const o={time:t,M:P.M[i],lo:ok?Math.min(...mh,P.M[i]):P.M[i],hi:ok?Math.max(...mh,P.M[i]):P.M[i],al:P.align[i]*(P.M[i]>=0?1:-1),er:P.er[i],acc:P.acc[i],st:P.state[i],th:P.thrust[i],q95:P.q95[i],q05:P.q05[i]};
   if(P.div[i])o.dv={type:P.div[i],b0:i-P.dp0[i],b1:i-P.dp1[i],M0:P.M[P.dp0[i]],M1:P.M[P.dp1[i]]};return o});
  A.pdiv=d.d.map((t,i)=>P.div[i]?{time:t,dv:{type:P.div[i],b0:i-P.dp0[i],b1:i-P.dp1[i],p0:P.div[i]>0?d.l[P.dp0[i]]:d.h[P.dp0[i]],p1:P.div[i]>0?d.l[P.dp1[i]]:d.h[P.dp1[i]]}}:{time:t})}
 else{A.pulse=d.d.map(t=>({time:t}));A.pdiv=d.d.map(t=>({time:t}))}
 A.yz=L(s&&s.yz20);A.garch=L(s&&s.garch);A.har=L(s&&s.har5);A.cc=L(s&&s.cc20);
 A.hurst=L(s&&s.hurst);A.adf=L(s&&s.adf);A.vr4=L(s&&s.vr4);A.vix=L(s&&s.vix);
 return A}
function buildChart(keep){
 const range=keep&&chart?chart.timeScale().getVisibleLogicalRange():null;
 if(chart){chart.remove();chart=null}
 const np=Object.values(UI.pn).filter(Boolean).length;$("lwc-wrap").style.height=(470+np*105+(UI.pn.pulse?60:0))+"px";
 chart=LW.createChart($("lwc"),{autoSize:true,
  layout:{background:{type:"solid",color:C.surface},textColor:C.muted,fontFamily:"'JetBrains Mono',ui-monospace,monospace",fontSize:11,attributionLogo:true,panes:{separatorColor:C.axis,separatorHoverColor:"rgba(57,135,229,.3)",enableResize:true}},
  grid:{vertLines:{color:"#222220"},horzLines:{color:"#222220"}},
  crosshair:{mode:LW.CrosshairMode.Normal,vertLine:{labelBackgroundColor:"#2a2a28"},horzLine:{labelBackgroundColor:"#2a2a28"}},
  rightPriceScale:{borderColor:C.axis},timeScale:{borderColor:C.axis,rightOffset:8,barSpacing:7,minBarSpacing:.4}});
 const line=(color,o={},pane=0)=>chart.addSeries(LW.LineSeries,Object.assign({color,lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false},o),pane);
 SER={};
 SER.zones=chart.addCustomSeries(new ZoneView(),{},0);
 SER.candle=chart.addSeries(LW.CandlestickSeries,{upColor:TV.up,downColor:TV.down,borderUpColor:TV.up,borderDownColor:TV.down,wickUpColor:TV.up,wickDownColor:TV.down},0);
 SER.vol=chart.addSeries(LW.HistogramSeries,{priceScaleId:"vol",priceFormat:{type:"volume"},lastValueVisible:false,priceLineVisible:false},0);SER.vol.priceScale().applyOptions({scaleMargins:{top:.84,bottom:0}});
 for(const k of ["kalman","trend","ou","ema20","factor"])SER[k]=line(C.mean[k]);
 SER.bbu=line("rgba(122,167,224,.9)",{title:"BB",lastValueVisible:true});SER.bbl=line("rgba(122,167,224,.9)",{lastValueVisible:true});SER.bbm=line("rgba(122,167,224,.55)",{lineStyle:LW.LineStyle.Dotted});
 SER.exit=line("#fab219",{lineWidth:1,lineStyle:LW.LineStyle.Dashed,title:"5d avg",lastValueVisible:true});
 SER.mean=line("#ffffff",{lineWidth:2,title:"20d mean",lastValueVisible:true,crosshairMarkerVisible:true});
 let pane=1;const P={};
 SER.pdiv=chart.addCustomSeries(new PriceDivView(),{},0);
 if(UI.pn.pulse){P.pulse=pane++;SER.pulse=chart.addCustomSeries(new PulseView(),{priceFormat:{type:"price",precision:2,minMove:.01}},P.pulse);SER.pulsePane=P.pulse}else SER.pulsePane=null;
 if(UI.pn.edge){P.edge=pane++;SER.edgeL=line("rgba(195,194,183,.35)",{},P.edge);SER.edgeH=chart.addSeries(LW.HistogramSeries,{lastValueVisible:false,priceLineVisible:false,title:"edge score",priceFormat:{type:"price",precision:1,minMove:.1}},P.edge);
  SER.edgeL.createPriceLine({price:THIRDS[1],color:"rgba(79,209,165,.6)",lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:"top ⅓"});SER.edgeL.createPriceLine({price:THIRDS[0],color:"rgba(138,138,133,.6)",lineWidth:1,lineStyle:LW.LineStyle.Dotted,axisLabelVisible:false})}
 if(UI.pn.rsi){P.rsi=pane++;SER.rsi=line("#c3c2b7",{lineWidth:1.5,title:"RSI(2)",lastValueVisible:true,priceFormat:{type:"price",precision:0,minMove:1}},P.rsi)}
 if(UI.pn.z){P.z=pane++;const zc=["rgba(79,150,240,.9)","rgba(79,150,240,.55)","rgba(79,150,240,.3)","rgba(240,110,110,.3)","rgba(240,110,110,.55)","rgba(240,110,110,.9)"];
  for(let k=0;k<6;k++)SER["zq"+k]=line(zc[k],{lineStyle:k===0||k===5?LW.LineStyle.Solid:LW.LineStyle.Dashed},P.z);
  SER.z=chart.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:0},lineWidth:2,priceLineVisible:false,title:"z20",topLineColor:"#e66767",topFillColor1:"rgba(230,103,103,.18)",topFillColor2:"rgba(230,103,103,0)",bottomLineColor:"#4f96f0",bottomFillColor1:"rgba(57,135,229,0)",bottomFillColor2:"rgba(57,135,229,.18)",priceFormat:{type:"price",precision:2,minMove:.01}},P.z)}
 if(UI.pn.vol){P.vol=pane++;SER.cc=line("rgba(137,135,129,.6)",{},P.vol);SER.yz=line("#3987e5",{lineWidth:1.5,title:"YZ20",lastValueVisible:true},P.vol);SER.garch=line("#fab219",{lineWidth:1.5,title:"GARCH",lastValueVisible:true},P.vol);SER.har=line("#c08cff",{title:"HAR 5d",lastValueVisible:true},P.vol)}
 if(UI.pn.reg){P.reg=pane++;SER.hurst=line(C.ink,{lineWidth:1.5,title:"Hurst",lastValueVisible:true},P.reg);SER.adf=line(C.mean.ou,{title:"ADF p",lastValueVisible:true},P.reg);SER.vr4=line(C.mean.kalman,{title:"VR(4)",lastValueVisible:true},P.reg);
  SER.hurst.createPriceLine({price:.5,color:C.axis,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:false})}
 if(UI.pn.fear){P.fear=pane++;SER.vix=line("#d55181",{lineWidth:1.5,title:"VIX",lastValueVisible:true},P.fear)}
 const panes=chart.panes();if(panes.length>1){panes[0].setStretchFactor(3.6);for(let i=1;i<panes.length;i++)panes[i].setStretchFactor(i===P.pulse?1.7:1)}
 MK=LW.createSeriesMarkers(SER.candle,[]);PLINES=[];
 chart.subscribeCrosshairMove(onCross);chart.subscribeClick(onChartClick);
 refreshOverlays(range);if(!range)showRange()}
const DKEYS=["bbu","bbm","bbl","pdiv","pulse","zones","candle","vol","mean","exit","kalman","trend","ou","ema20","factor","edgeH","edgeL","rsi","z","zq0","zq1","zq2","zq3","zq4","zq5","yz","garch","har","cc","hurst","adf","vr4","vix"];
function setAllData(upto){if(!ARR)return;for(const k of DKEYS)if(SER[k]&&ARR[k])SER[k].setData(upto>=ARR.n-1?ARR[k]:ARR[k].slice(0,upto+1))}
function stepData(i){for(const k of DKEYS)if(SER[k]&&ARR[k]&&ARR[k][i])SER[k].update(ARR[k][i])}
function applyVisibility(){const v=UI.ov,set=(k,on)=>SER[k]&&SER[k].applyOptions({visible:!!on});
 set("bbu",v.bb);set("bbm",v.bb);set("bbl",v.bb);set("zones",v.zones);set("pdiv",v.pdiv);set("mean",v.mean);set("exit",v.exit);set("vol",v.vol);for(const k of ["kalman","trend","ou","ema20","factor"])set(k,v[k])}
function refreshOverlays(range){
 if(!chart)return;const d=D();
 if(!d){ARR=null;for(const k of DKEYS)SER[k]&&SER[k].setData([]);annotate();renderLegend();return}
 ARR=buildArrays();const dg=pdig(d.c[d.c.length-1]),pf={type:"price",precision:dg,minMove:Math.pow(10,-dg)};
 for(const k of ["candle","mean","exit","kalman","trend","ou","ema20","factor","bbu","bbm","bbl"])SER[k].applyOptions({priceFormat:pf});
 if(SER.rsi){(SER.rl||[]).forEach(l=>SER.rsi.removePriceLine(l));SER.rl=[ECFG.trig,100-ECFG.trig].map((v,k)=>SER.rsi.createPriceLine({price:v,color:k?"rgba(230,103,103,.5)":"rgba(79,209,165,.7)",lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:k?"":"setup"}))}
 if(SER.edgeL){SER.thrLine&&SER.edgeL.removePriceLine(SER.thrLine);SER.thrLine=ECFG.scoreThr>-50&&ECFG.scoreThr!==THIRDS[1]?SER.edgeL.createPriceLine({price:ECFG.scoreThr,color:C.warn,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:"your filter"}):null}
 setAllData(cur());applyVisibility();if(range)chart.timeScale().setVisibleLogicalRange(range);
 annotate();renderLegend();syncScrub()}
function showRange(){if(!chart||!D())return;const c=cur();if(!st.n)chart.timeScale().setVisibleLogicalRange({from:0,to:c+8});else chart.timeScale().setVisibleLogicalRange({from:Math.max(0,c-st.n),to:c+8})}
function annotate(){
 if(!chart||!SER.candle)return;PLINES.forEach(l=>SER.candle.removePriceLine(l));PLINES=[];
 const d=D();if(!d){MK.setMarkers([]);return}
 const c=cur(),date=d.d[c],s=S(),mk=[];
 if(s){const lo=Math.max(s.first,0);
  for(let i=lo;i<=c;i++){
   if(s.sig[i]===1&&UI.ov.sys){mk.push({time:d.d[i],position:s.side>0?"belowBar":"aboveBar",shape:s.side>0?"arrowUp":"arrowDown",color:"#4fd1a5",text:`${s.aplus&&s.aplus[i]?"A+ ":""}${Math.round(100*s.P[i])}%`,size:s.aplus&&s.aplus[i]?1.9:1.4})}
   else if(s.sig[i]===2&&UI.ov.sys){mk.push({time:d.d[i],position:"belowBar",shape:"arrowUp",color:"#c08cff",text:"MOM",size:1.3})}
   else if(s.setup[i]&&UI.ov.setups)mk.push({time:d.d[i],position:s.side>0?"belowBar":"aboveBar",shape:"circle",color:THIRD_COL[thirdOf(s.score[i])],size:.5});
   else if(s.sig[i]===3&&UI.ov.sys)mk.push({time:d.d[i],position:"aboveBar",shape:"arrowDown",color:"#ef5350",text:"SHORT",size:1.3});
   else if(s.sgood&&s.sgood[i]&&ECFG.shorts!=="off"&&UI.ov.setups)mk.push({time:d.d[i],position:"aboveBar",shape:"circle",color:"#ef5350",size:.5});
   if(UI.ov.signs){const down=d.c[i]<(i?d.c[i-1]:d.c[i]);
    if(down&&s.volz[i]>1.5&&s.rangex[i]>1.5)mk.push({time:d.d[i],position:"aboveBar",shape:"square",color:"#fab219",size:.45});
    else if(Math.abs(s.gap[i])>1.5)mk.push({time:d.d[i],position:"aboveBar",shape:"square",color:"#8a8a85",size:.35})}}
  if(RES&&UI.ov.sys)for(const t of RES.bt.trades){if(t.symbol!==st.sym||t.exit_date>date)continue;mk.push({time:t.exit_date,position:t.direction==="short"?"belowBar":"aboveBar",shape:"circle",color:t.pnl>0?"#3fbf5f":"#e05252",size:.6})}}
 const sims=simAll();
 if(UI.ov.mine)for(const r of sims){if(r.o.sym!==st.sym||(r.status!=="open"&&r.status!=="closed"))continue;const lg=r.o.side>0;
  mk.push({time:d.d[r.entryIdx],position:lg?"belowBar":"aboveBar",shape:lg?"arrowUp":"arrowDown",color:TV.you,text:`YOU ${lg?"BUY":"SELL"}`,size:1.2});
  if(r.status==="closed")mk.push({time:d.d[r.exitIdx],position:lg?"aboveBar":"belowBar",shape:"square",color:TV.you,text:`${r.reason} ${sR(r.R)}`,size:.8})}
 mk.sort((a,b)=>a.time<b.time?-1:a.time>b.time?1:0);MK.setMarkers(mk);
 const PL=(price,color,title,style=LW.LineStyle.Dashed,w=1)=>{if(isF(price))PLINES.push(SER.candle.createPriceLine({price,color,lineWidth:w,lineStyle:style,axisLabelVisible:true,title}))};
 for(const r of sims){if(r.o.sym!==st.sym||(r.status!=="open"&&r.status!=="pending"))continue;const lv=levelsAt(r.o,c+1);
  PL(r.status==="open"?r.entryPx:NaN,TV.you,`${r.o.side>0?"Long":"Short"} ${r.o.qty}`,LW.LineStyle.Solid,2);PL(lv.stop,TV.down,"Stop");PL(lv.target,TV.up,"Target")}
 if(draft.show){const t=readTicket();PL(t.stop,TV.down,"Plan stop",LW.LineStyle.LargeDashed);PL(t.target,TV.up,"Plan target",LW.LineStyle.LargeDashed)}
 for(const h of HLINES[st.sym]||[])PL(h,TV.line,"",LW.LineStyle.Solid)}
function renderLegend(){try{const c0=cur(),i0=hoverIdx!=null?Math.max(0,Math.min(c0,hoverIdx)):(st.pinned&&st.cursor!=null?Math.min(st.cursor,c0):c0);renderPulseHud(i0)}catch(e){}

 const d=D(),el=$("legend");if(!d){el.innerHTML="";return}
 const c=cur(),i=hoverIdx!=null?Math.max(0,Math.min(c,hoverIdx)):(st.pinned&&st.cursor!=null?Math.min(st.cursor,c):c),s=S(),ch=i>0?d.c[i]/d.c[i-1]-1:NaN;
 const z=ARR?ARR.zArr[i]:NaN,mu=ARR?ARR.meanArr[i]:NaN;
 el.innerHTML=`<div class="l1"><b>${esc(st.sym)}</b><span class="lk">1D</span><span class="lk">${d.d[i]}</span><span><span class="lk">O</span> ${fp(d.o[i])}</span><span><span class="lk">H</span> ${fp(d.h[i])}</span><span><span class="lk">L</span> ${fp(d.l[i])}</span><span><span class="lk">C</span> ${fp(d.c[i])}</span><span class="${cl(ch)}">${spct(ch,2)}</span></div>
  <div class="l2"><span>mean ${fp(mu)}</span><span>z <span style="color:${isF(z)?(z<0?"#4f96f0":"#f08c8c"):"inherit"}">${fmt(z,2)}</span></span>${s?`<span>RSI2 <span class="${s.setup[i]?"up":""}">${fmt(s.rsi2[i],0)}</span></span><span>edge <span style="color:${THIRD_COL[thirdOf(s.score[i])]||"inherit"}">${fmt(s.score[i],1)}</span></span><span>P ${isF(s.P[i])?pct(s.P[i],0):"—"}</span>`:""}${isF(d.v[i])?`<span class="lk">vol ${d.v[i]>=1e6?(d.v[i]/1e6).toFixed(1)+"M":Math.round(d.v[i]).toLocaleString()}${s&&isF(s.volz[i])?` (${s.volz[i]>=0?"+":""}${s.volz[i].toFixed(1)}σ)`:""}</span>`:""}</div>`}
let raf=0;
function onCross(p){hoverIdx=p&&p.point&&p.logical!=null?Math.round(p.logical):null;
 if(raf)return;raf=requestAnimationFrame(()=>{raf=0;renderLegend();if(!st.pinned&&hoverIdx!=null&&hoverIdx>=0&&hoverIdx<=cur()&&hoverIdx!==st.cursor){st.cursor=hoverIdx;syncScrub();inspector(hoverIdx)}})}
function syncScrub(){const c=cur();const sc=$("scrub");sc.max=Math.max(1,c);if(st.cursor==null||st.cursor>c)st.cursor=c;sc.value=st.cursor;$("scrubd").textContent=D()?D().d[st.cursor]+(st.pinned?" · pinned":""):""}
$("scrub").addEventListener("input",e=>{if(!D())return;st.pinned=true;st.cursor=+e.target.value;const r=chart.timeScale().getVisibleLogicalRange(),i=st.cursor;
 if(r&&(i<r.from||i>r.to)){const w=r.to-r.from;chart.timeScale().setVisibleLogicalRange({from:i-w/2,to:i+w/2})}
 try{chart.setCrosshairPosition(ARR.candle[i].close,ARR.candle[i].time,SER.candle)}catch(err){}syncScrub();inspector(i);renderLegend()});

// drag stop/target lines
const wrapEl=$("lwc-wrap");let drag=null;
function dragTargets(){const out=[],c=cur();
 if(draft.show){const t=readTicket();if(isF(t.stop))out.push({kind:"draft",key:"stop",price:t.stop});if(isF(t.target))out.push({kind:"draft",key:"target",price:t.target})}
 for(const r of simAll())if(r.o.sym===st.sym&&(r.status==="open"||r.status==="pending")){const lv=levelsAt(r.o,c+1);if(isF(lv.stop))out.push({kind:"order",o:r.o,key:"stop",price:lv.stop});if(isF(lv.target))out.push({kind:"order",o:r.o,key:"target",price:lv.target})}
 return out}
function hitLine(y0){if(!SER.candle)return null;const y=y0-$("lwc").getBoundingClientRect().top;let best=null,bd=7;for(const t of dragTargets()){const yy=SER.candle.priceToCoordinate(t.price);if(yy!=null&&Math.abs(yy-y)<bd){bd=Math.abs(yy-y);best=t}}return best}
wrapEl.addEventListener("pointerdown",e=>{if(clickMode||!$("lwc").contains(e.target))return;const h=hitLine(e.clientY);if(!h)return;drag=h;e.stopPropagation();e.preventDefault();chart.applyOptions({handleScroll:false,handleScale:false});wrapEl.setPointerCapture(e.pointerId)},true);
for(const ev of ["mousedown","touchstart"])wrapEl.addEventListener(ev,e=>{if(drag)e.stopPropagation()},{capture:true,passive:true});
wrapEl.addEventListener("pointermove",e=>{
 if(!drag){if(!clickMode&&$("lwc").contains(e.target))$("lwc").style.cursor=hitLine(e.clientY)?"ns-resize":"";return}
 const y=e.clientY-$("lwc").getBoundingClientRect().top,pr0=SER.candle.coordinateToPrice(y);if(!isF(pr0)||pr0<=0)return;const pr=+pr0.toFixed(pdig(pr0));
 if(drag.kind==="draft"){$("t-"+drag.key).value=pr;ticketChanged(false)}else setLevel(drag.o,drag.key,pr,false);annotate()});
const endDrag=()=>{if(!drag)return;if(drag.kind==="order"){saveOrders();renderLive()}drag=null;chart.applyOptions({handleScroll:true,handleScale:true})};
wrapEl.addEventListener("pointerup",endDrag);wrapEl.addEventListener("pointercancel",endDrag);

let clickMode=null;
function setClickMode(m,txt){clickMode=m;$("clickhint").hidden=!m||m==="replay";$("clicktxt").textContent=txt||"";$("pickhint").hidden=m!=="replay";
 $("pick-stop").classList.toggle("on",m==="stop");$("pick-target").classList.toggle("on",m==="target");$("lwc").style.cursor=m?"crosshair":""}
$("click-cancel").addEventListener("click",()=>setClickMode(null));
function onChartClick(p){
 if(!p||!p.point)return;
 if(!clickMode){if(p.logical==null)return;const i=Math.round(p.logical);if(i<0||i>cur())return;st.pinned=!st.pinned||st.cursor!==i;st.cursor=i;syncScrub();inspector(i);renderLegend();return}
 if(clickMode==="replay"){if(p.logical==null)return;const i=Math.max(30,Math.min(lastIdx()-1,Math.round(p.logical)));setClickMode(null);startReplay(i);return}
 const pr0=SER.candle.coordinateToPrice(p.point.y);if(!isF(pr0))return;const pr=+pr0.toFixed(pdig(pr0));
 if(clickMode==="stop"||clickMode==="target"){$("t-"+clickMode).value=pr;draft.show=true;ticketChanged(false)}
 else if(clickMode==="hline"){(HLINES[st.sym]=HLINES[st.sym]||[]).push(pr);store("desk-hlines",JSON.stringify(HLINES))}
 setClickMode(null);annotate()}
$("pick-stop").addEventListener("click",()=>{if(st.tab!=="chart")show("chart");setClickMode(clickMode==="stop"?null:"stop","Click the chart at your stop price.")});
$("pick-target").addEventListener("click",()=>{if(st.tab!=="chart")show("chart");setClickMode(clickMode==="target"?null:"target","Click the chart at your target price.")});
$("hline-btn").addEventListener("click",()=>setClickMode(clickMode==="hline"?null:"hline","Click the chart to place a horizontal line."));
$("clear-lines").addEventListener("click",()=>{delete HLINES[st.sym];store("desk-hlines",JSON.stringify(HLINES));annotate()});

// ------------------------------------------------ bar replay
let playTimer=null;
function startReplay(i){stopPlay();closeReplayPositions();REPLAY={sym:st.sym,idx:i,startIdx:i,sid:Date.now().toString(36)};saveReplay();st.pinned=false;st.cursor=i;hoverIdx=null;
 setAllData(i);chart.timeScale().setVisibleLogicalRange({from:i-150,to:i+10});syncMode();draft.show=false;renderLive();annotate();inspector(i)}
function exitReplay(){stopPlay();closeReplayPositions();REPLAY=null;saveReplay();st.cursor=null;st.pinned=false;setAllData(lastIdx());showRange();syncMode();draft.show=false;renderLive();annotate();inspector(cur())}
function closeReplayPositions(){if(!REPLAY)return;const d=DS[REPLAY.sym];if(!d)return;
 for(const r of ORDERS.map(o=>simulate(o,uptoFor(o))))if(r.o.mode==="replay"&&r.o.sid===REPLAY.sid&&(r.status==="open"||r.status==="pending")){if(r.status==="pending")r.o.cancelled=true;else{r.o.closeDate=d.d[REPLAY.idx];r.o.closeFill="close"}}
 saveOrders()}
let saveT=null;
function replayStep(k){if(!REPLAY)return;const n=lastIdx(),ni=Math.max(30,Math.min(n,REPLAY.idx+k));if(ni===REPLAY.idx){stopPlay();return}
 const fwd=ni===REPLAY.idx+1;REPLAY.idx=ni;if(fwd)stepData(ni);else setAllData(ni);if(ni>=n)stopPlay();
 clearTimeout(saveT);saveT=setTimeout(saveReplay,400);st.pinned=false;st.cursor=ni;renderLive();annotate();inspector(ni)}
function stopPlay(){if(playTimer){clearInterval(playTimer);playTimer=null}$("rp-play").textContent="Play"}
function togglePlay(){if(playTimer)return stopPlay();if(!REPLAY)return;playTimer=setInterval(()=>replayStep(1),1000/+$("rp-speed").value);$("rp-play").textContent="Pause"}
$("rp-play").addEventListener("click",togglePlay);$("rp-fwd").addEventListener("click",()=>{stopPlay();replayStep(1)});$("rp-back").addEventListener("click",()=>{stopPlay();replayStep(-1)});
$("rp-speed").addEventListener("change",()=>{if(playTimer){stopPlay();togglePlay()}});$("rp-exit").addEventListener("click",exitReplay);
$("m-replay").addEventListener("click",()=>{if(!D()||REPLAY)return;setClickMode("replay")});
$("m-live").addEventListener("click",()=>{setClickMode(null);if(REPLAY)exitReplay()});
$("rp-cancel").addEventListener("click",()=>setClickMode(null));
$("rp-year").addEventListener("click",()=>{setClickMode(null);startReplay(Math.max(60,lastIdx()-252))});
$("rp-random").addEventListener("click",()=>{setClickMode(null);const s=S(),lo=s&&s.first>0?s.first+60:300,hi=lastIdx()-60;startReplay(hi>lo?lo+Math.floor(Math.random()*(hi-lo)):Math.max(30,lastIdx()-252))});
function syncMode(){const r=!!REPLAY;$("m-live").classList.toggle("on",!r);$("m-replay").classList.toggle("on",r);$("rpbar").hidden=!r;$("rtag").hidden=!r;
 $("t-mode").textContent=r?"replay":"live";$("t-mode").className="tag "+(r?"r":"l");$("chartnote").textContent=r?"The future is hidden. → next bar, ← back, Space play.":""}
document.addEventListener("keydown",e=>{if(e.target.closest("input,select,textarea"))return;if(e.key===" "&&e.target.closest("button"))return;
 if(e.key==="Escape"){setClickMode(null);return}if(!REPLAY||st.tab!=="chart")return;
 if(e.key==="ArrowRight"){e.preventDefault();stopPlay();replayStep(e.shiftKey?5:1)}else if(e.key==="ArrowLeft"){e.preventDefault();stopPlay();replayStep(e.shiftKey?-5:-1)}else if(e.key===" "){e.preventDefault();togglePlay()}});
