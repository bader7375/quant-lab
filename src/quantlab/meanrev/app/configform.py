"""Config sidebar generated from the dataclass metadata.

Every field of :class:`~quantlab.meanrev.config.MRConfig` becomes an input,
typed by its annotation and bounded by its metadata, with the help text on
hover. Adding a parameter to the config adds it to the UI.
"""
from __future__ import annotations

import dataclasses
import json
import typing

from dash import dcc, html

from ..config import MODEL_SECTIONS, MRConfig, TRADING_SECTIONS

SECTION_TITLES = {
    "data": "Data", "means": "Mean definitions", "features": "Feature engine", "label": "Labels",
    "walkforward": "Walk-forward", "model": "Models & calibration", "regime": "Regime gate",
    "signal": "Signal", "risk": "Risk & sizing", "exits": "Exits",
}


def _kind(f: dataclasses.Field, hints: dict) -> str:
    t = hints[f.name]
    origin = typing.get_origin(t)
    args = typing.get_args(t)
    if f.metadata.get("choices") and origin is not list:
        return "choice"
    if t is bool:
        return "bool"
    if origin in (list, dict):
        return "json"
    base = [a for a in args if a is not type(None)] if args else [t]
    if base and base[0] is int:
        return "int"
    if base and base[0] is float:
        return "float"
    return "text"


def _fmt(v, kind: str):
    if kind == "json":
        return json.dumps(v)
    if v is None:
        return ""
    return v


def build_form(cfg: MRConfig) -> list:
    sections = []
    for name in MODEL_SECTIONS + TRADING_SECTIONS:
        sec = getattr(cfg, name)
        hints = typing.get_type_hints(type(sec))
        rows = []
        for f in dataclasses.fields(sec):
            kind = _kind(f, hints)
            key = f"{name}.{f.name}"
            cid = {"type": "cfg", "key": key}
            val = getattr(sec, f.name)
            meta = f.metadata
            if kind == "bool":
                ctrl = dcc.Checklist(id=cid, options=[{"label": "", "value": "on"}], value=["on"] if val else [],
                                     className="cfg-check")
            elif kind == "choice":
                ctrl = dcc.Dropdown(id=cid, options=meta["choices"], value=val, clearable=False, className="cfg-dd")
            elif kind in ("int", "float"):
                ctrl = dcc.Input(id=cid, type="number", value=val, min=meta.get("min"), max=meta.get("max"),
                                 step=meta.get("step", 1 if kind == "int" else "any"), debounce=True,
                                 className="cfg-input")
            else:
                ctrl = dcc.Input(id=cid, type="text", value=_fmt(val, kind), debounce=True, className="cfg-input")
            rows.append(html.Div([
                html.Label(f.name.replace("_", " "), title=meta.get("help", ""), className="cfg-label"),
                ctrl,
            ], className="cfg-row", title=meta.get("help", "")))
        badge = html.Span("retrains" if name in MODEL_SECTIONS else "instant",
                          className="badge badge-model" if name in MODEL_SECTIONS else "badge badge-trade")
        sections.append(html.Details([
            html.Summary([SECTION_TITLES.get(name, name), badge]),
            html.Div(rows, className="cfg-body"),
        ], open=name in ("signal",), className="cfg-section"))
    return sections


def collect(ids: list[dict], values: list, base: MRConfig) -> tuple[MRConfig, list[str]]:
    """Rebuild a config from the form; returns (config, errors)."""
    cfg = base.copy()
    errors = []
    for cid, val in zip(ids, values):
        key = cid["key"]
        sec_name, field_name = key.split(".", 1)
        sec = getattr(cfg, sec_name)
        f = {x.name: x for x in dataclasses.fields(sec)}[field_name]
        kind = _kind(f, typing.get_type_hints(type(sec)))
        try:
            if kind == "bool":
                v = bool(val) and "on" in val
            elif kind == "json":
                v = json.loads(val) if isinstance(val, str) else val
            elif kind == "int":
                v = None if val in (None, "") else int(val)
            elif kind == "float":
                v = None if val in (None, "") else float(val)
            elif kind == "text":
                v = None if val in (None, "") and f.default is None else val
            else:
                v = val
            if v is None and f.default is not None and kind in ("int", "float"):
                errors.append(f"{key}: required")
                continue
            setattr(sec, field_name, v)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"{key}: {exc}")
    return cfg, errors
