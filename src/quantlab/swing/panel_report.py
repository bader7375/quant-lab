"""The multi-instrument report.

Ordered so the honest number comes first and the flattering ones come with their
caveats attached. Three rules govern every table here:

* nothing is tested on rows -- only on days, because a date contributes one
  observation no matter how many names traded on it;
* every headline t-statistic is shown next to what the run's own search would
  have produced from noise;
* per-instrument tables are labelled descriptive, because picking the best of
  fifty names is fifty more chances to be lucky.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _fmt(v, nd=3, pct=False):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    if pct:
        return f"{v:.1%}"
    return f"{v:,.{nd}f}" if isinstance(v, float) else str(v)


def _table(df, nd=4, index=True):
    if df is None or len(df) == 0:
        return "_(empty)_\n"
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: _fmt(v, nd))
    return d.to_markdown(index=index) + "\n"


def build_panel_report(res, ev, scan, importance, cfg, elapsed: float) -> str:
    o, v, base = ev["overall"], ev["verdict"], ev["base"]
    lo, hi = ev["ci"]
    port = ev["portfolio"]
    L = cfg.label
    u = res.universe

    out = []
    add = out.append
    add("# Multi-instrument swing research report\n")
    add(f"_{len(u.tickers)} instruments · {len(res.X):,} bars · "
        f"{res.X.index.min().date()} → {res.X.index.max().date()} · "
        f"{elapsed:.0f}s_\n")

    # ---------------------------------------------------------------- verdict
    add("## 0. The answer\n")
    survives = v["survives"]
    add(f"- **{'An edge survived the search.' if survives else 'No edge survived the search.'}** "
        f"{o['n_trades']:,} trades across {o['n_days']} trading days, "
        f"{o['mean_R']:+.4f}R per day, day-level t = {o['t']:+.2f}.")
    add(f"- The run evaluated **{v['trials']} configurations**. The best of that many "
        f"draws from pure noise would score t ≈ {v['expected_max_from_noise']:.2f}, so the "
        f"part the search cannot explain is **t = {v['t_deflated']:+.2f}**.")
    if not survives:
        add("- It is not called an edge because it fails: "
            + "; ".join(f"**{g}**" for g in v["failed_gates"]) + ".")
    add("")
    add("_All four gates must pass. Deflation alone is not enough: a result measured "
        "over sixteen trading days can clear it on noise, which is how an earlier "
        "version of this report announced an edge from 58 trades._\n")
    add(_table(pd.DataFrame([{"gate": k, "passed": ok} for k, ok in v["gates"].items()]),
               index=False))
    add(f"- 95% interval on R per day: **[{lo:+.4f}, {hi:+.4f}]**"
        f"{' — excludes zero.' if np.isfinite(lo) and lo > 0 else ' — includes zero.'}")
    add(f"- Unconditional benchmark (every candidate bar, same geometry): "
        f"{base['mean_R']:+.4f}R per day. The filter's excess is "
        f"{o['mean_R'] - base['mean_R']:+.4f}R per day.")
    add(f"- {o['share_days_positive']:.0%} of traded days were positive, "
        f"{o['trades_per_day']:.1f} trades on an average traded day.")
    add("")
    add("**Why day-level statistics.** Every date contributes one row per instrument, "
        "and one market factor drives most of any day's move. Testing those rows as "
        "independent observations is the fastest way to manufacture significance: on "
        "this very panel it turned a t of 1.3 into a t of 9.8. Every number above is "
        "computed on one observation per day.\n")

    # ------------------------------------------------------------- the search
    add("## 1. What the run searched\n")
    add(_table(res.counter.summary(), index=False))
    add(f"\nA t-statistic has to clear {v['expected_max_from_noise']:.2f} before it says "
        "anything that the search itself does not already explain.\n")

    # ---------------------------------------------------------------- universe
    add("## 2. Universe\n")
    s = u.summary()
    add(f"{len(s)} instruments loaded, {len(u.rejected)} rejected. "
        f"History {s['start'].min()} → {s['end'].max()}, "
        f"median {int(s['bars'].median()):,} bars each.\n")
    if u.rejected:
        add("Rejected:\n")
        for k, why in list(u.rejected.items())[:10]:
            add(f"- `{k}` — {why}")
        add("")
    add(_table(s.head(15), index=False))
    if len(s) > 15:
        add(f"\n…and {len(s)-15} more.\n")

    # ----------------------------------------------------------------- setup
    add("## 3. Trade construction\n")
    add(f"- Entry at the **{L.entry_mode.replace('_',' ')}**, stop `{L.sl_multiple:g} × "
        f"{L.risk_mode}`, target **{L.tp_multiple:g}R**, max hold **{L.lookahead} bars**, "
        f"ambiguous bars resolved as **{L.ambiguous_bar.replace('_',' ')}**.")
    add(f"- Round-trip cost **{cfg.decision.cost_bps:g} bps**, expressed in R "
        f"(a fixed spread is a heavier tax on a tight stop).")
    pr = res.primary
    add(f"- Primary rule **{pr.get('rule','none')}**"
        + (f" — fires on {pr['fires_on_share_of_bars']:.1%} of labelled bars "
           f"({pr['candidate_bars']:,} candidates)." if pr.get("rule") != "none" else
           " — every bar is a candidate."))
    add(f"- Selection score **{res.score}**, cut **{res.cut:.4f}**, chosen on "
        "out-of-fold training rows by day-level t.\n")

    # ------------------------------------------------------------ walk-forward
    add("## 4. Walk-forward, fold by fold\n")
    add(_table(res.fold_table, index=False))
    add("\nA result that lives in one fold has found nothing durable. Read the "
        "`days` column before the `t` column: a fold with nine traded days cannot "
        "produce a meaningful t at all.\n")

    if ev["by_year"]:
        add("### By calendar year\n")
        yr = pd.DataFrame([{"year": k, **{kk: vv for kk, vv in val.items()
                                          if kk in ("n_trades", "n_days", "mean_R", "t",
                                                    "share_days_positive")}}
                           for k, val in ev["by_year"].items()])
        add(_table(yr, index=False))

    # ------------------------------------------------------------------- cost
    add("\n## 5. Cost sensitivity\n")
    add(_table(ev["cost_curve"], index=False))
    add("\nThe breakeven spread is the number that decides whether this is a strategy "
        "or a backtest. If it is close to the cost you actually pay, it is not a strategy.\n")

    # -------------------------------------------------------------- portfolio
    add(f"## 6. Portfolio — at most {port.get('max_positions', '?')} "
        "positions at once\n")
    if port.get("n_trades", 0):
        add(_table(pd.DataFrame([{
            "trades": port["n_trades"], "names traded": port["names_traded"],
            "total return": port["total_return"], "CAGR": port["cagr"],
            "Sharpe": port["sharpe"], "max drawdown": port["max_drawdown"],
            "Calmar": port["calmar"], "expectancy R": port["expectancy_R"],
            "win rate": port["win_rate"],
        }]), index=False))
        add(f"\nRisk per position {port['risk_frac']:.0%} of equity. Signals cluster, so "
            "the cap is doing real work: without it the book would be most levered exactly "
            "when its positions were most correlated.\n")
    else:
        add("_No trades survived the position cap._\n")

    # ------------------------------------------------------------ per ticker
    add("## 7. Per instrument — descriptive, not a test\n")
    pt = ev["per_ticker"]
    add(f"{len(pt)} instruments traded; {(pt['mean_R'] > 0).mean():.0%} had positive mean R.\n")
    add(_table(pt.head(15)))
    add("\nPicking the best name from this table is choosing the best of "
        f"{len(pt)} draws. The spread here is what luck looks like across "
        "instruments, not a ranking of which to trade.\n")

    # ------------------------------------------------------------ importance
    add("## 8. What the model used\n")
    add(_table(importance, index=False))
    if "kind" in importance.columns:
        share = importance.groupby("kind")["gain"].sum()
        share = (share / share.sum()).sort_values(ascending=False)
        add("\nShare of top-feature gain by family: "
            + ", ".join(f"{k} {v:.0%}" for k, v in share.items()) + ".")
        add("\n`market-wide` features are identical across instruments on a given day. "
            "They can move the whole day's level but cannot rank one name against "
            "another — weight on them means the model is timing the market.\n")

    # ------------------------------------------------------------------ scan
    add("## 9. Latest scan\n")
    trade = scan[scan["decision"] == "TRADE"]
    add(f"{len(trade)} of {len(scan)} instruments are a TRADE on their most recent bar.\n")
    add(_table(scan.head(20), index=False))

    # --------------------------------------------------------------- caveats
    add("\n## 10. What would break this\n")
    for line in [
        "**Survivorship.** If the universe is today's index membership, everything "
        "delisted is missing and every long result is inflated. Point-in-time "
        "membership is the fix; nothing in this report can detect its absence.",
        "**Clustered signals.** Setups fire together across names, so the effective "
        "sample is far smaller than the trade count. That is why the statistics are "
        "day-level, and it is still optimistic if the days themselves cluster.",
        "**Costs are a flat spread.** No impact, no slippage against the open, no "
        "borrow, no capacity limit. Every one of these makes live results worse.",
        "**The search is counted, not eliminated.** Deflation is a correction, not a "
        "clean test. The only clean test is data this configuration has never seen.",
        "**Regime dependence.** A rule that profits from bounces will work in "
        "mean-reverting markets and fail in trending declines. Read the per-year table "
        "as a regime breakdown, not as a stability check.",
    ]:
        add(f"- {line}")
    add("")
    return "\n".join(out)
