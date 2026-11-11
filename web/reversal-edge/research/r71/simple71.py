"""Round 71 part 4 (PREREG section 4): the simplicity test. Each gate of the live rule is switched off; same account (5 x 5%)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi; from engine import perf, block_bootstrap
B, PB = saudi.load(); d = B.dates; T_ = B.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
V = {"live": {}, "S1 no ML rank bar": dict(use_ml=False), "S2 no market model": dict(use_pm=False), "S3 no loss filter": dict(use_loss=False), "S4 no weekly signals": dict(weekly=False),
     "S5 weekly signals only": dict(daily=False), "S6 price only (no ML, no market model, no loss filter)": dict(use_ml=False, use_pm=False, use_loss=False)}
E, eid = B.episodes(first=i0); blk = eid.copy(); blk[i0:E.start.iloc[0]] = len(E)
R = {}; RET = {}; OUT = {}
for nm, kw in V.items():
    SH = B.shadow(B.signals(**kw)); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); PL = B.plan(SH); tk = PL[PL.taken]; n = B.trade_net(tk)
    eq = B.account(PL, w=.05); eq8 = B.account(PL, w=.05, side=.004); RET[nm] = eq.pct_change().fillna(0).values
    R[nm] = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; R[nm]["cost08"] = perf(eq8, *ER["2013-26"]); R[nm]["trades"] = dict(paper=int(len(SH)), taken=int(len(tk)), win=float((n > 0).mean()), avg=float(n.mean()), worst=float(n.min()))
bs = block_bootstrap(RET, blk, n=2000, seed=71)
print(f"{'variant':58s} " + " | ".join(f"{e:>15s}" for e in ER) + " | 0.8% costs 13-26 | paper, taken, winners, average, worst | range 2013-26 (growth; drawdown) | beats live")
for nm in V:
    o = R[nm]; L = R["live"]; t = o["trades"]; g = np.quantile(bs[nm][:, 0], [.05, .95]); D_ = np.quantile(bs[nm][:, 1], [.05, .95])
    ratio = lambda x: x[:, 0] / np.maximum(x[:, 1], 1e-9); pb = float((ratio(bs[nm]) > ratio(bs["live"])).mean()) if nm != "live" else np.nan
    ok = all(o[e]["cagr"] >= L[e]["cagr"] - .001 and o[e]["dd"] <= L[e]["dd"] + .002 for e in ("2013-19", "2020-26", "2023-26")) and o["cost08"]["cagr"] >= L["cost08"]["cagr"] - .001 and o["cost08"]["dd"] <= L["cost08"]["dd"] + .002
    OUT[nm] = dict(eras={e: o[e] for e in ER}, cost08=o["cost08"], trades=t, cagr_range=[float(g[0]), float(g[1])], dd_range=[float(D_[0]), float(D_[1])], p_better_ratio=pb, gate_not_needed=bool(ok) if nm != "live" else None)
    print(f"{nm:58s} " + " | ".join(f"{100 * o[e]['cagr']:+5.1f}% / {100 * o[e]['dd']:4.1f}%" for e in ER) + f" | {100 * o['cost08']['cagr']:+5.1f}% / {100 * o['cost08']['dd']:4.1f}% | {t['paper']:4d}, {t['taken']:3d}, {100 * t['win']:3.0f}%, {100 * t['avg']:+5.1f}%, {100 * t['worst']:+5.1f}% | "
          f"{100 * g[0]:+.1f}..{100 * g[1]:+.1f}%; {100 * D_[0]:.1f}..{100 * D_[1]:.1f}% | " + ("-" if nm == "live" else f"{100 * pb:.0f}% of draws; rule: {'GATE NOT NEEDED' if ok else 'gate stays'}"))
json.dump(OUT, open(os.path.join(HERE, "simple71.json"), "w"), indent=1)
