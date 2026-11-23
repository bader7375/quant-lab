"""v24 -> v25: Z touch momentum (round 60) as a chart pane, HUD, inspector section, scanner column and research note."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old)); s = s.replace(old, new)

# ---- brand
rep("reversal edge v24 · Saudi + US scanner · US market leaders", "reversal edge v25 · Saudi + US scanner · Z touch momentum")
# ---- CSS
rep(".ztab{width:100%;border-collapse:collapse;font-size:11px}",
    ".pulse-hud .tc{display:inline-flex;gap:3px;align-items:baseline;margin-right:3px}.pulse-hud .tc b{font-weight:600}.pulse-hud .tc.u b{color:#26a69a}.pulse-hud .tc.d b{color:#ef5350}.pulse-hud .tc.z{opacity:.4}\n"
    ".ztm-opts{display:inline-flex;gap:4px;align-items:center}.ztm-opts select{padding:2px 6px;font-size:11px}\n"
    ".tmc{display:inline-flex;gap:6px;align-items:center;justify-content:flex-end}.tmb{display:inline-flex;width:46px;height:6px;border-radius:3px;overflow:hidden;background:var(--s2)}.tmb i{display:block;height:100%}\n"
    ".tmq{display:inline-block;width:34px;height:6px;background:var(--s2);border-radius:3px;overflow:hidden;margin-right:6px;vertical-align:middle}.tmq i{display:block;height:100%}\n"
    ".ztab{width:100%;border-collapse:collapse;font-size:11px}")
# ---- HUD element over the new pane
rep('<div class="pulse-hud" id="pulse-hud" hidden></div>', '<div class="pulse-hud" id="pulse-hud" hidden></div>\n          <div class="pulse-hud" id="ztm-hud" hidden></div>')
# ---- UI state: pane on by default, look-back and line remembered per viewer
rep("UI.pn=Object.assign({pulse:true,edge:true,rsi:true,z:true,zs:true,vz:true,ms:true,zl:false,vol:true,reg:false,fear:false},UI.pn||{});",
    "UI.pn=Object.assign({pulse:true,edge:true,rsi:true,z:true,zs:true,ztm:true,vz:true,ms:true,zl:false,vol:true,reg:false,fear:false},UI.pn||{});\nUI.ztm=Object.assign({L:250,mode:\"net\"},UI.ztm||{});")
# ---- calculation, custom pane renderer and HUD (before PULSE_STATE, i.e. before the chart is first built)
JS = r'''
// ------------------------------------------------ v25: Z touch momentum (round 60): level-weighted stretch-Z touches of +-1/2/3
// A touch = the first close at or beyond a level (Z >= k after < k, or Z <= -k after > -k). Weight = level. Same rule as the scanner (r27/final27.py).
function ztmL(){const v=+(UI.ztm&&UI.ztm.L);return v===120||v===60?v:250}
function ztmM(){const m=UI.ztm&&UI.ztm.mode;return m==="bal"||m==="occ"?m:"net"}
function ztmFmt(v){return isF(v)?(v>0?"+":"")+v:"—"}
function ztmCalc(z,L){const n=z.length,O={L,net:new Array(n).fill(NaN),bal:new Array(n).fill(NaN),occ:new Array(n).fill(NaN),ev:new Array(n).fill(0),U:new Array(n),D:new Array(n)};
 const EU=[],ED=[],EA=[],EB=[],U=[0,0,0],Dn=[0,0,0],Ab=[0,0,0],Be=[0,0,0];let first=-1;
 for(let i=0;i<n;i++){const a=z[i],b=i?z[i-1]:NaN,fa=isF(a),ok=fa&&isF(b);if(first<0&&fa)first=i;
  const u=[0,0,0],dd=[0,0,0],ab=[0,0,0],be=[0,0,0];
  for(let k=0;k<3;k++){const lv=k+1;if(ok&&a>=lv&&b<lv)u[k]=1;if(ok&&a<=-lv&&b>-lv)dd[k]=1;if(fa&&a>=lv)ab[k]=1;if(fa&&a<=-lv)be[k]=1}
  EU.push(u);ED.push(dd);EA.push(ab);EB.push(be);O.ev[i]=u[2]?3:u[1]?2:u[0]?1:dd[2]?-3:dd[1]?-2:dd[0]?-1:0;
  for(let k=0;k<3;k++){U[k]+=u[k];Dn[k]+=dd[k];Ab[k]+=ab[k];Be[k]+=be[k];if(i>=L){U[k]-=EU[i-L][k];Dn[k]-=ED[i-L][k];Ab[k]-=EA[i-L][k];Be[k]-=EB[i-L][k]}}
  O.U[i]=U.slice();O.D[i]=Dn.slice();
  if(first>=0&&i-first>=L-1){const uw=U[0]+2*U[1]+3*U[2],dw=Dn[0]+2*Dn[1]+3*Dn[2];O.net[i]=uw-dw;O.bal[i]=uw+dw>0?(uw-dw)/(uw+dw):0;O.occ[i]=((Ab[0]-Be[0])+2*(Ab[1]-Be[1])+3*(Ab[2]-Be[2]))/L}}
 return O}
class TouchView{
 constructor(){this.d=null}
 renderer(){const me=this;return {draw(target,pc){const d=me.d;if(!d||!d.visibleRange)return;
  target.useBitmapCoordinateSpace(({context:ctx,horizontalPixelRatio:hr,verticalPixelRatio:vr,bitmapSize})=>{
   const bars=d.bars,from=Math.max(0,d.visibleRange.from-1),to=Math.min(bars.length,d.visibleRange.to+1),W=bitmapSize.width,H=bitmapSize.height;
   const Y=v=>{const y=pc(v);return y==null?null:y*vr},X=i=>bars[i].x*hr,od=i=>bars[i].originalData,y0=Y(0);
   let mx=0;for(let i=from;i<to;i++){const o=od(i);if(o&&isF(o.v))mx=Math.max(mx,Math.abs(o.v))}if(!mx)mx=1;
   const sc=Math.min(1,Math.max(.5,d.barSpacing/7)),yUp=Math.round(32*vr),yDn=Math.round(H-8*vr);
   // dot lanes (faint), then the zero line
   ctx.lineWidth=Math.max(1,hr);ctx.setLineDash([1*hr,4*hr]);ctx.strokeStyle="rgba(195,194,183,.16)";for(const y of [yUp,yDn]){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}ctx.setLineDash([]);
   if(y0!=null){ctx.strokeStyle="rgba(195,194,183,.5)";ctx.beginPath();ctx.moveTo(0,y0);ctx.lineTo(W,y0);ctx.stroke()}
   // columns: teal = more up-touches, red = more down-touches; stronger colour for larger values in view; a crisp cap at the end
   const bw=Math.max(hr,Math.min(d.barSpacing*hr*.7,16*hr)),cap=Math.max(1,1.5*hr);
   if(y0!=null)for(let i=from;i<to;i++){const o=od(i);if(!o||!isF(o.v)||!o.v)continue;const y=Y(o.v);if(y==null)continue;
    const t=Math.min(1,Math.abs(o.v)/mx),c=o.v>0?PC.up:PC.dn,x=X(i)-bw/2,top=Math.min(y,y0),h=Math.abs(y-y0);
    ctx.fillStyle=prgb(c,.16+.46*t);ctx.fillRect(x,top,bw,h);if(h>cap){ctx.fillStyle=prgb(c,.62+.38*t);ctx.fillRect(x,o.v>0?y:y-cap,bw,cap)}}
   // touch dots: up-touches on the top lane, down-touches on the bottom lane; size by level; a glow for +-3
   for(let i=from;i<to;i++){const o=od(i);if(!o||!o.ev)continue;const k=Math.abs(o.ev),up=o.ev>0,c=up?PC.up:PC.dn,x=X(i),y=up?yUp:yDn,r=(1.3+1.25*k)*hr*sc;
    if(k===3){const g=ctx.createRadialGradient(x,y,0,x,y,r*2.8);g.addColorStop(0,prgb(c,.55));g.addColorStop(1,prgb(c,0));ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r*2.8,0,Math.PI*2);ctx.fill()}
    ctx.fillStyle=prgb(c,k===1?.5:k===2?.82:1);ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    if(k>1){ctx.strokeStyle="#1a1a19";ctx.lineWidth=Math.max(1,hr);ctx.stroke()}}
  })}}}
 update(data){this.d=data}
 priceValueBuilder(r){return [Math.min(r.v,0),Math.max(r.v,0),r.v]}
 isWhitespace(r){return !isF(r.v)}
 defaultOptions(){return Object.assign({},LW.customSeriesDefaultOptions,{lastValueVisible:true,priceLineVisible:false,title:"touches",color:"#c3c2b7"})}
}
function placeZtmHud(){const hud=$("ztm-hud");if(!chart||SER.ztmPane==null||!UI.pn.ztm){hud.hidden=true;return}
 try{const el=chart.panes()[SER.ztmPane].getHTMLElement(),r=el.getBoundingClientRect(),w=$("lwc-wrap").getBoundingClientRect();hud.style.top=(r.top-w.top+4)+"px";hud.style.left="8px";hud.hidden=false}catch(e){hud.hidden=true}}
function renderZtmHud(i){const hud=$("ztm-hud");if(!ARR||!ARR.ztmAll||!UI.pn.ztm||SER.ztmPane==null){hud.hidden=true;return}placeZtmHud();
 const T=ARR.ztmAll[ztmL()],net=T.net[i],bal=T.bal[i],U=T.U[i]||[0,0,0],Dn=T.D[i]||[0,0,0],ev=T.ev[i];
 const chip=!isF(bal)?["NEEDS "+T.L+" SESSIONS","#8a8a85"]:bal>=.25?["UP-TOUCHES LEAD","#26a69a"]:bal<=-.25?["DOWN-TOUCHES LEAD","#ef5350"]:["BALANCED","#c3c2b7"];
 const cnt=(a,up)=>a.map((v,k)=>`<span class="tc ${up?"u":"d"}${v?"":" z"}">${up?"+":"−"}${k+1}<b>${v}</b></span>`).join("");
 hud.innerHTML=`<b>Z TOUCH MOMENTUM</b><span class="pk">${T.L}d</span><span style="color:${net>0?"#26a69a":net<0?"#ef5350":"#c3c2b7"};font-weight:600">${ztmFmt(net)}</span>`+
  `<span class="pk">up</span>${cnt(U,1)}<span class="pk">down</span>${cnt(Dn,0)}<span class="pk">balance</span>${isF(bal)?(bal>0?"+":"")+Math.round(100*bal)+"%":"—"}`+
  `<span class="st" style="color:${chip[1]};border-color:${chip[1]}">${chip[0]}</span>${ev?`<span style="color:${ev>0?"#26a69a":"#ef5350"}">● touched ${ev>0?"+":"−"}${Math.abs(ev)} on this bar</span>`:""}`}
function tmCell(r){if(!isF(r.tm))return '<span class="note" title="less than 250 sessions of stretch-Z history">—</span>';const tu=r.tu||[0,0,0],td=r.td||[0,0,0],uw=tu[0]+2*tu[1]+3*tu[2],dw=td[0]+2*td[1]+3*td[2],tot=Math.max(1,uw+dw);
 return `<span class="tmc" title="last 250 sessions · up-touches of +1 / +2 / +3: ${tu.join(" / ")} · down-touches of −1 / −2 / −3: ${td.join(" / ")}"><span class="tmb"><i style="width:${(100*dw/tot).toFixed(0)}%;background:#ef5350"></i><i style="width:${(100*uw/tot).toFixed(0)}%;background:#26a69a"></i></span><b style="color:${r.tm>0?"#26a69a":r.tm<0?"#ef5350":"inherit"}">${r.tm>0?"+":""}${r.tm}</b></span>`}
'''
rep("const PULSE_STATE={", JS + "const PULSE_STATE={")
# ---- panel list, its options and their events
rep('["zs","Stretch Z (10/20/60d)"],["vz","VWAP stretch Z"]', '["zs","Stretch Z (10/20/60d)"],["ztm","Z touch momentum"],["vz","VWAP stretch Z"]')
rep('''$("pn").innerHTML=`<span class="lab">panels</span>`+PNS.map(([k,n])=>`<label><input type="checkbox" data-pn="${k}" ${UI.pn[k]?"checked":""}>${n}</label>`).join("");''',
    '''$("pn").innerHTML=`<span class="lab">panels</span>`+PNS.map(([k,n])=>`<label><input type="checkbox" data-pn="${k}" ${UI.pn[k]?"checked":""}>${n}</label>`+(k==="ztm"?`<span class="ztm-opts" id="ztm-opts"${UI.pn.ztm?"":" hidden"}><select id="ztm-L" aria-label="Touch momentum look-back">${[250,120,60].map(v=>`<option value="${v}"${ztmL()===v?" selected":""}>${v} days</option>`).join("")}</select><select id="ztm-m" aria-label="Touch momentum line">${[["net","net touches"],["bal","touch balance"],["occ","time beyond levels"]].map(([v,t])=>`<option value="${v}"${ztmM()===v?" selected":""}>${t}</option>`).join("")}</select></span>`:"")).join("");
$("pn").addEventListener("change",e=>{const id=e.target.id;if(id==="ztm-L"||id==="ztm-m"){if(id==="ztm-L")UI.ztm.L=+e.target.value;else UI.ztm.mode=e.target.value;saveUI();buildChart(true);return}if(e.target.dataset&&e.target.dataset.pn==="ztm"){const o=$("ztm-opts");if(o)o.hidden=!e.target.checked}});''')
# ---- arrays for the chart (all three look-backs, so the HUD and inspector can show them)
rep("A.z=L(A.zArr);A.zl=L(s&&s.z250?s.z250:A.zlArr);A.zs=L(A.zsArr);",
    "A.z=L(A.zArr);A.zl=L(s&&s.z250?s.z250:A.zlArr);A.zs=L(A.zsArr);\n {const z=A.zsArr||[];A.ztmAll={250:ztmCalc(z,250),120:ztmCalc(z,120),60:ztmCalc(z,60)};const T=A.ztmAll[ztmL()],md=ztmM();A.ztm=d.d.map((t,i)=>{const v=md===\"bal\"?T.bal[i]:md===\"occ\"?T.occ[i]:T.net[i];return isF(v)?{time:t,v,ev:T.ev[i]}:{time:t}})}\n ")
# ---- the pane, right under Stretch Z
rep(" if(UI.pn.vz){P.vz=pane++;",
    " if(UI.pn.ztm){P.ztm=pane++;const md=ztmM();SER.ztm=chart.addCustomSeries(new TouchView(),{priceFormat:md===\"net\"?{type:\"price\",precision:0,minMove:1}:{type:\"price\",precision:2,minMove:.01}},P.ztm);SER.ztm.priceScale().applyOptions({scaleMargins:{top:.34,bottom:.14}});SER.ztmPane=P.ztm}else SER.ztmPane=null;\n if(UI.pn.vz){P.vz=pane++;")
rep("for(let i=1;i<panes.length;i++)panes[i].setStretchFactor(i===P.pulse?1.7:1)}\n MK=", "for(let i=1;i<panes.length;i++)panes[i].setStretchFactor(i===P.pulse?1.7:i===P.ztm?1.4:1)}\n MK=")
rep('$("lwc-wrap").style.height=(470+np*105+(UI.pn.pulse?60:0))+"px";', '$("lwc-wrap").style.height=(470+np*105+(UI.pn.pulse?60:0)+(UI.pn.ztm?40:0))+"px";')
rep('const DKEYS=["zs",', 'const DKEYS=["zs","ztm",')
rep("renderPulseHud(i0)}catch(e){}", "try{renderPulseHud(i0)}catch(e){}try{renderZtmHud(i0)}catch(e){}}catch(e){}")
# ---- inspector section (both Saudi trend mode and the other stocks)
rep(' h+=`<div class="sec">stock-specific z-zones',
    ''' if(ARR&&ARR.ztmAll&&ARR.n===d.d.length){const T=ARR.ztmAll[250],U=T.U[i]||[0,0,0],Dn=T.D[i]||[0,0,0],net=T.net[i],bal=T.bal[i],mxc=Math.max(1,...U,...Dn);
  const row=(a,up)=>a.map(v=>`<td class="n"><span class="tmq"><i style="width:${Math.round(100*v/mxc)}%;background:${up?"#26a69a":"#ef5350"}"></i></span>${v}</td>`).join("");
  h+=`<div class="sec">Z touch momentum · stretch-Z level touches, last 250 sessions</div><table class="t"><tr><td></td><td class="n">level 1</td><td class="n">level 2</td><td class="n">level 3</td></tr><tr><td><span class="up">up-touches</span></td>${row(U,1)}</tr><tr><td><span class="down">down-touches</span></td>${row(Dn,0)}</tr></table>
  <table class="t"><tr><td>net touches (weighted 1/2/3) · 250 / 120 / 60 days</td><td class="n"><b style="color:${net>0?"#26a69a":net<0?"#ef5350":"inherit"}">${ztmFmt(net)}</b> / ${ztmFmt(ARR.ztmAll[120].net[i])} / ${ztmFmt(ARR.ztmAll[60].net[i])}</td></tr><tr><td>touch balance</td><td class="n">${isF(bal)?(bal>0?"+":"")+Math.round(100*bal)+"%":"—"}</td></tr></table>
  <div class="note">Round 60: across Saudi stocks, more up-touches went with better next-20-day returns (rank correlation +0.05 in 2013–19 and in 2020–26), mostly the same information as 12-month momentum, which the ML score already uses. Context, not a buy or sell rule.</div>`}
 h+=`<div class="sec">stock-specific z-zones''')
# ---- scanner column (Saudi stretch-Z scan)
rep('<th>weekly Z${MLPF.wk_done?"":" (forming)"}</th><th>ML rank</th>',
    '<th>weekly Z${MLPF.wk_done?"":" (forming)"}</th><th title="Z touch momentum: level-weighted stretch-Z touches of ±1/±2/±3 over the last 250 sessions, up minus down. Red share = down-touches, teal = up-touches. Round 60: context, not a rule.">touches 250d</th><th>ML rank</th>')
rep('${r.zw.toFixed(2)}</span>`:"—"}</td><td>${Math.round(100*r.pct)}%</td>', '${r.zw.toFixed(2)}</span>`:"—"}</td><td>${tmCell(r)}</td><td>${Math.round(100*r.pct)}%</td>')
# ---- research note
rep("<h2>Momentum Pulse (the pane under the chart)</h2>",
    """<h2>Z touch momentum (round 60, the pane under Stretch Z)</h2>
