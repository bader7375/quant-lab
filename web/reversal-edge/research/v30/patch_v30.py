"""v29 -> v30 (round 67, the user's choice 2026-11-09): plan A - Market returned only, 10% each; the scan shows the plan and the sizes."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v29 · Saudi + US scanner · Z score most volatile first", "reversal edge v30 · Saudi + US scanner · plan A (market returned, 10%)")
rep('. Z score signals: <b>${zsOn()?"ON":"off"}</b>. Switches: Data &amp; settings.</span></div>`}',
    '${O.plan?` · <b class="up">your plan ${esc(O.plan)}</b>: buy only these, ${Math.round(100*(O.mr_size||.05))}% of the account each, at most 5 (most volatile first); idle money in a SAR money-market fund`:""}'
    '. Z score signals: <b>${zsOn()?"ON":"off"}</b>. Switches: Data &amp; settings.</span></div>`}')
rep("return zsT+(mrT?\" · \"+mrT:\"\")+'<span class=\"note\"> · 5%, hold 40 sessions</span>'}",
    "const szT=[zsOn()?\"Z score 5%\":\"\",mrT.indexOf(\"BUY\")>=0?`${zsOn()?\"market returned \":\"\"}${Math.round(100*((O7&&O7.mr_size)||.05))}% of the account`:\"\"].filter(Boolean).join(\", \");\n"
    "     return zsT+(mrT?\" · \"+mrT:\"\")+(szT?`<span class=\"note\"> · ${szT}, hold 40 sessions</span>`:\"\")}")
open(p, "w").write(s); print("v30 written")
