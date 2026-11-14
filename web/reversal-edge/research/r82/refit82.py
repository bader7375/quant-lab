"""Round 82, after the confirm step: the product's Saudi adjustment and Saudi tables for Hold Edge, refitted by the same recipe on ALL
finished Saudi trades to date, on the live copy of the formula. The tested numbers stay under "saudi_tested".
Usage: RE_WORK=<work folder> python3 refit82.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
WORK = os.environ["RE_WORK"]; D = pd.concat([pd.read_parquet(os.path.join(WORK, f"r82_saudi_{m}.parquet")) for m in ("design", "confirm")], ignore_index=True); D = D[np.isfinite(D.Z) & np.isfinite(D.MS) & np.isfinite(D.rest)].reset_index(drop=True)
ML, ALL = HE.load("live"); e = RB.edge(ML, D); lo, hi = np.quantile(D.rest.values, [.01, .99]); y = np.clip(D.rest.values, lo, hi); g = D.gated.values; mon = D.month.values
def adj(ix, with_c=True):
    A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
full = adj(np.arange(len(D))); bs = np.array([adj(ix) for ix in EV.month_draws(mon, 600)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0); co = full if keep else adj(np.arange(len(D)), with_c=False)
S = dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))], fitted_on=f"all finished Saudi trades, {D.date.min().date()} to {D.date.max().date()}", cases=int(len(D)), trades=int(D.case.nunique()))
ea = RB.edge(ML, D, saudi=S, gated=g); S["band_edges"], S["bands"] = HE.tables(D, ea, ML); S["zones"] = [float(v) for v in np.quantile(ea, [1 / 3, 2 / 3])]
r = RB.raw_weights(ML); S["raw"] = dict(c0=float(S["a"] + S["b"] * r["c0"]), gate=float(S["c"]), clips=r["clips"], **{k: float(S["b"] * r[k]) for k in ML["names"]}); ML["raw"] = r
T = ALL["saudi_tested"]; print(f"Saudi hold cases to date: {len(D)} from {S['trades']} trades")
print(f"tested (2013-19, on M19):  saudi hold edge = {100 * T['a']:+.2f}% + {T['b']:.2f} x hold edge" + (f" {100 * T['c']:+.2f}% with the gates" if T["c_kept"] else ""))
print(f"product (all, live copy):  saudi hold edge = {100 * S['a']:+.2f}% + {S['b']:.2f} x hold edge" + (f" {100 * S['c']:+.2f}% with the gates" if keep else "") + f" | gate term tried {100 * full[2]:+.2f}% (range {100 * c5:+.2f} to {100 * c95:+.2f}) -> {'kept' if keep else 'not kept'}; slope range {S['b_range'][0]:.2f} to {S['b_range'][1]:.2f}")
w = S["raw"]; print(f"for Saudi, on the raw readings (Z = stretch Z now, M = market momentum now, L = sessions left / 40): hold edge % = {100 * w['c0']:+.2f} {100 * w['Z']:+.2f} x Z {100 * w['MS']:+.2f} x M {100 * w['ZMS']:+.3f} x Z x M {100 * w['LEFT']:+.2f} x L {100 * w['ZLEFT']:+.2f} x Z x L" + (f" {100 * w['gate']:+.2f} when the stock passes the gates" if keep else ""))
print(f"zones (thirds of the Saudi cases): weak below {100 * S['zones'][0]:+.1f}%, strong from {100 * S['zones'][1]:+.1f}%")
print("product Saudi table by band: reading -> rest of the trade | sold above the close | sessions to the sale | further dip typical / 1-in-10 (in 20-session swings)")
for k, b in enumerate(S["bands"]): print(f"  {k}: {b['n']:6d} | {100 * b['edge']:+5.1f}% -> {100 * b['rest']:+5.1f}% | {100 * b['up']:.0f} in 100 | {b['togo']:.0f} | {b['furz_med']:+.2f} / {b['furz_bad']:+.2f}")
ALL["saudi"] = S; ALL["live"] = ML; json.dump(ALL, open(HE.MODEL_FILE, "w"), indent=1); json.dump({k: v for k, v in S.items() if k != "bands"}, open(os.path.join(HERE, "refit82.json"), "w"), indent=1, default=float)
