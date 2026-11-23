from s_z import *
import pickle
ZP = pickle.load(open("Zs.pkl", "rb"))[("price", 250)]
mkt20 = np.log1p(P["Roo"].where(P["elig"]).mean(1)).rolling(20).sum()
def ztr2(Z, entry=-2.5, exit_z=-1.0, maxhold=60, ml=.5, confirm=True, look=20, mktmin=None):
    """confirm: signal when z crosses back ABOVE `entry` after having been below it within `look` days (the stock has turned)."""
    Zv = Z.values; Of = P["O"].ffill().values; el = P["elig"].values; PV = PCT.values; out = []; start = np.searchsorted(dates, np.datetime64("2013-01-01"))
    below = (Z <= entry).rolling(look, min_periods=1).max().values
    for j in range(len(cols)):
        i = start
        while i < len(dates) - 2:
            z0, z1 = Zv[i - 1, j], Zv[i, j]
            trig = (np.isfinite(z1) and np.isfinite(z0) and ((z0 <= entry < z1 and below[i - 1, j] > 0) if confirm else (z1 <= entry < z0)))
            if trig and el[i, j] and (ml is None or (np.isfinite(PV[i, j]) and PV[i, j] >= ml)) and (mktmin is None or mkt20.iloc[i] > mktmin):
                k = i + 1
                while k < min(len(dates) - 1, i + maxhold):
                    if np.isfinite(Zv[k, j]) and Zv[k, j] >= exit_z: break
                    k += 1
                a, b = Of[i + 1, j], Of[min(k + 1, len(dates) - 1), j]
                if a > 0 and b > 0: out.append((dates[i], cols[j], b / a - 1 - .004, k - i))
                i = k + 1
            else: i += 1
    return pd.DataFrame(out, columns=["date", "sym", "r", "days"])
def toW(T, nmax=10, size=.1, maxnew=99):
    W = pd.DataFrame(0.0, index=dates, columns=cols); di = {d: i for i, d in enumerate(dates)}; cnt = np.zeros(len(dates)); new = {}
    for _, t in T.sort_values("date").iterrows():
        i = di[t.date]; k = i + int(t.days)
        if cnt[i:k + 1].max() >= nmax or new.get(i // 5, 0) >= maxnew: continue
        W.iloc[i:k + 1, cols.get_loc(t.sym)] = size; cnt[i:k + 1] += 1; new[i // 5] = new.get(i // 5, 0) + 1
    return W
if __name__ == "__main__":
    Wb = pd.read_pickle("W_best.pkl"); core = Wb["ml"].add(Wb["trend"], fill_value=0)
    for nm, kw, wk in (("cross-down (old)", dict(confirm=False), dict()), ("CONFIRMED turn", dict(), dict()), ("confirmed, max 2 new/week", dict(), dict(maxnew=2)),
                       ("confirmed, 5% size x 10", dict(), dict(size=.05)), ("confirmed, market 20d > -5%", dict(mktmin=-.05), dict()), ("confirmed, entry -2.0", dict(entry=-2.0), dict()),
                       ("confirmed, no ML filter", dict(ml=None), dict())):
        T = ztr2(ZP, **kw); rep(f"Z {nm} (trades)", T)
        Wz = toW(T, **wk); r, inv = run(P, Wz); show(f"   sleeve {nm}", r, inv)
        W3 = core.add(Wz, fill_value=0); W3 = W3.div(np.maximum(W3.sum(1), 1), axis=0); r3, i3 = run(P, W3); show(f"   CORE + Z {nm}", r3, i3)
