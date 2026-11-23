"""Terminal layout: header controls, config sidebar, tabbed workspace."""
from __future__ import annotations

from dash import dash_table, dcc, html

from ..config import MRConfig
from ..viz.charts import PANES
from ..viz.theme import MEAN_LABELS
from .configform import build_form

GRAPH_CONFIG = {"displaylogo": False, "scrollZoom": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
                "toImageButtonOptions": {"format": "png", "scale": 2}}

MEAN_OPTIONS = [{"label": MEAN_LABELS[k], "value": k} for k in ("factor", "kalman", "ou", "trend", "ou_res", "ema_20")]
PANE_OPTIONS = [{"label": v, "value": k} for k, v in PANES.items()]


def _kpi(id_: str) -> html.Div:
    return html.Div(id=id_, className="kpi-row")


def header() -> html.Div:
    return html.Div([
        html.Div([html.Span("QUANTLAB", className="brand"), html.Span("mean-reversion research terminal",
                                                                       className="brand-sub")], className="brand-box"),
        html.Div([html.Label("run"), dcc.Dropdown(id="run-select", clearable=False, className="hdr-dd hdr-run")],
                 className="hdr-field"),
        html.Div([html.Label("symbol"), dcc.Dropdown(id="symbol-select", clearable=False, className="hdr-dd")],
                 className="hdr-field"),
        html.Div([html.Label("range"), dcc.DatePickerRange(id="date-range", display_format="YYYY-MM-DD",
                                                           className="hdr-dates")], className="hdr-field"),
        html.Div([html.Label("traded mean"), dcc.Dropdown(id="primary-select", options=MEAN_OPTIONS, value="factor",
                                                          clearable=False, className="hdr-dd")], className="hdr-field"),
        html.Div(id="data-badge", className="data-badge"),
        html.Div([
            html.Button("▶ Run walk-forward", id="btn-run", className="btn btn-primary",
                        title="Full run with the sidebar config (resumes from checkpoints when the model config matches)"),
            html.Button("↻ Re-run backtest", id="btn-backtest", className="btn",
                        title="Re-derive signals, backtest and metrics from stored predictions with the sidebar's "
                              "regime / signal / risk / exit settings. No retraining."),
            html.Button("■", id="btn-stop", className="btn btn-ghost", title="Stop after the current step"),
        ], className="hdr-actions"),
        html.Div([html.Div(html.Div(id="job-bar", className="job-bar-fill"), className="job-bar"),
                  html.Div(id="job-status", className="job-status")], className="job-box"),
    ], className="header")


def chart_tab() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Label("overlay means"),
                    dcc.Checklist(id="overlay-select", options=MEAN_OPTIONS, value=["kalman", "trend", "ou"],
                                  inline=True, className="chk"),
                ], className="ctl"),
                html.Div([html.Label("feature panes"),
                          dcc.Dropdown(id="pane-a", options=PANE_OPTIONS, value="zscores", clearable=True,
                                       className="pane-dd"),
                          dcc.Dropdown(id="pane-b", options=PANE_OPTIONS, value="vol", clearable=True, className="pane-dd"),
                          dcc.Dropdown(id="pane-c", options=PANE_OPTIONS, value="halflife", clearable=True,
                                       className="pane-dd")], className="ctl ctl-panes"),
            ], className="chart-controls"),
            dcc.Loading(dcc.Graph(id="main-graph", config=GRAPH_CONFIG, className="main-graph"),
                        type="dot", color="#9085e9", delay_show=400),
            html.Div([html.Label("scrub", className="scrub-label"),
                      html.Div(dcc.Slider(id="scrub", min=0, max=1, step=1, value=1, marks=None, updatemode="drag",
                                          tooltip={"placement": "top", "always_visible": False}),
                               className="scrub-slider")], className="scrub-row"),
        ], className="chart-col"),
        html.Div(id="inspector", className="inspector"),
    ], className="chart-tab")


def model_tab() -> html.Div:
    return html.Div([
        html.H3("Out-of-sample report cards", className="sec-title"),
        html.Div(id="model-cards", className="cards"),
        html.H3(id="imp-title", className="sec-title"),
        html.Div([
            html.Div([html.Label("retrain step", className="scrub-label"),
                      html.Div(dcc.Slider(id="imp-step", min=0, max=1, step=1, value=1, marks=None,
                                          tooltip={"placement": "top", "always_visible": False}),
                               className="scrub-slider")], className="scrub-row"),
            html.Div([
                dcc.Graph(id="imp-bars", config=GRAPH_CONFIG, className="half"),
                html.Div([dcc.Graph(id="meta-weights", config=GRAPH_CONFIG),
                          dcc.Graph(id="fam-importance", config=GRAPH_CONFIG)], className="half"),
            ], className="split"),
            dcc.Graph(id="imp-heat", config=GRAPH_CONFIG),
            html.Div([dcc.Graph(id="calib-detail", config=GRAPH_CONFIG, className="half"),
                      dcc.Graph(id="roc-detail", config=GRAPH_CONFIG, className="half")], className="split"),
            html.H3("Walk-forward steps", className="sec-title"),
            dash_table.DataTable(id="step-table", page_size=12, sort_action="native", style_as_list_view=True,
                                 style_table={"overflowX": "auto"}, **_table_style()),
        ]),
    ], className="tab-body")


