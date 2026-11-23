"""Plan A check: Market returned only, 10% positions, idle money at T-bill interest - volatility order vs ML order in the slots."""
exec(open("r67.py").read().split('ZB = {')[0])
def weights_r(books, rk):
    W = np.zeros((ND, NC))
    for T, w in books:
        Ts, _ = sleeve(T.reset_index(drop=True), rk, np.full(len(T), w), M, ND, slots=5)
        for r in Ts[Ts.taken].itertuples(): W[r.d1 - 1:max(r.ex - 1, r.d1), r.j] += w
    return pd.DataFrame(W, index=dates, columns=cols)
ERAS = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
def st(r, a, b):
    x = r.loc[a:b]; eq = (1 + x).cumprod(); cagr = eq.iloc[-1] ** (250 / len(x)) - 1; dd = -(eq / eq.cummax() - 1).min(); return f"{100 * cagr:+.1f}% DD {100 * dd:.1f}% Sh {x.mean() / x.std() * np.sqrt(250):.2f}"
for nm, rk in (("volatility order", VR), ("ML order", RANK)):
    r, inv = srun(PS, weights_r([(T_mr, .10)], rk)); print(f"{nm:18s} " + " | ".join(f"{e} {st(r, a, b)}" for e, (a, b) in ERAS.items()))
