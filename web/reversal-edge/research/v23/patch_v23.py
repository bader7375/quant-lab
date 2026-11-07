"""v22 -> v23: US most traded 30 table (option ranges, round 44) in the Scanner tab, from the daily export (ml/latest -> us30)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
BOX = '''<div class="planbox" id="u30-box" hidden><div class="ai-head"><b>US most traded 30 · option ranges</b><span class="note">calibrated expected ranges for call / put strikes, rebuilt daily</span><label class="note" for="u30-h">horizon</label><select id="u30-h"><option value="2">2 sessions</option><option value="5" selected>5 sessions</option><option value="10">10 sessions</option></select></div><div class="note" id="u30-note" style="margin:6px 0"></div><div class="tw"><table class="bl" id="u30-t"></table></div></div>
<h3 style="font-size:13px;margin:16px 0 6px;color:var(--muted,#8a8a85);letter-spacing:.06em">ALL SYMBOLS · LATEST BAR</h3>'''
JS = r'''
// ------------------------------------------------ v23: US most traded 30 - calibrated option ranges (round 44); no direction call (the direction model had no edge)
function drawUS30(){if(typeof MLPF==="undefined"||!MLPF||!MLPF.us30)return;const U=MLPF.us30,R=U.rows||[];if(!R.length)return;$("u30-box").hidden=false;const hz=+($("u30-h").value||5);
 $("u30-note").innerHTML=`Prices to the ${esc(U.date)} US close · list of ${esc(U.list_date)}: F, GM, TSLA, AAPL, MSFT + the 25 largest 20-day dollar volumes (market cap ≥ $10B, price ≥ $5), rebuilt every day. <b>Ranges, not direction:</b> the close ${hz} sessions from now has an 84% chance to stay below the <b>call 84%</b> level (95% for call 95%) and the same chance to stay above the put level. Tested 2010–26: promised 84% / 95%, delivered 83–84% / 94–95%. The price <i>touches</i> an 84% level at some point before then about 30% of the time (a 95% level about 10%). A call / put direction model was tested at 2, 5 and 10 sessions and did not beat a coin flip, so no buy-call or buy-put signal is shown.`;
 $("u30-t").innerHTML=`<tr><th>#</th><th style="text-align:left">stock</th><th>close $</th><th>day</th><th>$ traded/day</th><th>put 95%</th><th>put 84%</th><th>call 84%</th><th>call 95%</th><th>stretch Z</th><th>RSI(2)</th><th>200-day avg</th></tr>`+
  R.map((r,i)=>{const g=r["r"+hz],nm=(U.names&&U.names[r.sym])||"",dv=U.dv_m&&U.dv_m[r.sym];return `<tr><td>${i+1}</td><td style="text-align:left"><b>${esc(r.sym)}</b> <span class="note">${esc(nm.slice(0,24))}</span></td><td>${isF(r.close)?r.close.toFixed(2):"—"}</td><td class="${cl(r.chg)}">${spct(r.chg,1)}</td><td>${isF(dv)?"$"+(dv/1000).toFixed(1)+"B":"—"}</td>`+
   (g?`<td>${g.dn95.toFixed(2)}</td><td>${g.dn84.toFixed(2)}</td><td>${g.up84.toFixed(2)}</td><td>${g.up95.toFixed(2)}</td>`:'<td colspan="4"><span class="note">history too short</span></td>')+
   `<td>${isF(r.zc)?r.zc.toFixed(2):"—"}</td><td>${isF(r.rsi2)?r.rsi2.toFixed(0):"—"}</td><td>${r.above200?'<span class="up">above</span>':'<span class="down">below</span>'}</td></tr>`}).join("")}
document.addEventListener("change",e=>{if(e.target&&e.target.id==="u30-h"){try{drawUS30()}catch(err){console.error(err)}}});
'''
H3 = '<h3 style="font-size:13px;margin:16px 0 6px;color:var(--muted,#8a8a85);letter-spacing:.06em">ALL SYMBOLS · LATEST BAR</h3>'
CALL = ('try{drawZScans()}catch(e){console.error(e)};', 'try{drawZScans()}catch(e){console.error(e)};try{drawUS30()}catch(e){console.error(e)};')
BRAND = ("reversal edge v22 · Saudi + US stretch-Z scanner", "reversal edge v23 · Saudi + US scanner · US most traded 30")
ANCHOR = "\n// ------------------------------------------------ v22: scanner tables"
def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:80], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)
patch("index.html", [(H3, BOX), CALL, BRAND, (ANCHOR, JS + ANCHOR)])
patch("body.html", [(H3, BOX), BRAND])
patch("app7.js", [CALL, (ANCHOR, JS + ANCHOR)])
print("patched v23")
