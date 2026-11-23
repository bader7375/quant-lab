"""Round 83 (PREREG.md), step 1: Rebound Edge 40 and Hold Edge 40 on the other markets (the live plan's sale: a fixed 40-session
hold). Scores each formula out-of-market, runs the Hold Edge extras rule, freezes the two copies (M19: trades ended by 2019-12-31;
live: all) with their companion tables. No Saudi data is read here.
Usage: RE_WORK=<work folder> python3 fit83.py   -> fit83.json, fable/rebound40_model.json, fable/holdedge40_model.json"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
from scipy.stats import rankdata
WORK = os.environ["RE_WORK"]; OUT = {}
def setup(T, col):
    T = T[np.isfinite(T.Z) & np.isfinite(T.MS) & np.isfinite(T[col])].reset_index(drop=True); T19 = T[T.exdate <= "2019-12-31"].reset_index(drop=True); MK = sorted(T19.market.unique()); mk = T19.market.values
    w = 1.0 / T19.market.map(T19.market.value_counts()).values; lo, hi = T19[col].quantile([.01, .99]); return T, T19, MK, mk, w, T19[col].clip(lo, hi).values, T19[col].values
def lomo(T19, MK, mk, w, y, names):
    pred = np.zeros(len(T19)); mse = np.zeros(len(MK)); base = np.zeros(len(MK)); X, _ = RB.prepare(T19, names)
    for k, m in enumerate(MK):
        te = mk == m; b0, b = RB.ols(X[~te], y[~te], w[~te]); pred[te] = b0 + X[te] @ b; mse[k] = ((y[te] - pred[te]) ** 2).mean(); base[k] = ((y[te] - np.average(y[~te], weights=w[~te])) ** 2).mean()
    return mse, base, pred
def wmc(p, res, idx, MK): return float(np.mean([np.corrcoef(rankdata(p[idx[m]]), rankdata(res[idx[m]]))[0, 1] for m in MK]))
def step1(T19, MK, mk, pred, res, mse, base, comps, label, n_sub=300000):
    idx = {m: np.where(mk == m)[0] for m in MK}; blk = mk + "|" + T19.month.astype(str).values; sub = np.random.default_rng(83).choice(len(T19), min(n_sub, len(T19)), replace=False)
    sep = EV.separation(pred[sub], res[sub], blk[sub], n=200); rc = wmc(pred, res, idx, MK); cc = {k: wmc(v, res, idx, MK) for k, v in comps.items()}
    bym = {m: dict(n=int(len(idx[m])), corr=float(np.corrcoef(rankdata(pred[idx[m]]), rankdata(res[idx[m]]))[0, 1]), spread=float(res[idx[m]][pred[idx[m]] >= np.quantile(pred[idx[m]], 2 / 3)].mean() - res[idx[m]][pred[idx[m]] <= np.quantile(pred[idx[m]], 1 / 3)].mean())) for m in MK}
    dz = np.quantile(pred, np.arange(1, 10) / 10); bnd = np.searchsorted(dz, pred); cal = [(float(pred[bnd == k].mean()), float(res[bnd == k].mean())) for k in range(10)]
    print(f"\n[{label}] step 1, other markets, out-of-market: squared error {100 * (1 - mse.mean() / base.mean()):.2f}% below no-skill (better in {int((mse < base).sum())} of {len(MK)}); top third {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}% = {100 * sep[0]:+.2f} points (5th pct {100 * sep[1]:+.2f}); positive in {sum(v['spread'] > 0 for v in bym.values())} of {len(MK)} markets")
    print(f"[{label}] rank correlation with the result, average over markets: {label} {rc:.3f} | " + " | ".join(f"{k} alone {v:.3f}" for k, v in cc.items()))
    print(f"[{label}] by tenth: stated -> realized: " + "  ".join(f"{100 * a:+.1f}->{100 * b:+.1f}" for a, b in cal))
    return dict(error_below_noskill=float(1 - mse.mean() / base.mean()), markets_better=int((mse < base).sum()), markets=len(MK), separation=sep, corr=rc, comps=cc, tenths=cal, by_market=bym)
# ================================================================ Rebound Edge 40
T, T19, MK, mk, w, y, res = setup(pd.read_parquet(os.path.join(WORK, "r83_world_trades.parquet")), "net")
print(f"trades (40-session hold): {len(T)} in {T.market.nunique()} markets; ended by 2019-12-31: {len(T19)} in {len(MK)} markets (wins {100 * T19.win.mean():.1f}%, average net {100 * res.mean():+.2f}%, held {T19.held.mean():.1f})")
mse, base, pred = lomo(T19, MK, mk, w, y, RB.NAMES); OUT["rebound40"] = step1(T19, MK, mk, pred, res, mse, base, dict(momentum=-T19.MS.values, stretch=-T19.Z.values), "Rebound Edge 40")
def freeze_rb(T, label):
    w_ = 1.0 / T.market.map(T.market.value_counts()).values; lo, hi = T.net.quantile([.01, .99]); X, st = RB.prepare(T); b0, b = RB.ols(X, T.net.clip(lo, hi).values, w_)
    M = dict(names=RB.NAMES, b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, clip=[float(lo), float(hi)], fitted_to=label, cases=int(len(T)), markets=int(T.market.nunique()), exit="fixed 40-session hold")
    e = RB.edge(M, T); M["band_edges"] = [float(x) for x in np.quantile(e, np.arange(1, 10) / 10)]; M["zones"] = [float(x) for x in np.quantile(e, [1 / 3, 2 / 3])]; band = RB.band_of(M, e); M["bands"] = []
    for k in range(10): s = RB.band_stats(T[band == k], T.unit.values[band == k]); s["edge"] = float(e[band == k].mean()); M["bands"].append(s)
    M["raw"] = RB.raw_weights(M); return M, e
R19, _ = freeze_rb(T19, "2019-12-31"); RL, eL = freeze_rb(T, str(pd.Timestamp(T.exdate.max()).date())); eL19 = RB.edge(R19, T)
print(f"[Rebound Edge 40] M19 {R19['cases']} trades | live copy {RL['cases']} | the two copies on all trades: correlation {np.corrcoef(eL, eL19)[0, 1]:.4f}, average gap {100 * np.abs(eL - eL19).mean():.2f} points")
for nm, M in (("M19", R19), ("live", RL)): r = M["raw"]; print(f"[Rebound Edge 40] {nm}: edge % = {100 * r['c0']:+.2f} {100 * r['Z']:+.2f} x Z {100 * r['MS']:+.2f} x MS {100 * r['ZMS']:+.3f} x Z x MS; weak below {100 * M['zones'][0]:+.1f}%, strong from {100 * M['zones'][1]:+.1f}%")
print("[Rebound Edge 40] live companion table: edge -> realized, wins, sessions, typical dip / 1-in-10 dip (in 20-session swings)"); [print(f"  {k}: {100 * b['edge']:+5.1f}% -> {100 * b['gain']:+5.1f}%, {100 * b['win']:.0f}%, {b['days']:.0f}, {b['dipz_med']:+.2f} / {b['dipz_bad']:+.2f}") for k, b in enumerate(RL["bands"])]
json.dump(dict(m19=R19, live=RL, horizons=list(RB.HORIZONS), line=RB.LINE, exit="fixed 40-session hold", saudi=None), open(RB.MODEL_FILE_40, "w"), indent=1)
# ================================================================ Hold Edge 40
T, T19, MK, mk, w, y, res = setup(pd.read_parquet(os.path.join(WORK, "r83_world_hold.parquet")), "rest"); idx = {m: np.where(mk == m)[0] for m in MK}
print(f"\nhold cases (40-session hold): {len(T)} in {T.market.nunique()} markets; trades ended by 2019-12-31: {len(T19)} in {len(MK)} markets (sold above the close {100 * T19.up.mean():.1f}%, average rest {100 * res.mean():+.2f}%)")
chosen = list(HE.BASE); mse, base, pred = lomo(T19, MK, mk, w, y, chosen); rc = wmc(pred, res, idx, MK); LOG = []
print(f"[Hold Edge 40] base inputs: error {100 * (1 - mse.mean() / base.mean()):.2f}% below no-skill (better in {int((mse < base).sum())} of {len(MK)}); rank correlation {rc:.3f}")
for step in range(1, 4):
    rows = []
    for c in [c for c in HE.EXTRA if c not in chosen]:
        m2, _, p2 = lomo(T19, MK, mk, w, y, chosen + [c]); rows.append(dict(cand=c, gain=float(100 * (mse.mean() - m2.mean()) / base.mean()), better=int((m2 < mse).sum()), corr=wmc(p2, res, idx, MK)))
    rows.sort(key=lambda r: -r["gain"]); print(f"[Hold Edge 40] step {step}: " + " | ".join(f"{HE.WORDS[r['cand']]}: error {r['gain']:+.3f}%, {r['better']} markets, rank corr {r['corr']:.3f}" for r in rows)); LOG.append(rows)
    ok = [r for r in rows if r["better"] >= 17 and r["corr"] > rc and r["gain"] > 0]
    if not ok: print("  -> no extra meets the mark (17 markets and a higher rank correlation)."); break
    chosen.append(ok[0]["cand"]); mse, base, pred = lomo(T19, MK, mk, w, y, chosen); rc = wmc(pred, res, idx, MK); print(f"  -> added: {HE.WORDS[ok[0]['cand']]} (rank correlation {rc:.3f})")
noclock = RB.edge(R19, dict(Z=T19.Z.values, MS=T19.MS.values, ZMS=T19.ZMS.values))
OUT["hold40"] = step1(T19, MK, mk, pred, res, mse, base, dict(momentum=-T19.MS.values, stretch=-T19.Z.values, noclock=noclock), "Hold Edge 40"); OUT["hold40"]["chosen"] = chosen; OUT["hold40"]["log"] = LOG
print("[Hold Edge 40] by sessions held (stated -> realized): " + "  ".join(f"n={n}: {100 * pred[T19.n.values == n].mean():+.1f}->{100 * res[T19.n.values == n].mean():+.1f}" for n in HE.GRID))
def freeze_he(T, label):
    w_ = 1.0 / T.market.map(T.market.value_counts()).values; lo, hi = T.rest.quantile([.01, .99]); X, st = RB.prepare(T, chosen); b0, b = RB.ols(X, T.rest.clip(lo, hi).values, w_)
    M = dict(names=chosen, b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, clip=[float(lo), float(hi)], fitted_to=label, cases=int(len(T)), trades=int(T.groupby("market").case.nunique().sum()), markets=int(T.market.nunique()), exit="fixed 40-session hold")
    e = RB.edge(M, T); M["band_edges"], M["bands"] = HE.tables(T, e); M["zones"] = [float(v) for v in np.quantile(e, [1 / 3, 2 / 3])]; M["raw"] = RB.raw_weights(M); return M, e
H19, _ = freeze_he(T19, "2019-12-31"); HL, hL = freeze_he(T, str(pd.Timestamp(T.exdate.max()).date())); hL19 = RB.edge(H19, T)
print(f"[Hold Edge 40] M19 {H19['cases']} hold cases | live copy {HL['cases']} | the two copies: correlation {np.corrcoef(hL, hL19)[0, 1]:.4f}, average gap {100 * np.abs(hL - hL19).mean():.2f} points")
print("[Hold Edge 40] live companion table: reading -> rest, sold above the close, sessions to the sale, further dip typical / 1-in-10"); [print(f"  {k}: {100 * b['edge']:+5.1f}% -> {100 * b['rest']:+5.1f}%, {100 * b['up']:.0f} in 100, {b['togo']:.0f}, {b['furz_med']:+.2f} / {b['furz_bad']:+.2f}") for k, b in enumerate(HL["bands"])]
json.dump(dict(m19=H19, live=HL, grid=list(HE.GRID), exit="fixed 40-session hold", saudi=None), open(HE.MODEL_FILE_40, "w"), indent=1)
json.dump(OUT, open(os.path.join(HERE, "fit83.json"), "w"), indent=1, default=float)
