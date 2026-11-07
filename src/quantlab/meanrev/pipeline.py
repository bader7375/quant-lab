"""End-to-end orchestration and the run-directory format.

``run(cfg)``            data -> features -> labels -> walk-forward -> signals
                        -> backtest -> metrics, persisted to one directory.
``rerun_trading(dir)``  re-derives signals, backtest and metrics from the
                        stored out-of-sample predictions with a new
                        regime / signal / risk / exit configuration. Seconds,
                        not minutes, and no retraining.
``load_run(dir)``       lazy reader the terminal UI uses.
``live_signals(dir)``   brings data and features up to date incrementally and
                        scores the latest bar with each symbol's latest model.

Run directory::

    runs/<name>/
      config.yaml  run.json  run.log  metrics.json  trades.csv
      equity.parquet  symbol_pnl.parquet  specs.json
      market/<ticker>.parquet            bars actually used (+ market.json)
      symbols/<sym>/{features,means,signal,labels,predictions,shap,decisions,
                     importance,importance_smooth,family_importance,
                     family_importance_smooth,meta_weights,summaries,excluded}.parquet
      models/<sym>/latest.joblib         model for live scoring
      checkpoints/<model_hash>/step_NNNN.joblib   resumable walk-forward state
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import platform
import time
from functools import cached_property
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd

from .backtest.engine import run_backtest
from .backtest.metrics import (calibration_curve, classification_metrics, monthly_returns, symbol_trading_metrics,
                               trading_metrics)
from .config import MRConfig
from .data.loader import load_market
from .data.market import MarketData
from .features.engine import SymbolFeatures
from .features.registry import FeatureSpec
from .features.store import FeatureStore
from .labels import make_labels
from .models.walkforward import run_walkforward
from .signals import signal_frame

log = logging.getLogger("quantlab.meanrev")
Progress = Callable[[float, str], None]

SYMBOL_FRAMES = ("features", "means", "signal", "labels", "predictions", "shap", "decisions", "importance",
                 "importance_smooth", "family_importance", "family_importance_smooth", "meta_weights", "summaries",
                 "excluded")


def run_dir_for(cfg: MRConfig) -> Path:
    name = cfg.run_name or f"{cfg.data.provider}-{cfg.model_hash()}"
    return cfg.output_path / "runs" / name


def _stage(progress: Progress | None, lo: float, hi: float) -> Progress:
    def f(frac: float, msg: str) -> None:
        if progress:
            progress(lo + (hi - lo) * float(np.clip(frac, 0, 1)), msg)
    return f


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (pd.Timestamp, dt.date)):
        return str(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=_json_default))


# --------------------------------------------------------------------------
# market persistence (a run is self-contained)
# --------------------------------------------------------------------------
def save_market(md: MarketData, d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for t, b in md.bars.items():
        b.to_parquet(d / f"{t}.parquet")
    _write_json(d / "market.json", {"symbols": md.symbols, "market": md.market, "sector_map": md.sector_map,
                                    "size_etf": md.size_etf, "momentum_etf": md.momentum_etf,
                                    "factors": md.factors, "source": md.source})


def load_saved_market(d: Path) -> MarketData:
    meta = json.loads((d / "market.json").read_text())
    bars = {p.stem: pd.read_parquet(p) for p in d.glob("*.parquet")}
    return MarketData(bars=bars, **meta)


# --------------------------------------------------------------------------
# trading layer (shared by run and rerun_trading)
# --------------------------------------------------------------------------
def trading_layer(md: MarketData, signals: dict[str, pd.DataFrame], preds: dict[str, pd.DataFrame],
                  labels: dict[str, pd.DataFrame], cfg: MRConfig) -> dict:
    decs = {s: signal_frame(signals[s], preds[s], cfg) for s in preds if len(preds[s])}
    if not decs:
        raise RuntimeError("the walk-forward produced no predictions: history too short for the "
                           "configured train_days / min_train_samples")
    start = min(p.index.min() for p in preds.values() if len(p))
    bt = run_backtest(md, signals, decs, cfg, start=start)

    metrics = {"portfolio": trading_metrics(bt.equity, bt.trades), "symbols": {}, "calibration": {},
               "pooled": {}}
    ys, ps, los, his = [], [], [], []
    for s, P in preds.items():
        if not len(P):
            continue
        L = labels[s].reindex(P.index)
        m = L["in_domain"].fillna(False).astype(bool) & L["y"].notna() & P["p"].notna()
        y, p = L.loc[m, "y"].to_numpy(), P.loc[m, "p"].to_numpy()
        lo, hi = P.loc[m, "p_lo"].to_numpy(), P.loc[m, "p_hi"].to_numpy()
        ys.append(y), ps.append(p), los.append(lo), his.append(hi)
        tr = bt.trades[bt.trades["symbol"] == s] if len(bt.trades) else bt.trades
        metrics["symbols"][s] = {
            "classification": classification_metrics(y, p, cfg.signal.prob_threshold, lo, hi),
            "trading": symbol_trading_metrics(tr, bt.symbol_pnl[s], cfg.risk.initial_capital),
            "signals": int(decs[s]["entry"].sum()),
        }
        metrics["calibration"][s] = calibration_curve(y, p).to_dict(orient="list")
    if ys:
        y, p = np.concatenate(ys), np.concatenate(ps)
        metrics["pooled"] = classification_metrics(y, p, cfg.signal.prob_threshold, np.concatenate(los),
                                                   np.concatenate(his))
        metrics["calibration"]["_pooled"] = calibration_curve(y, p).to_dict(orient="list")
    return {"decisions": decs, "backtest": bt, "metrics": metrics}


def _persist_trading(run_dir: Path, out: dict) -> None:
    bt = out["backtest"]
    bt.trades.to_csv(run_dir / "trades.csv", index=False)
    bt.equity.to_parquet(run_dir / "equity.parquet")
    bt.symbol_pnl.to_parquet(run_dir / "symbol_pnl.parquet")
    for s, d in out["decisions"].items():
        (run_dir / "symbols" / s).mkdir(parents=True, exist_ok=True)
        d.to_parquet(run_dir / "symbols" / s / "decisions.parquet")
    mr = monthly_returns(bt.equity)
    mr.columns = [str(c) for c in mr.columns]
    mr.to_parquet(run_dir / "monthly_returns.parquet")
    _write_json(run_dir / "metrics.json", out["metrics"])


# --------------------------------------------------------------------------
# full run
# --------------------------------------------------------------------------
def run(cfg: MRConfig, progress: Progress | None = None, stop_flag: Callable[[], bool] | None = None,
        force_data: bool = False) -> Path:
    run_dir = run_dir_for(cfg)
    run_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(run_dir / "run.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
    if log.level == logging.NOTSET or log.level > logging.INFO:
        log.setLevel(logging.INFO)
    t0 = time.time()
    meta = {"run_name": run_dir.name, "model_hash": cfg.model_hash(), "status": "running",
            "started": dt.datetime.now().isoformat(timespec="seconds"), "python": platform.python_version()}
    _write_json(run_dir / "run.json", meta)
    cfg.dump(run_dir / "config.yaml")
    try:
        log.info("run %s: model hash %s", run_dir.name, cfg.model_hash())
        md = load_market(cfg, force=force_data, progress=_stage(progress, 0.0, 0.05))
        save_market(md, run_dir / "market")

        st = _stage(progress, 0.05, 0.22)
        store = FeatureStore(cfg.output_path / "features", cfg)
        feats: dict[str, SymbolFeatures] = {}
        if cfg.walkforward.n_jobs > 1 and len(md.symbols) > 1:
            from joblib import Parallel, delayed

            def _one(sym):
                return FeatureStore(cfg.output_path / "features", cfg).get(md, sym)
            st(0.0, "building features in parallel")
            for sf in Parallel(n_jobs=min(cfg.walkforward.n_jobs, len(md.symbols)))(
                    delayed(_one)(s) for s in md.symbols):
                feats[sf.symbol] = sf
        else:
            for i, sym in enumerate(md.symbols):
                feats[sym] = store.get(md, sym)
                st((i + 1) / len(md.symbols), f"features: {sym}")
        st(1.0, f"features ready: {len(next(iter(feats.values())).feature_names)} per symbol")

        labels = {s: make_labels(f.signal, cfg.label) for s, f in feats.items()}
        wf = run_walkforward(feats, labels, md.calendar, cfg, run_dir / "checkpoints" / cfg.model_hash(),
                             progress=_stage(progress, 0.22, 0.92), stop_flag=stop_flag)

        _stage(progress, 0.92, 0.97)(0.0, "signals, backtest and metrics")
        signals = {s: f.signal for s, f in feats.items()}
        out = trading_layer(md, signals, wf.predictions, labels, cfg)

        _stage(progress, 0.97, 1.0)(0.0, "writing artifacts")
        specs = next(iter(feats.values())).specs
        _write_json(run_dir / "specs.json", {k: vars(v) for k, v in specs.items()})
        frames = {
            "features": {s: f.features for s, f in feats.items()}, "means": {s: f.means for s, f in feats.items()},
            "signal": signals, "labels": labels, "predictions": wf.predictions, "shap": wf.shap,
            "importance": wf.importance, "importance_smooth": wf.importance_smooth,
            "family_importance": wf.family_importance, "family_importance_smooth": wf.family_importance_smooth,
            "meta_weights": wf.meta_weights, "summaries": wf.summaries, "excluded": wf.excluded,
        }
        for name, per_sym in frames.items():
            for s, df in per_sym.items():
                d = run_dir / "symbols" / s
                d.mkdir(parents=True, exist_ok=True)
                df = df.copy()
                df.columns = [str(c) for c in df.columns]
                if name == "labels":
                    df["t_end"] = pd.DatetimeIndex(df["t_end"])
                df.to_parquet(d / f"{name}.parquet")
        for s, m in wf.latest_models.items():
            (run_dir / "models" / s).mkdir(parents=True, exist_ok=True)
            joblib.dump(m, run_dir / "models" / s / "latest.joblib", compress=3)
        _persist_trading(run_dir, out)

        pm = out["metrics"]["portfolio"]
        meta.update(status="complete", finished=dt.datetime.now().isoformat(timespec="seconds"),
                    seconds=round(time.time() - t0, 1), data_source=md.source, symbols=md.symbols,
                    first_test=str(min(p.index.min() for p in wf.predictions.values() if len(p)).date()),
                    last_bar=str(md.calendar[-1].date()), n_steps=len(wf.steps),
                    n_features=len(specs), sharpe=pm.get("sharpe"), n_trades=pm.get("n_trades"))
        _write_json(run_dir / "run.json", meta)
        if progress:
            progress(1.0, f"done in {time.time() - t0:.0f}s")
        log.info("run complete in %.1fs: Sharpe %s, %s trades", time.time() - t0, pm.get("sharpe"),
                 pm.get("n_trades"))
        return run_dir
    except Exception as exc:
        meta.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        _write_json(run_dir / "run.json", meta)
        log.exception("run failed")
        raise
    finally:
        log.removeHandler(handler)
        handler.close()


def rerun_trading(run_dir: Path, cfg: MRConfig, progress: Progress | None = None) -> Path:
    """Recompute signals, backtest and metrics with new trading parameters."""
    run_dir = Path(run_dir)
    stored = MRConfig.load(run_dir / "config.yaml")
    if stored.model_hash() != cfg.model_hash():
        raise ValueError("model-defining parameters changed; a full walk-forward run is required")
    md = load_saved_market(run_dir / "market")
    rd = RunData(run_dir)
    syms = [s for s in md.symbols if (run_dir / "symbols" / s / "predictions.parquet").exists()]
    if progress:
        progress(0.2, "re-deriving signals")
    out = trading_layer(md, {s: rd.frame(s, "signal") for s in syms}, {s: rd.frame(s, "predictions") for s in syms},
                        {s: rd.frame(s, "labels") for s in syms}, cfg)
    _persist_trading(run_dir, out)
    cfg.dump(run_dir / "config.yaml")
    meta = json.loads((run_dir / "run.json").read_text())
    meta.update(sharpe=out["metrics"]["portfolio"].get("sharpe"), n_trades=out["metrics"]["portfolio"].get("n_trades"),
                trading_rerun=dt.datetime.now().isoformat(timespec="seconds"))
    _write_json(run_dir / "run.json", meta)
    if progress:
        progress(1.0, "backtest updated")
    return run_dir


# --------------------------------------------------------------------------
# reading runs
# --------------------------------------------------------------------------
class RunData:
    """Lazy, cached reader over a run directory."""

    def __init__(self, run_dir: Path):
        self.dir = Path(run_dir)
        self._cache: dict = {}

    @cached_property
    def meta(self) -> dict:
        return json.loads((self.dir / "run.json").read_text())

    @cached_property
    def config(self) -> MRConfig:
        return MRConfig.load(self.dir / "config.yaml")

    @property
    def metrics(self) -> dict:
        p = self.dir / "metrics.json"
        return json.loads(p.read_text()) if p.exists() else {}

    @cached_property
    def specs(self) -> dict[str, FeatureSpec]:
        raw = json.loads((self.dir / "specs.json").read_text())
        return {k: FeatureSpec(**v) for k, v in raw.items()}

    @property
    def symbols(self) -> list[str]:
        return sorted(p.name for p in (self.dir / "symbols").iterdir() if p.is_dir()) if (self.dir / "symbols").exists() else []

    def frame(self, symbol: str, name: str) -> pd.DataFrame:
        key = (symbol, name)
        path = self.dir / "symbols" / symbol / f"{name}.parquet"
        mtime = path.stat().st_mtime if path.exists() else None
        hit = self._cache.get(key)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        df = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        self._cache[key] = (mtime, df)
        return df

    def bars(self, ticker: str) -> pd.DataFrame:
        key = ("bars", ticker)
        if key not in self._cache:
            self._cache[key] = pd.read_parquet(self.dir / "market" / f"{ticker}.parquet")
        return self._cache[key]

    def _top(self, name: str) -> pd.DataFrame:
        path = self.dir / name
        mtime = path.stat().st_mtime if path.exists() else None
        hit = self._cache.get(name)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        if not path.exists():
            df = pd.DataFrame()
        elif name.endswith(".csv"):
            df = pd.read_csv(path, parse_dates=["signal_date", "entry_date", "exit_signal_date", "exit_date"])
        else:
            df = pd.read_parquet(path)
        self._cache[name] = (mtime, df)
        return df

    @property
    def trades(self) -> pd.DataFrame:
        return self._top("trades.csv")

    @property
    def equity(self) -> pd.DataFrame:
        return self._top("equity.parquet")

    @property
    def symbol_pnl(self) -> pd.DataFrame:
        return self._top("symbol_pnl.parquet")

    @property
    def monthly(self) -> pd.DataFrame:
        return self._top("monthly_returns.parquet")


def list_runs(cfg: MRConfig | None = None) -> list[dict]:
    root = (cfg or MRConfig()).output_path / "runs"
    out = []
    if not root.exists():
        return out
    for d in root.iterdir():
        p = d / "run.json"
        if p.exists():
            try:
                meta = json.loads(p.read_text())
                meta["path"] = str(d)
                meta["mtime"] = p.stat().st_mtime
                out.append(meta)
            except Exception:  # noqa: BLE001
                continue
    return sorted(out, key=lambda m: m["mtime"], reverse=True)


# --------------------------------------------------------------------------
# live scoring
# --------------------------------------------------------------------------
def live_signals(run_dir: Path, force_data: bool = False) -> pd.DataFrame:
    """Latest-bar probability and decision for every symbol of a finished run.

    Data are refreshed (incremental fetch for yfinance), features appended
    incrementally, and each symbol is scored by its most recent model.
    """
    run_dir = Path(run_dir)
    cfg = MRConfig.load(run_dir / "config.yaml")
    md = load_market(cfg, force=force_data)
    store = FeatureStore(cfg.output_path / "features", cfg)
    rows = []
    for sym in md.symbols:
        mpath = run_dir / "models" / sym / "latest.joblib"
        if not mpath.exists():
            continue
        model = joblib.load(mpath)
        sf = store.get(md, sym)
        X = sf.features[model.features].iloc[[-1]].to_numpy(np.float64)
        pred = pd.DataFrame(model.predict(X), index=sf.features.index[-1:])
        pred["payoff_b"] = model.summary.payoff_b
        dec = signal_frame(sf.signal.iloc[-1:], pred, cfg).iloc[-1]
        rows.append({"symbol": sym, "date": sf.features.index[-1].date(), "z": dec["z"], "p": dec["p"],
                     "p_lo": dec["p_lo"], "p_hi": dec["p_hi"], "regime": dec["regime"], "threshold": dec["thr"],
                     "confluence": sf.signal["confluence"].iloc[-1], "entry": bool(dec["entry"]),
                     "direction": "long" if dec["dir"] > 0 else "short", "weight": dec["weight"]})
    return pd.DataFrame(rows)
