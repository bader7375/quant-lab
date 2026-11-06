"""Python copy of stretch_z.pine (Pine semantics: strict window lengths, the stock's own bars), checked against the scanner."""
import os, sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
S = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
def pine_stretch(c, clip):
    r = np.log(c / c.shift(1)).clip(-clip, clip); sd = r.rolling(60).std(ddof=1)
    return sum(r.rolling(k).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
def pine_first(z, lvl): return (z <= lvl) & ~(z.shift(1) <= lvl)
def load(code):
    d = pd.read_csv(f"{S}/edge26/data/d/{code}.SR.csv", index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")]
    return d[d.close > 0]
# ---- scanner's own values (same code as daily/top3.py and r27/zfam.py, on the scanner panel)
sys.path.insert(0, f"{S}/r28"); sys.path.insert(0, f"{S}/r27"); os.chdir(f"{S}/r27")
from core import P, C
r = np.log(C).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
ZC = sum(r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
wk = C.index.to_period("W-THU"); we = pd.Series(C.index, index=C.index).groupby(wk).max(); Cw = C.groupby(wk).last(); Cw.index = we.reindex(Cw.index).values
rw = np.log(Cw).diff().clip(-.6, .6); sdw = rw.rolling(60, min_periods=40).std()
ZW = sum(rw.rolling(k, min_periods=int(.8 * k)).sum() / (sdw.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
print("Scanner panel last date:", C.index[-1].date())
rows = []
for code in ["4004", "1302", "4009", "2222", "1120", "2010", "7010", "1180", "4322", "2280"]:
    col = code + ".SR" if code + ".SR" in C.columns else code
    if col not in C.columns: print("missing", code); continue
    d = load(code); c = d.adjclose
    zd = pine_stretch(c, .25)
    cw = c.groupby(c.index.to_period("W-THU")).last(); cw.index = c.groupby(c.index.to_period("W-THU")).apply(lambda x: x.index[-1]).values
    zw = pine_stretch(cw, .6)
    a = pd.concat([zd, ZC[col]], axis=1, keys=["pine", "scan"]).dropna(); b = pd.concat([zw, ZW[col]], axis=1, keys=["pine", "scan"]).dropna()
    rows.append((code, len(a), float((a.pine - a.scan).abs().max()), float((a.pine - a.scan).abs().tail(250).max()), float(zd.iloc[-1]), float(ZC[col].iloc[-1]),
                 len(b), float((b.pine - b.scan).abs().tail(52).max()), float(zw.iloc[-1]), float(ZW[col].iloc[-1]), str(cw.index[-1].date())))
T = pd.DataFrame(rows, columns=["stock", "days", "max|diff| all", "max|diff| last 250", "pine daily now", "scanner daily now", "weeks", "max|diff| last 52 wk", "pine weekly now", "scanner weekly now", "last week end"])
pd.set_option("display.width", 250); print(T.round(4).to_string(index=False))
# ---- the scanner's printed numbers
d4004 = pine_stretch(load("4004").adjclose, .25); print("\n4004 daily Z on 2026-11-03 (scanner printed -3.02):", round(float(d4004.loc["2026-11-03"]), 2))
for code, printed in (("4004", -2.44), ("1302", -2.30), ("4009", -2.13)):
    c = load(code).adjclose; cw = c.groupby(c.index.to_period("W-THU")).last(); zw = pine_stretch(cw, .6)
    print(f"{code} weekly Z for the week ending Thu 2026-11-05 (scanner printed {printed}): {zw.iloc[-1]:.2f}; previous week {zw.iloc[-2]:.2f}; first touch of -2.08: {bool(pine_first(zw, -2.08).iloc[-1])}")
# ---- markers on the daily chart (bar after a daily first touch; first bar of the week after a weekly first touch)
for code in ("4004", "1302", "4009"):
    c = load(code).adjclose; zd = pine_stretch(c, .25); fd = pine_first(zd, -2.62)
    mk = c.index[fd.shift(1, fill_value=False).values]
    print(f"{code} daily 'D' entry markers since 2026-09-01: {[str(x.date()) for x in mk if x >= pd.Timestamp('2026-09-01')]}")
# ---- raw (split-only) close vs dividend-adjusted close, as TradingView shows by default
c_raw = load("4004").close; c_adj = load("4004").adjclose
print("\n4004 daily Z now, unadjusted close:", round(float(pine_stretch(c_raw, .25).iloc[-1]), 3), "| dividend-adjusted:", round(float(pine_stretch(c_adj, .25).iloc[-1]), 3))
