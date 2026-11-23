from feats27 import *
import json, sys; sys.path.insert(0, "../strat"); from sectors import industry
P = yahoo(); C, Hh, L, O = P["C"], P["H"], P["L"], P["O"]; d = C.index[-1]; F = pd.read_pickle("F27y.pkl")
T = json.load(open("today27.json")); rk = pd.Series(T["ranks"]); names = json.load(open("../edge26/extra_names.json"))
meta = json.load(open("../tadawul/meta.json")); nm = lambda s: (meta.get(s, {}).get("name") or names.get(s) or s)
tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(C.index); ATR = tr.rolling(20, min_periods=15).mean()
sma200 = C.rolling(200, min_periods=160).mean(); hi55 = C.rolling(55, min_periods=55).max(); val = P["VAL"].rolling(60, min_periods=20).median()
r = np.log(C).diff()
rows = []
for s in C.columns:
    c = C.loc[d, s]
    if not np.isfinite(c) or not P["elig"].loc[d, s]: continue
    rows.append(dict(sym=s, name=nm(s)[:26], sector=industry(s), close=c, chg1=float(np.exp(r.loc[d, s]) - 1) if np.isfinite(r.loc[d, s]) else np.nan,
        r20=float(C.loc[d, s] / C[s].iloc[-21] - 1), ml=rk.get(s, np.nan), brk=bool(c >= hi55.loc[d, s] and c > sma200.loc[d, s]),
        hi55=hi55.loc[d, s], sma200=sma200.loc[d, s], gap_to_hi=float(hi55.loc[d, s] / c - 1), atr=ATR.loc[d, s], zc=F["zc"].loc[d, s], val_m=val.loc[d, s] / 1e6, div=bool(F["divmonth"].loc[d, s] == 1)))
D = pd.DataFrame(rows); D = D[D.val_m >= 3]
pd.set_option("display.width", 250); f = lambda X: X.round({"close": 2, "chg1": 3, "r20": 3, "ml": 3, "hi55": 2, "sma200": 2, "gap_to_hi": 3, "atr": 3, "zc": 2, "val_m": 1})
print("date", d.date(), "| market model", round(T["pm"], 4), "| liquid stocks", len(D))
print("\nTREND BREAKOUTS TODAY (close at 55-day high and above 200-day avg):"); print(f(D[D.brk].sort_values("ml", ascending=False)).to_string(index=False))
print("\nML TOP 12 (liquid):"); print(f(D.sort_values("ml", ascending=False).head(12)).to_string(index=False))
print("\nNEAR BREAKOUT (within 1 ATR of the 55-day high, above SMA200, ML >= 70%):")
near = D[(~D.brk) & (D.close > D.sma200) & ((D.hi55 - D.close) <= D.atr) & (D.ml >= .7)]; print(f(near.sort_values("ml", ascending=False)).to_string(index=False))
D.to_csv("cands_1014.csv", index=False)
