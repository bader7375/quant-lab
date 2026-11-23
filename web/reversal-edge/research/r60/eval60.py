"""Round 60 T3: ranker C vs C + Z-touch-momentum features (CZ), with round 58's evaluation (eval58.evaluate)."""
import os, sys, json, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r58")); import eval58
res = {n: eval58.evaluate(n, pd.read_parquet(p)) for n, p in (("C", os.path.join(H, "../r27/preds/C.parquet")), ("CZ", os.path.join(H, "preds/CZ.parquet")))}
os.chdir(H); json.dump(res, open("eval60.json", "w"), indent=1, default=float)
for n, r in res.items():
    d, c = r["DESIGN"], r["CONFIRM"]
    print(f"{n:3s} | DESIGN IC {d['ic']:.4f} top10% {100 * d['top']:+.2f}% Core Sh {d['core_sh']:.2f} CAGR {100 * d['core_cagr']:+.1f}% Z {d['z_n']} {100 * d['z_avg']:+.1f}% {100 * d['z_win']:.0f}%"
          f" || CONFIRM IC {c['ic']:.4f} top10% {100 * c['top']:+.2f}% Core Sh {c['core_sh']:.2f} CAGR {100 * c['core_cagr']:+.1f}% Z {c['z_n']} {100 * c['z_avg']:+.1f}% {100 * c['z_win']:.0f}%")
a, b = res["C"], res["CZ"]
conds = dict(design_ic=b["DESIGN"]["ic"] > a["DESIGN"]["ic"], ic=b["CONFIRM"]["ic"] > a["CONFIRM"]["ic"], core=b["CONFIRM"]["core_sh"] > a["CONFIRM"]["core_sh"],
             top=b["CONFIRM"]["top"] > a["CONFIRM"]["top"], z=b["CONFIRM"]["z_avg"] >= a["CONFIRM"]["z_avg"] - .005)
print("T3 conditions:", conds, "->", "PASS" if all(conds.values()) else "FAIL")
print("IC by year C :", {y: round(v, 3) for y, v in a["ic_by_year"].items()}); print("IC by year CZ:", {y: round(v, 3) for y, v in b["ic_by_year"].items()})
