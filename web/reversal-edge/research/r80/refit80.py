"""Round 80, after the confirm step (PREREG amendment 2): the product's Saudi adjustment and Saudi companion tables, refitted by the
same recipe on ALL finished Saudi cases to date, on top of the live copy of the formula. The tested numbers stay in the model file
under "saudi_tested". Usage: RE_WORK=<work folder> python3 refit80.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, HERE)
import rebound as RB, eval80 as EV
WORK = os.environ["RE_WORK"]; D = pd.concat([pd.read_parquet(os.path.join(WORK, f"r80_saudi_{m}.parquet")) for m in ("design", "confirm")], ignore_index=True); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True)
ML, ALL = RB.load("live"); e = RB.edge(ML, D); net = D.net.values; lo, hi = np.quantile(net, [.01, .99]); y = np.clip(net, lo, hi); g = D.gated.values; mon = D.month.values
def adj(ix, with_c=True):
    A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
full = adj(np.arange(len(D))); bs = np.array([adj(ix) for ix in EV.month_draws(mon, 1000)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0); co = full if keep else adj(np.arange(len(D)), with_c=False)
S = dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))],
         fitted_on=f"all finished Saudi cases, {D.date.min().date()} to {D.date.max().date()}", cases=int(len(D)))
ea = RB.edge(ML, D, saudi=S, gated=g); S["band_edges"], S["bands"] = RB.saudi_tables(D, ea, ML); S["zones"] = [float(v) for v in np.quantile(ea, [1 / 3, 2 / 3])]
T = ALL["saudi_tested"]; print(f"Saudi cases to date: {len(D)}")
print(f"tested (2013-19, on M19):   saudi edge = {100 * T['a']:+.2f}% + {T['b']:.2f} x edge" + (f" {100 * T['c']:+.2f}% with the gates" if T["c_kept"] else ""))
print(f"product (all cases, live):  saudi edge = {100 * S['a']:+.2f}% + {S['b']:.2f} x edge" + (f" {100 * S['c']:+.2f}% with the gates" if keep else "") + f"   | gate term tried {100 * full[2]:+.2f}% (range {100 * c5:+.2f} to {100 * c95:+.2f}) -> {'kept' if keep else 'not kept'}; slope range {S['b_range'][0]:.2f} to {S['b_range'][1]:.2f}")
print(f"zones (thirds of the Saudi cases): weak below {100 * S['zones'][0]:+.1f}%, strong above {100 * S['zones'][1]:+.1f}%")
print("product Saudi table by edge band: edge -> result, wins, sessions, typical dip and 1-in-10 dip (in units of the stock's 20-session swing) | Saudi alone before the pull toward other markets")
for k, b in enumerate(S["bands"]): print(f"  {k}: {b['n']:5d} cases | {100 * b['edge']:+5.1f}% -> {100 * b['gain']:+5.1f}% | wins {100 * b['win']:.0f}% | {b['days']:.0f} sessions | dip {b['dipz_med']:+.2f} / {b['dipz_bad']:+.2f} | Saudi alone: {100 * b['saudi_only']['gain']:+5.1f}%, {100 * b['saudi_only']['win']:.0f}%")
r = ML["raw"]; print(f"\nthe formula (live copy, other markets): edge % = {100 * r['c0']:+.2f} {100 * r['Z']:+.2f} x Z {100 * r['MS']:+.2f} x MS {100 * r['ZMS']:+.3f} x Z x MS")
c0 = S["a"] + S["b"] * r["c0"]; print(f"for Saudi: edge % = {100 * c0:+.2f} {100 * S['b'] * r['Z']:+.2f} x Z {100 * S['b'] * r['MS']:+.2f} x MS {100 * S['b'] * r['ZMS']:+.3f} x Z x MS" + (f" {100 * S['c']:+.2f} when the stock passes the gates" if keep else ""))
S["raw"] = dict(c0=float(c0), Z=float(S["b"] * r["Z"]), MS=float(S["b"] * r["MS"]), ZMS=float(S["b"] * r["ZMS"]), gate=float(S["c"]), clips=r["clips"])
ALL["saudi"] = S; json.dump(ALL, open(RB.MODEL_FILE, "w"), indent=1); json.dump({k: v for k, v in S.items() if k != "bands"}, open(os.path.join(HERE, "refit80.json"), "w"), indent=1, default=float)
