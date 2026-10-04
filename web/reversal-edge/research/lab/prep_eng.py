"""Write split/dividend-adjusted OHLCV files (Date,Open,High,Low,Close,Volume) for engine runs.
dev: 6 long series + 87 StockNet stocks. lock: KDD17 (2007-2016), CMIN-US (2018-2021), CMIN-CN (2018-2021) - fresh, untouched."""
import pandas as pd, numpy as np
from pathlib import Path
S = Path(__file__).resolve().parent.parent; OUT = S / "eng"
def clean(df):
    df = df.sort_index(); df = df[~df.index.duplicated()]
    df = df[(df.close > 0) & (df.open > 0) & (df.high > 0) & (df.low > 0)]
    df["high"] = df[["high", "open", "close"]].max(axis=1); df["low"] = df[["low", "open", "close"]].min(axis=1)
    return df
def adj(df, adjcol="adjclose"):
    f = df[adjcol] / df["close"]
    for c in ["open", "high", "low"]: df[c] = df[c] * f
    df["close"] = df[adjcol]; df["volume"] = df["volume"] / f   # share volume in adjusted units
    return df
def write(df, folder, name):
    (OUT / folder).mkdir(parents=True, exist_ok=True)
    d = df[["open", "high", "low", "close", "volume"]].copy(); d.index = d.index.strftime("%Y-%m-%d"); d.index.name = "Date"
    d.columns = ["Open", "High", "Low", "Close", "Volume"]; d.round(6).to_csv(OUT / folder / f"{name}.csv")
def std(path):
    df = pd.read_csv(path); df.columns = [c.strip().lower().replace(" ", "").replace("_", "") for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]); return df.set_index("date")
LONG = ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]
n87 = []
for p in sorted((S / "rdata").glob("*.csv")):
    k = p.stem
    if k == "VIX": continue
    df = std(p)
    if k.endswith("_long"): write(clean(df), "dev_long", k.replace("_long", ""))
    else: write(clean(adj(df)), "dev87", k); n87.append(k)
# lockbox
excl = set(n87) | set(LONG)
kd = S / "fresh/adv/data/kdd17/price_long_50"; nk = []
for p in sorted(kd.glob("*.csv")):
    k = p.stem
    if k in LONG: continue
    df = pd.read_csv(p); df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    if "original_open" in df: df = df.drop(columns=["open"]).rename(columns={"original_open": "open"})
    df["date"] = pd.to_datetime(df["date"], format="mixed"); df = df.set_index("date")[["open", "high", "low", "close", "volume", "adjclose"]].astype(float)
    if k in excl: df = df[df.index < "2012-09-01"]   # same stock is in the 87 from 2012-09: keep only the earlier, unseen years
    write(clean(adj(df)), "lock_kdd17", k); nk.append(k)
nu = []
for p in sorted((S / "fresh/cmin/CMIN-US/price/raw").glob("*.csv")):
    k = p.stem.upper()
    if k in LONG: continue
    df = std(p)[["open", "high", "low", "close", "volume", "adjclose"]].astype(float); write(clean(adj(df)), "lock_cminus", k); nu.append(k)
nc = []
for p in sorted((S / "fresh/cmin/CMIN-CN/price/raw").glob("*.csv")):
    df = std(p)[["open", "high", "low", "close", "volume", "adjclose"]].astype(float); df = clean(adj(df))
    if len(df) < 500: continue
    write(df, "lock_cmincn", p.stem.replace(".", "_").upper()); nc.append(p.stem)
print("dev87", len(n87), "| kdd17", len(nk), nk, "| cmin-us", len(nu), "| cmin-cn", len(nc))
