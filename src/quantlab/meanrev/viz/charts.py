"""Plotly figure builders for the research terminal.

The main chart is one figure with a shared x-axis, so a single crosshair
spans every pane (``hoversubplots="axis"`` + ``spikemode="across"``) and
zooming any pane zooms all of them::

    price      candles, mean ribbon (+/-1/2/3 sigma zones), other means, trades
    volume     bars coloured by the deviation zone of that day
    P(revert)  calibrated probability, confidence band, regime-adjusted threshold
    regime     Hurst, ADF p-value, VR(4) on one dimensionless axis; armed strip
    panes...   user-selected feature panels (z-scores, vol estimators, ...)

No pane ever has two y-scales; quantities with different units get their own
pane.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..features.volatility import range_vols
from ..signals import MEAN_REVERTING, TRENDING
from . import theme as T

# --------------------------------------------------------------------------
# data assembly
# --------------------------------------------------------------------------


def symbol_view(rd, symbol: str, start=None, end=None) -> dict[str, pd.DataFrame]:
    """Slice every per-symbol frame of a run to [start, end]."""
    bars = rd.bars(symbol)
    v = {"bars": bars, "means": rd.frame(symbol, "means"), "signal": rd.frame(symbol, "signal"),
         "features": rd.frame(symbol, "features"), "pred": rd.frame(symbol, "predictions"),
         "dec": rd.frame(symbol, "decisions"), "labels": rd.frame(symbol, "labels")}
    idx = v["signal"].index
    lo = pd.Timestamp(start) if start else idx[0]
    hi = pd.Timestamp(end) if end else idx[-1]
    out = {}
    for k, df in v.items():
        out[k] = df.loc[(df.index >= lo) & (df.index <= hi)] if len(df) else df
    out["index"] = out["signal"].index
    return out


def _rangebreaks(idx: pd.DatetimeIndex) -> list[dict]:
    if len(idx) < 2:
        return []
    full = pd.bdate_range(idx[0], idx[-1])
    missing = full.difference(idx)
    rb = [dict(bounds=["sat", "mon"])]
    if len(missing):
        rb.append(dict(values=[d.strftime("%Y-%m-%d") for d in missing]))
    return rb


# --------------------------------------------------------------------------
# feature panes
# --------------------------------------------------------------------------
PANES: dict[str, str] = {
    "zscores": "Deviation z-scores",
    "halflife": "Half-life (bars)",
    "vol": "Volatility (annualised)",
    "acf": "Return autocorrelation",
    "volume_z": "Volume z-score",
    "pvalues": "Stationarity p-values",
    "confluence": "Confluence (means breached)",
}


def _pane_traces(key: str, v: dict) -> tuple[list[go.BaseTraceType], list[tuple[float, str]], dict]:
    idx = v["index"]
    F, M, S = v["features"], v["means"], v["signal"]
    tr, refs, yax = [], [], {}

    def line(y, name, color, width=1.2, hover=True):
        return go.Scatter(x=idx, y=y, name=name, mode="lines", line=dict(color=color, width=width),
                          hoverinfo=None if hover else "skip", showlegend=True,
                          hovertemplate=f"{name}: %{{y:.3f}}<extra></extra>")

    if key == "zscores":
        tr += [line(S["sig_z"], "traded z", T.INK, 1.6), line(M["kalman_z"], "Kalman z", T.MEAN_COLORS["kalman"]),
               line(M["trend_z"], "trend z", T.MEAN_COLORS["trend"]), line(M["ou_res_z"], "OU-res z", T.MEAN_COLORS["ou_res"])]
        refs = [(2.0, "+2σ"), (-2.0, "−2σ"), (0.0, "")]
    elif key == "halflife":
        tr += [go.Scatter(x=idx, y=M["oures_hl_hi"], line=dict(width=0), hoverinfo="skip", showlegend=False),
               go.Scatter(x=idx, y=M["oures_hl_lo"], fill="tonexty", fillcolor=T.rgba(T.MEAN_COLORS["ou_res"], 0.18),
                          line=dict(width=0), hoverinfo="skip", showlegend=False),
               line(M["oures_halflife"], "residual HL", T.MEAN_COLORS["ou_res"], 1.6),
               line(M["ss_halflife"], "s-score HL", T.MEAN_COLORS["factor"]),
               line(M["ou_halflife"], "price HL", T.MEAN_COLORS["ou"])]
        yax = dict(type="log")
    elif key == "vol":
        rv = range_vols(v["bars"].reindex(idx), 20)
        colors = [T.SERIES[0], T.SERIES[2], T.SERIES[3], T.SERIES[4], T.SERIES[6]]
        for (c, lab), col in zip([("cc", "close-close"), ("park", "Parkinson"), ("gk", "Garman-Klass"),
                                  ("rs", "Rogers-Satchell"), ("yz", "Yang-Zhang")], colors):
            tr.append(line(rv[c] * 100, lab, col))
        tr.append(line(S["sig_vol"] * np.sqrt(252) * 100, "GARCH fcst (traded)", T.INK, 1.6))
    elif key == "acf":
        for k, col in ((1, T.SERIES[0]), (2, T.SERIES[2]), (5, T.SERIES[3])):
            tr.append(line(F[f"acf{k}"], f"acf lag {k}", col))
        tr.append(line(F["vr4_res"] - 1 if "vr4_res" in F else F["vr4_px"] - 1, "VR(4) − 1", T.SERIES[6]))
        refs = [(0.0, "")]
    elif key == "volume_z":
        vz = F["volume_z"]
        tr.append(go.Bar(x=idx, y=vz, marker=dict(color=[T.zone_color(z) for z in S["sig_z"]], line=dict(width=0)),
                         name="volume z", showlegend=False, hovertemplate="volume z: %{y:.2f}<extra></extra>"))
        refs = [(2.0, ""), (0.0, "")]
    elif key == "pvalues":
        tr += [line(F["adf_p_res"] if "adf_p_res" in F else F["adf_p_px"], "ADF p", T.SERIES[3]),
               line(F["kpss_p_res"] if "kpss_p_res" in F else F["kpss_p_px"], "KPSS p", T.SERIES[2]),
               line(F["pp_p_res"] if "pp_p_res" in F else F["pp_p_px"], "PP p", T.SERIES[4]),
               line(F["eg_p"], "Engle-Granger p", T.SERIES[0])]
        refs = [(0.05, "5%"), (0.10, "10%")]
        yax = dict(range=[0, 1])
    elif key == "confluence":
        tr.append(go.Bar(x=idx, y=S["confluence"], marker=dict(color=T.rgba(T.SERIES[6], 0.8), line=dict(width=0)),
                         name="breached", showlegend=False, hovertemplate="breached ≥2σ: %{y:.0f}<extra></extra>"))
    elif key in F.columns:
        tr.append(line(F[key], key, T.INK, 1.4))
    return tr, refs, yax


# --------------------------------------------------------------------------
# main terminal chart
# --------------------------------------------------------------------------

def _band_polygon(x: np.ndarray, upper: np.ndarray, lower: np.ndarray) -> tuple[list, list]:
    """Closed polygons for each contiguous finite run -- fills never bridge gaps."""
    ok = np.isfinite(upper) & np.isfinite(lower)
    idx = np.flatnonzero(ok)
    xs: list = []
    ys: list = []
    if not len(idx):
        return xs, ys
    breaks = np.flatnonzero(np.diff(idx) > 1)
    for a, b in zip(np.r_[idx[0], idx[breaks + 1]], np.r_[idx[breaks], idx[-1]]):
        seg = slice(a, b + 1)
        xs += list(x[seg]) + list(x[seg][::-1]) + [None]
        ys += list(upper[seg]) + list(lower[seg][::-1]) + [None]
    return xs, ys


def _single_x(fig: go.Figure, rows: int) -> None:
    """Put every pane on one x-axis so hover and spikes span all of them."""
    for tr in fig.data:
        tr.xaxis = "x"
    for k in range(1, rows + 1):
        fig.layout["yaxis" if k == 1 else f"yaxis{k}"].anchor = "x"
        ax = fig.layout["xaxis" if k == 1 else f"xaxis{k}"]
        ax.matches = None  # make_subplots ties every axis to the (now empty) bottom one
        if k > 1:
            ax.visible = False
    fig.layout.xaxis.anchor = f"y{rows}"
    # Shapes drawn per pane (reference lines) point at that pane's x-axis. Once
    # those axes carry no traces Plotly drops them and would read the shapes'
    # 0..1 domain coordinates as dates on the shared axis (i.e. 1970).
    for shp in fig.layout.shapes or []:
        if shp.xref and shp.xref.startswith("x"):
            shp.xref = "x domain" if shp.xref.endswith("domain") else "x"


def _pane_legend(fig: go.Figure, name: str, row: int) -> None:
    dom = fig.layout["yaxis" if row == 1 else f"yaxis{row}"].domain
    fig.layout[name] = dict(x=0.004, y=dom[1] - 0.002, xanchor="left", yanchor="top", orientation="h",
                            bgcolor="rgba(26,26,25,0.72)", font=dict(size=9, color=T.INK2), itemwidth=30,
                            tracegroupgap=0)


def terminal_chart(v: dict, trades: pd.DataFrame, primary: str, overlays: list[str], panes: list[str],
                   synthetic: bool = False, cursor=None, height: int = 980, symbol: str = "",
                   annotate_trades: bool = True) -> go.Figure:
    idx = v["index"]
    x = np.asarray(idx.to_pydatetime())
    b = v["bars"].reindex(idx)
    M, S, P, D = v["means"], v["signal"], v["pred"].reindex(idx), v["dec"].reindex(idx)
    n_p = len(panes)
    heights = [0.42, 0.07, 0.15, 0.12] + [0.24 / max(n_p, 1)] * n_p
    rows = 4 + n_p
    titles = ["", "volume · coloured by deviation zone", "P(reversion within K) · calibrated, confidence band, "
              "regime-adjusted threshold", "regime · Hurst, ADF p-value, VR(4) · strip: armed / disarmed"] + \
             [PANES.get(p, p) for p in panes]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.022, row_heights=heights,
                        subplot_titles=titles)

    # -- price: deviation zones around the primary mean ------------------------
    fair = M[f"{primary}_level"].to_numpy(float)
    sig = M[f"{primary}_sigma"].to_numpy(float)
    lvl = {k: np.exp(fair + k * sig) for k in (-3, -2, -1, 0, 1, 2, 3)}
    zones = [(3, 2, T.RED, 0.22, "+2σ…+3σ"), (2, 1, T.RED, 0.12, "+1σ…+2σ"), (1, 0, T.MUTED, 0.07, "±1σ"),
             (0, -1, T.MUTED, 0.07, "±1σ"), (-1, -2, T.BLUE, 0.12, "−1σ…−2σ"), (-2, -3, T.BLUE, 0.22, "−2σ…−3σ")]
    for up, lo, col, a, lab in zones:
        xs, ys = _band_polygon(x, lvl[up], lvl[lo])
        fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself", fillcolor=T.rgba(col, a), mode="none",
                                 hoverinfo="skip", showlegend=False, name=lab), row=1, col=1)
    for k in (-3, -2, -1, 1, 2, 3):
        fig.add_trace(go.Scatter(x=idx, y=lvl[k], mode="lines", hoverinfo="skip", showlegend=False,
                                 line=dict(width=0.6, color=T.rgba(T.INK2, 0.22))), row=1, col=1)

    fig.add_trace(go.Candlestick(
        x=idx, open=b["aopen"], high=b["ahigh"], low=b["alow"], close=b["adj_close"], name="price",
        increasing=dict(line=dict(color=T.INK2, width=1), fillcolor=T.SURFACE),
        decreasing=dict(line=dict(color=T.MUTED, width=1), fillcolor=T.MUTED), showlegend=False,
        hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=lvl[0], mode="lines", line=dict(color=T.INK, width=2),
                             name=T.MEAN_LABELS.get(primary, primary) + " (traded)",
                             customdata=np.column_stack([lvl[-2], lvl[2]]),
                             hovertemplate="traded mean %{y:.2f} · ±2σ [%{customdata[0]:.2f}, %{customdata[1]:.2f}]"
                                           "<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=b["adj_close"], mode="lines", line=dict(width=0), showlegend=False,
                             customdata=np.column_stack([b["aopen"], b["ahigh"], b["alow"], S["sig_z"]]),
                             hovertemplate="O %{customdata[0]:.2f} H %{customdata[1]:.2f} L %{customdata[2]:.2f} "
                                           "C %{y:.2f} · z %{customdata[3]:+.2f}<extra></extra>"), row=1, col=1)
    for name in overlays:
        if name == primary or f"{name}_level" not in M:
            continue
        fig.add_trace(go.Scatter(x=idx, y=np.exp(M[f"{name}_level"]), mode="lines",
                                 line=dict(color=T.MEAN_COLORS.get(name, T.INK2), width=1.1),
                                 name=T.MEAN_LABELS.get(name, name),
                                 hovertemplate=f"{T.MEAN_LABELS.get(name, name)}: %{{y:.2f}}<extra></extra>"),
                      row=1, col=1)

    # -- trades ----------------------------------------------------------------
    if trades is not None and len(trades):
        t = trades[(trades["entry_date"] >= idx[0]) & (trades["entry_date"] <= idx[-1])]
        if len(t):
            win = (t["pnl"] > 0).to_numpy()
            seg_x, seg_y = [], []
            for _, r in t.iterrows():
                seg_x += [r["entry_date"], r["exit_date"], None]
                seg_y += [r["entry_price"], r["exit_price"], None]
            fig.add_trace(go.Scatter(x=seg_x, y=seg_y, mode="lines", line=dict(color=T.rgba(T.INK, 0.4), width=1),
                                     hoverinfo="skip", showlegend=False), row=1, col=1)
            longs = t["direction"] == "long"
            for mask, sym_, lab, col in ((longs, "triangle-up", "long entry", T.BLUE),
                                         (~longs, "triangle-down", "short entry", T.RED)):
                tt = t[mask]
                if not len(tt):
                    continue
                fig.add_trace(go.Scatter(
                    x=tt["entry_date"], y=tt["entry_price"], mode="markers", name=lab,
                    marker=dict(symbol=sym_, size=12, color=col, line=dict(color=T.SURFACE, width=2)),
                    customdata=np.column_stack([tt["trade_id"], tt["p"], tt["p_lo"], tt["z_entry"], tt["weight"]]),
                    hovertemplate="#%{customdata[0]} " + lab + " @ %{y:.2f} · P %{customdata[1]:.2f} "
                                  "(lo %{customdata[2]:.2f}) · z %{customdata[3]:+.2f} · w %{customdata[4]:.2f}"
                                  "<extra></extra>"), row=1, col=1)
            show_text = annotate_trades and len(t) <= 40
            fig.add_trace(go.Scatter(
                x=t["exit_date"], y=t["exit_price"], mode="markers+text" if show_text else "markers",
                name="exit (win / loss)",
                marker=dict(symbol="x-thin", size=11, line=dict(width=2.2, color=np.where(win, T.GOOD, T.CRITICAL))),
                text=[f"{r:+.1f}R" for r in t["R"]], textposition="top center", textfont=dict(size=9, color=T.INK2),
                customdata=np.column_stack([t["trade_id"], t["R"], t["exit_reason"], t["bars_held"]]),
                hovertemplate="#%{customdata[0]} exit %{customdata[2]} after %{customdata[3]} bars · "
                              "%{customdata[1]:+.2f}R<extra></extra>"), row=1, col=1)

    # -- volume, zone coloured ----------------------------------------------------
    fig.add_trace(go.Bar(x=idx, y=b["volume"], marker=dict(color=[T.zone_color(z) for z in S["sig_z"]],
                                                           line=dict(width=0)),
                         showlegend=False, hovertemplate="volume %{y:,.0f}<extra></extra>"), row=2, col=1)

    # -- probability ------------------------------------------------------------------
    xs, ys = _band_polygon(x, P["p_hi"].to_numpy(float), P["p_lo"].to_numpy(float))
    fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself", fillcolor=T.rgba(T.PROB_COLOR, 0.25), mode="none",
                             name="confidence band", hoverinfo="skip", legend="legend2"), row=3, col=1)
    in_dom = v["labels"].reindex(idx)["in_domain"].fillna(False).astype(bool) if len(v["labels"]) else \
        pd.Series(True, index=idx)
    fig.add_trace(go.Scatter(x=idx, y=P["p"], mode="lines", line=dict(color=T.rgba(T.PROB_COLOR, 0.35), width=1),
                             name="P (outside training domain)", hoverinfo="skip", legend="legend2"), row=3, col=1)
    fig.add_trace(go.Scatter(x=idx, y=P["p"].where(in_dom), mode="lines", line=dict(color=T.PROB_COLOR, width=1.8),
                             name="P(revert)", legend="legend2", customdata=np.column_stack([P["p_lo"], P["p_hi"]]),
                             hovertemplate="P %{y:.3f} [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<extra></extra>"),
                  row=3, col=1)
    thr = D["thr"].replace(np.inf, np.nan) if "thr" in D else pd.Series(np.nan, index=idx)
    fig.add_trace(go.Scatter(x=idx, y=thr, mode="lines", line=dict(color=T.INK2, width=1, dash="dash", shape="hv"),
                             name="threshold (gap = disarmed)", legend="legend2",
                             hovertemplate="threshold %{y:.2f}<extra></extra>"), row=3, col=1)
    ent = D["entry"].fillna(False).astype(bool) if "entry" in D else pd.Series(False, index=idx)
    if ent.any():
        ex = idx[ent]
        stems_x, stems_y = [], []
        for d_, p_ in zip(ex, P["p"][ent]):
            stems_x += [d_, d_, None]
            stems_y += [0.5, p_, None]
        fig.add_trace(go.Scatter(x=stems_x, y=stems_y, mode="lines", line=dict(color=T.GOOD, width=1),
                                 hoverinfo="skip", showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=ex, y=P["p"][ent], mode="markers", name="entry signal", legend="legend2",
                                 marker=dict(color=T.GOOD, size=8, line=dict(color=T.SURFACE, width=2)),
                                 hovertemplate="entry signal · P %{y:.3f}<extra></extra>"), row=3, col=1)
    pv = pd.concat([P["p_lo"], P["p_hi"], thr]).to_numpy(float)
    pv = pv[np.isfinite(pv)]
    p_rng = [max(0.0, float(pv.min()) - 0.04), min(1.0, float(pv.max()) + 0.04)] if len(pv) else [0, 1]

    # -- regime ------------------------------------------------------------------------
    reg = D["regime"] if "regime" in D else pd.Series(0, index=idx)
    for code, col, lab in ((MEAN_REVERTING, T.GOOD, "armed · mean-reverting"),
                           (TRENDING, T.CRITICAL, "disarmed · trending")):
        m = (reg == code).to_numpy()
        fig.add_trace(go.Bar(x=idx[m], y=np.full(m.sum(), 1.5), base=0, name=lab, legend="legend3",
                             marker=dict(color=T.rgba(col, 0.22), line=dict(width=0)),
                             hovertemplate=lab + "<extra></extra>"), row=4, col=1)
    fig.add_trace(go.Scatter(x=idx, y=S["gate_hurst"], mode="lines", line=dict(color=T.INK, width=1.4), name="Hurst",
                             legend="legend3", hovertemplate="Hurst %{y:.3f}<extra></extra>"), row=4, col=1)
    fig.add_trace(go.Scatter(x=idx, y=S["gate_adf_p"], mode="lines", line=dict(color=T.SERIES[3], width=1.1),
                             name="ADF p", legend="legend3", hovertemplate="ADF p %{y:.3f}<extra></extra>"), row=4, col=1)
    fig.add_trace(go.Scatter(x=idx, y=S["gate_vr4"], mode="lines", line=dict(color=T.SERIES[2], width=1.1),
                             name="VR(4)", legend="legend3", hovertemplate="VR(4) %{y:.3f}<extra></extra>"),
                  row=4, col=1)
    for yv in (0.5, 1.0):
        fig.add_hline(y=yv, line=dict(color=T.AXIS, width=1), row=4, col=1)

    # -- feature panes --------------------------------------------------------------------
    for i, key in enumerate(panes):
        r = 5 + i
        trs, refs, yax = _pane_traces(key, v)
        for trc in trs:
            trc.legend = f"legend{4 + i}"
            fig.add_trace(trc, row=r, col=1)
        for yv, lab in refs:
            fig.add_hline(y=yv, line=dict(color=T.AXIS, width=1), row=r, col=1)
        if yax:
            fig.update_yaxes(row=r, col=1, **yax)

    # -- layout ------------------------------------------------------------------------------
    fig.update_layout(**T.base_layout(height=height, margin=dict(l=56, r=16, t=16, b=28)), hovermode="x unified",
                      hoversubplots="axis", xaxis_rangeslider_visible=False, bargap=0.0, barmode="overlay",
                      dragmode="pan", uirevision=symbol)
    T.style_axes(fig, rows)
    fig.update_xaxes(rangebreaks=_rangebreaks(idx))
    lo_px = float(np.nanmin(b["alow"])) if len(b) else 1.0
    hi_px = float(np.nanmax(b["ahigh"])) if len(b) else 2.0
    fig.update_yaxes(type="log", row=1, col=1, range=[np.log10(lo_px * 0.95), np.log10(hi_px * 1.05)])
    fig.update_yaxes(row=3, col=1, range=p_rng)
    fig.update_yaxes(row=4, col=1, range=[0, 1.5])
    fig.update_yaxes(row=2, col=1, showticklabels=False)
    _single_x(fig, rows)
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=10, color=T.MUTED), x=1, xanchor="right")
    _pane_legend(fig, "legend", 1)
    _pane_legend(fig, "legend2", 3)
    _pane_legend(fig, "legend3", 4)
    for i in range(n_p):
        _pane_legend(fig, f"legend{4 + i}", 5 + i)
    if synthetic:
        dom = fig.layout.yaxis.domain
        fig.add_annotation(text="SIMULATED DATA — NOT MARKET PRICES", xref="paper", yref="paper", x=0.998,
                           y=dom[1] - 0.004, xanchor="right", yanchor="top", showarrow=False,
                           font=dict(size=10, color=T.WARNING))
    if cursor is not None:
        fig.add_vline(x=pd.Timestamp(cursor), line=dict(color=T.rgba(T.WARNING, 0.8), width=1))
    return fig


# --------------------------------------------------------------------------
# model report charts
# --------------------------------------------------------------------------


def calibration_chart(curve: dict, title: str = "Reliability") -> go.Figure:
    c = pd.DataFrame(curve)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=T.AXIS, width=1), hoverinfo="skip",
                             showlegend=False), row=1, col=1)
    if len(c):
        fig.add_trace(go.Scatter(
            x=c["p_mean"], y=c["y_rate"], mode="lines+markers", line=dict(color=T.PROB_COLOR, width=2),
            marker=dict(size=8, color=T.PROB_COLOR, line=dict(color=T.SURFACE, width=2)),
            error_y=dict(type="data", symmetric=False, array=c["hi"] - c["y_rate"], arrayminus=c["y_rate"] - c["lo"],
                         color=T.rgba(T.PROB_COLOR, 0.6), thickness=1, width=0),
            customdata=c["n"], name="observed",
            hovertemplate="predicted %{x:.3f} · observed %{y:.3f} · n %{customdata}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=c["p_mean"], y=c["n"], marker=dict(color=T.rgba(T.PROB_COLOR, 0.5), line=dict(width=0)),
                             width=0.02, showlegend=False, hovertemplate="n %{y}<extra></extra>"), row=2, col=1)
    fig.update_layout(**T.base_layout(height=320, margin=dict(l=48, r=12, t=30, b=30)), title=dict(
        text=title, font=dict(size=12, color=T.INK2), x=0.01), showlegend=False)
    T.style_axes(fig, 2)
    fig.update_xaxes(range=[0, 1], row=2, col=1, title_text="predicted probability")
    fig.update_yaxes(range=[0, 1], row=1, col=1, title_text="observed frequency")
    return fig


def roc_pr_chart(y: np.ndarray, p: np.ndarray) -> go.Figure:
    from sklearn.metrics import precision_recall_curve, roc_curve

    fig = make_subplots(rows=1, cols=2, subplot_titles=["ROC", "Precision-recall"], horizontal_spacing=0.12)
    if len(y) and len(np.unique(y)) > 1:
        fpr, tpr, _ = roc_curve(y, p)
        prec, rec, _ = precision_recall_curve(y, p)
        fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", line=dict(color=T.PROB_COLOR, width=2),
                                 hovertemplate="FPR %{x:.2f} TPR %{y:.2f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=rec, y=prec, mode="lines", line=dict(color=T.PROB_COLOR, width=2),
                                 hovertemplate="recall %{x:.2f} precision %{y:.2f}<extra></extra>"), row=1, col=2)
        fig.add_hline(y=float(np.mean(y)), line=dict(color=T.AXIS, width=1), row=1, col=2)
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=T.AXIS, width=1), hoverinfo="skip"),
                  row=1, col=1)
    fig.update_layout(**T.base_layout(height=260, margin=dict(l=40, r=12, t=30, b=30)), showlegend=False)
    T.style_axes(fig, 2)
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=11, color=T.INK2))
    return fig


def importance_bars(imp: pd.Series, specs: dict, top: int = 25, title: str = "") -> go.Figure:
    s = imp.dropna().sort_values(ascending=False).head(top)[::-1]
    fam = [specs[f].family if f in specs else "?" for f in s.index]
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h",
        marker=dict(color=[T.FAMILY_COLORS.get(f, T.MUTED) for f in fam], line=dict(width=0)),
        customdata=np.column_stack([fam, [specs[f].desc if f in specs else "" for f in s.index]]),
        hovertemplate="%{y} · %{customdata[0]}<br>%{customdata[1]}<br>Δ log-loss %{x:.4f}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=T.AXIS, width=1))
    fig.update_layout(**T.base_layout(height=max(260, 16 * len(s) + 60), margin=dict(l=150, r=16, t=30, b=30)),
                      title=dict(text=title, font=dict(size=12, color=T.INK2), x=0.01), bargap=0.25)
    fig.update_yaxes(tickfont=dict(family=T.MONO, size=10))
    return fig


def smooth_steps(df: pd.DataFrame, halflife: float) -> pd.DataFrame:
    """EWMA across retrain steps (rows), the same smoothing importance gets."""
    return df.ewm(halflife=halflife, min_periods=1).mean() if len(df) else df


def family_area(df: pd.DataFrame, title: str, normalize: bool = True, halflife: float | None = None) -> go.Figure:
    fig = go.Figure()
    if len(df):
        d = df.copy()
        d.columns = [c.replace("fam:", "") for c in d.columns]
        if normalize:
            d = d.clip(lower=0)
            d = d.div(d.sum(axis=1).replace(0, np.nan), axis=0)
        if halflife:
            d = smooth_steps(d, halflife)
        for fam in T.FAMILY_COLORS:
            if fam in d:
                fig.add_trace(go.Scatter(x=d.index, y=d[fam], name=fam, mode="lines", stackgroup="one" if normalize else None,
                                         line=dict(width=0.5 if normalize else 1.6, color=T.FAMILY_COLORS[fam]),
                                         fillcolor=T.rgba(T.FAMILY_COLORS[fam], 0.75) if normalize else None,
                                         hovertemplate=f"{fam}: %{{y:.3f}}<extra></extra>"))
        for extra, col in (("en_full", T.INK2), ("gbm", T.MUTED)):
            if extra in d:
                fig.add_trace(go.Scatter(x=d.index, y=d[extra], name={"en_full": "elastic-net (all)",
                                                                      "gbm": "LightGBM (all)"}[extra],
                                         mode="lines", stackgroup="one" if normalize else None,
                                         line=dict(width=0.5, color=col), fillcolor=T.rgba(col, 0.6) if normalize else None,
                                         hovertemplate=f"{extra}: %{{y:.3f}}<extra></extra>"))
    fig.update_layout(**T.base_layout(height=320, margin=dict(l=48, r=12, t=30, b=92),
                                      legend=dict(orientation="h", x=0, y=-0.2, xanchor="left", yanchor="top",
                                                  font=dict(size=9))),
                      hovermode="x unified", title=dict(text=title, font=dict(size=11, color=T.INK2), x=0.01, y=0.98))
    if normalize:
        fig.update_yaxes(range=[0, 1], tickformat=".0%")
    return fig


def importance_heatmap(df: pd.DataFrame, specs: dict, top: int = 30) -> go.Figure:
    if not len(df):
        return go.Figure(layout=T.base_layout(height=200))
    last = df.iloc[-1].abs().sort_values(ascending=False).head(top).index
    d = df[last].T
    zmax = float(np.nanpercentile(np.abs(d.to_numpy()), 98)) or 1e-3
    fig = go.Figure(go.Heatmap(
        z=d.to_numpy(), x=d.columns, y=d.index, zmin=-zmax, zmax=zmax, zmid=0,
        colorscale=[[0, T.RED], [0.5, T.NEUTRAL], [1, T.BLUE]],
        colorbar=dict(title=dict(text="Δ log-loss", font=dict(size=10)), thickness=10, tickfont=dict(size=9)),
        hovertemplate="%{y} · %{x|%Y-%m-%d}<br>smoothed importance %{z:.4f}<extra></extra>"))
    fig.update_layout(**T.base_layout(height=max(300, 14 * len(last) + 80), margin=dict(l=150, r=12, t=34, b=30)),
                      title=dict(text="importance evolution across retrains (top features at the latest step; "
                                      "blue helps out of sample, red hurts)", font=dict(size=11, color=T.INK2), x=0.01))
    fig.update_yaxes(tickfont=dict(family=T.MONO, size=9), autorange="reversed")
    return fig


# --------------------------------------------------------------------------
# performance charts
# --------------------------------------------------------------------------


def equity_chart(eq: pd.DataFrame, synthetic: bool = False, log_scale: bool = True) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03,
                        subplot_titles=["Equity · strategy vs buy & hold", "Underwater (drawdown)"])
    fig.add_trace(go.Scatter(x=eq.index, y=eq["equity"], name="strategy", line=dict(color=T.EQUITY_COLOR, width=2),
                             hovertemplate="strategy %{y:,.0f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=eq.index, y=eq["bh_equity"], name="buy & hold (equal weight)",
                             line=dict(color=T.MUTED, width=1.3), hovertemplate="buy & hold %{y:,.0f}<extra></extra>"),
                  row=1, col=1)
    if "market_equity" in eq:
        fig.add_trace(go.Scatter(x=eq.index, y=eq["market_equity"], name="market", line=dict(color=T.INK2, width=1),
                                 visible="legendonly", hovertemplate="market %{y:,.0f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=eq.index, y=eq["drawdown"] * 100, name="strategy DD", fill="tozeroy",
                             line=dict(color=T.RED, width=1), fillcolor=T.rgba(T.RED, 0.35),
                             hovertemplate="strategy DD %{y:.1f}%<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=eq.index, y=eq["bh_drawdown"] * 100, name="buy & hold DD",
                             line=dict(color=T.MUTED, width=1), hovertemplate="B&H DD %{y:.1f}%<extra></extra>"),
                  row=2, col=1)
    fig.update_layout(**T.base_layout(height=520, margin=dict(l=56, r=16, t=28, b=28),
                                      legend=dict(x=0.005, y=0.985, xanchor="left", yanchor="top", orientation="h",
                                                  bgcolor="rgba(26,26,25,0.75)", font=dict(size=10))), hovermode="x unified")
    T.style_axes(fig, 2)
    if log_scale:
        fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(ticksuffix="%", row=2, col=1)
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=10, color=T.MUTED), x=1, xanchor="right")
    if synthetic:
        fig.add_annotation(text="SIMULATED DATA", xref="paper", yref="paper", x=0.5, y=1.0, xanchor="center",
                           yanchor="bottom", showarrow=False, font=dict(size=10, color=T.WARNING))
    return fig


def r_histogram(trades: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(trades):
        r = trades["R"].clip(-4, 4)
        fig.add_trace(go.Histogram(x=r[r > 0], xbins=dict(start=-4, end=4, size=0.25), name="winners",
                                   marker=dict(color=T.rgba(T.GOOD, 0.8), line=dict(width=1, color=T.SURFACE))))
        fig.add_trace(go.Histogram(x=r[r <= 0], xbins=dict(start=-4, end=4, size=0.25), name="losers",
                                   marker=dict(color=T.rgba(T.CRITICAL, 0.8), line=dict(width=1, color=T.SURFACE))))
        fig.add_vline(x=float(trades["R"].mean()), line=dict(color=T.INK, width=1, dash="dash"))
    fig.update_layout(**T.base_layout(height=260, margin=dict(l=40, r=12, t=40, b=30),
                                      legend=dict(x=0.99, y=0.98, xanchor="right", yanchor="top", orientation="v",
                                                  bgcolor="rgba(26,26,25,0.75)")), barmode="overlay",
                      title=dict(text="R-multiple distribution (dashed = expectancy)", font=dict(size=12, color=T.INK2),
                                 x=0.01))
    return fig


def monthly_heatmap(mr: pd.DataFrame) -> go.Figure:
    if not len(mr):
        return go.Figure(layout=T.base_layout(height=200))
    z = mr.to_numpy() * 100
    zmax = float(np.nanpercentile(np.abs(z), 97)) or 1.0
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(
        z=z, x=[months[int(c) - 1] for c in mr.columns], y=[str(i) for i in mr.index], zmin=-zmax, zmax=zmax, zmid=0,
        colorscale=[[0, T.RED], [0.5, T.NEUTRAL], [1, T.BLUE]], xgap=2, ygap=2,
        text=np.where(np.isfinite(z), np.char.mod("%.1f", np.nan_to_num(z)), ""), texttemplate="%{text}",
        textfont=dict(size=9, color=T.INK), colorbar=dict(thickness=10, ticksuffix="%", tickfont=dict(size=9)),
        hovertemplate="%{y} %{x}: %{z:.2f}%<extra></extra>"))
    fig.update_layout(**T.base_layout(height=max(220, 22 * len(mr) + 70), margin=dict(l=48, r=12, t=30, b=30)),
                      title=dict(text="Monthly returns", font=dict(size=12, color=T.INK2), x=0.01))
    fig.update_yaxes(autorange="reversed", showspikes=False)
    fig.update_xaxes(showspikes=False)
    return fig


def shap_waterfall(contrib: pd.Series, base: float, p: float, specs: dict, top: int = 10) -> go.Figure:
    """Top contributions to today's log-odds, ordered by magnitude."""
    c = contrib.dropna()
    c = c[c.abs() > 0]
    top_c = c.reindex(c.abs().sort_values(ascending=False).index).head(top)
    rest = c.drop(top_c.index).sum()
    labels = list(top_c.index)[::-1]
    vals = list(top_c.values)[::-1]
    if abs(rest) > 1e-9:
        labels = ["(other features)"] + labels
        vals = [rest] + vals
    fam = [specs[f].family if f in specs else "" for f in labels]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(color=[T.BLUE if v > 0 else T.RED for v in vals], line=dict(width=0)),
        customdata=fam, hovertemplate="%{y} (%{customdata})<br>%{x:+.3f} log-odds<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=T.AXIS, width=1))
    fig.update_layout(**T.base_layout(height=40 + 22 * len(labels), margin=dict(l=130, r=10, t=26, b=24)),
                      title=dict(text=f"why P = {p:.3f}  (base log-odds {base:+.2f}; blue raises, red lowers)",
                                 font=dict(size=11, color=T.INK2), x=0.01), bargap=0.3)
    fig.update_yaxes(tickfont=dict(family=T.MONO, size=10))
    fig.update_xaxes(showspikes=False)
    fig.update_yaxes(showspikes=False)
    return fig
