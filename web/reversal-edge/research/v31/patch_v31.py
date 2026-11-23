"""v30 -> v31 (round 68): the scan follows the plan book in the daily export (held positions, free slots, sells due, and the tested
rule's decision for every fresh signal) instead of re-deriving buys in the page."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v30 · Saudi + US scanner · plan A (market returned, 10%)", "reversal edge v31 · Saudi + US scanner · plan A with its plan book")
# ---- status line: the plan book
rep("(on&&O.blocked&&O.blocked.length?` · ${O.blocked.length} stocks blocked (Z score bought them before the turn)`:\"\")+",
    "(on&&O.blocked&&O.blocked.length?` · ${O.blocked.length} stocks blocked (their paper trade started before the turn)`:\"\")+"
    "(on&&O.book?` · plan book: <b>${O.book.held.length} of ${O.book.slots}</b> slots in use${O.book.held.length?` (${O.book.held.map(h=>`${esc(nameOf(h.sym))} ${spct(h.ret,1)}, ${h.left} sessions left`).join(\"; \")})`:\"\"}`"
    "+(O.book.due.length?` · <b class=\"down\">SELL at the next open</b> (40 sessions done): ${O.book.due.map(h=>`${esc(nameOf(h.sym))} ${spct(h.ret,1)}`).join(\", \")}`:\"\"):\"\")+")
# ---- buys and their order come from the plan book when the export has one
rep("const buyQ=Z.filter(r=>(r.fd||r.fw)&&r.pct>=.5&&on&&mok&&!r.loss).map(r=>r.sym);",
    "const hasBook=!!(MLPF.opt7&&MLPF.opt7.book),buyQ=Z.filter(r=>(r.fd||r.fw)&&r.pct>=.5&&on&&mok&&!r.loss&&(!hasBook||(r.pa&&r.pa!==\"held\"&&r.pa!==\"repeat\"&&r.pa!==\"blocked\"))).map(r=>r.sym),mrQ=Z.filter(r=>r.pa===\"buy\").map(r=>r.sym);\n"
    "  const PAT=r=>({buy:`<span class=\"up\"><b>BUY next open</b> · market returned${mrQ.length>1?` · #${mrQ.indexOf(r.sym)+1} of ${mrQ.length} by volatility`:\"\"}</span>`,"
    "noslot:'<span class=\"note\">market returned: skip (no free slot, 5 positions held)</span>',"
    "held:`<span class=\"note\">market returned: already held${r.ps?\" (signal \"+esc(r.ps)+\")\":\"\"}: keep, no second buy</span>`,"
    "repeat:`<span class=\"note\">market returned: skip (it signalled after the turn${r.ps?\" on \"+esc(r.ps):\"\"} and was not bought then)</span>`,"
    "blocked:'<span class=\"note\">market returned: skip (its paper trade started before the turn)</span>',"
    "wait:'<span class=\"note\">market returned: skip (the market has not turned)</span>',"
    "before:'<span class=\"note\">market returned: before your plan started</span>'})[r.pa]||\"\";")
rep("     if(why.length)return `<span class=\"note\">fresh ${r.fd?\"daily\":\"weekly\"} touch · skip: ${why.join(\", \")}</span>`;\n",
    "     if(why.length)return `<span class=\"note\">fresh ${r.fd?\"daily\":\"weekly\"} touch · skip: ${why.join(\", \")}</span>`;\n"
    "     if(hasBook&&!r.pa)return `<span class=\"note\">fresh ${r.fd?\"daily\":\"weekly\"} touch · not a signal by the tested rule</span>`;\n"
    "     const again=hasBook&&(r.pa===\"held\"||r.pa===\"repeat\"||r.pa===\"blocked\");\n")
rep("const O7=MLPF.opt7,zsT=zsOn()?`<span class=\"up\"><b>BUY next open</b> · Z score",
    "const O7=MLPF.opt7,zsT=zsOn()&&again?'<span class=\"note\">Z score: its paper trade is already open, no new entry</span>':zsOn()?`<span class=\"up\"><b>BUY next open</b> · Z score")
rep("mrT=!o7On()||!O7?\"\":!O7.gate?", "mrT=!o7On()||!O7?\"\":hasBook?PAT(r):!O7.gate?")
rep("const szT=[zsOn()?\"Z score 5%\":\"\",", "const szT=[zsOn()&&!again?\"Z score 5%\":\"\",")
rep("(entered by the rule; the 5-position cap takes ${MLPF.zorder===\"volatility\"?\"the most volatile first\":\"the highest ML ranks first\"})",
    "(the Z score rule on paper, one per stock; for Market returned, those from before the market turn stay blocked until they end)")
open(p, "w").write(s); print("v31 written")
