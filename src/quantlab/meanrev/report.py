"""Exports: a standalone HTML research report and an artifact bundle."""
from __future__ import annotations

import html as htmlesc
import io
import zipfile
from pathlib import Path

import numpy as np
import plotly.io as pio

from .pipeline import RunData
from .viz import charts as C
from .viz import theme as T


def _fmt(v, spec="{:.3f}"):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    try:
        return spec.format(v)
    except (ValueError, TypeError):
        return str(v)


def _fig_html(fig, first: bool) -> str:
    return pio.to_html(fig, include_plotlyjs="cdn" if first else False, full_html=False,
                       config={"displaylogo": False, "responsive": True})


def build_report(run_dir: Path, symbol: str | None = None, bars: int = 504) -> str:
    rd = RunData(run_dir)
    m = rd.metrics
    cfg = rd.config
    syms = rd.symbols
    synthetic = rd.meta.get("data_source") == "synthetic"
    p, c = m.get("portfolio", {}), m.get("pooled", {})
    parts: list[str] = []
    first = True

    def add(fig, title=None):
        nonlocal first
        if title:
            parts.append(f"<h2>{htmlesc.escape(title)}</h2>")
        parts.append(_fig_html(fig, first))
        first = False

    kpis = [("Sharpe", _fmt(p.get("sharpe"), "{:.2f}")), ("Buy & hold Sharpe", _fmt(p.get("bh_sharpe"), "{:.2f}")),
            ("Sortino", _fmt(p.get("sortino"), "{:.2f}")), ("Max drawdown", _fmt(p.get("max_drawdown"), "{:.1%}")),
            ("CAGR", _fmt(p.get("cagr"), "{:.2%}")), ("Trades", _fmt(p.get("n_trades"), "{}")),
            ("Win rate", _fmt(p.get("win_rate"), "{:.1%}")), ("Expectancy", _fmt(p.get("expectancy_R"), "{:+.2f}R")),
            ("Profit factor", _fmt(p.get("profit_factor"), "{:.2f}")), ("Exposure", _fmt(p.get("exposure"), "{:.1%}")),
            ("OOS ROC AUC", _fmt(c.get("roc_auc"))), ("Brier skill", _fmt(c.get("brier_skill"), "{:+.3f}")),
            ("ECE", _fmt(c.get("ece"))), ("Precision @ thr", _fmt(c.get("precision_at_thr")))]
    tiles = "".join(f"<div class='k'><div class='kl'>{a}</div><div class='kv'>{b}</div></div>" for a, b in kpis)

    eq = rd.equity
    add(C.equity_chart(eq, synthetic), "Equity and drawdown")
    add(C.r_histogram(rd.trades))
    add(C.monthly_heatmap(rd.monthly.rename(columns=int) if len(rd.monthly) else rd.monthly))

    show = [symbol] if symbol else syms
    for s in show:
        v = C.symbol_view(rd, s)
        idx = v["index"][-bars:]
        v = C.symbol_view(rd, s, idx[0], idx[-1])
        add(C.terminal_chart(v, rd.trades[rd.trades["symbol"] == s] if len(rd.trades) else rd.trades,
                             cfg.means.primary_mean, ["kalman", "trend", "ou"], ["zscores", "vol"],
                             synthetic=synthetic, symbol=s, height=900), f"{s} — last {len(idx)} bars")
        cal = m.get("calibration", {}).get(s)
        if cal:
            add(C.calibration_chart(cal, f"{s} reliability (out-of-sample)"))
        mw = rd.frame(s, "meta_weights")
        if len(mw):
            add(C.family_area(mw, f"{s} stacking weights by family (EWMA over retrains)",
                              halflife=cfg.model.importance_halflife))
        imp = rd.frame(s, "importance_smooth")
        if len(imp):
            add(C.importance_bars(imp.iloc[-1], rd.specs, 20, f"{s} smoothed OOS permutation importance (latest)"))

    rows = []
    for s, d in m.get("symbols", {}).items():
        cc, tt = d["classification"], d["trading"]
        rows.append(f"<tr><td>{s}</td><td>{_fmt(cc.get('n'), '{}')}</td><td>{_fmt(cc.get('roc_auc'))}</td>"
                    f"<td>{_fmt(cc.get('brier_skill'), '{:+.3f}')}</td><td>{_fmt(cc.get('ece'))}</td>"
                    f"<td>{_fmt(tt.get('n_trades'), '{}')}</td><td>{_fmt(tt.get('sharpe'), '{:.2f}')}</td>"
                    f"<td>{_fmt(tt.get('expectancy_R'), '{:+.2f}')}</td></tr>")
    table = ("<table><thead><tr><th>symbol</th><th>n</th><th>ROC AUC</th><th>Brier skill</th><th>ECE</th>"
             "<th>trades</th><th>Sharpe</th><th>exp. R</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")
    banner = ("<div class='warn'>SIMULATED DATA — these results validate the system against a known ground truth. "
              "They are not a forecast of market performance.</div>" if synthetic else "")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mean-Reversion Research Report</title>
<style>
:root {{ color-scheme: dark; }}
body {{ background:{T.PAGE}; color:{T.INK2}; font-family:{T.FONT}; margin:0; padding:24px 16px; }}
main {{ max-width:1280px; margin:0 auto; }}
h1 {{ color:{T.INK}; font-weight:600; font-size:20px; margin:0 0 4px; }}
h2 {{ color:{T.INK}; font-weight:500; font-size:14px; margin:28px 0 8px; letter-spacing:.02em; }}
.sub {{ color:{T.MUTED}; font-size:12px; margin-bottom:16px; }}
.warn {{ border:1px solid {T.WARNING}; color:{T.WARNING}; padding:8px 12px; border-radius:6px; font-size:12px;
         margin:12px 0; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; margin:16px 0; }}
.k {{ background:{T.SURFACE}; border:1px solid rgba(255,255,255,.08); border-radius:6px; padding:10px 12px; }}
.kl {{ color:{T.MUTED}; font-size:11px; text-transform:uppercase; letter-spacing:.04em; }}
.kv {{ color:{T.INK}; font-size:18px; margin-top:4px; }}
table {{ border-collapse:collapse; width:100%; font-family:{T.MONO}; font-size:12px; font-variant-numeric:tabular-nums; }}
th, td {{ text-align:right; padding:6px 8px; border-bottom:1px solid {T.GRID}; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ color:{T.MUTED}; font-weight:500; }}
.plotly-graph-div {{ max-width:100%; }}
.scroll {{ overflow-x:auto; }}
</style></head><body><main>
<h1>Mean-reversion research report — {htmlesc.escape(rd.meta.get('run_name', ''))}</h1>
<div class="sub">{', '.join(syms)} · data: {rd.meta.get('data_source')} · out-of-sample from {rd.meta.get('first_test')}
 to {rd.meta.get('last_bar')} · traded mean: {cfg.means.primary_mean} · K = {cfg.label.horizon} bars ·
 walk-forward {rd.meta.get('n_steps')} steps · {rd.meta.get('n_features')} features</div>
{banner}
<div class="kpis">{tiles}</div>
<h2>Per-symbol out-of-sample summary</h2><div class="scroll">{table}</div>
{''.join(parts)}
</main></body></html>"""


def artifact_zip(run_dir: Path, include_checkpoints: bool = False) -> bytes:
    run_dir = Path(run_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in run_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(run_dir)
            if not include_checkpoints and rel.parts[0] == "checkpoints":
                continue
            z.write(p, arcname=str(Path(run_dir.name) / rel))
    return buf.getvalue()
