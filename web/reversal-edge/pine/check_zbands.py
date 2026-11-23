"""Python copy of z_bands.pine (Pine semantics: strict windows, the stock's own bars, no zero-volume holiday rows),
checked two ways: (1) a close at or below the band <=> the Pine stretch Z at that close <= -2.62; (2) the band equals the
scanner's r27/zbands.py on the same closes; plus the next-session values the daily list shows."""
import sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
S = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"; sys.path.insert(0, f"{S}/r27")
from zbands import band_next
def pine_stretch(c, clip=.25):
    r = np.log(c / c.shift(1)).clip(-clip, clip); sd = r.rolling(60).std(ddof=1)
    return sum(r.rolling(k).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
def pine_band_next(c, lvl, clip=.25):
    r = np.log(c / c.shift(1)).clip(-clip, clip); sd = r.rolling(60).std(ddof=1)
    d = {k: sd.shift(k - 1) * np.sqrt(k) for k in (10, 20, 60)}
    a = sum(r.rolling(k - 1).sum() / d[k] for k in (10, 20, 60)) / 3; b = sum(1 / d[k] for k in (10, 20, 60)) / 3; x = (lvl - a) / b
    return (c * np.exp(x)).where(x.abs() <= clip)
def load(code):
    d = pd.read_csv(f"{S}/edge26/data/d/{code}.SR.csv", index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")]
    return d[(d.close > 0) & (d.volume > 0)].adjclose
scan = {r["sym"]: r for r in json.load(open(f"{S}/r27/today27.json"))["zscan"]}
for code in ["1302", "4004", "4009", "2222", "1120", "2010", "7010", "1180"]:
    c = load(code); z = pine_stretch(c); bn = pine_band_next(c, -2.62); b = bn.shift(1); m = b.notna() & z.notna()
    dis = int(((c <= b) != (z <= -2.62))[m].sum()); touch = (c <= b) & ~(c.shift(1) <= b.shift(1)); first = (z <= -2.62) & ~(z.shift(1) <= -2.62)
    tdis = int((touch != first)[m & m.shift(1, fill_value=False)].sum())
    sb = band_next(c, -2.62); mm = sb.notna() & bn.notna(); rel = float((sb[mm] / bn[mm] - 1).abs().max())
    s = scan.get(code, {}); print(f"{code}: {int(m.sum())} days | close<=band vs Z<=-2.62 disagree {dis} | touch marker vs first touch disagree {tdis} | vs scanner formula max rel diff {rel:.1e} | next session: pine {bn.iloc[-1]:.3f}, daily list {s.get('bd')}")
