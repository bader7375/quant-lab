"""Python copy of zswing_vwap_entry.pine (bar-by-bar state machine) checked against round 57's 5-minute entries, plus the setup-day logic."""
import os, sys, glob, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
S = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
exec(open(f"{S}/pinetest/port.py").read().split("# ---- scanner's own values")[0])          # pine_stretch, pine_first, load (daily csv)
def pine_day(b, start=(10, 30)):
    """b: one session's 5-minute bars (o,h,l,c,v). Returns (entry, how) exactly as the Pine state machine."""
    cv = (((b.h + b.l + b.c) / 3) * b.v.fillna(0)).cumsum(); vv = b.v.fillna(0).cumsum(); vw = (cv / vv.replace(0, np.nan)).values
    armed = False; n = len(b)
    for k in range(n):
        last = k == n - 1
        if armed: return float(b.o.iloc[k]), "VWAP reclaim"
        after = b.index[k].hour * 60 + b.index[k].minute >= start[0] * 60 + start[1]
        if after and b.c.iloc[k] > vw[k] and not last: armed = True
        elif last: return float(b.c.iloc[k]), "close (no reclaim)"
    return np.nan, ""
# 1. entries vs round 57 (same 76 signal days)
sys.path.insert(0, f"{S}/r48"); cwd = os.getcwd(); from zswing import *; os.chdir(cwd)
first_ = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
broad = ((first_(zc, -2.62) | to_daily(first_(zw_b, -2.08))) & bc(MS <= -1.18).astype(bool)).values & EL
F5 = {os.path.basename(f)[:-4]: pd.read_csv(f, index_col=0, parse_dates=True) for f in glob.glob(f"{S}/r56/data/sa_5m/*.csv")}
rows = []
for i, j in zip(*np.where(broad)):
    d0 = dates[i]
    if d0 < pd.Timestamp("2026-08-13") or i + 5 >= len(dates): continue
    s = cols[j] if cols[j] in F5 else (cols[j] + ".SR" if cols[j] + ".SR" in F5 else None)
    if s is None: continue
    d = F5[s]; d = d[d.c > 0]; b = d[d.index.normalize() == dates[i + 1]]
    if len(b) < 20: continue
    # round 57's own computation (copied)
    tp = (b.h + b.l + b.c) / 3; vw = (tp * b.v.fillna(0)).cumsum() / b.v.fillna(0).cumsum().replace(0, np.nan)
    k = np.where((b.c.values > vw.values) & (b.index.time >= pd.Timestamp("10:30").time()))[0]
    E5 = b.o.iloc[k[0] + 1] if len(k) and k[0] + 1 < len(b) else b.c.iloc[-1]
    e, how = pine_day(b); rows.append((d0, cols[j], float(E5), e, how, float(b.o.iloc[0])))
V = pd.DataFrame(rows, columns=["date", "sym", "r57", "pine", "how", "open"])
print(f"1. Entry price, Pine logic vs round 57, {len(V)} setup days: identical on {int(np.isclose(V.r57, V.pine).sum())}; reclaim on {int((V.how == 'VWAP reclaim').sum())}, no reclaim (bought at the close) on {int((V.how != 'VWAP reclaim').sum())}")
print(f"   average entry vs the open: {100 * (V.pine / V.open - 1).mean():+.2f}% (median {100 * (V.pine / V.open - 1).median():+.2f}%)")
# 2. setup days: Pine's daily/weekly touch on TradingView-style bars vs the scanner's signals (window not applied on either side)
scan = ((first_(zc, -2.62) | to_daily(first_(zw_b, -2.08))).values & EL)
agree = tot = only_s = only_p = 0
for j, c in enumerate(cols):
    try: d = load(c.replace(".SR", ""))
    except Exception: continue
    d = d[d.volume > 0]; cl = d.adjclose
    zd = pine_stretch(cl, .25); td = pine_first(zd, -2.62)
    wk = cl.index.to_period("W-THU"); cw = cl.groupby(wk).last(); cw.index = cl.groupby(wk).apply(lambda x: x.index[-1]).values
    tw = pine_first(pine_stretch(cw, .6), -2.08).reindex(cl.index).fillna(False)
    p = (td | tw).loc["2024-01-01":]; s_ = pd.Series(scan[:, j], index=dates).reindex(p.index).fillna(False)
    m = EL[:, j][np.searchsorted(dates.values, p.index.values).clip(0, len(dates) - 1)]
    p, s_ = p[m], s_[m]; tot += int((p | s_).sum()); agree += int((p & s_).sum()); only_s += int((s_ & ~p).sum()); only_p += int((p & ~s_).sum())
print(f"2. First-touch days 2024-26 (liquid stocks): {tot} by either; both {agree} ({100 * agree / max(tot, 1):.0f}%); scanner only {only_s}; Pine only {only_p}")
