"""Round 83, after the confirm step: the product's Saudi adjustments and Saudi tables for Rebound Edge 40 and Hold Edge 40, refitted by
the same recipe on ALL finished Saudi trades to date, on the live copies. The tested numbers stay under "saudi_tested".
Usage: RE_WORK=<work folder> python3 refit83.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
WORK = os.environ["RE_WORK"]; OUT = {}
def both(nm): x = pd.concat([pd.read_parquet(os.path.join(WORK, f"r83_saudi_{nm}_{m}.parquet")) for m in ("design", "confirm")], ignore_index=True); return x[np.isfinite(x.Z) & np.isfinite(x.MS)].reset_index(drop=True)
def adjust(D, e, col):
    r = D[col].values; lo, hi = np.quantile(r, [.01, .99]); y = np.clip(r, lo, hi); g = D.gated.values
    def fit(ix, with_c=True): A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
    full = fit(np.arange(len(D))); bs = np.array([fit(ix) for ix in EV.month_draws(D.month.values, 600)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0); co = full if keep else fit(np.arange(len(D)), with_c=False)
    return dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))],
                fitted_on=f"all finished Saudi trades, {D.date.min().date()} to {D.date.max().date()}", cases=int(len(D)))
def raw(M, S): r = RB.raw_weights(M); return dict(c0=float(S["a"] + S["b"] * r["c0"]), gate=float(S["c"]), clips=r["clips"], **{k: float(S["b"] * r[k]) for k in M["names"]})
# ---- Rebound Edge 40
RL, RALL = RB.load("live", RB.MODEL_FILE_40); D = both("trades"); e = RB.edge(RL, D); S = adjust(D, e, "net"); ea = RB.edge(RL, D, saudi=S, gated=D.gated.values)
S["band_edges"], S["bands"] = RB.saudi_tables(D, ea, RL); S["zones"] = [float(v) for v in np.quantile(ea, [1 / 3, 2 / 3])]; S["raw"] = raw(RL, S); RALL["saudi"] = S; RALL["live"]["raw"] = RB.raw_weights(RL); json.dump(RALL, open(RB.MODEL_FILE_40, "w"), indent=1)
T = RALL["saudi_tested"]; w = S["raw"]; OUT["rebound40"] = {k: v for k, v in S.items() if k != "bands"}
print(f"Rebound Edge 40: {len(D)} Saudi trades | tested: {100 * T['a']:+.2f}% + {T['b']:.2f} x edge, {100 * T['c']:+.2f}% with the gates | product: {100 * S['a']:+.2f}% + {S['b']:.2f} x edge, {100 * S['c']:+.2f}% with the gates (range {100 * S['c_range'][0]:+.2f} to {100 * S['c_range'][1]:+.2f})")
print(f"  for Saudi: edge % = {100 * w['c0']:+.2f} {100 * w['Z']:+.2f} x Z {100 * w['MS']:+.2f} x M {100 * w['ZMS']:+.3f} x Z x M, {100 * w['gate']:+.2f} with the gates; weak below {100 * S['zones'][0]:+.1f}%, strong from {100 * S['zones'][1]:+.1f}%")
for k, b in enumerate(S["bands"]): print(f"  {k}: {b['n']:5d} | {100 * b['edge']:+5.1f}% -> {100 * b['gain']:+5.1f}% | wins {100 * b['win']:.0f}% | dip {b['dipz_med']:+.2f} / {b['dipz_bad']:+.2f} | Saudi alone {100 * b['saudi_only']['gain']:+5.1f}%, {100 * b['saudi_only']['win']:.0f}%")
# ---- Hold Edge 40
HL, HALL = HE.load("live", HE.MODEL_FILE_40); D = both("hold"); D = D[np.isfinite(D.rest)].reset_index(drop=True); e = RB.edge(HL, D); S = adjust(D, e, "rest"); ea = RB.edge(HL, D, saudi=S, gated=D.gated.values)
S["band_edges"], S["bands"] = HE.tables(D, ea, HL); S["zones"] = [float(v) for v in np.quantile(ea, [1 / 3, 2 / 3])]; S["raw"] = raw(HL, S); S["trades"] = int(D.case.nunique()); HALL["saudi"] = S; HALL["live"]["raw"] = RB.raw_weights(HL); json.dump(HALL, open(HE.MODEL_FILE_40, "w"), indent=1)
T = HALL["saudi_tested"]; w = S["raw"]; OUT["hold40"] = {k: v for k, v in S.items() if k != "bands"}
print(f"\nHold Edge 40: {len(D)} Saudi readings from {S['trades']} trades | tested: {100 * T['a']:+.2f}% + {T['b']:.2f} x reading, {100 * T['c']:+.2f}% with the gates | product: {100 * S['a']:+.2f}% + {S['b']:.2f} x reading, {100 * S['c']:+.2f}% with the gates (range {100 * S['c_range'][0]:+.2f} to {100 * S['c_range'][1]:+.2f})")
print(f"  for Saudi (L = sessions left / 40): hold edge % = {100 * w['c0']:+.2f} {100 * w['Z']:+.2f} x Z {100 * w['MS']:+.2f} x M {100 * w['ZMS']:+.3f} x Z x M {100 * w['LEFT']:+.2f} x L {100 * w['ZLEFT']:+.2f} x Z x L, {100 * w['gate']:+.2f} with the gates; weak below {100 * S['zones'][0]:+.1f}%, strong from {100 * S['zones'][1]:+.1f}%")
for k, b in enumerate(S["bands"]): print(f"  {k}: {b['n']:6d} | {100 * b['edge']:+5.1f}% -> {100 * b['rest']:+5.1f}% | sold above the close {100 * b['up']:.0f} in 100 | {b['togo']:.0f} sessions | further dip {b['furz_med']:+.2f} / {b['furz_bad']:+.2f}")
json.dump(OUT, open(os.path.join(HERE, "refit83.json"), "w"), indent=1, default=float)
