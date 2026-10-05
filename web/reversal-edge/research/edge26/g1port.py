import pandas as pd, numpy as np
from panel import nw_t
def g1_portfolio(oc, co, liqrank, th=-.03, maxn=5, min_liq=1/3, cost=0.004, side="gap"):
    """each morning: candidates = eligible stocks with open gap <= th and liquidity rank >= min_liq; take the maxn deepest gaps,
    equal capital, buy open, sell close. Day return = mean net trade return (0 when no trade)."""
    sig = (co <= th) & (liqrank >= min_liq) & oc.notna()
    out = pd.Series(0.0, oc.index); ntr = pd.Series(0, oc.index)
    for d in oc.index:
        s = sig.loc[d]
        if not s.any(): continue
        c = co.loc[d][s].nsmallest(maxn).index
        out[d] = oc.loc[d, c].mean() - cost; ntr[d] = len(c)
    return out, ntr
def stats(x, nm):
    yrs = len(x) / 250; eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1).min()
    return f"{nm:40s} CAGR {100*(eq.iloc[-1]**(1/yrs)-1):+6.1f}% | Sharpe {x.mean()/x.std()*np.sqrt(250):.2f} | maxDD {100*dd:.1f}% | NW t {nw_t(x):+.1f} | trade days {100*(x!=0).mean():.0f}%"
