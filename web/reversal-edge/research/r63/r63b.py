"""Round 63 robustness (pre-registered checks for the DESIGN pick, also run on the three variants that beat live in all periods)."""
import os, sys, json, numpy as np, pandas as pd
H63 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H63, "../r48")); sys.path.insert(0, H63)
from zswing import *
import zswing
from sim63 import simulate, TRIG, STOP
os.chdir(H63); ND = len(dates); rx = lambda X: X.reindex(index=dates, columns=cols).values; Cdf = P["C"].reindex(index=dates, columns=cols)
A = dict(Of=M["Of"], H=rx(P["H"]), L=rx(P["L"]), C=Cdf.values, Z=M["Z"], ATR=rx(ATR), SMA5=Cdf.rolling(5).mean().values)
sig = np.where(S_LIVE); o = np.lexsort((sig[1], sig[0])); sig = (sig[0][o], sig[1][o]); k = dates[sig[0]] >= pd.Timestamp("2013"); sig = (sig[0][k], sig[1][k])
E = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31")}
def ev(T, w=None, D=dates, Mx=M, rank=RANK, E=E):
    Ts, cv = zswing.sleeve(T.reset_index(drop=True), rank, np.full(len(T), .05) if w is None else w, Mx, len(D), slots=5)
    return " | ".join(f"{e} {100 * s['ret']:+.1f}%/y DD {100 * s['dd']:.1f}% r {s['ratio']:.2f} avg {100 * s['avg']:+.1f}% w5 {100 * s['worst5']:+.1f}%" if s else f"{e} n<10"
                      for e, s in ((e, stats(Ts, cv, a, b, D)) for e, (a, b) in E.items()))
TI = {t: i for i, t in enumerate(TRIG)}; SI = {s[0]: s for s in STOP}
CANDS = [("T3 reversal day", "1.5 ATR under low", "DESIGN pick"), ("T1 bounce 3%", "1.0 ATR under low", "beat live 3/3"), ("T2 bounce 5%", "none", "beat live 3/3"), ("T1 bounce 3%", "4% under low", "beat live 3/3")]
print("live:", ev(simulate(A, sig, 0, STOP[0])))
for t, s, why in CANDS:
    print(f"\n{t} / {s} ({why})")
    for lab, kw in (("base (10-session window)", {}), ("5-session window", dict(W=5)), ("15-session window", dict(W=15)), ("stop on the close", dict(mode="close")), ("costs 0.8%", dict(cost=.008))):
        if s == "none" and lab == "stop on the close": continue
        print(f"  {lab:26s} {ev(simulate(A, sig, TI[t], SI[s], **kw))}")
    if s != "none":   # risk-based sizing: 0.5% of the account at risk per trade, at most 10%
        T = simulate(A, sig, TI[t], SI[s]); L_ = A["L"]; stopd = []
        for r in T.itertuples():
            lo = np.nanmin(L_[r.i:r.d1, r.j]); st_ = lo * (1 - SI[s][2]) if SI[s][1] == "pct" else lo - SI[s][2] * A["ATR"][r.d1 - 1, r.j]; stopd.append(max(r.e1 - st_, 1e-9) / r.e1)
        w = np.clip(.005 / np.array(stopd), 0, .10); print(f"  {'risk-based sizing':26s} {ev(T, w=w)}  (median size {100 * np.median(w):.1f}%)")
# US sell-off swing, same rules (0.1% costs)
U = us_setup(); UP = U["G"]["P"]; UA = dict(Of=U["M"]["Of"], H=UP["h"].values.astype(float), L=UP["l"].values.astype(float), C=UP["c"].values.astype(float), Z=U["M"]["Z"],
                                           ATR=UP["ATR"].values.astype(float), SMA5=UP["c"].rolling(5).mean().values)
us = np.where(U["S"]); o = np.lexsort((us[1], us[0])); us = (us[0][o], us[1][o]); k = U["D"][us[0]] >= pd.Timestamp("2005"); us = (us[0][k], us[1][k])
print("\nUS sell-off swing (115 large caps), 0.1% costs")
print(f"  {'live (no wait, no stop)':40s} {ev(simulate(UA, us, 0, STOP[0], cost=.001), D=U['D'], Mx=U['M'], rank=U['rank'], E=U['E'])}")
for t, s, why in CANDS:
    print(f"  {t + ' / ' + s:40s} {ev(simulate(UA, us, TI[t], SI[s], cost=.001), D=U['D'], Mx=U['M'], rank=U['rank'], E=U['E'])}")
