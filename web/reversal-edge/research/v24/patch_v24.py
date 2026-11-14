"""v23 -> v24: the user found the option ranges and the dollar-volume list useless. The US table now lists the market leaders (30 largest US
companies) with the tested US rule (sell-off swing) instead of option ranges."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
OLD_BOX_START = '<div class="planbox" id="u30-box" hidden>'
NEW_BOX = '''<div class="planbox" id="u30-box" hidden><div class="ai-head"><b>US market leaders · the 30 largest US companies</b><span class="note">updated every day; the tested US rule for each: the sell-off swing</span></div><div class="note" id="u30-note" style="margin:6px 0"></div><div class="tw"><table class="bl" id="u30-t"></table></div></div>'''
JS = r'''
// ------------------------------------------------ v24: US market leaders (30 largest US companies) with the US sell-off swing status
function drawUS30(){if(typeof MLPF==="undefined"||!MLPF||!MLPF.us30)return;const U=MLPF.us30,R=U.rows||[];if(!R.length)return;$("u30-box").hidden=false;const win=!!U.window,nb=R.filter(r=>r.fd||r.fw).length;
 $("u30-note").innerHTML=`Prices to the ${esc(U.date)} US close · the 30 largest US companies by market value (list of ${esc(U.list_date)}). US sell-off window: ${isF(U.ms)?`market momentum <b>${U.ms.toFixed(2)}</b> → `+(win?'<span class="up"><b>OPEN</b></span>':'<span class="down">closed</span> (opens at −1.18 or lower)'):"unknown"}. A leader is a buy only on the first close at its stretch-Z line (daily ${U.dline}, weekly ${U.wline}) while the window is open: buy at the next US open, hold 40 sessions. Record (115 large caps): 2018–26 76% winners; random large caps on the same days did almost as well, so the edge is the timing. ${nb?`<b>${nb} fresh touch${nb>1?"es":""} at this close.</b>`:""}`;
 const pc=v=>isF(v)?spct(v,1):"—",st=r=>r.fd||r.fw?(win?`<span class="up"><b>BUY next US open</b> · ${r.fd?"daily":"weekly"} touch · hold 40</span>`:'<span class="note">touched the line, window closed: no buy</span>'):isF(r.zc)&&r.zc<=U.dline?'<span class="note">below the line, not a fresh touch</span>':isF(r.zc)&&r.zc<=U.dline+.4?`<span class="note">near the line: watch${win?"":" (window closed)"}</span>`:'<span class="note">—</span>';
 $("u30-t").innerHTML=`<tr><th>#</th><th style="text-align:left">company</th><th>value</th><th>close $</th><th>day</th><th>1 month</th><th>from 52w high</th><th>stretch Z</th><th>weekly Z${R[0]&&R[0].wk_done?"":" (forming)"}</th><th>RSI(2)</th><th>200-day avg</th><th style="text-align:left">next US session</th></tr>`+
  R.map((r,i)=>{const nm=(U.names&&U.names[r.sym])||"",cap=U.cap_bn&&U.cap_bn[r.sym];return `<tr><td>${i+1}</td><td style="text-align:left"><b>${esc(r.sym)}</b> <span class="note">${esc(nm.slice(0,24))}</span></td><td>${isF(cap)?(cap>=1000?"$"+(cap/1000).toFixed(2)+"T":"$"+cap+"B"):"—"}</td><td>${isF(r.close)?r.close.toFixed(2):"—"}</td><td class="${cl(r.chg)}">${pc(r.chg)}</td><td class="${cl(r.m1)}">${pc(r.m1)}</td><td>${pc(r.from_high)}</td>`+
   `<td><b style="color:${isF(r.zc)&&r.zc<=U.dline?"#4f96f0":isF(r.zc)&&r.zc<=U.dline+.4?"#7fb2f0":"inherit"}">${isF(r.zc)?r.zc.toFixed(2):"—"}</b></td><td>${isF(r.zw)?`<span style="color:${r.zw<=U.wline?"#4f96f0":"inherit"}">${r.zw.toFixed(2)}</span>`:"—"}</td><td>${isF(r.rsi2)?r.rsi2.toFixed(0):"—"}</td><td>${r.above200==null?"—":r.above200?'<span class="up">above</span>':'<span class="down">below</span>'}</td><td style="text-align:left">${st(r)}</td></tr>`}).join("")}
'''
def patch(fn):
    s = open(fn).read()
    if OLD_BOX_START in s:
        i = s.index(OLD_BOX_START); j = s.index("</div></div>", s.index('id="u30-t"', i)) + len("</div></div>"); s = s[:i] + NEW_BOX + s[j:]
    if "// ------------------------------------------------ v23:" in s:
        i = s.index("\n// ------------------------------------------------ v23:"); j = s.index("\n// ------------------------------------------------ v22: scanner tables", i); s = s[:i] + JS + s[j:]
    s = s.replace("reversal edge v23 · Saudi + US scanner · US most traded 30", "reversal edge v24 · Saudi + US scanner · US market leaders")
    assert "u30-h" not in s and "option ranges" not in s, fn
    open(fn, "w").write(s)
for fn in ("index.html", "body.html", "app7.js"): patch(fn)
print("patched v24")
