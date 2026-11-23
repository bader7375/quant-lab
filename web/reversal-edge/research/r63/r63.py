"""Round 63 (PREREG.md): buy the bounce off the low after a Z-swing signal, stop under the low with room."""
import os, sys, json, numpy as np, pandas as pd
H63 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H63, "../r48")); sys.path.insert(0, H63)
from zswing import *
import zswing
from sim63 import simulate, TRIG, STOP
os.chdir(H63); ND = len(dates)
rx = lambda X: X.reindex(index=dates, columns=cols).values
Cdf = P["C"].reindex(index=dates, columns=cols)
A = dict(Of=M["Of"], H=rx(P["H"]), L=rx(P["L"]), C=Cdf.values, Z=M["Z"], ATR=rx(ATR), SMA5=Cdf.rolling(5).mean().values)
sig = np.where(S_LIVE); o = np.lexsort((sig[1], sig[0])); sig = (sig[0][o], sig[1][o]); keep = dates[sig[0]] >= pd.Timestamp("2013"); sig = (sig[0][keep], sig[1][keep])
LIVE = live_trades(); print(f"signals {len(sig[0])}; live_trades rows {len(LIVE)}")
B = simulate(A, sig, 0, STOP[0]); m = B.merge(LIVE[["i", "j", "net"]], on=["i", "j"], suffixes=("", "_live"))
print(f"check: no-wait/no-stop reproduces the live trades: {len(B)} rows, {len(m)} matched, max |net diff| {float((m.net - m.net_live).abs().max()):.2e}")
E = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31")}
nsig = {e: int(((dates[sig[0]] >= pd.Timestamp(a)) & (dates[sig[0]] <= pd.Timestamp(b))).sum()) for e, (a, b) in E.items()}
def evaluate(T, w=None):
    Ts, cv = zswing.sleeve(T.reset_index(drop=True), RANK, np.full(len(T), .05) if w is None else w, M, ND, slots=5); out = {}
    for e, (a, b) in E.items():
        st = stats(Ts, cv, a, b); d = dates[T.i.values]; x = T[(d >= pd.Timestamp(a)) & (d <= pd.Timestamp(b))]
        if st is None or len(x) < 10: out[e] = None; continue
        st.update(traded=len(x) / max(nsig[e], 1), cost=float((x.e1 / x.ref - 1).mean()), stop_rate=float(x.stopped.mean()), early=float((x.mae10 < -.05).mean())); out[e] = st
    return out
def line(nm, o):
    if o is None: return f"  {nm:40s} n<10"
    return (f"  {nm:40s} traded {100 * o['traded']:3.0f}% entry {100 * o['cost']:+5.1f}% | win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.1f}% worst5 {100 * o['worst5']:+6.1f}%"
            f" stops {100 * o['stop_rate']:3.0f}% early {100 * o['early']:3.0f}% | {100 * o['ret']:+4.1f}%/y DD {100 * o['dd']:4.1f}% ratio {o['ratio']:5.2f}")
R = {}
for ti, tn in enumerate(TRIG):
    for st_ in STOP:
        R[(tn, st_[0])] = evaluate(simulate(A, sig, ti, st_))
    print(f"done {tn}", flush=True)
live = R[("T0 no wait", "none")]
for e in E:
    print(f"\n==== {e} (live: {line('', live[e]).strip()})")
    for k, o in sorted(R.items(), key=lambda kv: -(kv[1][e]["ratio"] if kv[1][e] else -9)): print(line(f"{k[0]} / {k[1]}", o[e]))
elig = {k: o for k, o in R.items() if o["DESIGN"] and o["DESIGN"]["traded"] >= .5 and k != ("T0 no wait", "none")}
pick = max(elig, key=lambda k: elig[k]["DESIGN"]["ratio"]); p = R[pick]
ok = bool(p["CONFIRM"] and p["CONFIRM"]["ratio"] > live["CONFIRM"]["ratio"] and p["CONFIRM"]["ret"] >= .8 * live["CONFIRM"]["ret"]
          and p["CONFIRM"]["worst5"] > live["CONFIRM"]["worst5"] and p["2023-26"] and p["2023-26"]["ratio"] >= live["2023-26"]["ratio"])
print(f"\nDESIGN pick: {pick[0]} / {pick[1]} -> {'PASSES' if ok else 'FAILS'} the CONFIRM rule")
for e in E: print(line("live", live[e])); print(line("pick", p[e]))
json.dump({"pick": list(pick), "passes": ok, "results": {f"{k[0]} | {k[1]}": v for k, v in R.items()}}, open("r63_results.json", "w"), indent=1, default=float)
