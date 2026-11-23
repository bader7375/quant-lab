"""Round 46 addendum C (PREREG.md): the machine-found filter (stock near its 1-year high) on the Core ML sleeve, Saudi + US."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
src = open(os.path.join(HERE, "gp46.py")).read(); exec(src.split("t0 = time.time(); pop")[0])           # Saudi measures (RK) as in engine 1
exec(src.split("# ---------------------------------------------------------------- holdout + US transfer")[1].split("def us_ok")[0])  # US panel, US ranker, US measures
os.chdir(R27); from core import core as core_w, combine, run, PRED, pm, START; from sim import stats; os.chdir(HERE)
DH = NAMES.index("dhi250")
def sleeve_w(pred, el, filt, gate, start, N=10, hold=20, tranches=4):
    T_, N_ = pred.shape; W = np.zeros((T_, N_))
    for k in range(tranches):
        cur = np.zeros(N_); off = start + k * hold // tranches
        for i in range(off, T_):
            if (i - off) % hold == 0:
                cur = np.zeros(N_); ok = el[i] & np.isfinite(pred[i])
                if ok.sum() >= 3 * N and (gate is None or gate[i]):
                    s = np.where(ok & (filt[i] if filt is not None else True), pred[i], -np.inf); top = np.argsort(-s)[:N]; top = top[np.isfinite(s[top])]
                    cur[top] = 1.0 / N
            W[i] += cur / tranches
    return W
E_S = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def fmt(s): return " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in s.items())
# ---------------- Saudi
CW = core_w(); gate = (pm > 0).reindex(dates).fillna(True).values; pv = PRED.reindex(index=dates, columns=cols).values; el = P["elig"].values
near = np.nan_to_num(RK[DH], nan=0) >= .8
SA = {"today's ML sleeve (rebuilt)": sleeve_w(pv, el, None, gate, START), "A: near 1-year high, hold 20": sleeve_w(pv, el, near, gate, START),
      "B: near 1-year high, hold 40": sleeve_w(pv, el, near, gate, START, hold=40)}
RS_ = {}
print("Saudi Core ML sleeve alone, then inside Core v2 (ML half size + trend breakouts):")
for k, W in SA.items():
    W = pd.DataFrame(W, index=dates, columns=cols); r1 = run(P, W)[0]; r2 = run(P, combine(W * .5, CW["trend"]))[0]
    RS_[k] = {"sleeve": {e: stats(r1, a, b) for e, (a, b) in E_S.items()}, "core_v2": {e: stats(r2, a, b) for e, (a, b) in E_S.items()}}
    print(f"  {k:30s} sleeve  {fmt(RS_[k]['sleeve'])}\n  {'':30s} Core v2 {fmt(RS_[k]['core_v2'])}", flush=True)
r_live = run(P, combine(CW["ml"] * .5, CW["trend"]))[0]; print(f"  {'(check) live Core v2 weights':30s} Core v2 {fmt({e: stats(r_live, a, b) for e, (a, b) in E_S.items()})}")
# ---------------- US
UOf = UP["Of"].values.astype(float) if hasattr(UP["Of"], "values") else UP["Of"].astype(float)
URoo = np.vstack([UOf[1:] / UOf[:-1] - 1, np.full((1, UOf.shape[1]), np.nan)]); URoo = np.where(np.isfinite(URoo), URoo, 0.0)
upred = up.pivot(index="date", columns="sym", values="pred").reindex(index=UD, columns=UC).values
unear = np.nan_to_num(URK[DH], nan=0) >= .8; ustart = int(np.searchsorted(UD, np.datetime64("2005-01-01")))
def urun(W):
    held = np.vstack([np.zeros((1, W.shape[1])), W[:-1]]); tc = np.abs(np.diff(np.vstack([np.zeros((1, W.shape[1])), W]), axis=0)).sum(1)
    tc = np.concatenate([[0], tc[:-1]]) * .0005; return pd.Series((held * URoo).sum(1) - tc, index=UD)
E_U = {"US 2005-09": ("2005", "2009-12-31"), "US 2010-17": ("2010", "2017-12-31"), "US 2018-26": ("2018", "2026-12-31")}
US_ = {}
print("\nUS 100 ML sleeve (top 10, 4 tranches):")
for k, (f, h) in {"today's-style ML sleeve": (None, 20), "A: near 1-year high, hold 20": (unear, 20), "B: near 1-year high, hold 40": (unear, 40)}.items():
    r = urun(sleeve_w(upred, UEL, f, None, ustart, hold=h)); US_[k] = {e: stats(r, a, b) for e, (a, b) in E_U.items()}
    print(f"  {k:30s} {fmt(US_[k])}", flush=True)
# ---------------- decision
B0, U0 = RS_["today's ML sleeve (rebuilt)"]["core_v2"], US_["today's-style ML sleeve"]; PASS = {}
for v in ("A: near 1-year high, hold 20", "B: near 1-year high, hold 40"):
    s, u = RS_[v]["core_v2"], US_[v]
    ok_s = all(s[e]["sharpe"] > B0[e]["sharpe"] and s[e]["maxdd"] >= B0[e]["maxdd"] - .03 for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
    ok_u = all(u[e]["sharpe"] > U0[e]["sharpe"] for e in ("US 2010-17", "US 2018-26")); PASS[v] = ok_s and ok_u
    print(f"{v}: Saudi Core v2 better in both eras: {ok_s} | US better in 2010-17 and 2018-26: {ok_u} -> passes: {PASS[v]}")
win = [v for v in PASS if PASS[v]]; pick = max(win, key=lambda v: RS_[v]["core_v2"]["DESIGN 2013-19"]["sharpe"]) if win else None
print(f"\nDECISION: {pick or 'none'} adopted as a candidate change to the Core ML sleeve")
json.dump({"saudi": RS_, "us": US_, "pass": PASS, "pick": pick}, open(os.path.join(HERE, "core46c_results.json"), "w"), indent=1, default=float)
