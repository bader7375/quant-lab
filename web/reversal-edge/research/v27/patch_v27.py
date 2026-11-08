"""v26 -> v27: option 7 switch (buy Z swings only after the market turns) in Settings, its status in the Saudi stretch-Z scan."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v26 · Saudi + US scanner · Z bands", "reversal edge v27 · Saudi + US scanner · option 7 switch")
rep(".zbl b{color:var(--ink)}", ".o7{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;margin-bottom:6px}.o7 svg{display:block;flex:0 0 auto}.o7 span{min-width:0}\n.zbl b{color:var(--ink)}")
# ---- the switch in Settings (after the Saudi ML filter)
rep('<option value="off">off</option></select>\n          <label for="c-apsize"',
    '<option value="off">off</option></select>\n'
    '          <label for="o7-mode" title="Option 7 (round 47, pending decision): take a Z-swing signal only while the market-turn window is open - the market index (equal-weight liquid Saudi stocks) closed 4% above its 20-day low after a fall of 10% or more, within the last 20 sessions - and skip stocks the live rule bought before the turn. 2020-26: 88% winners, +12.1% per trade, worst 5% -5.2% (all Z swing: 71%, +7.4%, -11.7%). It missed money in fast V-shaped rebounds (April 2025) and in late 2015. The daily list follows its own switch (daily/settings.json); this setting changes how the terminal shows Z-swing signals.">Z swing: option 7 (buy only after the market turns)</label>'
    '<select id="o7-mode"><option value="auto">as the daily list</option><option value="on">on</option><option value="off">off</option></select>\n'
    '          <label for="c-apsize"')
rep(' if(el.id.startsWith("a-")){saveAcct();ticketChanged(false);renderLive();return}',
    ' if(el.id.startsWith("a-")){saveAcct();ticketChanged(false);renderLive();return}\n if(el.id==="o7-mode"){UI.o7=el.value;saveUI();try{drawZScans()}catch(e){}return}')
rep("UI.ztm=Object.assign({L:250,mode:\"net\"},UI.ztm||{});",
    "UI.ztm=Object.assign({L:250,mode:\"net\"},UI.ztm||{});\nUI.o7=[\"auto\",\"on\",\"off\"].includes(UI.o7)?UI.o7:\"auto\";try{$(\"o7-mode\").value=UI.o7}catch(e){}")
# ---- helpers: is option 7 on for this viewer, its status line with a small market chart
JS = r'''
// ------------------------------------------------ v27: option 7 switch (round 47): Z swing only after the market turns
function o7On(){const O=typeof MLPF!=="undefined"&&MLPF?MLPF.opt7:null;return UI.o7==="on"||(UI.o7!=="off"&&!!(O&&O.on))}
function o7Spark(O){const sp=O&&O.spark;if(!sp||!sp.idx||!sp.idx.length)return "";const W=180,H=40,n=sp.idx.length,v=[...sp.idx,...sp.trig].filter(isF);if(!v.length)return "";
 const lo=Math.min(...v),hi=Math.max(...v),X=i=>(i+.5)*W/n,Y=x=>2+(H-4)*(1-(x-lo)/((hi-lo)||1));let r="",i=0;
 while(i<n){if(!sp.gate[i]){i++;continue}let j=i;while(j<n&&sp.gate[j])j++;r+=`<rect x="${(X(i)-W/n/2).toFixed(1)}" y="0" width="${((j-i)*W/n).toFixed(1)}" height="${H}" fill="rgba(79,209,165,.16)"/>`;i=j}
 const path=(a)=>{let d="",pen=false;a.forEach((x,k)=>{if(!isF(x)){pen=false;return}d+=(pen?"L":"M")+X(k).toFixed(1)+" "+Y(x).toFixed(1);pen=true});return d};
 return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Market index over the last ${n} sessions with the turn line"><title>Market index (equal-weight liquid Saudi stocks), last ${n} sessions. Dashed: 20-day low + 4% (the turn line). Shaded: option 7 window open.</title>${r}<path d="${path(sp.trig)}" fill="none" stroke="#4fd1a5" stroke-width="1" stroke-dasharray="3 2"/><path d="${path(sp.idx)}" fill="none" stroke="#e8e6dc" stroke-width="1.6"/></svg>`}
function o7Line(){const O=typeof MLPF!=="undefined"&&MLPF?MLPF.opt7:null;if(!O)return "";const on=o7On(),fd=x=>{if(!x)return "—";const d=new Date(x+"T00:00:00Z");return d.toUTCString().slice(0,11)};
 return `<div class="o7">${o7Spark(O)}<span><b>Option 7</b> (Z swing only after the market turns): <b class="${on?"up":""}">${on?"ON":"off"}</b> ${UI.o7==="auto"?"(as the daily list)":"(your terminal setting; the daily list is "+(O.on?"on":"off")+")"} · market index ${spct(O.bounce,1)} above its 20-day low, ${spct(O.dd,0)} from its 1-year high · turn window `+
  (O.gate?`<b class="up">open</b> since ${fd(O.window_start)}, until about ${fd(O.window_end)}`:'<b class="down">closed</b> (opens on a close 4% above the 20-day low after a fall of 10% or more)')+
  (on&&O.blocked&&O.blocked.length?` · ${O.blocked.length} stocks blocked (bought by the live rule before the turn)`:"")+`. Settings → Z swing: option 7.</span></div>`}
'''
rep("// ------------------------------------------------ v22: scanner tables (Saudi and US stretch Z, next session) from the daily export", JS + "// ------------------------------------------------ v22: scanner tables (Saudi and US stretch Z, next session) from the daily export")
rep('$("zsa-note").innerHTML=`Prices to the ${esc(MLPF.date)} close.', '$("zsa-note").innerHTML=o7Line()+`Prices to the ${esc(MLPF.date)} close.')
rep('if(r.loss)why.push("loss-making (your rule)");', 'if(r.loss)why.push("loss-making (your rule)");if(o7On()&&MLPF.opt7){if(!MLPF.opt7.gate)why.push("option 7: the market has not turned");else if(r.b7)why.push("option 7: bought before the turn")}')
# ---- research note
rep("<h2>Z bands (round 61): the price that triggers the stretch Z</h2>",
    """<h2>Option 7 switch: Z swing only after the market turns</h2>
<p>Settings → <i>Z swing: option 7</i>. When it is on, a Z-swing signal counts only while the market-turn window is open: the market index (an equal-weight average of the liquid Saudi stocks, about 100-200 names; official TASI history is not available to this system) has closed at least 4% above its lowest close of the last 20 sessions while at least 10% below its 1-year high, within the last 20 sessions. Stocks the live rule bought before the turn stay blocked for their 40 sessions. The Saudi stretch-Z scan shows the window's state with a small chart of the index. In 2020-26 the trades after a turn won 88% of the time (+12.1% per trade, worst 5% −5.2%) against 44% (0.0%) for the trades before a turn; it cost money in fast V-shaped rebounds (April 2025) and in late 2015. The daily list has its own switch (ask Claude to turn it on or off); the terminal setting can follow it or override it for this browser.</p>
<h2>Z bands (round 61): the price that triggers the stretch Z</h2>""")
open(p, "w").write(s); print("patched v27:", len(s), "bytes")
