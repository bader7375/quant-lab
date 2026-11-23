import sys; sys.path.insert(0, ".")
from grid import *
def evalcfg(cfg):
    jobs = [("dev_long", "single", cfg), ("dev_long", "portfolio", cfg), ("dev87", "portfolio", dict(cfg, maxPos=10))]
    L, P6, P87 = runmany(jobs, 3)
    return single_summary(L), port_summary(P6), port_summary(P87)
def line(name, r):
    l, p6, p87 = r
    return f"{name:30s} L6 Sh {l['all'][0]:5.2f} (des {l['design'][0]:5.2f} tst {l['test'][0]:5.2f}) CAGR {100*l['cagr']:4.1f}% MDD {100*l['mdd']:5.1f}% n {l['trades']:4d} | 6-port Sh {p6['all'][0]:4.2f} CAGR {100*p6['all'][1]:4.1f}% MDD {100*p6['all'][2]:5.1f}% | 87-port Sh {p87['all'][0]:4.2f} CAGR {100*p87['all'][1]:4.1f}% MDD {100*p87['all'][2]:5.1f}% n {p87['trades']}"
groups = {
 "costs (bp per side)": [("slippage 0", {"slippage": 0}), ("slippage 5 (default)", {}), ("slippage 10", {"slippage": 10}), ("slippage 20", {"slippage": 20})],
 "execution realism": [("exit at the close (default)", {}), ("exit at NEXT OPEN", {"exitAt": "open"}), ("next-open entry instead of limit", {"entry": "open"})],
 "trigger RSI(2) below": [(f"trig {v}", {"trig": v}) for v in (5, 7, 10, 15, 20)],
 "limit depth (ATR)": [(f"limit {v}", {"limitATR": v}) for v in (0, 0.25, 0.5, 0.75, 1.0)],
 "max hold (bars)": [(f"maxHold {v}", {"maxHold": v}) for v in (3, 5, 10, 15, 20)],
 "exit rule": [(f"exit {v}", {"exit": v}) for v in ("prevhigh", "sma5", "sma10", "rsi70")],
 "score filter": [("top third", {}), ("top two thirds", {"scoreThr": -1.7889}), ("all setups", {"scoreThr": -99})],
 "character switch": [("acThr 0.04", {"acThr": 0.04}), ("acThr 0.08 (default)", {}), ("acThr 0.12", {"acThr": 0.12}), ("reversal only", {"mode": "rev"})],
 "model adaptation": [("research weights only", {"adapt": False}), ("adapt n0 100", {"n0": 100}), ("adapt n0 300 (default)", {}), ("adapt n0 1000", {"n0": 1000}), ("adapt, no pooling", {"pool": 0})],
 "stops": [("no stop (default)", {}), ("stop 2 ATR", {"stopATR": 2}), ("stop 3 ATR", {"stopATR": 3}), ("stop 5 ATR", {"stopATR": 5})],
}
for g, items in groups.items():
    print(f"\n== {g}", flush=True)
    for name, cfg in items: print(line(name, evalcfg(cfg)), flush=True)