def perf_tab() -> html.Div:
    return html.Div([
        _kpi("perf-kpis"),
        dcc.Graph(id="equity-graph", config=GRAPH_CONFIG),
        html.Div([dcc.Graph(id="rhist-graph", config=GRAPH_CONFIG, className="half"),
                  dcc.Graph(id="exit-graph", config=GRAPH_CONFIG, className="half")], className="split"),
        dcc.Graph(id="monthly-graph", config=GRAPH_CONFIG),
        html.H3("Per-symbol attribution", className="sec-title"),
        dash_table.DataTable(id="symbol-table", sort_action="native", style_as_list_view=True, **_table_style()),
    ], className="tab-body")


def trades_tab() -> html.Div:
    return html.Div([
        html.Div([dcc.Checklist(id="trades-filter", options=[{"label": "selected symbol only", "value": "sym"}],
                                value=[], inline=True, className="chk")], className="ctl"),
        dash_table.DataTable(id="trades-table", page_size=25, sort_action="native", filter_action="native",
                             style_as_list_view=True, style_table={"overflowX": "auto"}, **_table_style()),
    ], className="tab-body")


def log_tab() -> html.Div:
    return html.Div([html.Pre(id="log-pre", className="log-pre")], className="tab-body")


def _table_style() -> dict:
    return dict(
        style_header={"backgroundColor": "#141413", "color": "#898781", "border": "none",
                      "borderBottom": "1px solid #2c2c2a", "fontWeight": "500", "fontSize": "11px",
                      "textTransform": "uppercase", "letterSpacing": "0.04em"},
        style_cell={"backgroundColor": "#1a1a19", "color": "#c3c2b7", "border": "none",
                    "borderBottom": "1px solid #232321", "fontFamily": "'JetBrains Mono', ui-monospace, monospace",
                    "fontSize": "11px", "padding": "4px 8px", "fontVariantNumeric": "tabular-nums",
                    "maxWidth": "220px", "overflow": "hidden", "textOverflow": "ellipsis"},
        style_filter={"backgroundColor": "#141413", "color": "#ffffff"},
        style_data_conditional=[{"if": {"state": "active"}, "backgroundColor": "#242423",
                                 "border": "1px solid #3987e5"}],
    )


def build_layout(cfg: MRConfig) -> html.Div:
    return html.Div([
        dcc.Store(id="store-refresh", data=0),
        dcc.Store(id="store-cursor"),
        dcc.Store(id="store-pinned", data=False),
        dcc.Store(id="store-cursor-idx"),
        dcc.Interval(id="job-interval", interval=700, disabled=True),
        dcc.Download(id="dl"),
        header(),
        html.Div([
            html.Div([
                html.Div([html.Span("CONFIG", className="side-title"),
                          html.Span("hover a label for its meaning", className="side-hint")], className="side-head"),
                html.Div(build_form(cfg), id="config-form"),
                html.Div(id="config-errors", className="config-errors"),
                html.Div([
                    html.Div("EXPORT", className="side-title"),
                    html.Button("Trades CSV", id="btn-export-trades", className="btn btn-block"),
                    html.Button("Model artifacts (.zip)", id="btn-export-artifacts", className="btn btn-block"),
                    html.Button("Chart (.html)", id="btn-export-chart", className="btn btn-block"),
                    html.Button("Full report (.html)", id="btn-export-report", className="btn btn-block"),
                ], className="export-box"),
            ], className="sidebar"),
            html.Div([
                dcc.Tabs(id="tabs", value="chart", className="tabs", children=[
                    dcc.Tab(label="Chart", value="chart", children=chart_tab(), className="tab",
                            selected_className="tab-sel"),
                    dcc.Tab(label="Model", value="model", children=model_tab(), className="tab",
                            selected_className="tab-sel"),
                    dcc.Tab(label="Performance", value="perf", children=perf_tab(), className="tab",
                            selected_className="tab-sel"),
                    dcc.Tab(label="Trades", value="trades", children=trades_tab(), className="tab",
                            selected_className="tab-sel"),
                    dcc.Tab(label="Run log", value="log", children=log_tab(), className="tab",
                            selected_className="tab-sel"),
                ]),
            ], className="workspace"),
        ], className="body"),
    ], className="app")
