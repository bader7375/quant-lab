"""Dash callbacks for the research terminal."""
from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, Patch, State, callback_context, dcc, html, no_update

from ..config import MRConfig
from ..pipeline import RunData, list_runs
from ..signals import MEAN_REVERTING, REGIME_NAMES, TRENDING
from ..viz import charts as C
from ..viz import theme as T
from .configform import collect
from .jobs import JOBS

DEFAULT_BARS = 504


@lru_cache(maxsize=8)
def _run(path: str, mtime: float) -> RunData:
    return RunData(Path(path))


def run_data(path: str | None) -> RunData | None:
    if not path:
        return None
    p = Path(path) / "run.json"
    if not p.exists():
        return None
    return _run(path, p.stat().st_mtime)


def fmt(v, spec="{:.3f}", dash="—"):
    if v is None:
        return dash
    try:
        if isinstance(v, (float, np.floating)) and not np.isfinite(v):
            return dash
        return spec.format(v)
    except (ValueError, TypeError):
        return str(v)


def kpi(label, value, note=None, tone=None):
    return html.Div([html.Div(label, className="kpi-label"),
                     html.Div(value, className=f"kpi-value {tone or ''}"),
                     html.Div(note or "", className="kpi-note")], className="kpi")


def empty_fig(msg="no data", height=300):
    f = go.Figure(layout=T.base_layout(height=height))
    f.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                     font=dict(color=T.MUTED, size=12))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return f


