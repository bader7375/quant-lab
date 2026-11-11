"""Round 75 (PREREG.md): the two listed Saudi sukuk ETFs against the T-bill assumption the account tests use for idle money."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.environ["RE_WORK"]; sys.path.insert(0, os.path.join(WORK, "edge26")); import yf
out = os.path.join(WORK, "r75data"); os.makedirs(out, exist_ok=True); irx = pd.read_csv(os.path.join(WORK, "edge26/data/ext/IRX.csv"), index_col=0, parse_dates=True)["close"]; OUT = {}
for sym, nm in (("9404.SR", "Alinma short-maturity government sukuk ETF"), ("9403.SR", "Albilad sovereign sukuk ETF")):
    r = yf.daily(sym, out); d = pd.read_csv(os.path.join(out, sym + ".csv"), index_col=0, parse_dates=True); d = d[(d.adjclose > 0)]
    x = d.adjclose; yrs = (x.index[-1] - x.index[0]).days / 365.25; cagr = (x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1; dd = float(-(x / x.cummax() - 1).min())
    px = d.close; cagr_px = (px.iloc[-1] / px.iloc[0]) ** (1 / yrs) - 1; yr = x.groupby(x.index.year).last().pct_change().dropna()
    tb = irx.reindex(irx.index.union(x.index)).ffill().reindex(x.index) / 100 / 250; tbill = float((1 + tb.fillna(0)).prod() ** (1 / yrs) - 1); val = (d.volume * d.close); live = val[val > 0]
    big = float(x.pct_change().abs().max())
    OUT[sym] = dict(name=nm, first=str(x.index[0].date()), last=str(x.index[-1].date()), years=round(yrs, 1), total_return=float(cagr), price_only=float(cagr_px), tbill=tbill, dd=dd, worst_year=float(yr.min()) if len(yr) else None,
                    median_value=float(val.median()), days_traded=float((d.volume > 0).mean()), biggest_day=big)
    ok = cagr >= tbill - .005 and dd < .01 and val.median() >= 1e5
    print(f"{sym} {nm}: {x.index[0].date()} to {x.index[-1].date()} ({yrs:.1f} years) | total return {100 * cagr:+.2f}% a year (price only {100 * cagr_px:+.2f}%) against T-bill {100 * tbill:+.2f}% | worst drawdown {100 * dd:.1f}% | "
          f"worst calendar year {100 * yr.min():+.1f}% | median value traded SAR {val.median():,.0f} a day, traded on {100 * (d.volume > 0).mean():.0f}% of days | biggest one-day move {100 * big:.1f}% -> {'usable cash leg' if ok else 'NOT a usable cash leg by the plan'}")
json.dump(OUT, open(os.path.join(HERE, "r75_results.json"), "w"), indent=1)
