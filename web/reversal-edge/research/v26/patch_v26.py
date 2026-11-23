"""v25 -> v26: Z bands (round 61 tool) - the close that puts the stretch Z on the buy line (-2.62), on 0, and on the weekly line (-2.08)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v25 · Saudi + US scanner · Z touch momentum", "reversal edge v26 · Saudi + US scanner · Z bands")
rep(".tmc{display:inline-flex;", ".zbl b{color:var(--ink)}.zbl .lim{color:var(--muted);text-decoration:line-through}\n.tmc{display:inline-flex;")
# ---- overlay switch (on by default)
rep('["zb","Long-term Z bands (250d: mean, −1, ±2.5σ)","#b39dff"]', '["zband","Z bands: close for stretch Z −2.62 / 0","#4f96f0"],["zb","Long-term Z bands (250d: mean, −1, ±2.5σ)","#b39dff"]')
rep("UI.ov=Object.assign({sect:true,", "UI.ov=Object.assign({zband:true,sect:true,")
# ---- the calculation
JS = r'''
// ------------------------------------------------ v26: Z bands (round 61 tool): the close that puts the stretch Z exactly on a line.
// At the next close Z = A + B x (its log return): only the newest return depends on that close, so the close for a level L is
// previous close x exp((L - A) / B). Same windows as stretchZ() and the scanner (r27/zbands.py: 0 disagreements in 430,780 stock-days).
function zBands(c,level,clip=.25){const n=c.length,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n+1).fill(NaN);
 for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-clip,Math.min(clip,a-b))}
 for(let i=59;i<n;i++){let s1=0,s2=0,m=0;for(let k=i-59;k<=i;k++)if(isF(rr[k])){s1+=rr[k];s2+=rr[k]*rr[k];m++}if(m>=40)sd[i]=Math.sqrt(Math.max(1e-12,(s2-s1*s1/m)/(m-1)))}
 for(let t=61;t<=n;t++){const p=t-1;if(!isF(c[p]))continue;let A=0,B=0,ok=true;      // out[t]: close at bar t for Z = level (out[n] = the next session)
  for(const K of [10,20,60]){const s=sd[t-K];if(!isF(s)||s<=0){ok=false;break}let s1=0,m=0;for(let k=t-K+1;k<=t-1;k++)if(isF(rr[k])){s1+=rr[k];m++}if(m+1<.8*K){ok=false;break}A+=s1/(s*Math.sqrt(K));B+=1/(s*Math.sqrt(K))}
  if(!ok)continue;A/=3;B/=3;const x=(level-A)/B;if(Math.abs(x)<=clip)out[t]=c[p]*Math.exp(x)}
 return out}
function thuKey(d){const t=new Date(d+"T00:00:00Z"),k=(4-t.getUTCDay()+7)%7;t.setUTCDate(t.getUTCDate()+k);return t.toISOString().slice(0,10)}
function zWeekBand(d){const keys=[],wc=[];for(let i=0;i<d.d.length;i++){const k=thuKey(d.d[i]);if(keys.length&&keys[keys.length-1]===k)wc[wc.length-1]=d.c[i];else{keys.push(k);wc.push(d.c[i])}}
 const last=d.d[d.d.length-1],done=new Date(last+"T00:00:00Z").getUTCDay()===4||thuKey(new Date().toISOString().slice(0,10))!==thuKey(last);
 const base=done?wc:wc.slice(0,-1),out=zBands(base,TF_LINE_W,.6),zw=stretchZ(base,.6),prev=zw[zw.length-1];
 return {price:out[base.length],week:done?"next week's close":"this week's close (Thursday)",fresh:isF(prev)&&prev>TF_LINE_W,prevZ:prev}}
const TF_LINE_W=-2.08;
function zbCell(price,ref,lim){if(!isF(price))return '<span class="note">—</span>';const ch=price/ref-1,over=lim&&Math.abs(ch)>lim+1e-9;
 return `<span class="zbl" title="${over?"beyond the ±10% daily price limit: cannot happen in one session":"close needed"}"><b class="${over?"lim":""}">${fp(price)}</b> <span class="note">${spct(ch,1)}</span></span>`}
'''
rep("const PULSE_STATE={", JS + "const PULSE_STATE={")
# ---- arrays for the chart
rep(" {const z=A.zsArr||[];A.ztmAll=", " {const bd=zBands(d.c,ZC_LINE),b0=zBands(d.c,0);A.zbdArr=bd;A.zb0Arr=b0;A.zbd=L(bd.slice(0,n));A.zb0=L(b0.slice(0,n))}\n {const z=A.zsArr||[];A.ztmAll=")
# ---- series on the price pane (step lines), visibility, data keys
rep(' SER.exit=line("#fab219",', ' SER.zbd=line("#4f96f0",{lineWidth:1.5,lineStyle:LW.LineStyle.Dashed,lineType:LW.LineType.WithSteps});SER.zb0=line("rgba(195,194,183,.6)",{lineWidth:1,lineStyle:LW.LineStyle.Dotted,lineType:LW.LineType.WithSteps});\n SER.exit=line("#fab219",')
rep('const DKEYS=["zs","ztm",', 'const DKEYS=["zbd","zb0","zs","ztm",')
rep('set("sect",v.sect);', 'set("sect",v.sect);set("zbd",v.zband);set("zb0",v.zband);')
rep('for(const k of ["candle","mean","exit",', 'for(const k of ["zbd","zb0","candle","mean","exit",')
# ---- labelled price lines for the next session (or the bar after the replay cursor)
rep(" const sims=simAll();\n if(UI.ov.mine)",
    ''' if(UI.ov.zband&&ARR&&ARR.zbdArr){const nx=c+1,zs0=ARR.zsArr?ARR.zsArr[c]:NaN,bd=ARR.zbdArr[nx],b0=ARR.zb0Arr[nx];
  if(isF(bd)&&!(isF(zs0)&&zs0<=ZC_LINE))PLINES.push(SER.candle.createPriceLine({price:bd,color:"#4f96f0",lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:`Z −2.62 next close ${spct(bd/d.c[c]-1,1)}`}));
  if(isF(b0))PLINES.push(SER.candle.createPriceLine({price:b0,color:"rgba(195,194,183,.7)",lineWidth:1,lineStyle:LW.LineStyle.Dotted,axisLabelVisible:true,title:`Z 0 ${spct(b0/d.c[c]-1,1)}`}));
  if(c===d.d.length-1&&msOn(st.sym)){const W=zWeekBand(d);if(W.fresh&&isF(W.price))PLINES.push(SER.candle.createPriceLine({price:W.price,color:"#7fb2f0",lineWidth:1,lineStyle:LW.LineStyle.SparseDotted,axisLabelVisible:true,title:`weekly −2.08 by Thu ${spct(W.price/d.c[c]-1,1)}`}))}}
 const sims=simAll();
 if(UI.ov.mine)''')
# ---- inspector section, before the touch momentum section
rep(" if(ARR&&ARR.ztmAll&&ARR.n===d.d.length){",
    ''' if(ARR&&ARR.zbdArr&&ARR.n===d.d.length){const nx=i+1,ref=d.c[i],lim=saudiSym(st.sym)?.10:0,zs0=ARR.zsArr?ARR.zsArr[i]:NaN,below=isF(zs0)&&zs0<=ZC_LINE,W=i===d.d.length-1&&msOn(st.sym)?zWeekBand(d):null;
  h+=`<div class="sec">Z bands · the close that puts the stretch Z on a line, ${i===d.d.length-1?"next session":"the session after "+d.d[i]}</div><table class="t">
   <tr><td>stretch Z −2.62 (daily Z-swing line)</td><td class="n">${below?'<span class="note">already below: a new touch needs Z back above −2.62 first</span>':zbCell(ARR.zbdArr[nx],ref,lim)}</td></tr>
   <tr><td>stretch Z 0 (the stretch fully gone)</td><td class="n">${zbCell(ARR.zb0Arr[nx],ref,lim)}</td></tr>
   ${W?`<tr><td>weekly stretch Z −2.08 at ${esc(W.week)}</td><td class="n">${W.fresh?zbCell(W.price,ref,0):`<span class="note">weekly Z ${fmt(W.prevZ,2)}: ${isF(W.prevZ)&&W.prevZ<=TF_LINE_W?"already below the line":"—"}</span>`}</td></tr>`:""}</table>
  <div class="note">Exact, not a forecast: the stretch Z at the next close depends on that close in a fixed way, so these are the closes where it lands on each line. A close at or below the −2.62 band is a daily Z touch (checked: no disagreement over 430,780 stock-days). Use them for price alerts; the Z-swing buy still needs the other filters.</div>`}
 if(ARR&&ARR.ztmAll&&ARR.n===d.d.length){''')
# ---- scanner columns
rep('<th title="Z touch momentum: level-weighted', '<th title="Close at the next session that puts the daily stretch Z at −2.62 (a daily Z touch). Struck through when it is beyond the ±10% daily limit.">close for Z −2.62</th><th title="Weekly close (Thursday) that puts the weekly stretch Z at −2.08 (a weekly Z touch); only when last week was above the line.">week close for −2.08</th><th title="Z touch momentum: level-weighted')
rep('${r.zw.toFixed(2)}</span>`:"—"}</td><td>${tmCell(r)}</td>',
    '${r.zw.toFixed(2)}</span>`:"—"}</td><td>${r.fd?\'<span class="up">touched today</span>\':r.bd!=null?zbCell(r.bd,r.close,.10):\'<span class="note">below</span>\'}</td><td>${r.bw!=null?zbCell(r.bw,r.close,0):\'<span class="note">${r.fw?"touched":"below / —"}</span>\'}</td><td>${tmCell(r)}</td>')
# ---- research note
rep("<h2>Z touch momentum (round 60, the pane under Stretch Z)</h2>",
    """<h2>Z bands (round 61): the price that triggers the stretch Z</h2>
