"""Event-driven portfolio backtest.

Timing is the conservative daily convention: every decision uses only data
available at the close of bar ``t`` and is filled at the **open of t + 1**,
so overnight gaps are borne in full. Costs (commission + slippage, per side,
on every leg) and short-borrow carry are charged explicitly.

Positions
---------
In residual space a position is the stock plus hedge legs in the factor
ETFs, sized with the point-in-time betas known at the signal close -- the
exact hedge the residual series assumes. In price space it is the stock
alone. Share quantities are fixed at entry; the book is marked to market at
every close.

Exits (evaluated at the close, filled at the next open)
-------------------------------------------------------
``TP``      the deviation reaches ``tp_z`` (0 = touches the dynamic mean)
``SL_Z``    residual-breach invalidation: it extends ``stop_z`` beyond entry
``SL_ATR``  the traded series moves ``stop_atr_mult`` ATRs against the trade
``TRAIL``   after ``trail_activation`` of the gap has reverted, giving back
            ``trail_z`` sigmas from the best level reached
``TIME``    ``time_stop`` bars held
``INVALID`` the mean definition itself broke down (no stationary fit)
``END``     still open at the last bar (closed at that close)

R-multiples are P&L over the risk at entry: notional x the distance to the
nearer of the two stops.

The loop is over dates -- a path-dependent portfolio with slot limits and
cooldowns is inherently sequential -- but each step is a few dictionary
operations, so a 20-year multi-symbol run takes well under a second.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..data.market import MarketData

MIN_HEDGE = 1e-3


@dataclass
class Position:
    symbol: str
    direction: int
    signal_t: int
    fill_t: int
    shares: dict[str, float]
    entry_px: dict[str, float]
    notional: float
    gross: float
    weight: float
    z_entry: float
    v_entry: float
    sigma_entry: float
    atr_entry: float
    risk: float
    info: dict
    cost: float = 0.0
    borrow: float = 0.0
    best: float = np.inf
    mae: float = 0.0
    mfe: float = 0.0
    exit_reason: str | None = None
    exit_signal_t: int | None = None
    last_value: float = 0.0


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.DataFrame
    symbol_pnl: pd.DataFrame
    decisions: dict[str, pd.DataFrame] = field(default_factory=dict)


def _prices(md: MarketData, cal: pd.DatetimeIndex, tickers) -> tuple[dict, dict]:
    op, cl = {}, {}
    for t in tickers:
        b = md.bars[t].reindex(cal)
        op[t] = b["aopen"].to_numpy(float)
        cl[t] = b["adj_close"].to_numpy(float)
    return op, cl


def run_backtest(md: MarketData, sigs: dict[str, pd.DataFrame], decs: dict[str, pd.DataFrame], cfg: MRConfig,
                 start: pd.Timestamp | None = None) -> BacktestResult:
    cal = md.calendar
    n = len(cal)
    rc, sc, ec = cfg.risk, cfg.signal, cfg.exits
    symbols = [s for s in md.symbols if s in decs]
    hedged = rc.hedge and cfg.signal_space == "residual"
    etfs = sorted({c[6:] for s in symbols for c in sigs[s].columns if c.startswith("hedge_")}) if hedged else []
    tickers = list(dict.fromkeys(symbols + etfs))
    op, cl = _prices(md, cal, tickers)

    S = {s: sigs[s].reindex(cal) for s in symbols}
    D = {s: decs[s].reindex(cal) for s in symbols}
    arr = {s: {c: S[s][c].to_numpy(float) for c in ("sig_z", "sig_v", "sig_sigma", "sig_atr", "confluence")}
           for s in symbols}
    darr = {s: {c: D[s][c].to_numpy(float) for c in ("p", "p_lo", "p_hi", "weight", "edge", "regime", "exp_gap",
                                                      "m_kelly", "m_conf", "regime_mult")} | {
        "entry": D[s]["entry"].fillna(False).to_numpy(bool)} for s in symbols}
    hedge_w = {s: {e: S[s][f"hedge_{e}"].to_numpy(float) for e in etfs if f"hedge_{e}" in S[s]} for s in symbols}

    t0 = int(cal.searchsorted(start)) if start is not None else 0
    cash = float(rc.initial_capital)
    side_cost = (rc.commission_bps + rc.slippage_bps) / 1e4
    borrow_daily = rc.borrow_bps_annual / 1e4 / 252.0

    positions: dict[str, Position] = {}
    pending_entry: dict[str, dict] = {}
    last_exit: dict[str, int] = {}
    trades: list[dict] = []
    eq = np.full(n, np.nan)
    gross_lev = np.zeros(n)
    net_lev = np.zeros(n)
    n_pos = np.zeros(n)
    sym_pnl = np.zeros((n, len(symbols)))
    s_index = {s: i for i, s in enumerate(symbols)}
    time_stop = cfg.time_stop

    def value(pos: Position, px: dict, t: int) -> float:
        return sum(q * px[k][t] for k, q in pos.shares.items())

    def close_position(pos: Position, t: int, px: dict, reason: str) -> None:
        nonlocal cash
        proceeds = 0.0
        cost = 0.0
        for k, q in pos.shares.items():
            p = px[k][t] if np.isfinite(px[k][t]) else cl[k][t - 1]
            proceeds += q * p
            cost += abs(q * p) * side_cost
        cash += proceeds - cost
        pos.cost += cost
        entry_val = sum(q * pos.entry_px[k] for k, q in pos.shares.items())
        pnl = proceeds - entry_val - pos.cost - pos.borrow
        sym_pnl[t, s_index[pos.symbol]] += proceeds - pos.last_value - cost
        stock_exit = px[pos.symbol][t] if np.isfinite(px[pos.symbol][t]) else cl[pos.symbol][t - 1]
        sig_t = pos.exit_signal_t if pos.exit_signal_t is not None else t
        trades.append({
            "symbol": pos.symbol, "direction": "long" if pos.direction > 0 else "short",
            "signal_date": cal[pos.signal_t], "entry_date": cal[pos.fill_t], "exit_signal_date": cal[sig_t],
            "exit_date": cal[t], "entry_price": pos.entry_px[pos.symbol], "exit_price": stock_exit,
            "bars_held": t - pos.fill_t, "exit_reason": reason, "notional": pos.notional, "gross": pos.gross,
            "weight": pos.weight, "pnl": pnl, "ret_on_notional": pnl / pos.notional, "risk": pos.risk,
            "R": pnl / pos.risk if pos.risk > 0 else np.nan,
            "mae_R": pos.mae / pos.risk if pos.risk > 0 else np.nan,
            "mfe_R": pos.mfe / pos.risk if pos.risk > 0 else np.nan, "costs": pos.cost, "borrow": pos.borrow,
            "z_entry": pos.z_entry, "z_exit": arr[pos.symbol]["sig_z"][sig_t],
            "hedge": ";".join(f"{k}:{q * pos.entry_px[k] / pos.notional:+.2f}" for k, q in pos.shares.items()
                              if k != pos.symbol),
            **pos.info,
        })
        last_exit[pos.symbol] = t

    for t in range(t0, n):
        # ---- 1. fills at the open ------------------------------------------
        for sym in [s for s, p in positions.items() if p.exit_reason is not None]:
            pos = positions.pop(sym)
            close_position(pos, t, op, pos.exit_reason)
        for sym, order in list(pending_entry.items()):
            px_ok = all(np.isfinite(op[k][t]) for k in order["legs"])
            if not px_ok:
                continue
            shares, entry_px, cost, gross = {}, {}, 0.0, 0.0
            for k, notional_k in order["legs"].items():
                q = notional_k / op[k][t]
                shares[k] = q
                entry_px[k] = op[k][t]
                cost += abs(notional_k) * side_cost
                gross += abs(notional_k)
            cash -= sum(q * entry_px[k] for k, q in shares.items()) + cost
            pos = Position(sym, order["dir"], order["signal_t"], t, shares, entry_px, abs(order["legs"][sym]), gross,
                           order["weight"], order["z"], order["v"], order["sigma"], order["atr"], order["risk"],
                           order["info"], cost=cost)
            pos.last_value = value(pos, op, t)
            sym_pnl[t, s_index[sym]] -= cost
            positions[sym] = pos
        pending_entry.clear()

        # ---- 2. mark to market at the close -----------------------------------
        gross = net = held_value = 0.0
        for sym, pos in positions.items():
            v = borrow = 0.0
            for k, q in pos.shares.items():
                p = cl[k][t] if np.isfinite(cl[k][t]) else pos.entry_px[k]
                v += q * p
                gross += abs(q * p)
                net += q * p
                if q < 0:
                    borrow += -q * p * borrow_daily
            pos.borrow += borrow
            cash -= borrow
            sym_pnl[t, s_index[sym]] += v - pos.last_value - borrow
            pos.last_value = v
            held_value += v
            unreal = v - sum(q * pos.entry_px[k] for k, q in pos.shares.items())
            pos.mae = min(pos.mae, unreal)
            pos.mfe = max(pos.mfe, unreal)
        equity = cash + held_value
        eq[t] = equity
        gross_lev[t] = gross / equity if equity > 0 else np.nan
        net_lev[t] = net / equity if equity > 0 else np.nan
        n_pos[t] = len(positions)

        if t == n - 1:
            break

        # ---- 3. exit decisions at the close -----------------------------------
        for sym, pos in positions.items():
            a = arr[sym]
            s = -pos.direction
            z = a["sig_z"][t]
            held = t - pos.fill_t + 1
            reason = None
            if not np.isfinite(z):
                reason = "INVALID"
            else:
                stretch = s * z
                pos.best = min(pos.best, stretch)
                fav = pos.direction * (a["sig_v"][t] - pos.v_entry)
                progress = (abs(pos.z_entry) - pos.best) / abs(pos.z_entry)
                if stretch <= ec.tp_z:
                    reason = "TP"
                elif stretch >= abs(pos.z_entry) + ec.stop_z:
                    reason = "SL_Z"
                elif ec.stop_atr_mult > 0 and fav <= -ec.stop_atr_mult * pos.atr_entry:
                    reason = "SL_ATR"
                elif progress >= ec.trail_activation and stretch - pos.best >= ec.trail_z:
                    reason = "TRAIL"
                elif held >= time_stop:
                    reason = "TIME"
            if reason:
                pos.exit_reason, pos.exit_signal_t = reason, t

        # ---- 4. entry decisions at the close -------------------------------------
        staying = [p for p in positions.values() if p.exit_reason is None]
        slots = sc.max_positions - len(staying)
        if slots <= 0:
            continue
        gross_now = sum(p.gross for p in staying)
        cands = []
        for sym in symbols:
            if sym in positions or not darr[sym]["entry"][t]:
                continue
            if sym in last_exit and t - last_exit[sym] < sc.cooldown_days:
                continue
            w = darr[sym]["weight"][t]
            if not np.isfinite(w) or w <= 0:
                continue
            cands.append((darr[sym]["edge"][t], sym))
        cands.sort(reverse=True)
        for _, sym in cands[:slots]:
            a, d = arr[sym], darr[sym]
            direction = 1 if a["sig_z"][t] < 0 else -1
            notional = d["weight"][t] * equity
            legs = {sym: direction * notional}
            for e, wser in hedge_w.get(sym, {}).items():
                hw = wser[t]
                if np.isfinite(hw) and abs(hw) >= MIN_HEDGE and e != sym:
                    legs[e] = legs.get(e, 0.0) + direction * hw * notional
            g = sum(abs(v) for v in legs.values())
            cap = rc.max_gross_leverage * equity - gross_now
            if cap <= 0:
                break
            if g > cap:
                scale = cap / g
                if scale < 0.25:
                    continue
                legs = {k: v * scale for k, v in legs.items()}
                notional *= scale
                g = cap
            gross_now += g
            dist = [ec.stop_z * a["sig_sigma"][t]]
            if ec.stop_atr_mult > 0:
                dist.append(ec.stop_atr_mult * a["sig_atr"][t])
            risk = notional * float(np.nanmin(dist))
            pending_entry[sym] = {
                "dir": direction, "signal_t": t, "legs": legs, "weight": d["weight"][t], "z": a["sig_z"][t],
                "v": a["sig_v"][t], "sigma": a["sig_sigma"][t], "atr": a["sig_atr"][t], "risk": risk,
                "info": {"p": d["p"][t], "p_lo": d["p_lo"][t], "p_hi": d["p_hi"][t], "exp_gap": d["exp_gap"][t],
                         "regime": d["regime"][t], "confluence": a["confluence"][t], "m_kelly": d["m_kelly"][t],
                         "m_conf": d["m_conf"][t], "m_regime": d["regime_mult"][t]},
            }

    # close anything still open at the final close
    for sym in list(positions):
        pos = positions.pop(sym)
        close_position(pos, n - 1, cl, "END")

    idx = cal[t0:]
    equity = pd.DataFrame({"equity": eq[t0:], "gross_leverage": gross_lev[t0:], "net_leverage": net_lev[t0:],
                           "positions": n_pos[t0:]}, index=idx)
    equity["equity"] = equity["equity"].ffill()
    # positions still open were closed at the final close; their exit costs land here
    equity.loc[idx[-1], "equity"] = cash
    equity["ret"] = equity["equity"].pct_change().fillna(0.0)
    equity["drawdown"] = equity["equity"] / equity["equity"].cummax() - 1.0
    bh = {}
    for s in symbols:
        px = pd.Series(cl[s][t0:], index=idx).ffill()
        bh[s] = px / px.dropna().iloc[0]
    bh_df = pd.DataFrame(bh)
    equity["bh_equity"] = rc.initial_capital * bh_df.mean(axis=1)
    equity["bh_drawdown"] = equity["bh_equity"] / equity["bh_equity"].cummax() - 1.0
    if md.market and md.market in md.bars:
        mk = md.bars[md.market]["adj_close"].reindex(idx).ffill()
        equity["market_equity"] = rc.initial_capital * mk / mk.dropna().iloc[0]
    tr = pd.DataFrame(trades)
    if len(tr):
        tr = tr.sort_values("entry_date").reset_index(drop=True)
        tr.insert(0, "trade_id", np.arange(1, len(tr) + 1))
    return BacktestResult(tr, equity, pd.DataFrame(sym_pnl[t0:], index=idx, columns=symbols), decs)
