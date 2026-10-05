from lib import *
P = {s: load(s) for s in syms()}
def t(x, h=1): x = pd.Series(np.asarray(x, float)).dropna(); return x.mean() / x.std() * np.sqrt(len(x) / max(1, h)) if len(x) > 2 and x.std() > 0 else np.nan
liq = pd.Series({s: META[s]["value_med"] for s in P}); q = pd.qcut(liq, 3, labels=["low", "mid", "high"])
rows = []
for s, d in P.items():
    c, o = d.Close, d.Open; r = c.pct_change()
    # tradable versions: after a limit-up close, BUY the NEXT OPEN; hold to that close (1 day) or 5 closes; and the open gap itself
    rows.append(pd.DataFrame({"s": s, "liq": q[s], "r": r, "gap_next": o.shift(-1) / c - 1, "o2c_next": c.shift(-1) / o.shift(-1) - 1,
                              "o2c5": c.shift(-5) / o.shift(-1) - 1, "gap": o / c.shift() - 1, "intra": c / o - 1, "vol": d.Volume}).loc["2004":])
A = pd.concat(rows).sort_index(); cost = 0.001
print("LIMIT-UP CONTINUATION, as a trade: you cannot buy at a locked limit close, so buy the NEXT OPEN")
for nm, m in (("limit up", A.r >= .095), ("limit down (for reference)", A.r <= -.095)):
    for lq in ("low", "mid", "high", "all"):
        x = A[m] if lq == "all" else A[m & (A.liq == lq)]
        for per, a, b in (("2004-12", "2004", "2013"), ("2013-20", "2013", "2021")):
            y = x.loc[a:b]
            if len(y) < 30: continue
            print(f"  {nm:26s} liq {lq:4s} {per}: n {len(y):5d} | overnight gap next morning {100*y.gap_next.mean():+.2f}% | buy next open -> next close {100*(y.o2c_next.mean()-cost):+.2f}% (t {t(y.o2c_next):+.1f}) | -> 5th close {100*(y.o2c5.mean()-cost):+.2f}% (t {t(y.o2c5,5):+.1f})")
print("\nGAP-DOWN OPEN (< -2%), buy at the open, sell at the close, by liquidity and period (before costs; normal day open->close shown)")
for lq in ("low", "mid", "high"):
    for per, a, b in (("2004-12", "2004", "2013"), ("2013-20", "2013", "2021")):
        x = A[(A.liq == lq)].loc[a:b]; g = x[x.gap < -.02]; g2 = x[x.gap > .02]
        print(f"  liq {lq:4s} {per}: gap-down n {len(g):5d} open->close {100*g.intra.mean():+.2f}% (t {t(g.intra):+.1f}) | gap-up n {len(g2):5d} open->close {100*g2.intra.mean():+.2f}% | normal {100*x.intra.mean():+.2f}% | share of days open==prev close {100*(x.gap.abs()<1e-9).mean():.0f}%")
