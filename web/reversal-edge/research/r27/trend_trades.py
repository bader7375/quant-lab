"""Per-trade stats of the Saudi trend breakout on clean data (entry next open after a close at the 55-day high above SMA200; exit next open after close < peak - 3 ATR)."""
from core import *
hi = C.rolling(55, min_periods=55).max(); base = ((C >= hi) & (C > SMA200) & P["elig"]).values
Of = P["Of"].values; Cv = C.values; Av = ATR.values; pv = PCT.values; g = (pm > 0).values
def trades(filt):
    out = []
    for j in range(len(cols)):
        i = START
        while i < len(dates) - 2:
            if base[i, j] and filt(i, j) and np.isfinite(Av[i, j]):
                e = Of[i + 1, j]; peak = Cv[i, j]; k = i + 1
                while k < len(dates) - 1:
                    c = Cv[k, j]
                    if np.isfinite(c):
                        peak = max(peak, c)
                        if c < peak - 3 * Av[i, j]: break
                    k += 1
                x = Of[min(k + 1, len(dates) - 1), j]; out.append((dates[i], x / e - 1 - 2 * SIDE, k - i)); i = k + 1
            else: i += 1
    return pd.DataFrame(out, columns=["date", "net", "days"])
for nm, f in (("all breakouts", lambda i, j: True), ("ML top 30% & market model positive", lambda i, j: np.isfinite(pv[i, j]) and pv[i, j] >= .7 and bool(g[i]))):
    T = trades(f)
    for a, b in (("2013", "2026-12-31"), ("2013", "2019-12-31"), ("2020", "2026-12-31")):
        x = T[(T.date >= a) & (T.date <= b)]; w = x[x.net > 0]; l = x[x.net <= 0]
        print(f"{nm:36s} {a}-{b[:4]} n {len(x):4d} net {100*x.net.mean():+.2f}% win {100*len(w)/len(x):.0f}% avg win {100*w.net.mean():+.1f}% avg loss {100*l.net.mean():+.1f}% days {x.days.median():.0f}")
