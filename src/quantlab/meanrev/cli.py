"""Command line for the mean-reversion research system.

    python -m quantlab.meanrev.cli run --config configs/meanrev_demo.yaml
    python -m quantlab.meanrev.cli run --provider yfinance --symbols SPY QQQ AAPL MSFT
    python -m quantlab.meanrev.cli backtest --run artifacts/meanrev/runs/<name> --set signal.prob_threshold=0.6
    python -m quantlab.meanrev.cli signals --run artifacts/meanrev/runs/<name>
    python -m quantlab.meanrev.cli app --port 8050
    python -m quantlab.meanrev.cli runs
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from .config import MRConfig


def _parse_set(items: list[str]) -> dict:
    out = {}
    for it in items or []:
        key, _, raw = it.partition("=")
        out[key.strip()] = yaml.safe_load(raw)
    return out


def _config(args) -> MRConfig:
    overrides = _parse_set(args.set)
    if getattr(args, "provider", None):
        overrides["data.provider"] = args.provider
    if getattr(args, "symbols", None):
        overrides["data.symbols"] = args.symbols
    if getattr(args, "start", None):
        overrides["data.start"] = args.start
    if getattr(args, "name", None):
        overrides["run_name"] = args.name
    return MRConfig.load(args.config, **overrides)


def _progress(frac: float, msg: str) -> None:
    bar = "#" * int(frac * 30)
    sys.stderr.write(f"\r[{bar:<30}] {frac:5.1%} {msg[:70]:<70}")
    sys.stderr.flush()
    if frac >= 1.0:
        sys.stderr.write("\n")


def _summary(run_dir: Path) -> str:
    m = json.loads((run_dir / "metrics.json").read_text())
    p, c = m["portfolio"], m.get("pooled", {})

    def f(v, fmt="{:.2f}"):
        return "n/a" if v is None else fmt.format(v)

    lines = [
        f"run: {run_dir}",
        "-- out-of-sample forecast quality (pooled, in-domain) --",
        f"  n={c.get('n')}  base rate {f(c.get('base_rate'), '{:.3f}')}  Brier {f(c.get('brier'), '{:.4f}')} "
        f"(skill {f(c.get('brier_skill'), '{:+.3f}')})  ROC AUC {f(c.get('roc_auc'), '{:.3f}')}  "
        f"PR AUC {f(c.get('pr_auc'), '{:.3f}')}  ECE {f(c.get('ece'), '{:.3f}')}",
        f"  precision@thr {f(c.get('precision_at_thr'), '{:.3f}')} (coverage {f(c.get('coverage_at_thr'), '{:.1%}')})",
        "-- trading (next-open fills, costs and borrow included) --",
        f"  Sharpe {f(p.get('sharpe'))}  Sortino {f(p.get('sortino'))}  CAGR {f(p.get('cagr'), '{:.2%}')}  "
        f"MaxDD {f(p.get('max_drawdown'), '{:.2%}')}  vs buy&hold Sharpe {f(p.get('bh_sharpe'))}",
        f"  trades {p.get('n_trades')}  win rate {f(p.get('win_rate'), '{:.1%}')}  expectancy {f(p.get('expectancy_R'))}R  "
        f"profit factor {f(p.get('profit_factor'))}  exposure {f(p.get('exposure'), '{:.1%}')}",
    ]
    for s, d in m["symbols"].items():
        cc, tt = d["classification"], d["trading"]
        lines.append(f"  {s:<6} AUC {f(cc.get('roc_auc'), '{:.3f}')}  BSS {f(cc.get('brier_skill'), '{:+.3f}')}  "
                     f"trades {tt.get('n_trades')}  Sharpe {f(tt.get('sharpe'))}  exp {f(tt.get('expectancy_R'))}R")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="quantlab.meanrev", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="full walk-forward run")
    r.add_argument("--config", default=None)
    r.add_argument("--provider", choices=["synthetic", "yfinance", "files"])
    r.add_argument("--symbols", nargs="+")
    r.add_argument("--start")
    r.add_argument("--name", help="run name (default: <provider>-<model hash>)")
    r.add_argument("--set", nargs="*", default=[], help="dotted overrides, e.g. label.horizon=5")
    r.add_argument("--force-data", action="store_true")

    b = sub.add_parser("backtest", help="re-run only the trading layer of an existing run")
    b.add_argument("--run", required=True)
    b.add_argument("--set", nargs="*", default=[])

    s = sub.add_parser("signals", help="score the latest bar (incremental data + feature update)")
    s.add_argument("--run", required=True)

    a = sub.add_parser("app", help="launch the research terminal")
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8050)
    a.add_argument("--config", default=None)
    a.add_argument("--debug", action="store_true")

    sub.add_parser("runs", help="list runs")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("numba", "matplotlib", "yfinance", "urllib3", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    from . import pipeline

    if args.command == "run":
        cfg = _config(args)
        run_dir = pipeline.run(cfg, progress=_progress, force_data=args.force_data)
        print(_summary(run_dir))
    elif args.command == "backtest":
        run_dir = Path(args.run)
        cfg = MRConfig.load(run_dir / "config.yaml", **_parse_set(args.set))
        pipeline.rerun_trading(run_dir, cfg, progress=_progress)
        print(_summary(run_dir))
    elif args.command == "signals":
        df = pipeline.live_signals(Path(args.run))
        print(df.to_string(index=False))
    elif args.command == "runs":
        for m in pipeline.list_runs():
            print(f"{m['run_name']:<40} {m.get('status'):<9} {m.get('data_source', '?'):<10} "
                  f"Sharpe {m.get('sharpe')}  trades {m.get('n_trades')}  {m['path']}")
    elif args.command == "app":
        from .app.server import serve

        serve(host=args.host, port=args.port, config=args.config, debug=args.debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
