"""Dark terminal theme.

Colours come from a validated reference palette (dark-surface steps), and
each colour has exactly one job:

* **Diverging** blue <-> red with a neutral grey midpoint encodes the side of
  the mean: blue = below (long zone), red = above (short zone). Deviation
  bands, zone-coloured volume and the monthly-returns heatmap use it.
* **Categorical** slots identify entities -- mean definitions and feature
  families -- in a fixed order, so a colour always means the same thing
  (both subsets pass the colour-vision-deficiency checks on this surface).
* **Status** colours (good / warning / critical) are reserved for state:
  regime armed / neutral / disarmed, winning / losing trades. They always
  ship with a text label.
* Candles are monochrome (hollow up, filled down) so the overlays carry the
  meaning.
"""
from __future__ import annotations

SURFACE = "#1a1a19"
PAGE = "#0d0d0d"
PANEL = "#141413"
INK = "#ffffff"
INK2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"

SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
BLUE, RED, NEUTRAL = "#3987e5", "#e66767", "#383835"
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"

#: mean definition -> colour (entity-stable; validated as a set)
MEAN_COLORS = {"factor": "#d95926", "kalman": "#199e70", "ou": "#c98500", "trend": "#d55181",
               "ou_res": "#9085e9", "ema_20": "#008300", "sma_20": "#008300"}
MEAN_LABELS = {"factor": "Factor-residual fair value", "kalman": "Kalman level", "ou": "OU mean (price)",
               "trend": "Trend regression", "ou_res": "OU mean (residual)", "ema_20": "EMA 20", "sma_20": "SMA 20"}

#: feature family -> colour (fixed categorical order)
FAMILY_COLORS = {"stochastic": SERIES[0], "deviation": SERIES[1], "volatility": SERIES[2], "tail": SERIES[3],
                 "market": SERIES[4], "micro": SERIES[5], "confluence": SERIES[6]}

PROB_COLOR = "#9085e9"
EQUITY_COLOR = BLUE

FONT = "Inter, 'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def zone_color(z: float) -> str:
    """Diverging colour for a deviation: blue below the mean, red above."""
    if z != z:  # NaN
        return rgba(MUTED, 0.35)
    a = abs(z)
    if a < 1:
        return rgba(MUTED, 0.45)
    base = BLUE if z < 0 else RED
    return rgba(base, 0.55 if a < 2 else 0.8 if a < 3 else 1.0)


def base_layout(height: int = 600, **kw) -> dict:
    axis = dict(gridcolor=GRID, gridwidth=1, zeroline=False, linecolor=AXIS, tickfont=dict(color=MUTED, size=10),
                title=dict(font=dict(color=MUTED, size=10)), showspikes=True, spikecolor=MUTED, spikethickness=1,
                spikedash="solid", spikemode="across", spikesnap="cursor")
    layout = dict(
        template="plotly_dark", paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        font=dict(family=FONT, color=INK2, size=11), margin=dict(l=56, r=16, t=28, b=28),
        hoverlabel=dict(bgcolor="#111110", bordercolor=AXIS, font=dict(family=MONO, size=11, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=10, color=INK2)),
        xaxis=axis, yaxis=axis,
    )
    layout.update(kw)
    return layout


def style_axes(fig, rows: int) -> None:
    for i in range(1, rows + 1):
        sfx = "" if i == 1 else str(i)
        fig.layout[f"xaxis{sfx}"].update(gridcolor=GRID, linecolor=AXIS, tickfont=dict(color=MUTED, size=10),
                                         showspikes=True, spikemode="across", spikesnap="cursor",
                                         spikecolor=MUTED, spikethickness=1, spikedash="solid", zeroline=False)
        fig.layout[f"yaxis{sfx}"].update(gridcolor=GRID, linecolor=AXIS, tickfont=dict(color=MUTED, size=10),
                                         zeroline=False, title=dict(font=dict(color=MUTED, size=10)))
