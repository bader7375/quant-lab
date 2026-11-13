"""Round 80 (PREREG.md), step 1: choose the inputs, fit the two frozen copies of the formula, build the companion tables, and score
the formula out-of-market on the other markets. No Saudi data is read here.
Usage: RE_WORK=<work folder> python3 select80.py     -> select80.json, fable/odds_model.json (m19 and live)"""
import os, sys, json, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, HERE)
import odds as OD, eval80 as EV
WORK = os.environ["RE_WORK"]; D = pd.read_parquet(os.path.join(WORK, "r80_world_cases.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True)
D19 = D[D.exdate <= "2019-12-31"].reset_index(drop=True); MK = sorted(D19.market.unique()); rng = np.random.default_rng(80)
print(f"cases: {len(D)} in {D.market.nunique()} markets; trade ended by 2019-12-31: {len(D19)} (win {100 * D19.win.mean():.1f}%, average net {100 * D19.net.mean():+.2f}%)")
sub = np.concatenate([rng.choice(ix, size=min(len(ix), 30000), replace=False) for ix in (np.where(D19.market.values == m)[0] for m in MK)]); S_ = D19.iloc[np.sort(sub)].reset_index(drop=True)   # selection sample: at most 30,000 cases a market
mkS = S_.market.values; wS = 1.0 / pd.Series(mkS).map(pd.Series(mkS).value_counts()).values; yS = S_.win.values
def ll(y, p): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
def lomo(names, want_pred=False):
    """each market scored by a formula fitted on the other markets -> log loss per market (and the out-of-market odds)."""
    out = np.zeros(len(MK)); pred = np.zeros(len(S_))
    for k, m in enumerate(MK):
        te = mkS == m; tr = ~te; X, st = OD.prepare(S_[tr], names); b0, b = OD.fit(X, yS[tr], wS[tr]); Xt, _ = OD.prepare(S_[te], names, st); p = 1 / (1 + np.exp(-(b0 + Xt @ b))); out[k] = ll(yS[te], p).mean(); pred[te] = p
    return (out, pred) if want_pred else out
noskill = np.array([ll(yS[mkS == m], np.average(yS[mkS != m], weights=wS[mkS != m])).mean() for m in MK])
chosen = list(OD.BASE); cur = lomo(chosen); LOG = [dict(step=0, added="base (stretch Z, market momentum, their product)", logloss=float(cur.mean()), noskill=float(noskill.mean()))]
print(f"no-skill log loss {noskill.mean():.5f} | base formula {cur.mean():.5f} (better in {int((cur < noskill).sum())} of {len(MK)} markets)")
for step in range(1, 6):
    rows = []
    for c in [c for c in OD.EXTRA if c not in chosen]:
        x = lomo(chosen + [c]); rows.append(dict(cand=c, gain=float((cur - x).mean()), better=int((cur - x > 0).sum()), logloss=float(x.mean())))
    rows.sort(key=lambda r: -r["gain"]); print(f"\nstep {step}: candidates (gain in average out-of-market log loss, markets better of {len(MK)})")
    for r in rows: print(f"  {OD.WORDS[r['cand']]:42s} {r['gain']:+.5f}  {r['better']:2d}")
    ok = [r for r in rows if r["better"] >= 17 and r["gain"] >= .0005]; LOG.append(dict(step=step, table=rows, added=ok[0]["cand"] if ok else None))
    if not ok: print("  -> none meets the mark (17 of 24 markets and 0.0005). Stop."); break
    chosen.append(ok[0]["cand"]); cur = lomo(chosen); print(f"  -> added: {OD.WORDS[ok[0]['cand']]}  (log loss now {cur.mean():.5f})")
print("\ninputs of the formula:", [OD.WORDS[c] for c in chosen])
# ---- ceiling check: boosted trees with every input, scored the same out-of-market way
import lightgbm as lgb
allf = [c for c in OD.BASE + OD.EXTRA if c not in ("ZMS", "Z2", "MS2")]; XT = S_[allf].values.astype(np.float32); tre = np.zeros(len(MK)); t0 = time.time()
for k, m in enumerate(MK):
    te = mkS == m; g = lgb.LGBMClassifier(n_estimators=300, learning_rate=.05, num_leaves=31, min_child_samples=200, subsample=.8, subsample_freq=1, colsample_bytree=.8, verbose=-1, n_jobs=4, random_state=80)
    g.fit(XT[~te], yS[~te], sample_weight=wS[~te]); tre[k] = ll(yS[te], g.predict_proba(XT[te])[:, 1]).mean()
gf = float((noskill - cur).mean()); gt = float((noskill - tre).mean()); share = gf / gt if gt > 0 else np.nan
print(f"\nceiling check ({time.time() - t0:.0f}s): gain over no-skill, formula {gf:.5f} | boosted trees with every input {gt:.5f} | the formula gets {100 * share:.0f}% of the trees' gain (mark: 80%)")
# ---- step 1: the formula out-of-market on the other markets (selection sample)
_, pS = lomo(chosen, want_pred=True); blk = S_.market.values + "|" + S_.month.astype(str).values
sep = EV.separation(pS, S_.net.values, blk, n=300); bt = EV.beats(pS, dict(stretch=(S_.Z.values, -1), momentum=(S_.MS.values, -1)), S_.net.values, blk, n=300)
print(f"\nstep 1, other markets, out-of-market odds: AUC {EV.auc(yS, pS):.3f} | top third {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}%: {100 * sep[0]:+.2f} points (5th pct {100 * sep[1]:+.2f})")
print(f"rank correlation with the net result: odds {bt['odds']:.3f} | stretch Z alone {bt['stretch']['corr']:.3f} (lead {bt['stretch']['lead']:+.3f}, 5th pct {bt['stretch']['lead_p5']:+.3f}) | market momentum alone {bt['momentum']['corr']:.3f} (lead {bt['momentum']['lead']:+.3f}, 5th pct {bt['momentum']['lead_p5']:+.3f})")
cal = EV.calibration(pS, yS); print("stated odds -> share of wins, by tenth: " + "  ".join(f"{100 * r['stated']:.0f}->{100 * r['wins']:.0f}" for r in cal))
bym = {m: dict(n=int((mkS == m).sum()), auc=EV.auc(yS[mkS == m], pS[mkS == m]), spread=float(S_.net.values[(mkS == m) & (pS >= np.quantile(pS[mkS == m], 2 / 3))].mean() - S_.net.values[(mkS == m) & (pS <= np.quantile(pS[mkS == m], 1 / 3))].mean())) for m in MK}
print("by market (AUC, top third minus bottom third): " + "  ".join(f"{m} {v['auc']:.2f} {100 * v['spread']:+.1f}" for m, v in bym.items())); print(f"markets with a positive spread: {sum(v['spread'] > 0 for v in bym.values())} of {len(MK)}")
# ---- the two frozen copies and their companion tables
def freeze(T, label):
    w = 1.0 / T.market.map(T.market.value_counts()).values; X, st = OD.prepare(T, chosen); b0, b = OD.fit(X, T.win.values, w); M = dict(names=chosen, b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, fitted_to=label, cases=int(len(T)), markets=int(T.market.nunique()))
    p = OD.odds(M, T); M["band_edges"] = [float(x) for x in np.quantile(p, np.arange(1, 10) / 10)]; band = OD.band_of(M, p); M["bands"] = []
    for k in range(10):
        x = T[band == k]; M["bands"].append(dict(n=int(len(x)), odds=float(p[band == k].mean()), win=float(x.win.mean()), gain=float(x.net.mean()), gain_med=float(x.net.median()), dip_med=float(x.dip.median()), dip_bad=float(x.dip.quantile(.1)), days=float(x.held.median()),
                                                 cone={q: [float(x[f"p{h}"].quantile(v)) for h in OD.HORIZONS] for q, v in (("q10", .1), ("q25", .25), ("q50", .5), ("q75", .75), ("q90", .9))}))
    return M, p
M19, p19 = freeze(D19, "2019-12-31"); ML, pL = freeze(D, str(pd.Timestamp(D.exdate.max()).date())); pL19 = OD.odds(M19, D)
print(f"\nM19 (trades ended by 2019): {M19['cases']} cases | live copy: {ML['cases']} cases | the two copies' odds on all cases: correlation {np.corrcoef(pL, pL19)[0, 1]:.4f}, average gap {100 * np.abs(pL - pL19).mean():.1f} points")
print("weights per one standard deviation of each input (M19 | live):"); [print(f"  {OD.WORDS[k]:42s} {a:+.3f} | {b:+.3f}") for k, a, b in zip(chosen, M19["b"], ML["b"])]
print("M19 companion table by odds band (other markets): band odds -> wins, average gain, typical dip, bad dip (1 in 10), sessions")
for k, b in enumerate(M19["bands"]): print(f"  {k}: {100 * b['odds']:.0f}% -> {100 * b['win']:.0f}%, {100 * b['gain']:+.1f}%, {100 * b['dip_med']:+.1f}%, {100 * b['dip_bad']:+.1f}%, {b['days']:.0f}")
json.dump(dict(m19=M19, live=ML, horizons=list(OD.HORIZONS), line=OD.LINE, saudi=None), open(OD.MODEL_FILE, "w"), indent=1)
json.dump(dict(log=LOG, chosen=chosen, noskill=float(noskill.mean()), formula=float(cur.mean()), trees=float(tre.mean()), share_of_trees=share, step1=dict(auc=EV.auc(yS, pS), separation=sep, beats=bt, calibration=cal, by_market=bym)), open(os.path.join(HERE, "select80.json"), "w"), indent=1, default=float)
