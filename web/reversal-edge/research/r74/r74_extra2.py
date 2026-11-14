"""Extra 3 (not judged): the live plan with a -3% stop order at bigger positions (a near stop risks less per trade, so the same account
risk allows a bigger position). Plan book engine, live signals, 5 slots, sell after 40 sessions otherwise."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daily"))
import planbook as PB
SH = PB.shadow(PB.signals()); SH = SH[(SH.ex < PB.T_) & (PB.dates[SH.i.values] >= pd.Timestamp("2013-01-01"))]
pct = lambda x: f"{100 * x:+.1f}%"; out = {}
for nm, spec, w in [("no stop, 5% positions (live)", None, .05), ("-3% stop, 5%", dict(kind="pct_order", p=.03), .05), ("-3% stop, 7.5%", dict(kind="pct_order", p=.03), .075),
                    ("-3% stop, 10%", dict(kind="pct_order", p=.03), .10), ("-5% stop, 7.5%", dict(kind="pct_order", p=.05), .075), ("no stop, 7.5%", None, .075)]:
    PL = PB.plan(SH, gate=PB.ALL, stop=PB.stop_fn(spec) if spec else None, reuse=True); eq = PB.account(PL, w=w); tk = PL[PL.taken]; net = PB.trade_net(tk)
    pe = {e: PB.perf(eq, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")), ("2023-26", ("2023-01-01", "2026-12-31")))}
    out[nm] = dict(trades=len(tk), worst_trade_acct=float(net.min() * w), acct=pe)
    print(f"  {nm:30s} trades {len(tk):3d}, worst trade {pct(net.min() * w)} of the account | " + " | ".join(f"{e} {pct(v['cagr'])} DD {100*v['dd']:.1f}% Calmar {v['ratio']:.2f} losing years {v['losing_years']}" for e, v in pe.items()), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r74_extra2.json"), "w"), indent=1, default=float)
