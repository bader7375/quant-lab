"""Round 82 (PREREG.md), step 1: Hold Edge on the other markets. Chooses the extras, scores the formula out-of-market, freezes the
two copies (M19: trades ended by 2019-12-31; live: all) with their companion tables. No Saudi data is read here.
Usage: RE_WORK=<work folder> python3 fit82.py   -> fit82.json, fable/holdedge_model.json"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
from scipy.stats import rankdata
WORK = os.environ["RE_WORK"]; D = pd.read_parquet(os.path.join(WORK, "r82_world_hold.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS) & np.isfinite(D.rest)].reset_index(drop=True)
D19 = D[D.exdate <= "2019-12-31"].reset_index(drop=True); MK = sorted(D19.market.unique()); mk = D19.market.values; w19 = 1.0 / D19.market.map(D19.market.value_counts()).values
lo, hi = D19.rest.quantile([.01, .99]); y = D19.rest.clip(lo, hi).values; rest = D19.rest.values
print(f"hold cases: {len(D)} in {D.market.nunique()} markets; trades ended by 2019-12-31: {len(D19)} in {len(MK)} markets (sold above the close {100 * D19.up.mean():.1f}%, average rest {100 * rest.mean():+.2f}%)")
idx = {m: np.where(mk == m)[0] for m in MK}; wm = lambda p: float(np.mean([np.corrcoef(rankdata(p[idx[m]]), rankdata(rest[idx[m]]))[0, 1] for m in MK]))
def lomo(names):
    pred = np.zeros(len(D19)); mse = np.zeros(len(MK)); base = np.zeros(len(MK)); X, _ = RB.prepare(D19, names)      # one standardisation for the selection runs (the frozen copies make their own)
    for k, m in enumerate(MK):
        te = mk == m; b0, b = RB.ols(X[~te], y[~te], w19[~te]); pred[te] = b0 + X[te] @ b; mse[k] = ((y[te] - pred[te]) ** 2).mean(); base[k] = ((y[te] - np.average(y[~te], weights=w19[~te])) ** 2).mean()
    return mse, base, pred
chosen = list(HE.BASE); mse, base, pred = lomo(chosen); rc = wm(pred); LOG = []
print(f"\nbase inputs ({', '.join(HE.WORDS[c] for c in chosen)}): out-of-market squared error {100 * (1 - mse.mean() / base.mean()):.2f}% below no-skill (better in {int((mse < base).sum())} of {len(MK)}); rank correlation {rc:.3f}")
for step in range(1, 4):
    rows = []
    for c in [c for c in HE.EXTRA if c not in chosen]:
        m2, _, p2 = lomo(chosen + [c]); rows.append(dict(cand=c, gain=float(100 * (mse.mean() - m2.mean()) / base.mean()), better=int((m2 < mse).sum()), corr=wm(p2)))
    rows.sort(key=lambda r: -r["gain"]); print(f"step {step}: " + " | ".join(f"{HE.WORDS[r['cand']]}: error {r['gain']:+.3f}%, {r['better']} markets, rank corr {r['corr']:.3f}" for r in rows)); LOG.append(rows)
    ok = [r for r in rows if r["better"] >= 17 and r["corr"] > rc and r["gain"] > 0]
    if not ok: print("  -> no extra meets the mark (17 markets and a higher rank correlation)."); break
    chosen.append(ok[0]["cand"]); mse, base, pred = lomo(chosen); rc = wm(pred); print(f"  -> added: {HE.WORDS[ok[0]['cand']]} (error now {100 * (1 - mse.mean() / base.mean()):.2f}% below no-skill, rank correlation {rc:.3f})")
print("\ninputs of the formula:", [HE.WORDS[c] for c in chosen])
# ---- step 1: out-of-market
blk = mk + "|" + D19.month.astype(str).values; sub = np.random.default_rng(82).choice(len(D19), 300000, replace=False); sep = EV.separation(pred[sub], rest[sub], blk[sub], n=200)
M80, _ = RB.load("m19"); noclock = RB.edge(M80, dict(Z=D19.Z.values, MS=D19.MS.values, ZMS=D19.ZMS.values)); cz = wm(-D19.Z.values); cms = wm(-D19.MS.values); cnc = wm(noclock)
bym = {m: dict(n=int(len(idx[m])), corr=float(np.corrcoef(rankdata(pred[idx[m]]), rankdata(rest[idx[m]]))[0, 1]), spread=float(rest[idx[m]][pred[idx[m]] >= np.quantile(pred[idx[m]], 2 / 3)].mean() - rest[idx[m]][pred[idx[m]] <= np.quantile(pred[idx[m]], 1 / 3)].mean())) for m in MK}
dz = np.quantile(pred, np.arange(1, 10) / 10); bnd = np.searchsorted(dz, pred); cal = [(float(pred[bnd == k].mean()), float(rest[bnd == k].mean()), float(D19.up.values[bnd == k].mean())) for k in range(10)]
print(f"\nstep 1, other markets, out-of-market: top third of readings {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}% = {100 * sep[0]:+.2f} points (5th pct {100 * sep[1]:+.2f}); positive in {sum(v['spread'] > 0 for v in bym.values())} of {len(MK)} markets")
print(f"rank correlation with the rest of the trade, average over markets: Hold Edge {rc:.3f} | stretch Z now alone {cz:.3f} | market momentum alone {cms:.3f} | Rebound Edge with no clock {cnc:.3f}")
print("by tenth: stated -> realized (sold above the close): " + "  ".join(f"{100 * a:+.1f}->{100 * b:+.1f} ({100 * c:.0f}%)" for a, b, c in cal))
print("by sessions held (stated -> realized): " + "  ".join(f"n={n}: {100 * pred[D19.n.values == n].mean():+.1f}->{100 * rest[D19.n.values == n].mean():+.1f}" for n in HE.GRID))
# ---- the two frozen copies
def freeze(T, label):
    w = 1.0 / T.market.map(T.market.value_counts()).values; lo_, hi_ = T.rest.quantile([.01, .99]); X, st = RB.prepare(T, chosen); b0, b = RB.ols(X, T.rest.clip(lo_, hi_).values, w)
    M = dict(names=chosen, b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, clip=[float(lo_), float(hi_)], fitted_to=label, cases=int(len(T)), trades=int(T.groupby("market").case.nunique().sum()), markets=int(T.market.nunique()))
    e = RB.edge(M, T); M["band_edges"], M["bands"] = HE.tables(T, e); M["zones"] = [float(v) for v in np.quantile(e, [1 / 3, 2 / 3])]; return M, e
M19, e19 = freeze(D19, "2019-12-31"); ML, eL = freeze(D, str(pd.Timestamp(D.exdate.max()).date())); eL19 = RB.edge(M19, D)
print(f"\nM19: {M19['cases']} hold cases | live copy: {ML['cases']} | the two copies on all cases: correlation {np.corrcoef(eL, eL19)[0, 1]:.4f}, average gap {100 * np.abs(eL - eL19).mean():.2f} points")
print("weights per one standard deviation of each input, in % (M19 | live): " + "; ".join(f"{HE.WORDS[k]} {100 * a:+.2f} | {100 * b:+.2f}" for k, a, b in zip(chosen, M19["b"], ML["b"])))
print("live companion table by band: reading -> rest of the trade, sold above the close, sessions to the sale, further dip typical / 1-in-10 (in 20-session swings)")
for k, b in enumerate(ML["bands"]): print(f"  {k}: {100 * b['edge']:+5.1f}% -> {100 * b['rest']:+5.1f}%, {100 * b['up']:.0f} in 100, {b['togo']:.0f} sessions, {b['furz_med']:+.2f} / {b['furz_bad']:+.2f}")
json.dump(dict(m19=M19, live=ML, grid=list(HE.GRID), saudi=None), open(HE.MODEL_FILE, "w"), indent=1)
json.dump(dict(chosen=chosen, log=LOG, step1=dict(error_below_noskill=float(1 - mse.mean() / base.mean()), markets_better=int((mse < base).sum()), markets=len(MK), separation=sep, corr=rc, corr_z=cz, corr_ms=cms, corr_noclock=cnc, tenths=cal, by_market=bym), copies=dict(corr=float(np.corrcoef(eL, eL19)[0, 1]), gap=float(np.abs(eL - eL19).mean()))), open(os.path.join(HERE, "fit82.json"), "w"), indent=1, default=float)
