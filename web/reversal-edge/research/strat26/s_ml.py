from sim import *
P = load(); dates = P["C"].index
pred = pd.read_parquet("../ml26/pred_q20stockonly.parquet").pivot(index="date", columns="sym", values="pred").reindex(index=dates)
pm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates)
vol60 = np.log(P["C"]).diff().rolling(60, min_periods=40).std()
def ml_weights(N=10, hold=20, tranches=4, weight="eq", timing="bin", sector_cap=None):
    W = pd.DataFrame(0.0, index=dates, columns=P["C"].columns); idx = np.arange(len(dates)); start = np.searchsorted(dates, np.datetime64("2013-01-01"))
    for k in range(tranches):
        cur = pd.Series(0.0, index=W.columns)
        rows = []
        for i in range(start + k * hold // tranches, len(dates)):
            if (i - start - k * hold // tranches) % hold == 0:
                d = dates[i]; s = pred.loc[d].where(P["elig"].loc[d]).dropna()
                cur = pd.Series(0.0, index=W.columns)
                if len(s) >= 3 * N:
                    top = s.nlargest(N).index
                    if weight == "eq": w = pd.Series(1.0 / N, top)
                    else: iv = 1 / vol60.loc[d, top].clip(lower=.005); w = iv / iv.sum()
                    if timing == "bin": w *= float(pm.loc[d] > 0) if pd.notna(pm.loc[d]) else 1
                    elif timing == "soft": w *= float(np.clip(0.5 + pm.loc[d] / 0.04, 0, 1)) if pd.notna(pm.loc[d]) else 1
                    cur[w.index] = w.values
            rows.append(cur.values)
        W.iloc[start + k * hold // tranches:] += np.array(rows) / tranches
    return W
if __name__ == "__main__":
    for kw in (dict(N=10, tranches=1, timing="none"), dict(N=10, tranches=1, timing="bin"), dict(N=10, tranches=4, timing="none"), dict(N=10, tranches=4, timing="bin"),
               dict(N=10, tranches=4, timing="soft"), dict(N=10, tranches=4, timing="bin", weight="iv"), dict(N=20, tranches=4, timing="bin", weight="iv"),
               dict(N=15, tranches=4, timing="bin", weight="iv"), dict(N=10, hold=60, tranches=4, timing="bin", weight="iv")):
        W = ml_weights(**kw); r, inv = run(P, W); show("ML " + " ".join(f"{k}={v}" for k, v in kw.items()), r, inv)
