"""Round 72: a price panel for one foreign market from the Yahoo files world.py downloaded, cleaned the same way for every market,
and the Fable Book built on it (price-only rule: no ML rank, no market model, no accounts; those exist only for Saudi)."""
import os, sys, glob, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
from engine import Book
WEEK = {"qatar": "W-THU", "dubai": "W-THU", "abudhabi": "W-THU", "kuwait": "W-THU", "egypt": "W-THU"}      # Sunday-Thursday markets; all others end the week on Friday
def panel(folder, min_rows=750, jump=np.log(1.6)):
    D = {}; cut = 0
    for f in glob.glob(os.path.join(folder, "*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")].sort_index(); d = d[(d.close > 0) & d.adjclose.notna() & (d.adjclose > 0)]
        if len(d) < min_rows: continue
        lr = np.log(d.adjclose).diff().abs(); big = lr[lr > jump]                 # a one-day move above 60%: a split or currency change Yahoo did not adjust
        if len(big): d = d.loc[big.index[-1]:].iloc[1:]; cut += 1                 # keep only the history after the last such jump
        if len(d) < min_rows: continue
        k = d.adjclose / d.close; D[os.path.basename(f)[:-4]] = pd.DataFrame({"o": d.open * k, "c": d.adjclose, "v": d.volume})
    if len(D) < 12: return None
    idx = sorted(set().union(*[x.index for x in D.values()])); C = pd.DataFrame({s: D[s].c for s in D}).reindex(idx); O = pd.DataFrame({s: D[s].o for s in D}).reindex(idx); V = pd.DataFrame({s: D[s].v for s in D}).reindex(idx)
    bad = (V <= 0) | V.isna() | C.isna()
    C = C.mask(bad); O = O.mask(bad); cnt = (~bad).sum(1); med = cnt.rolling(21, min_periods=1).median().shift(1).fillna(cnt)
    keep = ~((cnt < .3 * med) & (med >= 5)); C, O, bad = C.loc[keep], O.loc[keep], bad.loc[keep]       # holiday rows with almost no trading (backward-looking window)
    O = O.where((O / C - 1).abs() <= .25, C)
    traded = (~bad).astype(float).rolling(60, min_periods=40).mean() >= .8
    elig = C.notna() & (C.notna().cumsum() >= 250) & traded
    elig = elig & (elig.sum(1) >= 10).values[:, None]                              # market momentum needs a market: at least 10 eligible stocks that day
    liq = (V.loc[keep] * C).rolling(60, min_periods=20).median()                   # 60-session median value traded (local currency), for the market basket
    return dict(C=C, O=O, elig=elig, liq=liq, cut=cut, n=len(D))
def book(mk, root):
    P = panel(os.path.join(root, mk))
    if P is None: return None
    B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=WEEK.get(mk, "W-FRI")); B.meta = dict(market=mk, stocks=P["n"], cut=P["cut"]); return B
