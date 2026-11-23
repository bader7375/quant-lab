"""Out-of-sample evaluation: forecast quality and trading performance.

Classification metrics are computed on in-domain bars with resolved labels
only -- the population the model was built for. Every number carries its
comparison: Brier against the base-rate forecast (skill score), precision at
the threshold against the base rate, strategy equity against buy & hold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ANN = 252.0


def _safe(f, *a, **k):
    try:
        v = f(*a, **k)
        return float(v) if np.isfinite(v) else None
    except Exception:  # noqa: BLE001 - degenerate samples (one class) have no AUC
        return None


def calibration_curve(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Reliability diagram on equal-count bins (robust when p clusters)."""
    if len(y) == 0:
        return pd.DataFrame(columns=["p_mean", "y_rate", "n", "lo", "hi"])
    q = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.searchsorted(q, p, side="right") - 1, 0, max(len(q) - 2, 0))
    df = pd.DataFrame({"y": y, "p": p, "b": idx})
    g = df.groupby("b").agg(p_mean=("p", "mean"), y_rate=("y", "mean"), n=("y", "size"))
    se = np.sqrt(g["y_rate"] * (1 - g["y_rate"]) / g["n"].clip(lower=1))
    g["lo"], g["hi"] = (g["y_rate"] - 1.96 * se).clip(0, 1), (g["y_rate"] + 1.96 * se).clip(0, 1)
    return g.reset_index(drop=True)


def classification_metrics(y: np.ndarray, p: np.ndarray, threshold: float, p_lo: np.ndarray | None = None,
                           p_hi: np.ndarray | None = None) -> dict:
    from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    n = len(y)
    if n == 0:
        return {"n": 0}
    base = y.mean()
    brier = float(np.mean((p - y) ** 2))
    brier_ref = float(np.mean((base - y) ** 2))
    sel = p >= threshold
    cal = calibration_curve(y, p)
    ece = float((cal["n"] * (cal["p_mean"] - cal["y_rate"]).abs()).sum() / n) if len(cal) else None
    out = {
        "n": int(n), "base_rate": float(base), "mean_p": float(p.mean()),
        "brier": brier, "brier_ref": brier_ref, "brier_skill": 1 - brier / brier_ref if brier_ref > 0 else None,
        "log_loss": _safe(log_loss, y, p, labels=[0, 1]),
        "roc_auc": _safe(roc_auc_score, y, p), "pr_auc": _safe(average_precision_score, y, p),
        "ece": ece, "threshold": threshold, "coverage_at_thr": float(sel.mean()),
        "precision_at_thr": float(y[sel].mean()) if sel.any() else None,
        "lift_at_thr": float(y[sel].mean() / base) if sel.any() and base > 0 else None,
    }
    if p_lo is not None and p_hi is not None:
        w = np.asarray(p_hi) - np.asarray(p_lo)
        out["ci_width_mean"] = float(np.nanmean(w))
        sel_lo = np.asarray(p_lo) >= threshold
        out["coverage_lo_thr"] = float(sel_lo.mean())
        out["precision_lo_thr"] = float(y[sel_lo].mean()) if sel_lo.any() else None
    return out


def trading_metrics(equity: pd.DataFrame, trades: pd.DataFrame) -> dict:
    r = equity["ret"].fillna(0.0)
    n = len(r)
    if n < 2:
        return {}
    yrs = n / ANN
    total = equity["equity"].iloc[-1] / equity["equity"].iloc[0] - 1
    vol = r.std() * np.sqrt(ANN)
    downside = np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(ANN)
    sharpe = r.mean() * ANN / vol if vol > 0 else None
    mdd = float(equity["drawdown"].min())
    cagr = (1 + total) ** (1 / yrs) - 1 if yrs > 0 and total > -1 else None
    out = {
        "total_return": float(total), "cagr": cagr, "ann_vol": float(vol), "sharpe": sharpe,
        "sortino": r.mean() * ANN / downside if downside > 0 else None, "max_drawdown": mdd,
        "calmar": cagr / abs(mdd) if cagr is not None and mdd < 0 else None,
        "exposure": float((equity["positions"] > 0).mean()),
        "avg_gross_leverage": float(equity["gross_leverage"].mean()),
        "n_trades": int(len(trades)), "years": float(yrs),
    }
    if "bh_equity" in equity:
        br = equity["bh_equity"].pct_change().fillna(0.0)
        bv = br.std() * np.sqrt(ANN)
        out["bh_total_return"] = float(equity["bh_equity"].iloc[-1] / equity["bh_equity"].iloc[0] - 1)
        out["bh_sharpe"] = float(br.mean() * ANN / bv) if bv > 0 else None
        out["bh_max_drawdown"] = float(equity["bh_drawdown"].min())
        out["corr_to_bh"] = float(r.corr(br)) if r.std() > 0 else None
    if len(trades):
        pnl = trades["pnl"]
        wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
        out.update({
            "win_rate": float((pnl > 0).mean()),
            "expectancy_R": float(trades["R"].mean()),
            "median_R": float(trades["R"].median()),
            "avg_win_R": float(trades.loc[pnl > 0, "R"].mean()) if len(wins) else None,
            "avg_loss_R": float(trades.loc[pnl <= 0, "R"].mean()) if len(losses) else None,
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else None,
            "avg_bars_held": float(trades["bars_held"].mean()),
            "trades_per_year": float(len(trades) / yrs) if yrs > 0 else None,
            "total_costs": float(trades["costs"].sum() + trades["borrow"].sum()),
            "exit_reasons": trades["exit_reason"].value_counts().to_dict(),
        })
    return out


def symbol_trading_metrics(trades: pd.DataFrame, sym_pnl: pd.Series, capital: float) -> dict:
    """Per-symbol attribution: P&L-based Sharpe plus trade statistics."""
    r = sym_pnl / capital
    vol = r.std() * np.sqrt(ANN)
    eq = capital + sym_pnl.cumsum()
    dd = (eq / eq.cummax() - 1).min()
    out = {"pnl": float(sym_pnl.sum()), "sharpe": float(r.mean() * ANN / vol) if vol > 0 else None,
           "max_drawdown": float(dd), "n_trades": int(len(trades))}
    if len(trades):
        pnl = trades["pnl"]
        losses = pnl[pnl <= 0]
        out.update({"win_rate": float((pnl > 0).mean()), "expectancy_R": float(trades["R"].mean()),
                    "profit_factor": float(pnl[pnl > 0].sum() / -losses.sum()) if losses.sum() < 0 else None,
                    "avg_bars_held": float(trades["bars_held"].mean())})
    return out


def monthly_returns(equity: pd.DataFrame) -> pd.DataFrame:
    m = (1 + equity["ret"]).resample("ME").prod() - 1
    df = pd.DataFrame({"year": m.index.year, "month": m.index.month, "ret": m.to_numpy()})
    return df.pivot(index="year", columns="month", values="ret")
