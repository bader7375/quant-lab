"""v31 -> v32 (2026-11-10): plan Z. When the export's plan book is the Z score book (opt7.book.kind "Z"), the scan shows its decisions
(buy in tested order, no free slot, already held, paper trade open) and the plan line names the Z score plan and its size."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v31 · Saudi + US scanner · plan A with its plan book", "reversal edge v32 · Saudi + US scanner · Z score plan with its plan book")
rep("${O.plan?` · <b class=\"up\">your plan ${esc(O.plan)}</b>: buy only these, ${Math.round(100*(O.mr_size||.05))}% of the account each, at most 5 (most volatile first); idle money in a SAR money-market fund`:\"\"}",
    "${O.plan===\"Z\"?` · <b class=\"up\">your plan: Z score</b> (stretch Z with ML): ${Math.round(100*((O.book&&O.book.size)||.05))}% of the account each, at most 5 (most volatile first), hold 40 sessions; the turn window is context only; idle money in a SAR money-market fund`"
    ":O.plan?` · <b class=\"up\">your plan ${esc(O.plan)}</b>: buy only these, ${Math.round(100*(O.mr_size||.05))}% of the account each, at most 5 (most volatile first); idle money in a SAR money-market fund`:\"\"}")
rep("     const again=hasBook&&(r.pa===\"held\"||r.pa===\"repeat\"||r.pa===\"blocked\");\n",
    "     const again=hasBook&&(r.pa===\"held\"||r.pa===\"repeat\"||r.pa===\"blocked\");\n"
    "     if(hasBook&&MLPF.opt7.book.kind===\"Z\"){const B=MLPF.opt7.book,sz=Math.round(100*(B.size||.05)),tn=MLPF.opt7.gate?\"after the market turn\":\"before the market turn\";\n"
    "      return ({buy:`<span class=\"up\"><b>BUY next open</b> · Z score${r.fd?\"\":\" (weekly)\"}${mrQ.length>1?` · #${mrQ.indexOf(r.sym)+1} of ${mrQ.length} by volatility`:\"\"}</span><span class=\"note\"> · ${sz}% of the account, hold 40 sessions · ${tn}</span>`,\n"
    "       noslot:`<span class=\"note\">Z score: skip (no free slot, ${B.slots} positions held)</span>`,rule:'<span class=\"note\">Z score: not bought (held back by the plan\\'s own limits)</span>',\n"
    "       held:`<span class=\"note\">Z score: already held${r.ps?\" (signal \"+esc(r.ps)+\")\":\"\"}: keep, no second buy</span>`,\n"
    "       repeat:`<span class=\"note\">Z score: skip (it signalled${r.ps?\" on \"+esc(r.ps):\"\"} and was not bought then; no second signal within its 40 sessions)</span>`,\n"
    "       before:'<span class=\"note\">Z score: before your plan started</span>'})[r.pa]||'<span class=\"note\">Z score: no action</span>'}\n")
rep("(on&&O.blocked&&O.blocked.length?` · ${O.blocked.length} stocks blocked", "(on&&O.plan!==\"Z\"&&O.blocked&&O.blocked.length?` · ${O.blocked.length} stocks blocked")
open(p, "w").write(s); print("v32 written")
