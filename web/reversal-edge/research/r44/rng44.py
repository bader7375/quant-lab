"""Round 44 addendum: calibrated expected ranges (volatility, not direction) for the US30 at 2 / 5 / 10 sessions."""
import os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import norm
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); DATA = os.path.join(SP, "edge26/data")
L = json.load(open(f"{DATA}/us30_list.json"))["list"]; HZ = (2, 5, 10); LV = (.84, .95)
ERAS = {"DESIGN 2010-17": ("2010", "2017-12-31"), "CONFIRM 2018-26": ("2018", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
rows = []
for s in L:
    d = pd.read_csv(f"{DATA}/us30/{s}.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()]; k = d.adjclose / d.close
    c, h, l = d.adjclose, d.high * k, d.low * k; r = np.log(c).diff()
    var = r.pow(2).ewm(alpha=.06, adjust=False).mean().shift(0); sig = np.sqrt(var)          # EWMA known at the close of t (includes today's return)
    for hh in HZ:
        fut = np.log(c.shift(-hh) / c); hi = np.log(h[::-1].rolling(hh).max()[::-1].shift(-1) / c); lo = np.log(l[::-1].rolling(hh).min()[::-1].shift(-1) / c)
        zs = fut / (sig * np.sqrt(hh))
        past = zs.shift(hh)                                                                        # standardised outcomes already known at t
        q = {p: past.rolling(750, min_periods=250).quantile(p) for p in (.05, .16, .84, .95)}
        x = pd.DataFrame({"date": c.index, "sym": s, "h": hh, "fut": fut.values, "hi": hi.values, "lo": lo.values, "s": (sig * np.sqrt(hh)).values,
                          **{f"q{int(100 * p)}": v.values for p, v in q.items()}})
        rows.append(x)
X = pd.concat(rows); X = X[X.fut.notna() & X.s.notna() & (X.date >= "2010")]
def calib(x, ver):
    out = {}
    for p in LV:
        if ver == "V1": up, dn = norm.ppf(p) * x.s, norm.ppf(1 - p) * x.s
        else: up, dn = x[f"q{int(100 * p)}"] * x.s, x[f"q{int(round(100 * (1 - p)))}"] * x.s
        ok = up.notna() & dn.notna(); y = x[ok]
        out[p] = dict(below=float((y.fut < up[ok]).mean()), above=float((y.fut > dn[ok]).mean()), touch_up=float((y.hi >= up[ok]).mean()), touch_dn=float((y.lo <= dn[ok]).mean()))
    return out
R = {}
for ver in ("V1", "V2"):
    for e, (a, b) in ERAS.items():
        for hh in HZ:
            x = X[(X.h == hh) & (X.date >= a) & (X.date <= b)]; R[(ver, e, hh)] = calib(x, ver)
def err(ver, e): return float(np.mean([abs(R[(ver, e, hh)][p][k] - p) for hh in HZ for p in LV for k in ("below", "above")]))
for ver in ("V1", "V2"):
    print(f"\n{ver} ({'EWMA, normal' if ver == 'V1' else 'EWMA, own empirical quantiles'}): mean calibration error DESIGN {100 * err(ver, 'DESIGN 2010-17'):.1f} pts, CONFIRM {100 * err(ver, 'CONFIRM 2018-26'):.1f} pts")
    for e in ERAS:
        for hh in HZ:
            print(f"  {e} {hh:2d}d: " + " | ".join(f"{int(100 * p)}%: close below upper {100 * R[(ver, e, hh)][p]['below']:.1f}%, above lower {100 * R[(ver, e, hh)][p]['above']:.1f}%,"
                                                    f" touched upper {100 * R[(ver, e, hh)][p]['touch_up']:.0f}% / lower {100 * R[(ver, e, hh)][p]['touch_dn']:.0f}%" for p in LV))
pick = min(("V1", "V2"), key=lambda v: err(v, "DESIGN 2010-17"))
ok = all(abs(R[(pick, "CONFIRM 2018-26", hh)][p][k] - p) <= .03 for hh in HZ for p in LV for k in ("below", "above"))
print(f"\nDESIGN pick {pick}; DECISION expected ranges shown: {ok}")
json.dump({"pick": pick, "shown": bool(ok), "res": {f"{v}|{e}|{hh}": {str(p): o for p, o in R[(v, e, hh)].items()} for (v, e, hh) in R}}, open(os.path.join(HERE, "rng44_results.json"), "w"), indent=1)
