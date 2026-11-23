"""H1: VWAP stretch Z (vz) - line, overlap with stretch Z, VZ swing vs Z swing, vz as a confirmation filter; DEEP price-only check."""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r28")); sys.path.insert(0, os.path.join(H, "../r27"))
os.chdir(os.path.join(H, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
from sim28 import trades, line
from feat31 import *
os.chdir(os.path.dirname(os.path.abspath(__file__)))
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
el = P["elig"] & P["liq"]
F = pd.read_pickle(os.path.join(H, "../r27/F27y.pkl")); zc = F["zc"].reindex(index=dates, columns=cols)
vz, parts = vwap_z(P, parts=True); pd.to_pickle(vz, "vz.pkl")
d = vz.where(el).loc["2013":"2019"].stack(); zd = zc.where(el).loc["2013":"2019"].stack()
VLINE = round(float(d.quantile(.02)), 2)
print("vz DESIGN quantiles:", {q: round(float(d.quantile(q)), 2) for q in (.005, .01, .02, .05, .1, .5, .9, .95, .98, .99)})
print("zc DESIGN 2%:", round(float(zd.quantile(.02)), 2), "| vz line (2%):", VLINE)
for k in (10, 20, 60): print(f"  z{k} sd {parts[k].where(el).loc['2013':'2019'].stack().std():.2f}")
j = pd.concat([d.rename("vz"), zd.rename("zc")], axis=1).dropna()
print("corr vz~zc", round(j.corr().iloc[0, 1], 3), "| spearman", round(j.corr("spearman").iloc[0, 1], 3))
ve, ze = j.vz <= VLINE, j.zc <= -2.62
print(f"vz extremes also zc extremes: {100 * (ve & ze).sum() / ve.sum():.0f}% | zc extremes also vz extremes: {100 * (ve & ze).sum() / ze.sum():.0f}%")
scale = {q: round(float(d.quantile(q)), 2) for q in (1 / 500, 1 / 200, 1 / 100, 1 / 50, 1 / 20, 1 / 10)}
json.dump({"line": VLINE, "lower": scale, "upper": {q: round(float(d.quantile(1 - q)), 2) for q in scale}}, open("vz_scale.json", "w"), indent=1)
first = lambda x: x & ~x.shift(1, fill_value=False)
MK = pd.DataFrame(np.repeat((pm > 0).values[:, None], len(cols), 1), index=dates, columns=cols)
zs = first(zc <= -2.62) & (PCT >= .5) & MK; vs = first(vz <= VLINE) & (PCT >= .5) & MK
print("\nH1b swing comparison (hold 40, ML >= .5, market model > 0):")
TZ = trades(P, ATR, zs, "X2 hold40"); line("Z swing (stretch Z)", TZ)
TV = trades(P, ATR, vs, "X2 hold40"); line("VZ swing (VWAP stretch Z)", TV)
for a, b in ((-2.4, None), (-2.8, None)): pass
both = zs & (vz <= VLINE); only_z = zs & ~(vz <= VLINE)
print("\nH1c Z swing split by vz at the signal:")
TB = trades(P, ATR, both, "X2 hold40"); line("Z swing AND vz at/below its line", TB)
TO = trades(P, ATR, only_z, "X2 hold40"); line("Z swing, vz above its line", TO)
vonly = vs & ~(zc <= -2.62); line("VZ swing where zc is NOT extreme", trades(P, ATR, vonly, "X2 hold40"))
print(f"share of Z-swing trades kept by the filter: DESIGN {len(TB[TB.date < '2020']) / max(1, len(TZ[TZ.date < '2020'])):.0%}, "
      f"CONFIRM {len(TB[TB.date >= '2020']) / max(1, len(TZ[TZ.date >= '2020'])):.0%}")
# DEEP 2004-12, price only (no ML or market model then)
L_ = library(); L_["liq"] = L_["VAL"].rolling(60, min_periods=20).median() >= 3e6
zcl, vzl = zc_of(L_), vwap_z(L_)
trL = pd.concat([L_["H"] - L_["L"], (L_["H"] - L_["C"].shift()).abs(), (L_["L"] - L_["C"].shift()).abs()]).groupby(level=0).max().reindex(L_["C"].index)
ATRL = trL.rolling(20, min_periods=15).mean()
print("\nDEEP 2004-12, price only, hold 40:")
for nm, s in (("zc first <= -2.62", first(zcl <= -2.62)), (f"vz first <= {VLINE}", first(vzl <= VLINE)),
              ("zc first & vz at/below line", first(zcl <= -2.62) & (vzl <= VLINE)), ("zc first & vz above line", first(zcl <= -2.62) & ~(vzl <= VLINE))):
    line(nm, trades(L_, ATRL, s, "X2 hold40"), eras=("DEEP",))
print("\nDESIGN/CONFIRM, price only, hold 40 (same rules as DEEP):")
for nm, s in (("zc first <= -2.62", first(zc <= -2.62)), (f"vz first <= {VLINE}", first(vz <= VLINE))):
    line(nm, trades(P, ATR, s, "X2 hold40"))
TZ.to_csv("h1_zswing.csv", index=False); TV.to_csv("h1_vzswing.csv", index=False)
