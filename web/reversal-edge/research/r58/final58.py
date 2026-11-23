"""Round 58 decision (PREREG.md): pick on DESIGN, confirm once on CONFIRM, with the US replication label."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); E = json.load(open(os.path.join(HERE, "eval58.json")))
U = json.load(open(os.path.join(HERE, "u58_results.json"))) if os.path.exists(os.path.join(HERE, "u58_results.json")) else {}
B = E["S0"]; cands = [k for k in E if k != "S0"]
ok = [k for k in cands if E[k]["DESIGN"]["core_sh"] >= B["DESIGN"]["core_sh"] - .05]
pick = max(ok, key=lambda k: E[k]["DESIGN"]["ic"]); p = E[pick]
print(f"{'model':6s} {'DESIGN IC':>9s} {'CONF IC':>8s} | {'top10% D':>8s} {'top10% C':>8s} | {'Core Sh D':>9s} {'Core Sh C':>9s} {'CAGR C':>7s} | {'Z avg D':>7s} {'Z avg C':>7s}")
for k in ["S0"] + sorted(cands, key=lambda k: -E[k]["DESIGN"]["ic"]):
    d, c = E[k]["DESIGN"], E[k]["CONFIRM"]
    print(f"{k:6s} {d['ic']:9.4f} {c['ic']:8.4f} | {100 * d['top']:+7.2f}% {100 * c['top']:+7.2f}% | {d['core_sh']:9.2f} {c['core_sh']:9.2f} {100 * c['core_cagr']:+6.1f}% | {100 * d['z_avg']:+6.1f}% {100 * c['z_avg']:+6.1f}%" + ("   <- pick" if k == pick else ""))
c, b = p["CONFIRM"], B["CONFIRM"]
tests = {"IC higher": c["ic"] > b["ic"], "Core ML Sharpe higher": c["core_sh"] > b["core_sh"], "top-decile excess higher": c["top"] > b["top"], "Z-swing average not lower by > 0.5 pt": c["z_avg"] >= b["z_avg"] - .005}
print(f"\nDESIGN pick: {pick} (IC {p['DESIGN']['ic']:.4f} vs M0 {B['DESIGN']['ic']:.4f}; Core Sharpe {p['DESIGN']['core_sh']:.2f} vs {B['DESIGN']['core_sh']:.2f})")
for k, v in tests.items(): print(f"  CONFIRM {k}: {v}")
adopt = all(tests.values()); print(f"DECISION: {'ADOPT ' + pick if adopt else 'keep M0'}")
if U: print("US replication:", U)
json.dump({"pick": pick, "tests": tests, "adopt": adopt}, open(os.path.join(HERE, "final58.json"), "w"), indent=1)
