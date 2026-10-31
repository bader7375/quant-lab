"""Research terminal entry point.

    python -m quantlab.meanrev.cli app            # http://127.0.0.1:8050
    make meanrev-app
"""
from __future__ import annotations

import logging
from pathlib import Path

import dash

from ..config import MRConfig
from .callbacks import register
from .layout import build_layout

ASSETS = Path(__file__).parent / "assets"
FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&"
         "family=JetBrains+Mono:wght@400;500&display=swap")


def create_app(config: str | None = None) -> dash.Dash:
    cfg = MRConfig.load(config)
    app = dash.Dash(__name__, title="QuantLab · Mean-Reversion Terminal", assets_folder=str(ASSETS),
                    external_stylesheets=[FONTS], suppress_callback_exceptions=True, update_title=None)
    app.layout = build_layout(cfg)
    register(app, cfg)
    return app


def serve(host: str = "127.0.0.1", port: int = 8050, config: str | None = None, debug: bool = False) -> None:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app = create_app(config)
    print(f"research terminal on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