<p>The pane counts how often the stock's stretch Z (the scanner's 10/20/60-day measure) has <b>touched</b> the levels +1, +2, +3 and −1, −2, −3 over the last 250 sessions. A touch is the first close at or beyond a level. Deeper levels count more (1, 2, 3), so each column is <i>weighted up-touches minus weighted down-touches</i>: teal when the stock keeps reaching its plus levels, red when it keeps falling to its minus levels. Dots mark the touches themselves, on the top lane for up and the bottom lane for down, larger for deeper levels, with a glow at ±3. Next to the panel switch you can pick the look-back (250, 120 or 60 sessions) and the line: net touches, touch balance (−100% to +100%) or time spent beyond the levels. The Saudi stretch-Z scan shows the same count for each stock, and the inspector breaks it down by level.</p>
<p><b>What the test found</b> (pre-registered; 2013–19 to choose, 2020–26 to confirm; 270 Saudi stocks). It behaves as momentum: stocks with more up-touches did better over the next 20 sessions (rank correlation +0.046 and +0.049). But it moves 77% together with 12-month momentum and adds little beyond it. Added to the ML ranker, the portfolio got slightly worse (Sharpe 0.57 vs 0.62 and 1.47 vs 1.56). As a Z-swing filter (buy dips only after many down-touches) the gain was small and failed half the robustness checks and the US test. Read it as context on the chart and in the scanner, not as a rule.</p>
<h2>Momentum Pulse (the pane under the chart)</h2>""")
assert "TouchView" in s and "tmCell(r)" in s
open(p, "w").write(s); print("patched v25:", len(s), "bytes")