def register(app, base_cfg: MRConfig) -> None:
    # ------------------------------------------------------------------ runs
    @app.callback(Output("run-select", "options"), Output("run-select", "value"),
                  Input("store-refresh", "data"), State("run-select", "value"))
    def refresh_runs(_, current):
        runs = [r for r in list_runs(base_cfg) if r.get("status") in ("complete",)]
        opts = [{"label": f"{r['run_name']} · {r.get('data_source', '?')} · Sharpe {fmt(r.get('sharpe'), '{:.2f}')}",
                 "value": r["path"]} for r in runs]
        values = [o["value"] for o in opts]
        job = JOBS.job
        if job and job.state == "done" and job.run_dir in values:
            return opts, job.run_dir
        return opts, current if current in values else (values[0] if values else None)

    @app.callback(Output("symbol-select", "options"), Output("symbol-select", "value"),
                  Output("date-range", "min_date_allowed"), Output("date-range", "max_date_allowed"),
                  Output("date-range", "start_date"), Output("date-range", "end_date"),
                  Output("data-badge", "children"), Output("data-badge", "className"),
                  Output("primary-select", "value"),
                  Input("run-select", "value"), State("symbol-select", "value"))
    def on_run(path, sym):
        rd = run_data(path)
        if rd is None:
            return [], None, None, None, None, None, "no run — press ▶ Run walk-forward", "data-badge", "factor"
        syms = rd.symbols
        sym = sym if sym in syms else (syms[0] if syms else None)
        idx = rd.frame(sym, "signal").index
        src = rd.meta.get("data_source", "?")
        badge = "SIMULATED DATA" if src == "synthetic" else f"LIVE DATA · {src}"
        start = idx[max(0, len(idx) - DEFAULT_BARS)]
        return ([{"label": s, "value": s} for s in syms], sym, idx[0].date(), idx[-1].date(), start.date(),
                idx[-1].date(), badge, "data-badge synthetic" if src == "synthetic" else "data-badge live",
                rd.config.means.primary_mean)

    @app.callback(Output("config-form", "children"), Input("run-select", "value"))
    def on_run_config(path):
        from .configform import build_form
        rd = run_data(path)
        return build_form(rd.config if rd else base_cfg)

    # ------------------------------------------------------------------ chart
    @app.callback(Output("main-graph", "figure"), Output("scrub", "min"), Output("scrub", "max"),
                  Output("scrub", "value"), Output("store-cursor-idx", "data"),
                  Input("run-select", "value"), Input("symbol-select", "value"), Input("date-range", "start_date"),
                  Input("date-range", "end_date"), Input("primary-select", "value"), Input("overlay-select", "value"),
                  Input("pane-a", "value"), Input("pane-b", "value"), Input("pane-c", "value"),
                  State("store-cursor", "data"))
    def draw_chart(path, sym, start, end, primary, overlays, pa, pb, pc, cursor):
        rd = run_data(path)
        if rd is None or not sym:
            return empty_fig("no run loaded", 600), 0, 1, 0, None
        v = C.symbol_view(rd, sym, start, end)
        if not len(v["index"]):
            return empty_fig("empty date range", 600), 0, 1, 0, None
        panes = [p for p in (pa, pb, pc) if p]
        tr = rd.trades
        tr = tr[tr["symbol"] == sym] if len(tr) else tr
        fig = C.terminal_chart(v, tr, primary or "factor", overlays or [], panes,
                               synthetic=rd.meta.get("data_source") == "synthetic", symbol=sym,
                               height=640 + 120 * len(panes))
        n = len(v["index"])
        cur = pd.Timestamp(cursor) if cursor else v["index"][-1]
        pos = int(np.clip(v["index"].searchsorted(cur), 0, n - 1))
        shapes = list(fig.layout.shapes or [])
        fig.add_shape(type="line", xref="x", yref="paper", x0=v["index"][pos], x1=v["index"][pos], y0=0, y1=1,
                      line=dict(color=T.rgba(T.WARNING, 0.7), width=1))
        return fig, 0, n - 1, pos, len(shapes)

    @app.callback(Output("store-cursor", "data"), Output("store-pinned", "data"),
                  Input("main-graph", "hoverData"), Input("main-graph", "clickData"), Input("scrub", "value"),
                  State("store-pinned", "data"), State("run-select", "value"), State("symbol-select", "value"),
                  State("date-range", "start_date"), State("date-range", "end_date"))
    def move_cursor(hover, click, scrub, pinned, path, sym, start, end):
        trig = callback_context.triggered_id
        if trig == "main-graph" and callback_context.triggered[0]["prop_id"].endswith("clickData"):
            if click and click.get("points"):
                return str(pd.Timestamp(click["points"][0]["x"]).date()), not pinned
        if trig == "main-graph":
            if pinned or not hover or not hover.get("points"):
                return no_update, no_update
            return str(pd.Timestamp(hover["points"][0]["x"]).date()), no_update
        if trig == "scrub":
            rd = run_data(path)
            if rd is None or not sym:
                return no_update, no_update
            idx = C.symbol_view(rd, sym, start, end)["index"]
            if not len(idx):
                return no_update, no_update
            return str(idx[int(np.clip(scrub or 0, 0, len(idx) - 1))].date()), no_update
        return no_update, no_update

    @app.callback(Output("main-graph", "figure", allow_duplicate=True), Input("store-cursor", "data"),
                  State("store-cursor-idx", "data"), prevent_initial_call=True)
    def move_cursor_line(cursor, idx):
        if cursor is None or idx is None:
            return no_update
        p = Patch()
        p["layout"]["shapes"][idx]["x0"] = cursor
        p["layout"]["shapes"][idx]["x1"] = cursor
        return p

    @app.callback(Output("inspector", "children"), Input("store-cursor", "data"), Input("run-select", "value"),
                  Input("symbol-select", "value"), State("store-pinned", "data"))
    def inspector(cursor, path, sym, pinned):
        rd = run_data(path)
        if rd is None or not sym:
            return html.Div("hover the chart to inspect a bar", className="insp-empty")
        return build_inspector(rd, sym, cursor, pinned)

    # ------------------------------------------------------------------ model tab
    @app.callback(Output("model-cards", "children"), Input("run-select", "value"), Input("tabs", "value"))
    def model_cards(path, tab):
        rd = run_data(path)
        if rd is None or tab != "model":
            return no_update if tab != "model" else html.Div("no run")
        m = rd.metrics
        cards = []
        for s in rd.symbols:
            d = m.get("symbols", {}).get(s, {})
            cc, tt = d.get("classification", {}), d.get("trading", {})
            cal = m.get("calibration", {}).get(s, {})
            mw = rd.frame(s, "meta_weights")
            cards.append(html.Div([
                html.Div([html.Span(s, className="card-sym"),
                          html.Span(f"{cc.get('n', 0)} OOS samples · base rate {fmt(cc.get('base_rate'), '{:.2f}')}",
                                    className="card-sub")], className="card-head"),
                html.Div([kpi("ROC AUC", fmt(cc.get("roc_auc"))), kpi("PR AUC", fmt(cc.get("pr_auc"))),
                          kpi("Brier", fmt(cc.get("brier"), "{:.4f}"), f"skill {fmt(cc.get('brier_skill'), '{:+.3f}')}",
                              "pos" if (cc.get("brier_skill") or 0) > 0 else "neg"),
                          kpi("ECE", fmt(cc.get("ece"))),
                          kpi("Prec@thr", fmt(cc.get("precision_at_thr")), f"cov {fmt(cc.get('coverage_at_thr'), '{:.0%}')}"),
                          kpi("Sharpe", fmt(tt.get("sharpe"), "{:.2f}"), f"{tt.get('n_trades', 0)} trades"),
                          kpi("Win", fmt(tt.get("win_rate"), "{:.0%}")), kpi("Exp.", fmt(tt.get("expectancy_R"), "{:+.2f}R")),
                          kpi("PF", fmt(tt.get("profit_factor"), "{:.2f}")), kpi("Max DD", fmt(tt.get("max_drawdown"), "{:.1%}"))],
                         className="kpi-grid"),
                html.Div([dcc.Graph(figure=C.calibration_chart(cal, "reliability"), config={"displayModeBar": False},
                                    className="card-graph"),
                          dcc.Graph(figure=C.family_area(mw, "family weights (stacking), EWMA over retrains",
                                                         halflife=rd.config.model.importance_halflife)
                                    if len(mw) else empty_fig("no retrains", 280),
                                    config={"displayModeBar": False}, className="card-graph")], className="card-graphs"),
            ], className="card"))
        return cards

    @app.callback(Output("imp-step", "min"), Output("imp-step", "max"), Output("imp-step", "value"),
                  Output("imp-step", "marks"), Input("run-select", "value"), Input("symbol-select", "value"))
    def imp_slider(path, sym):
        rd = run_data(path)
        if rd is None or not sym:
            return 0, 1, 1, None
        imp = rd.frame(sym, "importance_smooth")
        n = len(imp)
        if n == 0:
            return 0, 1, 1, None
        step = max(1, n // 8)
        marks = {i: str(pd.Timestamp(imp.index[i]).year) for i in range(0, n, step)}
        return 0, n - 1, n - 1, marks

    @app.callback(Output("imp-title", "children"), Output("imp-bars", "figure"), Output("meta-weights", "figure"),
                  Output("fam-importance", "figure"), Output("imp-heat", "figure"), Output("calib-detail", "figure"),
                  Output("roc-detail", "figure"), Output("step-table", "data"), Output("step-table", "columns"),
                  Input("run-select", "value"), Input("symbol-select", "value"), Input("imp-step", "value"),
                  Input("tabs", "value"))
    def model_detail(path, sym, step, tab):
        if tab != "model":
            return (no_update,) * 9
        rd = run_data(path)
        if rd is None or not sym:
            e = empty_fig()
            return "", e, e, e, e, e, e, [], []
        imp = rd.frame(sym, "importance_smooth")
        raw = rd.frame(sym, "importance")
        title = f"{sym} · feature weights: out-of-sample permutation importance, EWMA-smoothed across retrains"
        if len(imp):
            i = int(np.clip(step if step is not None else len(imp) - 1, 0, len(imp) - 1))
            date = pd.Timestamp(imp.index[i]).date()
            n_raw = int(raw.loc[:imp.index[i]].shape[0]) if len(raw) else 0
            bars = C.importance_bars(imp.iloc[i], rd.specs, 25,
                                     f"as of retrain {date} · {n_raw} OOS readings folded in")
        else:
            bars = empty_fig("importance appears after the second retrain")
        mw = rd.frame(sym, "meta_weights")
        fam = rd.frame(sym, "family_importance_smooth")
        hl = rd.config.model.importance_halflife
        meta_fig = C.family_area(mw, f"stacking weight share by family model (EWMA, halflife {hl:g} retrains)",
                                 halflife=hl) if len(mw) else empty_fig()
        fam_fig = C.family_area(fam, "smoothed family permutation importance (Δ log-loss)", normalize=False) \
            if len(fam) else empty_fig()
        heat = C.importance_heatmap(imp, rd.specs, 30) if len(imp) else empty_fig()
        cal = rd.metrics.get("calibration", {}).get(sym, {})
        P, L = rd.frame(sym, "predictions"), rd.frame(sym, "labels").reindex(rd.frame(sym, "predictions").index)
        m = L["in_domain"].fillna(False).astype(bool) & L["y"].notna() & P["p"].notna() if len(P) else []
        roc = C.roc_pr_chart(L.loc[m, "y"].to_numpy(), P.loc[m, "p"].to_numpy()) if len(P) else empty_fig()
        summ = rd.frame(sym, "summaries")
        cols, data = [], []
        if len(summ):
            s2 = summ.reset_index().rename(columns={"index": "date"})
            s2["date"] = pd.to_datetime(s2["date"]).dt.date.astype(str)
            keep = [c for c in ("date", "n", "n_own", "base_rate", "gbm_rounds", "payoff_b", "features", "eval_n",
                                "eval_loss", "seconds") if c in s2]
            s2 = s2[keep].round(4)
            cols = [{"name": c, "id": c} for c in keep]
            data = s2.to_dict("records")
        return (title, bars, meta_fig, fam_fig, heat, C.calibration_chart(cal, f"{sym} reliability"), roc, data, cols)

    # ------------------------------------------------------------------ performance
    @app.callback(Output("perf-kpis", "children"), Output("equity-graph", "figure"), Output("rhist-graph", "figure"),
                  Output("exit-graph", "figure"), Output("monthly-graph", "figure"), Output("symbol-table", "data"),
                  Output("symbol-table", "columns"), Input("run-select", "value"), Input("tabs", "value"))
    def perf(path, tab):
        if tab != "perf":
            return (no_update,) * 7
        rd = run_data(path)
        if rd is None:
            e = empty_fig()
            return [], e, e, e, e, [], []
        p, c = rd.metrics.get("portfolio", {}), rd.metrics.get("pooled", {})
        tone = lambda v: "pos" if (v or 0) > 0 else "neg"  # noqa: E731
        kp = [kpi("Sharpe", fmt(p.get("sharpe"), "{:.2f}"), f"buy&hold {fmt(p.get('bh_sharpe'), '{:.2f}')}", tone(p.get("sharpe"))),
              kpi("Sortino", fmt(p.get("sortino"), "{:.2f}")), kpi("CAGR", fmt(p.get("cagr"), "{:.2%}")),
              kpi("Max DD", fmt(p.get("max_drawdown"), "{:.1%}"), f"buy&hold {fmt(p.get('bh_max_drawdown'), '{:.1%}')}"),
              kpi("Calmar", fmt(p.get("calmar"), "{:.2f}")), kpi("Trades", fmt(p.get("n_trades"), "{}"),
                                                                  f"{fmt(p.get('trades_per_year'), '{:.1f}')}/yr"),
              kpi("Win rate", fmt(p.get("win_rate"), "{:.1%}")),
              kpi("Expectancy", fmt(p.get("expectancy_R"), "{:+.2f}R"), f"median {fmt(p.get('median_R'), '{:+.2f}R')}",
                  tone(p.get("expectancy_R"))),
              kpi("Profit factor", fmt(p.get("profit_factor"), "{:.2f}")),
              kpi("Exposure", fmt(p.get("exposure"), "{:.1%}"), f"gross {fmt(p.get('avg_gross_leverage'), '{:.2f}')}x"),
              kpi("Corr to B&H", fmt(p.get("corr_to_bh"), "{:+.2f}")),
              kpi("OOS AUC", fmt(c.get("roc_auc")), f"Brier skill {fmt(c.get('brier_skill'), '{:+.3f}')}")]
        eq = rd.equity
        synthetic = rd.meta.get("data_source") == "synthetic"
        tr = rd.trades
        ex = empty_fig("no trades", 260)
        if len(tr):
            vc = tr.groupby("exit_reason")["R"].agg(["count", "mean"]).sort_values("count")
            ex = go.Figure(go.Bar(x=vc["count"], y=vc.index, orientation="h",
                                  marker=dict(color=[T.GOOD if m_ > 0 else T.CRITICAL for m_ in vc["mean"]],
                                              line=dict(width=0)),
                                  text=[f"{m_:+.2f}R avg" for m_ in vc["mean"]], textposition="outside",
                                  textfont=dict(color=T.INK2, size=10),
                                  hovertemplate="%{y}: %{x} trades<extra></extra>"))
            ex.update_layout(**T.base_layout(height=260, margin=dict(l=70, r=60, t=40, b=30)),
                             title=dict(text="Exits by reason (colour = average R sign)", font=dict(size=12, color=T.INK2), x=0.01))
        rows = []
        for s, d in rd.metrics.get("symbols", {}).items():
            cc, tt = d["classification"], d["trading"]
            rows.append({"symbol": s, "signals": d.get("signals"), "trades": tt.get("n_trades"),
                         "pnl": round(tt.get("pnl", 0), 0), "sharpe": fmt(tt.get("sharpe"), "{:.2f}"),
                         "win": fmt(tt.get("win_rate"), "{:.1%}"), "exp_R": fmt(tt.get("expectancy_R"), "{:+.2f}"),
                         "PF": fmt(tt.get("profit_factor"), "{:.2f}"), "max_dd": fmt(tt.get("max_drawdown"), "{:.1%}"),
                         "auc": fmt(cc.get("roc_auc")), "brier_skill": fmt(cc.get("brier_skill"), "{:+.3f}")})
        cols = [{"name": k, "id": k} for k in (rows[0].keys() if rows else [])]
        mr = rd.monthly
        return (kp, C.equity_chart(eq, synthetic), C.r_histogram(tr), ex, C.monthly_heatmap(mr), rows, cols)

    # ------------------------------------------------------------------ trades & log
    @app.callback(Output("trades-table", "data"), Output("trades-table", "columns"),
                  Input("run-select", "value"), Input("symbol-select", "value"), Input("trades-filter", "value"),
                  Input("tabs", "value"))
    def trades_table(path, sym, flt, tab):
        if tab != "trades":
            return no_update, no_update
        rd = run_data(path)
        if rd is None or not len(rd.trades):
            return [], []
        t = rd.trades.copy()
        if flt and "sym" in flt and sym:
            t = t[t["symbol"] == sym]
        for c in ("signal_date", "entry_date", "exit_signal_date", "exit_date"):
            t[c] = pd.to_datetime(t[c]).dt.date.astype(str)
        t["regime"] = t["regime"].map(lambda r: REGIME_NAMES.get(int(r), "?") if pd.notna(r) else "?")
        keep = ["trade_id", "symbol", "direction", "entry_date", "exit_date", "bars_held", "exit_reason", "entry_price",
                "exit_price", "R", "pnl", "ret_on_notional", "weight", "p", "p_lo", "p_hi", "z_entry", "z_exit",
                "regime", "confluence", "mae_R", "mfe_R", "hedge"]
        t = t[[c for c in keep if c in t]]
        num = t.select_dtypes("number").columns
        t[num] = t[num].round(4)
        return t.to_dict("records"), [{"name": c, "id": c} for c in t.columns]

    @app.callback(Output("log-pre", "children"), Input("tabs", "value"), Input("run-select", "value"),
                  Input("job-interval", "n_intervals"))
    def log_view(tab, path, _):
        if tab != "log":
            return no_update
        out = []
        if JOBS.job:
            out.append("── current job ──\n" + "\n".join(JOBS.job.history[-40:]))
        rd = run_data(path)
        if rd is not None:
            out.append("── run.json ──\n" + json.dumps(rd.meta, indent=2))
            lp = rd.dir / "run.log"
            if lp.exists():
                out.append("── run.log (tail) ──\n" + "\n".join(lp.read_text().splitlines()[-80:]))
        return "\n\n".join(out) or "no run"

    # ------------------------------------------------------------------ jobs
    @app.callback(Output("job-interval", "disabled"), Output("config-errors", "children"),
                  Input("btn-run", "n_clicks"), Input("btn-backtest", "n_clicks"), Input("btn-stop", "n_clicks"),
                  State({"type": "cfg", "key": ALL}, "id"), State({"type": "cfg", "key": ALL}, "value"),
                  State("run-select", "value"), prevent_initial_call=True)
    def jobs(n_run, n_bt, n_stop, ids, values, path):
        trig = callback_context.triggered_id
        if trig == "btn-stop":
            JOBS.request_stop()
            return False, ""
        rd = run_data(path)
        base = rd.config if rd else base_cfg
        cfg, errors = collect(ids, values, base)
        if errors:
            return True, html.Ul([html.Li(e) for e in errors])
        if JOBS.busy():
            return False, "a job is already running"
        try:
            if trig == "btn-run":
                cfg.run_name = None if (rd is None or cfg.model_hash() != rd.config.model_hash()) else rd.dir.name
                JOBS.start_run(cfg)
            elif trig == "btn-backtest":
                if rd is None:
                    return True, "no run selected"
                if cfg.model_hash() != rd.config.model_hash():
                    return True, ("model-defining settings changed (sections marked 'retrains'); "
                                  "use ▶ Run walk-forward")
                JOBS.start_trading(rd.dir, cfg)
        except Exception as exc:  # noqa: BLE001
            return True, str(exc)
        return False, ""

    @app.callback(Output("job-bar", "style"), Output("job-status", "children"), Output("store-refresh", "data"),
                  Output("job-interval", "disabled", allow_duplicate=True),
                  Input("job-interval", "n_intervals"), State("store-refresh", "data"), prevent_initial_call=True)
    def poll(_, refresh):
        job = JOBS.job
        if job is None:
            return {"width": "0%"}, "", no_update, True
        el = (job.finished or time.time()) - job.started
        style = {"width": f"{job.frac * 100:.0f}%"}
        if job.state == "running":
            return style, f"{job.kind} · {job.frac:.0%} · {job.message} · {el:.0f}s", no_update, False
        if job.state == "failed":
            return {"width": "100%", "background": T.CRITICAL}, f"{job.kind} failed: {job.error}", no_update, True
        return style, f"{job.kind} {job.state} in {el:.0f}s", (refresh or 0) + 1, True

    # ------------------------------------------------------------------ exports
    @app.callback(Output("dl", "data"), Input("btn-export-trades", "n_clicks"),
                  Input("btn-export-artifacts", "n_clicks"), Input("btn-export-chart", "n_clicks"),
                  Input("btn-export-report", "n_clicks"), State("run-select", "value"), State("main-graph", "figure"),
                  State("symbol-select", "value"), prevent_initial_call=True)
    def exports(a, b, c, d, path, fig, sym):
        rd = run_data(path)
        if rd is None:
            return no_update
        trig = callback_context.triggered_id
        name = rd.dir.name
        if trig == "btn-export-trades":
            return dcc.send_data_frame(rd.trades.to_csv, f"{name}_trades.csv", index=False)
        if trig == "btn-export-artifacts":
            from ..report import artifact_zip
            return dcc.send_bytes(artifact_zip(rd.dir), f"{name}_artifacts.zip")
        if trig == "btn-export-chart" and fig:
            html_str = go.Figure(fig).to_html(include_plotlyjs="cdn", config={"displaylogo": False})
            return dict(content=html_str, filename=f"{name}_{sym}_chart.html")
        if trig == "btn-export-report":
            from ..report import build_report
            return dict(content=build_report(rd.dir), filename=f"{name}_report.html")
        return no_update


# ----------------------------------------------------------------------------
# inspector
# ----------------------------------------------------------------------------

def _pill(z):
    if z is None or not np.isfinite(z):
        return html.Span("—", className="pill")
    return html.Span(f"{z:+.2f}σ", className="pill", style={"background": T.zone_color(z), "color": T.INK})


def build_inspector(rd: RunData, sym: str, cursor, pinned) -> list:
    sig = rd.frame(sym, "signal")
    if not len(sig):
        return [html.Div("no data", className="insp-empty")]
    d = pd.Timestamp(cursor) if cursor else sig.index[-1]
    pos = int(np.clip(sig.index.searchsorted(d), 0, len(sig) - 1))
    d = sig.index[pos]
    S = sig.iloc[pos]
    M = rd.frame(sym, "means").loc[d]
    F = rd.frame(sym, "features").loc[d] if d in rd.frame(sym, "features").index else None
    P = rd.frame(sym, "predictions")
    Dd = rd.frame(sym, "decisions")
    L = rd.frame(sym, "labels")
    pr = P.loc[d] if d in P.index else None
    dec = Dd.loc[d] if d in Dd.index else None
    lab = L.loc[d] if d in L.index else None
    cfg = rd.config

    out = [html.Div([html.Span(sym, className="insp-sym"), html.Span(str(d.date()), className="insp-date"),
                     html.Span("PINNED" if pinned else "live", className="insp-pin" + (" on" if pinned else ""))],
                    className="insp-head")]

    # probability & decision --------------------------------------------------------
    if pr is not None and np.isfinite(pr.get("p", np.nan)):
        reg = int(dec["regime"]) if dec is not None and np.isfinite(dec["regime"]) else 0
        reg_cls = {MEAN_REVERTING: "st-good", TRENDING: "st-crit"}.get(reg, "st-warn")
        reg_txt = {MEAN_REVERTING: "● armed · mean-reverting", TRENDING: "● disarmed · trending"}.get(reg, "● neutral")
        thr = dec["thr"] if dec is not None else np.nan
        gates = []
        if dec is not None:
            for key, lab_ in (("gate_stretch", f"|z| ≥ {cfg.signal.entry_z}"), ("gate_prob", f"P ≥ {fmt(thr, '{:.2f}')}"
                                                                                           + (" (lower bound)" if cfg.signal.require_lower_bound else "")),
                              ("gate_confluence", f"confluence ≥ {cfg.signal.min_confluence}"), ("gate_regime", "regime armed")):
                ok = bool(dec[key])
                gates.append(html.Div([html.Span("✓" if ok else "✗", className="g-ok" if ok else "g-no"), lab_],
                                      className="gate"))
            action = ("ENTER " + ("LONG" if dec["dir"] > 0 else "SHORT")) if bool(dec["entry"]) else "no entry"
        else:
            action = "—"
        out += [
            html.Div([
                html.Div([html.Div("P(revert ≤ K)", className="kpi-label"),
                          html.Div(fmt(pr["p"]), className="big-p"),
                          html.Div(f"[{fmt(pr['p_lo'])}, {fmt(pr['p_hi'])}]", className="kpi-note")]),
                html.Div([html.Div("decision", className="kpi-label"),
                          html.Div(action, className="action" + (" on" if action.startswith("ENTER") else "")),
                          html.Div(reg_txt, className=f"kpi-note {reg_cls}")]),
            ], className="insp-top"),
            html.Div(gates, className="gates"),
            html.Div([html.Span(f"exp. gap recovered {fmt(pr.get('exp_gap'), '{:.0%}')}"),
                      html.Span(f"payoff b {fmt(pr.get('payoff_b'), '{:.2f}')}"),
                      html.Span(f"size {fmt(dec['weight'] if dec is not None else None, '{:.2f}')}x eq")],
                     className="insp-line"),
        ]
    else:
        out.append(html.Div("no out-of-sample prediction for this bar (warm-up / before first test block)",
                            className="insp-empty"))

    # deviation by mean -------------------------------------------------------------------
    rows = []
    for name in ("factor", "kalman", "ou", "trend", "ou_res", "ema_20", "sma_20"):
        z = M.get(f"{name}_z", np.nan)
        lvl = M.get(f"{name}_level", np.nan)
        rows.append(html.Tr([html.Td(html.Span("■", style={"color": T.MEAN_COLORS.get(name, T.INK2)})),
                             html.Td(T.MEAN_LABELS.get(name, name)), html.Td(_pill(z)),
                             html.Td(fmt(np.exp(lvl) if np.isfinite(lvl) else None, "{:.2f}"), className="num")]))
    out += [html.Div("deviation by mean definition", className="insp-sec"),
            html.Table(rows, className="insp-table"),
            html.Div([html.Span(f"s-score HL {fmt(M.get('ss_halflife'), '{:.1f}')}b"),
                      html.Span(f"resid HL {fmt(M.get('oures_halflife'), '{:.1f}')}b "
                                f"[{fmt(M.get('oures_hl_lo'), '{:.0f}')}–{fmt(M.get('oures_hl_hi'), '{:.0f}')}]"),
                      html.Span(f"confluence {fmt(S.get('confluence'), '{:.0f}')}")], className="insp-line")]

    # family probabilities ----------------------------------------------------------------------
    if pr is not None:
        fam_cols = [c for c in P.columns if c.startswith("fam_")]
        if fam_cols:
            bars = []
            for c in fam_cols:
                v = pr[c]
                name = c[4:]
                col = T.FAMILY_COLORS.get(name, T.INK2)
                bars.append(html.Div([html.Span(name, className="fb-name"),
                                      html.Div(html.Div(style={"width": f"{(v if np.isfinite(v) else 0) * 100:.0f}%",
                                                               "background": col}, className="fb-fill"),
                                               className="fb-track"),
                                      html.Span(fmt(v, "{:.2f}"), className="fb-val")], className="fb"))
            out += [html.Div("family-model probabilities", className="insp-sec"), html.Div(bars)]

    # SHAP ---------------------------------------------------------------------------------------
    sh = rd.frame(sym, "shap")
    if pr is not None and len(sh) and d in sh.index:
        row = sh.loc[d]
        base = float(row.get("shap_base", 0.0))
        contrib = row.drop(labels=["shap_base"], errors="ignore").astype(float)
        out += [html.Div("what drove the score (exact SHAP, log-odds)", className="insp-sec"),
                dcc.Graph(figure=C.shap_waterfall(contrib, base, float(pr["p"]), rd.specs, 10),
                          config={"displayModeBar": False}, className="shap-graph")]

    # hindsight ---------------------------------------------------------------------------------
    if lab is not None and np.isfinite(lab.get("y", np.nan)):
        out.append(html.Div([
            html.Span("hindsight (not known at the time): ", className="muted"),
            html.Span(f"{'reverted' if lab['y'] == 1 else 'failed'} · {lab['exit_reason']} after {int(lab['tau'])} bars · "
                      f"gap recovered {fmt(lab['gap_frac'], '{:.0%}')}")], className="insp-line hindsight"))

    # all features by family -------------------------------------------------------------------------
    if F is not None:
        groups: dict[str, list] = {}
        for f, spec in rd.specs.items():
            if f in F.index:
                groups.setdefault(spec.family, []).append(
                    html.Tr([html.Td(f, title=spec.desc, className="fname"), html.Td(fmt(F[f]), className="num")]))
        out.append(html.Div("all features (oriented to the trade; hover a name for its meaning)", className="insp-sec"))
        for fam, trs in groups.items():
            out.append(html.Details([html.Summary([html.Span("■", style={"color": T.FAMILY_COLORS.get(fam, T.INK2)}),
                                                   f" {fam} ({len(trs)})"]),
                                     html.Table(trs, className="insp-table feat")], className="fam-group"))
    return out
