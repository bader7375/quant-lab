"""Command line interface.

    python -m quantlab.cli run --config configs/default.yaml
    python -m quantlab.cli run --provider synthetic --folds 5
    python -m quantlab.cli predict --top 20
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import Config
from . import pipeline


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quantlab", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["data", "features", "run", "predict"],
                   help="data: download+cache prices | features: build the matrix | "
                        "run: full walk-forward + report | predict: score the latest date")
    p.add_argument("--config", default=None, help="path to a YAML config")
    p.add_argument("--provider", choices=["yfinance", "synthetic"], default=None)
    p.add_argument("--universe", default=None, help="sp500 | sp100")
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--folds", type=int, default=None)
    p.add_argument("--model", choices=["lightgbm", "logistic"], default=None)
    p.add_argument("--calibration", choices=["isotonic", "sigmoid", "none"], default=None)
    p.add_argument("--threshold-sigma", type=float, default=None,
                   help="label threshold in units of trailing volatility")
    p.add_argument("--cost-bps", type=float, default=None, help="round-trip cost for the backtest")
    p.add_argument("--output", default=None, help="output directory")
    p.add_argument("--top", type=int, default=25, help="predict: how many names to print")
    p.add_argument("--force", action="store_true", help="ignore caches and rebuild")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = Config.load(
        args.config,
        **{
            "data.provider": args.provider,
            "data.universe": args.universe,
            "data.start": args.start,
            "data.end": args.end,
            "split.n_folds": args.folds,
            "model.kind": args.model,
            "model.calibration": args.calibration,
            "label.threshold_sigma": args.threshold_sigma,
            "backtest.cost_bps": args.cost_bps,
            "output_dir": args.output,
        },
    )

    if args.command == "data":
        from .data.panel import build_panel
        panel = build_panel(cfg, force=args.force)
        print(f"panel: {len(panel):,} rows, "
              f"{panel.index.get_level_values('ticker').nunique()} tickers")
        return 0

    if args.command == "features":
        df = pipeline.prepare(cfg, force=args.force)
        print(f"features: {len(df):,} rows x {df.shape[1]} columns")
        return 0

    if args.command == "run":
        results = pipeline.run(cfg, force=args.force)
        r, b = results["ranking"], results["backtest"]
        print("\n" + "=" * 62)
        print(f"  within-date AUC : {r.get('daily_auc_mean', float('nan')):.4f} "
              f"(t = {r.get('daily_auc_t_stat', float('nan')):.1f})")
        print(f"  information coef: {r.get('ic_mean', float('nan')):.4f} "
              f"(t = {r.get('ic_t_stat', float('nan')):.1f})")
        print(f"  net Sharpe      : {b.get('sharpe', float('nan')):.2f} "
              f"at {b.get('cost_bps', float('nan')):.0f} bps")
        print(f"  breakeven cost  : {b.get('breakeven_cost_bps', float('nan')):.1f} bps")
        print(f"  report          : {cfg.output_path / 'REPORT.md'}")
        print("=" * 62)
        if cfg.data.provider == "synthetic":
            print("  NOTE: synthetic data. These numbers verify the pipeline;\n"
                  "        they are not a forecast of real-world performance.")
            print("=" * 62)
        return 0

    if args.command == "predict":
        preds = pipeline.predict_latest(cfg, force=args.force)
        out_file = cfg.output_path / "latest_predictions.csv"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        preds.to_csv(out_file)
        cols = ["probability", "cs_rank", "threshold_move"]
        print(f"\nTop {args.top} by predicted probability "
              f"(P[next-day return > +{cfg.label.threshold_sigma}σ]):\n")
        print(preds[cols].head(args.top).round(4).to_string())
        print(f"\nfull output: {out_file}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
