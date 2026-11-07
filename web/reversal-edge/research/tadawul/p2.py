from lib import *
rows = []
for s in syms():
    d = load(s); c, h = d.Close, d.High; R = rsi(c); ret, xi = mom_trades(d, maxhold=20)
    B0 = (R > 90); dip5 = (R < 10).rolling(5).max() > 0; M3 = (c > c.rolling(200).mean()) & dip5 & (c > h.shift())
    for nm, a, b in (("2002-12", "2002", "2013"), ("2013-20", "2013", "2021")):
        s0 = system(d, B0.fillna(False), xi, a, b)[0]; s1 = system(d, (B0 | M3).fillna(False), xi, a, b)[0]
        if np.isfinite(s0) and np.isfinite(s1): rows.append((s, nm, s0, s1))
P = pd.DataFrame(rows, columns=["sym", "half", "B0", "B0_M3"])
for nm, g in P.groupby("half"): print(f"P2 {nm}: B0+M3 beats B0 on {100*(g.B0_M3>g.B0).mean():.0f}% of {len(g)} stocks | mean Sharpe B0 {g.B0.mean():.2f} B0+M3 {g.B0_M3.mean():.2f}")
