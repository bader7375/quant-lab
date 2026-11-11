"""Round 71 part 2: no look-ahead. Every signal input is rebuilt on data cut at a past close and compared with the full-history value."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi; from engine import Book
B, PB = saudi.load(); P = PB.P; d = PB.dates; T_ = PB.T_; rng = np.random.default_rng(71); bad = 0; n_sig = 0
wk = d.to_period("W-THU"); wlast = pd.Series(d, index=d).groupby(wk).max(); week_end = np.array([d[t] == wlast.loc[wk[t]] for t in range(T_)])
SIGF = B.signals(); eq = lambda a, b: bool(np.allclose(np.nan_to_num(np.asarray(a, float), nan=-99), np.nan_to_num(np.asarray(b, float), nan=-99), atol=1e-9))
tests = sorted(rng.choice(np.arange(900, T_ - 5), 40, replace=False)); sig_days = np.where(SIGF.any(1))[0]; tests = sorted(set(tests) | set(rng.choice(sig_days[sig_days > 900], 20, replace=False)))
for t in tests:
    C = PB.C.iloc[:t + 1]; O = P["O"].iloc[:t + 1]; VAL = P["VAL"].iloc[:t + 1]
    elig = C.notna() & (C.notna().cumsum() >= 120) & (VAL.rolling(60, min_periods=20).median() >= 3e6)      # base._finish, on the cut data
    el = elig & (VAL.rolling(60, min_periods=20).median() >= 3e6)
    b = Book(C=C, O=O, elig=el, week="W-THU", pm=PB.pm.iloc[:t + 1], pct=PB.PCT.iloc[:t + 1], loss=PB.LOSS[:t + 1], ms_elig=elig)
    s = b.signals(week_complete=bool(week_end[t]))
    ok = dict(stretchZ=eq(b.ZC.iloc[-1].values, B.ZC.iloc[t].values), momentum=eq(b.MS[-1], B.MS[t]), volatility=eq(b.VOL[-1], B.VOL[t]), liquid=bool((b.EL[-1] == B.EL[t]).all()),
              first_touch=bool((b.ZFIRST[-1] == B.ZFIRST[t]).all()))
    if week_end[t]: ok["weekly_touch"] = bool((b.WFIRST[-1] == B.WFIRST[t]).all()); ok["signals"] = bool((s[-1] == SIGF[t]).all())
    else: ok["signals"] = bool((s[-1] == (SIGF[t] & ~B.WFIRST[t])).all()) and not B.WFIRST[t].any()     # mid-week rows carry no weekly touch in the full history either
    n_sig += int(SIGF[t].sum())
    if not all(ok.values()): bad += 1; print("MISMATCH", d[t].date(), ok)
print(f"{len(tests)} past closes checked ({int(week_end[tests].sum())} week-ends, {n_sig} signals on them): mismatches {bad}")
# ---- ranker features on cut data
os.chdir(os.path.join(saudi.work_dir(), "r27")); sys.path.insert(0, os.getcwd())
from feats27 import build
F = pd.read_pickle("F27y.pkl"); fbad = {}; cuts = sorted(rng.choice(np.arange(1500, T_ - 5), 5, replace=False))
for t in cuts:
    Pt = {k: (v.iloc[:t + 1] if isinstance(v, (pd.DataFrame, pd.Series)) and len(v) == T_ and k != "G" else v) for k, v in P.items()}
    Ft = build(Pt); nb = 0
    for k in F:
        a = Ft[k].iloc[-1].reindex(PB.cols).values.astype(float); b_ = F[k].reindex(index=d, columns=PB.cols).iloc[t].values.astype(float)
        if not np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(b_, nan=-99), atol=1e-7, rtol=1e-6): nb += 1; fbad.setdefault(k, []).append(str(d[t].date()))
    print(f"features at {d[t].date()}: {len(F)} rebuilt on cut data, different from the full build: {nb}")
print("features that differ on cut data:", fbad if fbad else "none")
print("ranker C (r27/wfC.py): the model for a quarter is trained on rows up to (h + 2) sessions before the quarter starts; target = open t+1 -> open t+h+1, so the last label ends before the quarter")
print("market model (r27/mkt27.py): the model for a year is trained on rows up to 22 sessions before the year; target = the next 20 sessions")
json.dump(dict(closes=len(tests), mismatches=bad, feature_cuts=[str(d[t].date()) for t in cuts], feature_diffs=fbad), open(os.path.join(HERE, "trunc71.json"), "w"), indent=1)
