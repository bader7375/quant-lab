from panel import *; from xs import *
P = lib_panel(); C, O, V, VAL = P["C"], P["O"], P["V"], P["VAL"]
R = C.pct_change(fill_method=None).clip(-.5, .5)
meta_sec = pd.Series({s: META[s]["sector"] for s in C.columns})
sc = {}
sc["1w momentum (past week return)"] = ("W", C / C.shift(5) - 1)
sc["1m momentum"] = ("W", C / C.shift(21) - 1)
sc["3m momentum"] = ("W", C / C.shift(63) - 1)
sc["12-1m momentum (monthly)"] = ("M", C.shift(21) / C.shift(252) - 1)
sc["low volatility 60d (monthly)"] = ("M", -R.rolling(60, min_periods=40).std())
sc["MAX effect: low max-day (monthly)"] = ("M", -R.rolling(21, min_periods=15).max())
sc["near 52w high (monthly)"] = ("M", C / C.rolling(250, min_periods=200).max())
sc["near 52w high (weekly)"] = ("W", C / C.rolling(250, min_periods=200).max())
vz = np.log(V.rolling(5, min_periods=3).mean() / V.rolling(60, min_periods=40).mean())
sc["volume surge 5d/60d (weekly)"] = ("W", vz)
sc["volume surge x up-week (weekly)"] = ("W", vz.where(C / C.shift(5) > 1))
sc["1w reversal (loser week)"] = ("W", -(C / C.shift(5) - 1))
sc["illiquidity (Amihud, monthly)"] = ("M", (R.abs() / VAL).rolling(60, min_periods=40).mean())
sec_ret = (C / C.shift(21) - 1).T.groupby(meta_sec).transform("median").T
sc["industry 1m momentum (weekly)"] = ("W", sec_ret)
skip={"1w momentum (past week return)","1m momentum","3m momentum","12-1m momentum (monthly)","low volatility 60d (monthly)","MAX effect: low max-day (monthly)","near 52w high (monthly)"}
for k, (f, s) in sc.items():
    if k in skip: continue
    Rr = run(P, s, freq=f); print(report(k, Rr, 52 if f == "W" else 12), flush=True)
