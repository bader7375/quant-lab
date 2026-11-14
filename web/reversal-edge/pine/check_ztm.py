"""Python copy of z_touch_momentum.pine (Pine semantics: strict windows, the stock's own bars), checked against round 60's scanner values."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
S = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
def pine_stretch(c, clip=.25):
    r = np.log(c / c.shift(1)).clip(-clip, clip); sd = r.rolling(60).std(ddof=1)
    return sum(r.rolling(k).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
def pine_ztm(c, L):
    z = pine_stretch(c); zp = z.shift(1); ok = z.notna() & zp.notna()
    U = sum(k * ((ok & (z >= k) & (zp < k)).astype(float)).rolling(L).sum() for k in (1, 2, 3))
    D = sum(k * ((ok & (z <= -k) & (zp > -k)).astype(float)).rolling(L).sum() for k in (1, 2, 3))
    A = sum(k * ((z.notna() & (z >= k)).astype(float) - (z.notna() & (z <= -k)).astype(float)).rolling(L).sum() for k in (1, 2, 3)) / L
    ready = pd.Series(np.arange(len(c)) >= L + 120, index=c.index)
    net = (U - D).where(ready); bal = ((U - D) / (U + D)).where(U + D > 0, 0.0).where(ready); return net, bal, A.where(ready), z
def load(code):
    d = pd.read_csv(f"{S}/edge26/data/d/{code}.SR.csv", index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")]; return d[(d.close > 0) & (d.volume > 0)]   # TradingView has no bars on zero-volume holiday rows (the scanner drops them too)
Z = pd.read_parquet(f"{S}/r60/ztm60.parquet"); Z["sym"] = Z.sym.astype(str)
rows = []
for code in ["4004", "1302", "4009", "2222", "1120", "2010", "7010", "1180", "4322", "2280"]:
    c = load(code).adjclose; sc = Z[Z.sym.isin([code, code + ".SR"])].set_index("date")
    for L in (120, 250):
        net, bal, occ, _ = pine_ztm(c, L); a = pd.concat([net, sc[f"N{L}"]], axis=1, keys=["pine", "scan"]).dropna().tail(250)
        b = pd.concat([bal, sc[f"B{L}"]], axis=1, keys=["pine", "scan"]).dropna().tail(250); o = pd.concat([occ, sc[f"O{L}"]], axis=1, keys=["pine", "scan"]).dropna().tail(250)
        rows.append((code, L, len(a), f"{100 * (a.pine == a.scan).mean():.0f}%", float((a.pine - a.scan).abs().max()), float((b.pine - b.scan).abs().max()), float((o.pine - o.scan).abs().max()),
                     float(net.iloc[-1]), float(sc[f"N{L}"].dropna().iloc[-1])))
T = pd.DataFrame(rows, columns=["stock", "L", "days", "net equal", "max|diff| net", "max|diff| balance", "max|diff| time", "pine net now", "scanner net now"])
pd.set_option("display.width", 250); print("Last 250 sessions, Pine copy vs scanner panel:"); print(T.round(3).to_string(index=False))
