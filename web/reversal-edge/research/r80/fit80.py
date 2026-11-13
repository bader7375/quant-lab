"""Round 80 (PREREG.md, amendment 1): Rebound Edge. Scores the three-input formula out-of-market on the other markets, runs the
ceiling check, freezes the two copies (M19: trades ended by 2019-12-31; live: all cases) with their companion tables.
No Saudi data is read here. Usage: RE_WORK=<work folder> python3 fit80.py   -> fit80.json, fable/rebound_model.json"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, HERE)
import rebound as RB, eval80 as EV
from scipy.stats import rankdata
WORK = os.environ["RE_WORK"]; D = pd.read_parquet(os.path.join(WORK, "r80_world_cases.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True)
D19 = D[D.exdate <= "2019-12-31"].reset_index(drop=True); MK = sorted(D19.market.unique()); mk = D19.market.values; w19 = 1.0 / D19.market.map(D19.market.value_counts()).values
def target(T, clip=None):
    lo, hi = T.net.quantile([.01, .99]) if clip is None else clip; return T.net.clip(lo, hi).values, (float(lo), float(hi))
y19, clip19 = target(D19); print(f"cases: {len(D)} in {D.market.nunique()} markets; trades ended by 2019-12-31: {len(D19)} in {len(MK)} markets (wins {100 * D19.win.mean():.1f}%, average net {100 * D19.net.mean():+.2f}%)")
# ---- step 1: every market scored by a formula fitted on the others
pred = np.zeros(len(D19)); mse = np.zeros(len(MK)); base = np.zeros(len(MK))
for k, m in enumerate(MK):
    te = mk == m; tr = ~te; X, st = RB.prepare(D19[tr]); b0, b = RB.ols(X, y19[tr], w19[tr]); Xt, _ = RB.prepare(D19[te], stats=st); pred[te] = b0 + Xt @ b; mse[k] = ((y19[te] - pred[te]) ** 2).mean(); base[k] = ((y19[te] - np.average(y19[tr], weights=w19[tr])) ** 2).mean()
net = D19.net.values; blk = mk + "|" + D19.month.astype(str).values; wm = lambda p: float(np.mean([np.corrcoef(rankdata(p[mk == m]), rankdata(net[mk == m]))[0, 1] for m in MK]))
sep = EV.separation(pred, net, blk, n=400); cal = [(float(pred[b_].mean()), float(net[b_].mean()), float(D19.win.values[b_].mean())) for b_ in (np.searchsorted(np.quantile(pred, np.arange(1, 10) / 10), pred) == k for k in range(10))]
bym = {m: dict(n=int((mk == m).sum()), corr=float(np.corrcoef(rankdata(pred[mk == m]), rankdata(net[mk == m]))[0, 1]), corr_ms=float(np.corrcoef(rankdata(-D19.MS.values[mk == m]), rankdata(net[mk == m]))[0, 1]),
               spread=float(net[(mk == m) & (pred >= np.quantile(pred[mk == m], 2 / 3))].mean() - net[(mk == m) & (pred <= np.quantile(pred[mk == m], 1 / 3))].mean())) for m in MK}
print(f"\nstep 1, other markets, out-of-market edge: squared error {100 * (1 - mse.mean() / base.mean()):.2f}% below no-skill (better in {int((mse < base).sum())} of {len(MK)} markets)")
print(f"top third of edge {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}%: {100 * sep[0]:+.2f} points (5th pct {100 * sep[1]:+.2f})")
print(f"rank correlation with the net result, average over markets: edge {wm(pred):.3f} | market momentum alone {wm(-D19.MS.values):.3f} | stretch Z alone {wm(-D19.Z.values):.3f}; edge ahead of market momentum in {sum(v['corr'] > v['corr_ms'] for v in bym.values())} of {len(MK)} markets")
print("by tenth of edge: stated -> realized (wins): " + "  ".join(f"{100 * a:+.1f}->{100 * b:+.1f} ({100 * c:.0f}%)" for a, b, c in cal))
print("by market (rank corr, top minus bottom third): " + "  ".join(f"{m} {v['corr']:.2f} {100 * v['spread']:+.1f}" for m, v in bym.items())); print(f"markets with a positive spread: {sum(v['spread'] > 0 for v in bym.values())} of {len(MK)}")
import lightgbm as lgb
XT = D19[["Z", "MS"]].values.astype(np.float32); mt = np.zeros(len(MK)); pt = np.zeros(len(D19))
for k, m in enumerate(MK):
    te = mk == m; g = lgb.LGBMRegressor(n_estimators=200, learning_rate=.03, num_leaves=15, min_child_samples=500, subsample=.7, subsample_freq=1, verbose=-1, n_jobs=4, random_state=80); g.fit(XT[~te], y19[~te], sample_weight=w19[~te]); pt[te] = g.predict(XT[te]); mt[k] = ((y19[te] - pt[te]) ** 2).mean()
print(f"ceiling check: boosted trees on the same two readings: {100 * (1 - mt.mean() / base.mean()):.2f}% below no-skill, rank corr {wm(pt):.3f} (the formula: {100 * (1 - mse.mean() / base.mean()):.2f}%, {wm(pred):.3f}); trees with all 22 inputs: 1.64%, 0.174 (explore80.py)")
# ---- the two frozen copies and their companion tables
def freeze(T, label):
    w = 1.0 / T.market.map(T.market.value_counts()).values; y, clip = target(T); X, st = RB.prepare(T); b0, b = RB.ols(X, y, w)
    M = dict(names=RB.NAMES, b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, clip=list(clip), fitted_to=label, cases=int(len(T)), markets=int(T.market.nunique()))
    e = RB.edge(M, T); M["band_edges"] = [float(x) for x in np.quantile(e, np.arange(1, 10) / 10)]; M["zones"] = [float(x) for x in np.quantile(e, [1 / 3, 2 / 3])]; band = RB.band_of(M, e); M["bands"] = []; u = T.unit.values
    for k in range(10):
        m = band == k; x = T[m]; ok = np.isfinite(u[m]) & (u[m] > 0); dz = x.dip.values[ok] / u[m][ok]
        M["bands"].append(dict(n=int(m.sum()), edge=float(e[m].mean()), win=float(x.win.mean()), gain=float(x.net.mean()), gain_med=float(x.net.median()), days=float(x.held.median()), dipz_med=float(np.median(dz)), dipz_bad=float(np.quantile(dz, .1)),
                               dip_med=float(x.dip.median()), dip_bad=float(x.dip.quantile(.1)), cone={q: [float(np.nanquantile(x[f"p{h}"].values[ok] / u[m][ok], v)) for h in RB.HORIZONS] for q, v in (("q10", .1), ("q25", .25), ("q50", .5), ("q75", .75), ("q90", .9))}))
    M["raw"] = RB.raw_weights(M); return M, e
M19, e19 = freeze(D19, "2019-12-31"); ML, eL = freeze(D, str(pd.Timestamp(D.exdate.max()).date())); eL19 = RB.edge(M19, D)
print(f"\nM19: {M19['cases']} cases | live copy: {ML['cases']} cases | the two copies on all cases: correlation {np.corrcoef(eL, eL19)[0, 1]:.4f}, average gap {100 * np.abs(eL - eL19).mean():.2f} points")
for nm, M in (("M19", M19), ("live", ML)):
    r = M["raw"]; print(f"{nm}: edge % = {100 * r['c0']:+.2f} {100 * r['Z']:+.2f} x Z {100 * r['MS']:+.2f} x MS {100 * r['ZMS']:+.2f} x Z x MS   (Z kept within {r['clips']['Z'][0]:.2f}..{r['clips']['Z'][1]:.2f}, MS within {r['clips']['MS'][0]:.2f}..{r['clips']['MS'][1]:.2f}); weak below {100 * M['zones'][0]:+.1f}%, strong above {100 * M['zones'][1]:+.1f}%")
print("live companion table by edge band (other markets): edge -> realized gain, wins, sessions, typical dip and 1-in-10 dip in units of the stock's 20-session swing (and in % for the average case)")
for k, b in enumerate(ML["bands"]): print(f"  {k}: {100 * b['edge']:+5.1f}% -> {100 * b['gain']:+5.1f}%, {100 * b['win']:.0f}%, {b['days']:.0f} sessions, dip {b['dipz_med']:+.2f} / {b['dipz_bad']:+.2f} ({100 * b['dip_med']:+.1f}% / {100 * b['dip_bad']:+.1f}%)")
json.dump(dict(m19=M19, live=ML, horizons=list(RB.HORIZONS), line=RB.LINE, saudi=None), open(RB.MODEL_FILE, "w"), indent=1)
json.dump(dict(step1=dict(error_below_noskill=float(1 - mse.mean() / base.mean()), markets_better=int((mse < base).sum()), markets=len(MK), separation=sep, corr_edge=wm(pred), corr_ms=wm(-D19.MS.values), corr_z=wm(-D19.Z.values), tenths=cal, by_market=bym,
                              trees_two_inputs=dict(error_below_noskill=float(1 - mt.mean() / base.mean()), corr=wm(pt))), copies=dict(corr=float(np.corrcoef(eL, eL19)[0, 1]), gap=float(np.abs(eL - eL19).mean()))), open(os.path.join(HERE, "fit80.json"), "w"), indent=1, default=float)
