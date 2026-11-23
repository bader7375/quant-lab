"""v28 -> v29 (round 66, the user's choice 2026-11-09): Z score signals most volatile first; a 60-day volatility column in the Saudi scan."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = "index.html"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep("reversal edge v28 · Saudi + US scanner · Z score + market returned", "reversal edge v29 · Saudi + US scanner · Z score most volatile first")
# ---- meter style for the volatility cell (same shape as the touch meter)
rep(".tmb i{display:block;height:100%}", ".tmb i{display:block;height:100%}\n.vlc{display:inline-flex;gap:6px;align-items:center;justify-content:flex-end}.vlc i{display:block;height:100%;background:#d9a54a}")
# ---- the cell
rep("function tmCell(r){",
    "function volCell(r){if(!isF(r.vol))return '<span class=\"note\">—</span>';const vr=isF(r.vr)?r.vr:null;\n"
    " return `<span class=\"vlc\" title=\"60-day volatility: ${(100*r.vol).toFixed(2)}% a day (about ${(100*r.vol*Math.sqrt(250)).toFixed(0)}% a year)${vr!=null?`; more volatile than ${Math.round(100*vr)}% of liquid Saudi stocks`:\"\"}. Round 66: with more Z score signals than free slots, the most volatile go first.\">`+\n"
    "  `${vr!=null?`<span class=\"tmb\"><i style=\"width:${Math.round(100*vr)}%\"></i></span>`:\"\"}<b>${(100*r.vol).toFixed(1)}%</b>${vr!=null?`<span class=\"note\">${Math.round(100*vr)}</span>`:\"\"}</span>`}\n"
    "function tmCell(r){")
# ---- table header and cell
rep("<th>ML rank</th><th>accounts</th><th style=\"text-align:left\">next session</th>",
    "<th title=\"60-day volatility: daily standard deviation of returns over the last 60 sessions; bar and small number = rank among liquid Saudi stocks (100 = most volatile). Z score signals are taken most volatile first (round 66).\">volatility 60d</th><th>ML rank</th><th>accounts</th><th style=\"text-align:left\">next session</th>")
rep("<td>${tmCell(r)}</td><td>${Math.round(100*r.pct)}%</td>", "<td>${tmCell(r)}</td><td>${volCell(r)}</td><td>${Math.round(100*r.pct)}%</td>")
# ---- order wording
rep("hold at most 5 Z-swing positions, taking the rows from the top (highest ML rank first).",
    "hold at most 5 Z-swing positions, taking the rows from the top (${MLPF.zorder===\"volatility\"?\"<b>most volatile first</b>: 60-day volatility, round 66; ML rank 50%+ stays a filter\":\"highest ML rank first\"}).")
rep("(entered by the rule; the 5-position cap takes the highest ML ranks first)",
    "(entered by the rule; the 5-position cap takes ${MLPF.zorder===\"volatility\"?\"the most volatile first\":\"the highest ML ranks first\"})")
# ---- priority number on buys
rep("const st_=r=>{if(r.fd||r.fw){const why=[];",
    "const buyQ=Z.filter(r=>(r.fd||r.fw)&&r.pct>=.5&&on&&mok&&!r.loss).map(r=>r.sym);\n  const st_=r=>{if(r.fd||r.fw){const why=[];")
rep("zsT=zsOn()?`<span class=\"up\"><b>BUY next open</b> · Z score${r.fd?\"\":\" (weekly)\"}</span>`",
    "zsT=zsOn()?`<span class=\"up\"><b>BUY next open</b> · Z score${r.fd?\"\":\" (weekly)\"}${buyQ.length>1?` · #${buyQ.indexOf(r.sym)+1} of ${buyQ.length}${MLPF.zorder===\"volatility\"?\" by volatility\":\" by ML\"}`:\"\"}</span>`")
open(p, "w").write(s); print("v29 written", len(s))
# ---- existing bug (since v25): the weekly band cell printed the template text instead of "touched" / "below / —"
s = open(p).read()
rep("'<span class=\"note\">${r.fw?\"touched\":\"below / —\"}</span>'", "`<span class=\"note\">${r.fw?\"touched\":\"below / —\"}</span>`")
open(p, "w").write(s); print("weekly cell fixed")
