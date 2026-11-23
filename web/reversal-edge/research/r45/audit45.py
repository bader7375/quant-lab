"""Round 45, idea 5 (PREREG.md): how much to trust the backtests. (a) Deflated Sharpe ratio of the live Z sleeve with N = 200 trials;
(b) does a good 2013-19 result predict 2020-26 across the variants of rounds 39-43? (c) share of families whose 2013-19 pick fell below the
2020-26 median."""
import os, sys, json, math, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import norm, spearmanr, skew, kurtosis
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r41"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
from sim41 import trades, sleeve
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
T = trades((BASE & (PCT >= .5)).values & EL, M); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
T, cv = sleeve(T, np.nan_to_num(PCT.values, nan=-1.0), np.full(len(T), .05), M, len(dates))
m = dates >= pd.Timestamp("2013"); r = np.diff(cv[m]); n = len(r); sr = r.mean() / r.std(); g3, g4 = skew(r), kurtosis(r, fisher=False)
# trial Sharpe dispersion from the sleeve variants of rounds 41-43 (annual Sharpe, mean of the two eras), per-day units
sh = []
for f in ("r41/r41_results.json", "r42/r42_results.json", "r43/r43_results.json"):
    J = json.load(open(os.path.join(SP, f)))["res"]
    for k, v in J.items():
        if v.get("DESIGN") and v.get("CONFIRM") and v["DESIGN"].get("sharpe") is not None: sh.append((v["DESIGN"]["sharpe"] + v["CONFIRM"]["sharpe"]) / 2 / math.sqrt(250))
V = float(np.var(sh)); N = 200; gam = 0.5772156649
sr0 = math.sqrt(V) * ((1 - gam) * norm.ppf(1 - 1 / N) + gam * norm.ppf(1 - 1 / (N * math.e)))
den = math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
psr = norm.cdf(sr * math.sqrt(n - 1) / den); dsr = norm.cdf((sr - sr0) * math.sqrt(n - 1) / den)
print(f"(a) live Z sleeve 2013-26: {n} days, annual Sharpe {sr * math.sqrt(250):.2f}, skew {g3:+.2f}, kurtosis {g4:.1f}")
print(f"    probability the true Sharpe > 0 ignoring the search (PSR): {100 * psr:.1f}%")
print(f"    after {N} trials (variance of trial Sharpes from {len(sh)} variants; best-of-{N} expected annual Sharpe under no skill {sr0 * math.sqrt(250):.2f}): deflated Sharpe probability {100 * dsr:.1f}%")
# (b) and (c)
rows = []
for f, key, fam in (("r39/s39_results.json", "ml05", None), ("r41/r41_results.json", "res", "first"), ("r42/r42_results.json", "res", None), ("r43/r43_results.json", "res", "first")):
    J = json.load(open(os.path.join(SP, f)))[key]
    for k, v in J.items():
        if k.startswith("baseline") or k == "no stop": continue
        if v.get("DESIGN") and v.get("CONFIRM"): rows.append(dict(round=f[:3], variant=k, fam=(f[:3] + ":" + (k.split()[0][0] if fam else "all")), d=v["DESIGN"]["ratio"], c=v["CONFIRM"]["ratio"]))
X = pd.DataFrame(rows); rho, p = spearmanr(X.d, X.c)
print(f"\n(b) {len(X)} variants (rounds 39, 41, 42, 43): rank correlation of 2013-19 vs 2020-26 ratio {rho:+.2f} (p {p:.2f})")
for rd, g in X.groupby("round"): print(f"    round {rd[1:]}: {len(g)} variants, rank correlation {spearmanr(g.d, g.c)[0]:+.2f}")
below = [(f_, g.loc[g.d.idxmax(), "variant"], bool(g.loc[g.d.idxmax(), "c"] < g.c.median())) for f_, g in X.groupby("fam") if len(g) >= 3]
print(f"(c) families whose 2013-19 best fell below the 2020-26 median: {sum(b for _, _, b in below)} of {len(below)} (PBO-style estimate {100 * sum(b for _, _, b in below) / len(below):.0f}%; chance level 50%)")
for f_, v_, b in below: print(f"    {f_:8s} pick '{v_}': {'below' if b else 'above'} the 2020-26 median")
json.dump({"sharpe": float(sr * math.sqrt(250)), "psr": float(psr), "dsr": float(dsr), "sr0_annual": float(sr0 * math.sqrt(250)), "rho": float(rho), "families": below}, open(os.path.join(HERE, "audit45_results.json"), "w"), indent=1)
