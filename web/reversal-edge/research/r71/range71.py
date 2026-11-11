"""Round 71 part 3: honest ranges for the live rule (bootstrap over sell-off episodes) and the anatomy of the episodes."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi; from engine import perf, block_bootstrap
B, PB = saudi.load(); d = B.dates; T_ = B.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
SH = B.shadow(B.signals()); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); PL = B.plan(SH); PL["net"] = B.trade_net(PL)
E, eid = B.episodes(first=i0); blk = eid.copy(); blk[i0:E.start.iloc[0]] = len(E)                 # the quiet time before the first episode is its own block
E["date"] = d[E.start.values]; E["end"] = d[E["last"].values]; PL["ep"] = eid[PL.i.values]
print(f"episodes since 2013 (market momentum <= -1.18, gaps up to 20 sessions joined): {len(E)}")
rows = []
for k, e in E.iterrows():
    x = PL[PL.ep == k]; t = x[x.taken]; a = int(e.start); b_ = int(E.start.iloc[k + 1]) if k + 1 < len(E) else T_
    idx = np.exp(np.nancumsum(B.mret.values[a:min(a + 120, b_)])); low = float(idx.min() - 1) if len(idx) else np.nan
    rows.append(dict(start=str(e.date.date()), sessions_stretched=int(e.n), span=int(e["last"] - e.start + 1), depth=round(float(e.depth), 2), market_low_after_start=round(low, 3), paper=int(len(x)),
                     taken=int(len(t)), taken_day0=int((t.i == t.i.min()).sum()) if len(t) else 0, days_to_fill=int(t.i.max() - t.i.min()) if len(t) else None,
                     avg_paper=round(float(x.net.mean()), 3) if len(x) else None, avg_taken=round(float(t.net.mean()), 3) if len(t) else None, worst_taken=round(float(t.net.min()), 3) if len(t) else None))
A = pd.DataFrame(rows); print(A.to_string(index=False)); A.to_csv(os.path.join(HERE, "episodes71.csv"), index=False)
print(f"signals outside any episode block: {(PL.ep < 0).sum()}")
# ---- bootstrap ranges of the live account
OUT = {"episodes": rows, "ranges": {}}
for w, cash in ((.05, True), (.05, False), (.10, True)):
    eq = B.account(PL, w=w, cash=cash); r = eq.pct_change().fillna(0).values; key = f"live 5 x {100 * w:.0f}%" + ("" if cash else ", idle money earning nothing")
    for e, (a, b_) in ER.items():
        ia, ib = int(np.searchsorted(d.values, np.datetime64(a))), int(np.searchsorted(d.values, np.datetime64(b_), side="right")); m = np.full(T_, -1); m[ia:ib] = blk[ia:ib]
        o = perf(eq, a, b_); bs = block_bootstrap({"x": r}, m, n=2000, seed=71)["x"]; q = lambda v: [float(np.quantile(v, .05)), float(np.quantile(v, .5)), float(np.quantile(v, .95))]
        OUT["ranges"][f"{key} | {e}"] = dict(cagr=o["cagr"], dd=o["dd"], cagr_range=q(bs[:, 0]), dd_range=q(bs[:, 1]), blocks=int(len(np.unique(m[m >= 0]))), p_loss=float((bs[:, 0] < 0).mean()))
        g, D_ = q(bs[:, 0]), q(bs[:, 1])
        print(f"{key:44s} {e}: growth {100 * o['cagr']:+.1f}% a year (range {100 * g[0]:+.1f}% to {100 * g[2]:+.1f}%), worst drawdown {100 * o['dd']:.1f}% (range {100 * D_[0]:.1f}% to {100 * D_[2]:.1f}%), blocks {OUT['ranges'][f'{key} | {e}']['blocks']}")
# ---- per trade, resampling episodes
rng = np.random.default_rng(71)
def trade_range(x, n=4000):
    g = [v.net.values for _, v in x.groupby("ep")]; m = []; w_ = []
    for _ in range(n):
        s = np.concatenate([g[k] for k in rng.integers(len(g), size=len(g))]); m.append(s.mean()); w_.append((s > 0).mean())
    return [float(np.quantile(m, .05)), float(np.quantile(m, .95))], [float(np.quantile(w_, .05)), float(np.quantile(w_, .95))]
for nm, x in (("taken trades", PL[PL.taken]), ("all paper trades", PL)):
    for e, (a, b_) in ER.items():
        y = x[(d[x.i.values] >= a) & (d[x.i.values] <= b_)]
        if len(y) < 5: continue
        mr, wr = trade_range(y); OUT["ranges"][f"{nm} | {e}"] = dict(n=int(len(y)), avg=float(y.net.mean()), avg_range=mr, win=float((y.net > 0).mean()), win_range=wr, episodes=int(y.ep.nunique()))
        print(f"{nm:18s} {e}: {len(y):3d} trades in {y.ep.nunique():2d} episodes, average {100 * y.net.mean():+.1f}% (range {100 * mr[0]:+.1f}% to {100 * mr[1]:+.1f}%), winners {100 * (y.net > 0).mean():.0f}% (range {100 * wr[0]:.0f}% to {100 * wr[1]:.0f}%)")
json.dump(OUT, open(os.path.join(HERE, "range71.json"), "w"), indent=1)
