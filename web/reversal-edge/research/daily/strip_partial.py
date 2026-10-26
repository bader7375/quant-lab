"""Drop today's still-forming daily candle (Yahoo returns intraday bars during a session): Saudi files before 15:45 Riyadh on a trading day,
US ETF/index/large-cap files from New York pre-market to the close. Keeps the pipeline on completed closes only."""
import os, glob, datetime as dt, pandas as pd
from zoneinfo import ZoneInfo
H = os.path.dirname(os.path.abspath(__file__)); E = os.path.join(H, "../edge26/data")
def strip(files, today):
    n = 0
    for f in files:
        d = pd.read_csv(f)
        if len(d) and str(d.date.iloc[-1]) == today: d.iloc[:-1].to_csv(f, index=False); n += 1
    return n
r = dt.datetime.now(ZoneInfo("Asia/Riyadh"))
if r.weekday() in (6, 0, 1, 2, 3) and r.time() < dt.time(15, 45):
    print("Saudi partial candles removed:", strip(glob.glob(f"{E}/d/*.SR.csv"), r.date().isoformat()))
ny = dt.datetime.now(ZoneInfo("America/New_York"))
if ny.weekday() < 5 and dt.time(4, 0) <= ny.time() < dt.time(16, 30):   # pre-market through the close (the evening Saudi run lands in it)
    print("US partial candles removed:", strip([f"{E}/idx/SPY.csv", f"{E}/idx/QQQ.csv"] + glob.glob(f"{E}/ext/*.csv") + glob.glob(f"{E}/us100/*.csv"), ny.date().isoformat()))
