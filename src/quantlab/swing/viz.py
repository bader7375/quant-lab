"""Charts.

A candlestick chart that a trader recognises, plus the diagnostics that decide
whether the signals on it should be believed. Rendered with matplotlib only, so
the output is a file rather than a notebook dependency.

Colour convention throughout: green marks a high-probability long signal that
the system would have taken, red marks a taken signal that ended at its stop,
grey marks bars where it stood aside. Nothing is coloured by *prediction* alone
-- outcome colouring on the chart is deliberate, because a chart of confident
predictions with the outcomes hidden is a sales document, not a diagnostic.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BG = "#12161c"
FG = "#d6dae0"
GRID = "#232a33"
UP = "#26a69a"
DOWN = "#ef5350"
ACCENT = "#5b9bd5"
WARN = "#f0a202"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": FG, "axes.labelcolor": FG, "xtick.color": FG, "ytick.color": FG,
    "axes.edgecolor": GRID, "grid.color": GRID, "font.size": 9,
    "axes.titlesize": 11, "axes.titleweight": "bold", "legend.framealpha": 0.15,
})


def _style(ax, title: str = "") -> None:
    ax.grid(True, alpha=0.35, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_alpha(0.4)
    if title:
        ax.set_title(title, loc="left")


def candlestick(ax, df: pd.DataFrame) -> None:
    """Draw OHLC candles with real bodies and wicks."""
    x = mdates.date2num(df.index.to_pydatetime())
    width = 0.62 * (np.median(np.diff(x)) if len(x) > 1 else 1.0)
    for xi, (_, row) in zip(x, df.iterrows()):
        up = row["close"] >= row["open"]
        colour = UP if up else DOWN
        ax.vlines(xi, row["low"], row["high"], color=colour, linewidth=0.9, alpha=0.95)
        lo = min(row["open"], row["close"])
        height = max(abs(row["close"] - row["open"]), (row["high"] - row["low"]) * 0.002)
        ax.add_patch(Rectangle((xi - width / 2, lo), width, height,
                               facecolor=colour, edgecolor=colour, linewidth=0.6,
                               alpha=0.95 if up else 0.9))
    ax.xaxis_date()


def price_chart(df: pd.DataFrame, features: pd.DataFrame, pred: pd.DataFrame,
                signal, out: Path, bars: int = 240, symbol: str = "") -> Path:
    """The main chart: candles, VWAP, bands, taken signals, and the live setup."""
    sub = df.iloc[-bars:]
    feats = features.reindex(sub.index)
    p = pred.reindex(sub.index)

    fig, axes = plt.subplots(
        3, 1, figsize=(15, 10), sharex=True,
        gridspec_kw={"height_ratios": [3.0, 0.8, 1.0], "hspace": 0.08},
    )
    ax = axes[0]
    candlestick(ax, sub)

    mid = sub["close"].rolling(20, min_periods=5).mean()
    sd = sub["close"].rolling(20, min_periods=5).std(ddof=0)
    ax.plot(sub.index, mid, color=ACCENT, lw=1.0, alpha=0.8, label="BB mid (20)")
    ax.plot(sub.index, mid + 2 * sd, color=ACCENT, lw=0.8, alpha=0.45)
    ax.plot(sub.index, mid - 2 * sd, color=ACCENT, lw=0.8, alpha=0.45)
    ax.fill_between(sub.index, mid - 2 * sd, mid + 2 * sd, color=ACCENT, alpha=0.06)

    tp = ((sub["high"] + sub["low"] + sub["close"]) / 3 * sub["volume"])
    vwap = tp.rolling(20, min_periods=5).sum() / sub["volume"].rolling(20, min_periods=5).sum()
    ax.plot(sub.index, vwap, color=WARN, lw=1.2, alpha=0.9, label="VWAP (20)")

    atr = feats.get("atrp_14")
    if atr is not None:
        band = sub["close"] * atr
        ax.plot(sub.index, sub["close"] + 2 * band, color="#8f98a3", lw=0.7,
                ls="--", alpha=0.6, label="±2 ATR channel")
        ax.plot(sub.index, sub["close"] - 2 * band, color="#8f98a3", lw=0.7, ls="--", alpha=0.6)

    if "trade" in p.columns:
        taken = p[p["trade"].fillna(False)]
        won = taken[taken["y"] == 2]
        lost = taken[taken["y"] == 0]
        flat = taken[taken["y"] == 1]
        ax.scatter(won.index, sub.loc[won.index, "low"] * 0.975, marker="^", s=70,
                   color=UP, edgecolor="white", linewidth=0.4, zorder=5,
                   label=f"signal → target ({len(won)})")
        ax.scatter(lost.index, sub.loc[lost.index, "low"] * 0.975, marker="v", s=70,
                   color=DOWN, edgecolor="white", linewidth=0.4, zorder=5,
                   label=f"signal → stop ({len(lost)})")
        ax.scatter(flat.index, sub.loc[flat.index, "low"] * 0.975, marker="s", s=36,
                   color="#8f98a3", edgecolor="white", linewidth=0.3, zorder=5,
                   label=f"signal → time exit ({len(flat)})")

    if signal is not None:
        for level, colour, name in ((signal.target, UP, "target"),
                                    (signal.entry_reference, FG, "entry ref"),
                                    (signal.stop, DOWN, "stop")):
            ax.axhline(level, color=colour, ls=":", lw=1.1, alpha=0.8)
            ax.annotate(f"{name} {level:,.2f}", xy=(sub.index[-1], level),
                        xytext=(6, 0), textcoords="offset points", color=colour,
                        va="center", fontsize=8, fontweight="bold")
        ax.set_title(
            f"{symbol} — last {bars} bars · live setup: P(target)={signal.p_tp:.1%} "
            f"P(stop)={signal.p_sl:.1%} · {signal.decision} · regime: {signal.regime_name}",
            loc="left",
        )
    _style(ax)
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    ax.set_ylabel("price")

    axv = axes[1]
    colours = np.where(sub["close"] >= sub["open"], UP, DOWN)
    axv.bar(sub.index, sub["volume"], color=colours, alpha=0.55, width=0.8)
    axv.plot(sub.index, sub["volume"].rolling(20, min_periods=5).mean(),
             color=WARN, lw=1.0, alpha=0.8)
    _style(axv)
    axv.set_ylabel("volume")

    axp = axes[2]
    if "p_tp" in p.columns and p["p_tp"].notna().any():
        axp.plot(p.index, p["p_tp"], color=UP, lw=1.2, label="P(target before stop)")
        axp.plot(p.index, p["p_sl"], color=DOWN, lw=1.0, alpha=0.8, label="P(stop first)")
        thr = float(p["threshold"].dropna().iloc[-1]) if p["threshold"].notna().any() else np.nan
        if np.isfinite(thr):
            axp.axhline(thr, color=WARN, ls="--", lw=1.0, alpha=0.9,
                        label=f"trade threshold {thr:.2f}")
        axp.fill_between(p.index, 0, 1, where=p["trade"].fillna(False),
                         color=UP, alpha=0.10, transform=axp.get_xaxis_transform())
    axp.set_ylim(0, 1)
    axp.set_ylabel("probability")
    _style(axp)
    axp.legend(loc="upper left", ncol=3, fontsize=8)
    axp.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def equity_chart(bt: dict, bh: dict, out: Path) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1], "hspace": 0.1})
    eq = bt.get("equity")
    if eq is not None:
        axes[0].plot(eq.index, eq.to_numpy(), color=UP, lw=1.6,
                     label=f"strategy ({bt['risk_frac']:.0%} risk/trade)")
    if bh.get("equity") is not None:
        axes[0].plot(bh["equity"].index, bh["equity"].to_numpy(), color="#8f98a3",
                     lw=1.2, alpha=0.8, label="buy & hold")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("equity (log)")
    _style(axes[0], "Walk-forward equity — out-of-sample only")
    axes[0].legend(loc="upper left")

    dd = bt.get("drawdown")
    if dd is not None:
        axes[1].fill_between(dd.index, dd.to_numpy(), 0, color=DOWN, alpha=0.5)
    if bh.get("equity") is not None:
        bh_dd = bh["equity"] / bh["equity"].cummax() - 1
        axes[1].plot(bh_dd.index, bh_dd.to_numpy(), color="#8f98a3", lw=0.9,
                     alpha=0.8, label="buy & hold")
        axes[1].legend(loc="lower left", fontsize=8)
    axes[1].set_ylabel("drawdown")
    _style(axes[1])
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def calibration_chart(cal: dict, out: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    rel = cal.get("reliability", [])
    if rel:
        pred = [r[0] for r in rel]
        obs = [r[1] for r in rel]
        cnt = [r[2] for r in rel]
        axes[0].plot([0, 1], [0, 1], color="#8f98a3", ls="--", lw=1)
        axes[0].plot(pred, obs, "o-", color=ACCENT, lw=1.6, ms=6)
        for x, yv, c in zip(pred, obs, cnt):
            axes[0].annotate(f"n={c}", (x, yv), textcoords="offset points",
                             xytext=(0, 7), fontsize=7, ha="center", color=FG)
        axes[0].axhline(cal["base_rate"], color=WARN, ls=":", lw=1,
                        label=f"base rate {cal['base_rate']:.3f}")
        axes[0].legend(fontsize=8)
    axes[0].set_xlabel("predicted P(target)")
    axes[0].set_ylabel("observed frequency")
    _style(axes[0], f"Reliability — ECE {cal.get('ece', float('nan')):.4f}, "
                    f"Brier skill {cal.get('brier_skill', float('nan')):+.4f}")

    if rel:
        axes[1].bar(range(len(rel)), [r[2] for r in rel], color=ACCENT, alpha=0.7)
        axes[1].set_xlabel("probability decile")
        axes[1].set_ylabel("bars")
    _style(axes[1], "Sample size behind each point")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def importance_chart(importance: pd.DataFrame, ranking: pd.DataFrame, out: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    if not importance.empty:
        d = importance.head(18).iloc[::-1]
        axes[0].barh(d["feature"], d["mean_abs_shap"], color=ACCENT, alpha=0.85)
    _style(axes[0], "SHAP importance — boosted tabular engine (final fit)")
    axes[0].set_xlabel("mean |SHAP|")

    if ranking is not None and not ranking.empty:
        d = ranking.head(18).iloc[::-1]
        axes[1].barh(d.index, d["mutual_info"], color=UP, alpha=0.8, label="mutual information")
        ax2 = axes[1].twiny()
        ax2.plot(d["lgbm_gain"], d.index, "o", color=WARN, ms=5, label="LightGBM gain")
        ax2.set_xlabel("LightGBM gain", color=WARN)
        ax2.tick_params(colors=WARN)
    _style(axes[1], "Selection ranking (training block)")
    axes[1].set_xlabel("mutual information")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def agreement_chart(pred: pd.DataFrame, engines: list[str], out: Path) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                             gridspec_kw={"hspace": 0.12})
    cols = [f"p_tp_{e}" for e in engines if f"p_tp_{e}" in pred.columns]
    for col in cols:
        axes[0].plot(pred.index, pred[col].rolling(21, min_periods=5).mean(),
                     lw=0.9, alpha=0.75, label=col.replace("p_tp_", ""))
    axes[0].plot(pred.index, pred["p_tp"].rolling(21, min_periods=5).mean(),
                 color="white", lw=1.8, label="meta")
    axes[0].set_ylabel("P(target), 21-bar mean")
    _style(axes[0], "Where the engines agree, and where they do not")
    axes[0].legend(ncol=6, fontsize=7, loc="upper left")

    axes[1].plot(pred.index, pred["ens_tp_std"], color=WARN, lw=0.8, alpha=0.85)
    axes[1].set_ylabel("dispersion of P(target)")
    _style(axes[1], "Disagreement between engines (higher = less consensus)")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def regime_chart(df: pd.DataFrame, pred: pd.DataFrame, out: Path) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1], "hspace": 0.1})
    sub = df.reindex(pred.index)
    axes[0].plot(sub.index, sub["close"], color="#8f98a3", lw=0.8, alpha=0.7)
    palette = ["#26a69a", "#ef5350", "#5b9bd5", "#f0a202", "#ab47bc", "#26c6da"]
    for code, grp in pred.groupby("regime"):
        name = grp["regime_name"].iloc[0]
        axes[0].scatter(grp.index, sub.reindex(grp.index)["close"], s=7,
                        color=palette[int(code) % len(palette)], alpha=0.85, label=name)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("close (log)")
    _style(axes[0], "Regime assignment over the out-of-sample period")
    axes[0].legend(fontsize=8, ncol=3, loc="upper left", markerscale=2)

    perf = pred.groupby("regime_name")["ret_R_net"].mean().sort_values()
    axes[1].barh(perf.index, perf.to_numpy(),
                 color=[UP if v > 0 else DOWN for v in perf.to_numpy()], alpha=0.85)
    axes[1].axvline(0, color=FG, lw=0.8)
    axes[1].set_xlabel("mean net R per bar (all bars, not only taken)")
    _style(axes[1], "Unconditional expectancy by regime")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def pattern_chart(table: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6.5))
    if table.empty or "oos_p_tp" not in table.columns:
        ax.text(0.5, 0.5, "no patterns survived", ha="center", color=FG)
        _style(ax)
        fig.savefig(out, dpi=130, bbox_inches="tight")
        plt.close(fig)
        return out
    d = table.dropna(subset=["oos_p_tp"]).copy()
    d = d[d["oos_n"] >= 8]
    ax.scatter(d["p_shrunk"], d["oos_p_tp"], s=np.clip(d["n"] / 3, 12, 160),
               c=d["lift"], cmap="viridis", alpha=0.85, edgecolor="white", linewidth=0.3)
    lims = [min(0.05, d["p_shrunk"].min(), d["oos_p_tp"].min()),
            max(d["p_shrunk"].max(), d["oos_p_tp"].max()) + 0.05]
    ax.plot(lims, lims, color="#8f98a3", ls="--", lw=1, label="mined = realised")
    base = float(d["baseline"].mean())
    ax.axhline(base, color=WARN, ls=":", lw=1, label=f"baseline P(target) ≈ {base:.3f}")
    ax.axvline(base, color=WARN, ls=":", lw=1)
    ax.set_xlabel("mined conditional P(target), shrunk — training block")
    ax.set_ylabel("realised P(target) — unseen test block")
    _style(ax, "Every mined pattern, in-sample against out-of-sample "
               "(point size = training occurrences)")
    ax.legend(fontsize=8)
    fig.colorbar(ax.collections[0], ax=ax, label="lift over baseline")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def probability_curve(pred: pd.DataFrame, out: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    bins = np.linspace(pred["p_tp"].min(), pred["p_tp"].max(), 12)
    idx = np.digitize(pred["p_tp"], bins[1:-1])
    rows = []
    for b in np.unique(idx):
        m = idx == b
        rows.append((float(pred["p_tp"][m].mean()), float((pred["y"][m] == 2).mean()),
                     float(pred["ret_R_net"][m].mean()), int(m.sum())))
    d = pd.DataFrame(rows, columns=["p", "hit", "R", "n"])
    axes[0].plot(d["p"], d["hit"], "o-", color=UP, lw=1.6)
    axes[0].plot([d["p"].min(), d["p"].max()], [d["p"].min(), d["p"].max()],
                 color="#8f98a3", ls="--", lw=1)
    axes[0].set_xlabel("predicted P(target)")
    axes[0].set_ylabel("realised hit rate")
    _style(axes[0], "Does a higher probability mean a higher hit rate?")

    axes[1].bar(d["p"], d["R"], width=(d["p"].max() - d["p"].min()) / 14,
                color=[UP if v > 0 else DOWN for v in d["R"]], alpha=0.85)
    axes[1].axhline(0, color=FG, lw=0.8)
    axes[1].set_xlabel("predicted P(target)")
    axes[1].set_ylabel("mean net R")
    _style(axes[1], "…and a higher net expectancy?")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def interaction_chart(table: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    if table.empty:
        ax.text(0.5, 0.5, "no interactions tested", ha="center", color=FG)
    else:
        d = table.head(12).iloc[::-1]
        labels = [f"{a} × {b}" for a, b in zip(d["feature_a"], d["feature_b"])]
        ypos = np.arange(len(d))
        ax.barh(ypos - 0.18, d["train_did"], height=0.36, color=ACCENT,
                alpha=0.9, label="training block")
        ax.barh(ypos + 0.18, d["test_did"].fillna(0), height=0.36, color=WARN,
                alpha=0.9, label="unseen test block")
        ax.set_yticks(ypos)
        ax.set_yticklabels(labels, fontsize=8)
        ax.axvline(0, color=FG, lw=0.8)
        ax.legend(fontsize=8)
    ax.set_xlabel("interaction effect on P(target)  —  (P11−P01) − (P10−P00)")
    _style(ax, "Two-way interactions: does the effect of one condition depend on the other?")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out