<p>The stretch Z at tomorrow's close depends on tomorrow's close in a fixed, straight-line way: everything else in it is already known tonight. So for any level there is one exact close that puts the stretch Z on it. The chart draws two of these as step lines on the price pane: the <b>Z −2.62 band</b> (dashed blue, the daily Z-swing line) and the <b>Z 0 band</b> (dotted grey, where the stretch is gone). A candle closing at or below the blue band is a daily Z touch; this was checked against the scanner with no disagreement over 430,780 stock-days. The labelled lines on the right are the values for the next session, plus the weekly −2.08 line for this week's (or next week's) Thursday close. The Saudi stretch-Z scan lists the same closes for each stock, struck through when they are beyond the ±10% daily limit. They are good levels for price alerts; a Z-swing buy still needs the ML rank, the market model, market momentum and a profitable company.</p>
<p>Round 61 also tested three new readings of the stretch Z as Z-swing filters: the shape of the stretch (a sudden shock vs a slow grind), the stock's own rebound record after earlier dips, and the selling volume on the signal day. None helped in the direction set in advance, and the two patterns that pointed the other way in Saudi data (slow grinds and quiet dips doing better) did not hold in the US, so nothing changed in the rule.</p>
<h2>Z touch momentum (round 60, the pane under Stretch Z)</h2>""")
assert "zBands(" in s
open(p, "w").write(s); print("patched v26:", len(s), "bytes")
