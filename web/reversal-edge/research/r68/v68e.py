"""Round 68 check 5 (look-ahead): recompute every signal input on data cut at a past close and compare with the full-history value for that day.
A formula that peeks ahead gives a different number once the future rows are removed."""
import os, sys, numpy as np, pandas as pd
H68 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H68); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB, opt7
os.chdir(H68); P = PB.P; C = PB.C; d = PB.dates; rng = np.random.default_rng(68); bad = 0
tests = sorted(rng.choice(np.arange(900, PB.T_ - 5), 40, replace=False))
for t in tests:
    Ct = C.iloc[:t + 1]; el = P["elig"].iloc[:t + 1]; VAL = P["VAL"].iloc[:t + 1]
    r = np.log(Ct).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    zc = sum(r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
    mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std(); ms = (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).iloc[-1]
    vol = r.rolling(60, min_periods=40).std().iloc[-1].values; gate = opt7.market_turn(Ct, VAL, el).gate.iloc[-1]
    eq = lambda a, b: np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(b, nan=-99), atol=1e-9)
    ok = dict(stretchZ=eq(zc.iloc[-1].values, PB.ZC.iloc[t].values), momentum=eq(ms, PB.MS[t]), volatility=eq(vol, PB.VOL[t]), turn_window=bool(gate) == bool(PB.GATE[t]),
              liquid=bool((el.iloc[-1].values & (VAL.rolling(60, min_periods=20).median().iloc[-1].values >= 3e6) == PB.EL[t]).all()))
    if d[t] == pd.Series(d, index=d).groupby(d.to_period("W-THU")).max().loc[d[t].to_period("W-THU")]:     # a week's last session: the weekly bar is complete
        wk = Ct.index.to_period("W-THU"); Cw = Ct.groupby(wk).last(); zw = PB._zc_bars(Cw).iloc[-1].reindex(PB.cols).values; ok["weeklyZ"] = eq(zw, PB.ZWV[t])
    if not all(ok.values()): bad += 1; print("MISMATCH", d[t].date(), ok)
print(f"{len(tests)} random past closes checked (2013-2026): mismatches {bad}")
# the ranker and the market model: training cut-offs (read from the code)
print("ranker C: a quarter's model is trained on rows up to (h + 2) sessions before the quarter, target = open t+1 -> open t+h+1, so the last label ends before the quarter starts")
print("market model: a year's model is trained on rows up to 22 sessions before the year, target = next 20 sessions")
p = pd.read_parquet(os.path.join(SP, "r27/preds/C.parquet")); print("walk-forward predictions from", p.date.min().date(), "to", p.date.max().date(), "| last date matches the panel:", p.date.max() == d[-1])
