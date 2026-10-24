"""Final validation on clean data: Core v1 sizing vs Core v2 (DESIGN-chosen sizing), optional Z-rebound and sector-laggard sleeves."""
from core import *
from zfam import zfamily, sector_resid
from scipy.stats import norm
Z, A = zfamily(P); zc = Z["zc"]; mk = pd.DataFrame({c: (pm > 0) for c in cols})
Wm = ml_weights(); Wt = trend(); V1 = combine(Wm, Wt); V2 = combine(Wm * .5, Wt)
e = zc <= -2.62; ZX = sleeve(e & ~e.shift(1, fill_value=False) & (PCT >= .5) & mk, h=20, N=5, w=.05)
res, beta, corr, LOO = sector_resid(P); rz = res.rolling(10, min_periods=8).sum() / (res.rolling(120, min_periods=80).std() * np.sqrt(10))
SL = sleeve((rz <= -2) & (corr >= .4) & (PCT >= .5) & mk, h=10, N=10, w=.05)
E = P["elig"].astype(float); rm, _ = run(P, E.div(E.sum(1), axis=0), side=0, cash=False)
def line(nm, W=None, r=None, side=SIDE):
    if r is None: r, inv = run(P, W, side=side)
    s = f"{nm:34s}"
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = stats(r, a, b); s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True); return r
line("market (equal weight, liquid)", r=rm)
r1 = line("CORE v1 sizing (ML 100%, trend 10x10%)", V1); r2 = line("CORE v2 (ML 50%, trend 10x10%)", V2)
line("  v2 at 0.30%/side costs", V2, side=.003); line("  v2 at 0.50%/side costs", V2, side=.005)
rz_ = line("CORE v2 + Z rebound 5x5%", combine(V2, ZX)); line("CORE v2 + sector laggard 10x5%", combine(V2, SL)); line("CORE v2 + both", combine(V2, ZX, SL))
line("Z rebound sleeve alone", ZX); line("sector laggard sleeve alone", SL)
yr = lambda x: x.loc["2013":].groupby(x.loc["2013":].index.year).apply(lambda v: (1 + v).prod() - 1)
print("by year (v2 / v2+Z / market):", " ".join(f"{y}:{100*a:+.0f}/{100*b:+.0f}/{100*c:+.0f}" for (y, a), b, c in zip(yr(r2).items(), yr(rz_), yr(rm))))
# deflated Sharpe (Bailey & Lopez de Prado) for Core v2, N trials ~ portfolio variants tried in rounds 24-27
x = r2.loc["2013":]; n = len(x); sr = x.mean() / x.std(); sk = x.skew(); ku = x.kurt() + 3
for N in (50, 200):
    emax = np.sqrt(1 / 250) * ((1 - 0.5772) * norm.ppf(1 - 1 / N) + 0.5772 * norm.ppf(1 - 1 / (N * np.e)))   # expected max daily SR of N zero-skill trials, trial SR sd ~ 1/sqrt(250)... annual sd 1
    psr = norm.cdf((sr - emax) * np.sqrt(n - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2))
    print(f"deflated Sharpe probability (N={N} trials, trial Sharpe sd 1.0/yr): {psr:.3f}  (annual SR {sr*np.sqrt(250):.2f}, benchmark max {emax*np.sqrt(250):.2f})")
pd.to_pickle({"V2": V2, "ZX": ZX, "SL": SL}, "W_final.pkl")
