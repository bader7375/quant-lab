"""H2: which momentum gauge tells when mean reversion works? Terciles chosen on DESIGN EB trades, checked on CONFIRM, DEEP and Z swing (EA)."""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r27")); os.chdir(os.path.join(H, "../r27"))
from core import P, dates, cols
from feat31 import *
os.chdir(os.path.dirname(os.path.abspath(__file__)))
first = lambda x: x & ~x.shift(1, fill_value=False)
def eb(Pn, zc):
    T = events(Pn, first(zc <= -2.0), 20); return T
def attach(T, G):
    for k, g in G.items():
        s = g.stack(); s.index.names = ["date", "sym"]; T = T.merge(s.rename(k).reset_index(), on=["date", "sym"], how="left")
    return T
F = pd.read_pickle(os.path.join(H, "../r27/F27y.pkl")); zc = F["zc"].reindex(index=dates, columns=cols)
G = gauges(P); pd.to_pickle(G, "gauges.pkl")
T = attach(eb(P, zc), G)
L_ = library(); TL = attach(eb(L_, zc_of(L_)), gauges(L_))
D = T[(T.date >= "2013") & (T.date <= "2019-12-31")]; Cf = T[T.date >= "2020"]; C1 = Cf[Cf.date <= "2022-12-31"]; C2 = Cf[Cf.date >= "2023"]
DP = TL[(TL.date >= "2004") & (TL.date <= "2012-12-31")]
print(f"EB trades: DEEP {len(DP)}, DESIGN {len(D)}, CONFIRM {len(Cf)} | mean excess DESIGN {100 * D['xs'].mean():+.2f}% CONFIRM {100 * Cf['xs'].mean():+.2f}% DEEP {100 * DP['xs'].mean():+.2f}%")
def terc(x, k, cuts):
    b = np.digitize(x[k], cuts); return [x['xs'][b == i] for i in range(3)], [x.net[b == i] for i in range(3)]
def tstat(a, b): return (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
res = {}
print("\nexcess return over the market by tercile (low / mid / high gauge); net win rate in brackets")
for k in G:
    x = D.dropna(subset=[k]); cuts = list(x[k].quantile([1 / 3, 2 / 3]).values)
    (lo, mi, hi), _ = terc(x, k, cuts); m = [lo.mean(), mi.mean(), hi.mean()]
    best, worst = (0, 2) if m[0] > m[2] else (2, 0); mono = min(m[0], m[2]) <= m[1] <= max(m[0], m[2])
    t = tstat([lo, mi, hi][best], [lo, mi, hi][worst]); res[k] = dict(cuts=cuts, best=best, worst=worst, mono=bool(mono), t=float(t), diff=float(m[best] - m[worst]))
    s = f"{k:10s} cuts {cuts[0]:+.3f}/{cuts[1]:+.3f} |"
    for nm, y in (("DESIGN", D), ("CONFIRM", Cf), ("C1", C1), ("C2", C2), ("DEEP", DP)):
        y = y.dropna(subset=[k])
        if len(y) < 30: s += f" {nm} n/a |"; continue
        (a, b_, c), (na, nb, nc) = terc(y, k, cuts)
        s += f" {nm} {100 * a.mean():+.1f}/{100 * b_.mean():+.1f}/{100 * c.mean():+.1f} ({100 * (na > 0).mean():.0f}/{100 * (nb > 0).mean():.0f}/{100 * (nc > 0).mean():.0f}%) |"
    print(s + f" DESIGN t {t:+.2f} {'monotonic' if mono else 'NOT monotonic'}")
ok = {k: v for k, v in res.items() if v["mono"]}; win = max(ok, key=lambda k: abs(ok[k]["t"])) if ok else None
print("\nSELECTED on DESIGN:", win, res.get(win))
json.dump({"selected": win, "res": res}, open("h2_selection.json", "w"), indent=1)
if win:
    v = res[win]; cuts = v["cuts"]
    def zone(x): b = np.digitize(x[win], cuts); return np.where(b == v["best"], "trade", np.where(b == v["worst"], "avoid", "middle"))
    print("\nCONFIRMATION (EB excess return: trade zone - avoid zone; must keep the sign and >= half the DESIGN size):")
    for nm, y in (("DESIGN", D), ("CONFIRM", Cf), ("C1", C1), ("C2", C2), ("DEEP", DP)):
        y = y.dropna(subset=[win]).copy(); y["z"] = zone(y); a, b_ = y[y.z == "trade"], y[y.z == "avoid"]
        print(f"  {nm:8s} trade {100 * a['xs'].mean():+.2f}% (win {100 * (a.net > 0).mean():.0f}%, n {len(a)}) | avoid {100 * b_['xs'].mean():+.2f}% (win {100 * (b_.net > 0).mean():.0f}%, n {len(b_)}) "
              f"| diff {100 * (a['xs'].mean() - b_['xs'].mean()):+.2f} pts (t {tstat(a['xs'], b_['xs']):+.2f})")
    Z = pd.read_csv("h1_zswing.csv", parse_dates=["date"], dtype={"sym": str}); Z = attach(Z, {win: G[win]}).dropna(subset=[win]); Z["z"] = zone(Z)
    print("\nEA Z swing (hold 40): all vs dropping avoid-zone trades")
    for nm, (a0, b0) in (("DESIGN", ("2013", "2019-12-31")), ("CONFIRM", ("2020", "2026-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        y = Z[(Z.date >= a0) & (Z.date <= b0)]; k_ = y[y.z != "avoid"]; av = y[y.z == "avoid"]
        print(f"  {nm:8s} all n {len(y)} win {100 * (y.net > 0).mean():.0f}% exp {100 * y.net.mean():+.2f}% | kept n {len(k_)} win {100 * (k_.net > 0).mean():.0f}% exp {100 * k_.net.mean():+.2f}% "
              f"| avoid-zone n {len(av)} win {100 * (av.net > 0).mean():.0f}% exp {100 * av.net.mean():+.2f}%")
T.to_parquet("h2_eb.parquet"); TL.to_parquet("h2_eb_deep.parquet")
