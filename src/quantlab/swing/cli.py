"""Command line for the adaptive swing research platform.

    python -m quantlab.swing.cli run --data uploads/tsla_us_d.csv
    python -m quantlab.swing.cli run --config configs/swing.yaml --folds 8
    python -m quantlab.swing.cli audit --data uploads/tsla_us_d.csv
    python -m quantlab.swing.cli predict --data uploads/tsla_us_d.csv
    python -m quantlab.swing.cli run --set label.tp_multiple=2.5 --set patterns.max_depth=3

Multi-instrument (a folder of one file per ticker):

    python -m quantlab.swing.cli scan --data uploads/universe
    python -m quantlab.swing.cli scan --data uploads/universe --limit 100 \
        --score p_tp --set label.primary_rule=reversal
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import SwingConfig


def _build_config(args) -> SwingConfig:
    cfg = SwingConfig.from_yaml(args.config) if args.config else SwingConfig()
    if args.data:
        cfg.data.path = args.data
    if args.symbol:
        cfg.data.symbol = args.symbol
    if args.folds:
        cfg.split.n_folds = args.folds
    if args.out:
        cfg.output.dir = args.out
    if args.no_plots:
        cfg.output.make_plots = False
    if args.fast:
        cfg.models.optuna_trials = 6
        cfg.models.enabled = ("knn", "rf", "lgbm", "xgb", "logit")
        cfg.patterns.max_patterns = 12
        cfg.rl.episodes = 120
    for item in args.set or []:
        key, _, value = item.partition("=")
        cfg.override(key, value)
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quantlab.swing",
                                     description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command",
                        choices=["run", "audit", "predict", "config", "scan"])
    parser.add_argument("--config", help="YAML config file")
    parser.add_argument("--data", help="CSV/XLSX/Parquet file (or a folder holding one)")
    parser.add_argument("--symbol", help="override the symbol inferred from the filename")
    parser.add_argument("--folds", type=int, help="walk-forward folds")
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--fast", action="store_true",
                        help="smaller engine set and search budget, for a quick pass")
    parser.add_argument("--limit", type=int,
                        help="scan: cap how many instruments are loaded")
    parser.add_argument("--score", default="exp_R_hat", choices=["exp_R_hat", "p_tp"],
                        help="scan: rank candidates by predicted expected R (default) "
                             "or by P(target)")
    parser.add_argument("--no-cross-sectional", action="store_true",
                        help="scan: withhold peer-relative features")
    parser.add_argument("--set", action="append", metavar="section.key=value",
                        help="override any config value; repeatable")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S",
    )
    cfg = _build_config(args)

    if args.command == "config":
        import yaml
        print(yaml.safe_dump(cfg.to_dict(), sort_keys=False))
        return 0

    if args.command == "audit":
        from .data import load_and_audit
        _, audit = load_and_audit(cfg.data)
        print(audit.to_markdown())
        return 0

    if args.command == "scan":
        from .panel_pipeline import run_scan

        bundle = run_scan(cfg, cfg.data.path, score=args.score, limit=args.limit,
                          cross_sectional=not args.no_cross_sectional,
                          out_dir=cfg.output.dir, progress=not args.quiet)
        head = bundle["report"].split("## 1.")[0]
        print(head)
        trade = bundle["scan"][bundle["scan"]["decision"] == "TRADE"]
        print(f"\nTRADE candidates on the latest bar: {len(trade)}")
        if len(trade):
            print(trade.head(15).to_string(index=False))
        print(f"\nfull report: {bundle['out_dir']}/PANEL_REPORT.md")
        return 0

    from .pipeline import run

    if args.command == "predict":
        cfg.output.make_plots = False
    result = run(cfg, progress=not args.quiet)

    if args.command == "predict":
        sig = result["signal"]
        print(f"\n{result['audit'].symbol} — next bar after {sig.asof.date()}")
        print(f"  P(target)={sig.p_tp:.1%}  P(stop)={sig.p_sl:.1%}  "
              f"P(neither)={sig.p_none:.1%}")
        print(f"  entry~{sig.entry_reference:,.2f}  stop {sig.stop:,.2f}  "
              f"target {sig.target:,.2f}  ({sig.rr:g}R)")
        print(f"  regime: {sig.regime_name}   tier T{sig.tier}   "
              f"decision: {sig.decision}")
    else:
        print("\n".join(result["report"].split("\n")[:60]))
        print(f"\n… full report: {result['artifacts']['full report']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
