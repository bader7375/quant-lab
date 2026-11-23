"""Builds RESULTS.md from r74_results.json, r74_extra.json and r74_extra2.json (no hand-copied numbers in the tables)."""
import json, math, os
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(H, "r74_results.json")))
X = json.load(open(os.path.join(H, "r74_extra.json"))); X2 = json.load(open(os.path.join(H, "r74_extra2.json")))
fin = lambda x: isinstance(x, (int, float)) and math.isfinite(x)
p = lambda x: f"{100 * x:+.1f}%" if fin(x) else "–"; f = lambda x, d=2: f"{x:.{d}f}" if fin(x) else "–"
L = R["live"]
A1 = ["| Stop | Trades | Stopped | Win | Avg win | Avg loss | Payoff | Worst trade | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for nm, o in R["A1"].items():
    a = o["acct"]; A1.append(f"| {nm} | {o['trades']} | {o['stopped']} | {100*o['win']:.0f}% | {p(o['avg_win'])} | {p(o['avg_loss'])} | {f(o['payoff'])} | {p(o['worst'])} | {p(a['2013-19']['cagr'])} · {100*a['2013-19']['dd']:.1f}% · {f(a['2013-19']['calmar'])} | {p(a['2020-26']['cagr'])} · {100*a['2020-26']['dd']:.1f}% · {f(a['2020-26']['calmar'])} |")
eras = ["Era 1 2004-12", "Era 2 2013-19", "Era 3 2020-26", "2023-26", "US 2010-17", "US 2018-26", "lib 2013-19 (check)"]
A2 = ["| Stop | " + " | ".join(eras) + " |", "|---|" + "---:|" * len(eras)]
for nm, o in R["A2"].items():
    A2.append(f"| {nm} | " + " | ".join((f"{v['n']} · {100*v['win']:.0f}% · avg {p(v['ret'])}" if nm == "no stop" else f"{v['n']} · {100*v['win']:.0f}% · {f(v['payoff'],1)} · {f(v['exp'])}R · {p(v['ret'])}") if v.get("n") else "0" for v in (o[e] for e in eras)) + " |")
B = ["| Rule | " + " | ".join(eras) + " |", "|---|" + "---:|" * len(eras)]
for nm, o in R["B"].items():
    B.append(f"| {nm} | " + " | ".join(f"{v['n']} · {100*v['win']:.0f}% · {f(v['payoff'],1)} · {f(v['exp'])}R ({f(v['t'],1)}) · {f(v['pf'],1)}" if v.get("n") else "0" for v in (o["eras"][e] for e in eras)) + " |")
BA = ["| Rule | Trades taken | Worst trade (account) | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | Live signals per trade 2013-19 · 2020-26 |", "|---|---:|---:|---:|---:|---:|",
      f"| **live plan (5 x 5%, no stop)** | | | {p(L['2013-19']['cagr'])} · {100*L['2013-19']['dd']:.1f}% · {f(L['2013-19']['calmar'])} | {p(L['2020-26']['cagr'])} · {100*L['2020-26']['dd']:.1f}% · {f(L['2020-26']['calmar'])} | |"]
for nm, o in R["B"].items():
    a, t = o["acct"], o["live_trades"]
    BA.append(f"| {nm} | {o['taken']} | {p(o['worst_acct'])} | {p(a['2013-19']['cagr'])} · {100*a['2013-19']['dd']:.1f}% · {f(a['2013-19']['calmar'])} | {p(a['2020-26']['cagr'])} · {100*a['2020-26']['dd']:.1f}% · {f(a['2020-26']['calmar'])} | {t['2013-19']['n']} · {100*t['2013-19']['win']:.0f}% · {f(t['2013-19']['exp'])}R ; {t['2020-26']['n']} · {100*t['2020-26']['win']:.0f}% · {f(t['2020-26']['exp'])}R |")
ST = ["| Rule | Era 2 2013-19 | Era 3 2020-26 | (1) all eras | (2) payoff | (3) account | (4) stress | Verdict |", "|---|---:|---:|---|---|---|---|---|"]
ok = lambda b: "pass" if b else "**fail**"
for nm, o in R["B"].items():
    s, a = o["stress"], o["accept"]
    ST.append(f"| {nm} | {f(s['Era 2 2013-19']['exp'])}R · PF {f(s['Era 2 2013-19']['pf'],1)} | {f(s['Era 3 2020-26']['exp'])}R · PF {f(s['Era 3 2020-26']['pf'],1)} | {ok(a['c1'])} | {ok(a['c2'])} | {ok(a['c3'])} | {ok(a['c4'])} | {'offered' if a['all'] else 'not offered'} |")
E1 = ["| Rule | Fill rule | Era 1 2004-12 | Era 2 2013-19 | Era 3 2020-26 | 2023-26 | US 2010-17 | US 2018-26 |", "|---|---|---:|---:|---:|---:|---:|---:|"]
nmap = {"B3X1True": "B3·X1·re", "B3X1False": "B3·X1", "B2X2True": "B2·X2·re", "B2X3False": "B2·X3", "B1X2True": "B1·X2·re"}
for k, o in X.items():
    for mode in ("base", "pess"):
        cells = []
        for e in ("Era 1 2004-12", "Era 2 2013-19", "Era 3 2020-26", "2023-26", "US 2010-17", "US 2018-26"):
            v = next((o[m][e] for m in o if m.startswith(mode) and isinstance(o[m], dict) and e in o[m]), {})
            cells.append(f"{f(v.get('exp'))}R · PF {f(v.get('pf'),1)}" if v.get("n") else "–")
        E1.append(f"| {nmap[k]} | {'as tested' if mode == 'base' else 'pessimistic'} | " + " | ".join(cells) + " |")
E2 = ["| Rule (live signals) | Risk per trade | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | Invested on average |", "|---|---:|---:|---:|---:|",
      f"| live plan (5 x 5%, no stop) | – | {p(L['2013-19']['cagr'])} · {100*L['2013-19']['dd']:.1f}% · {f(L['2013-19']['calmar'])} | {p(L['2020-26']['cagr'])} · {100*L['2020-26']['dd']:.1f}% · {f(L['2020-26']['calmar'])} | about 4% |"]
for k, o in X.items():
    m = o["risk_matched"]; a = m["acct"]
    E2.append(f"| {nmap[k]} | {100*m['risk']:.2f}% | {p(a['2013-19']['cagr'])} · {100*a['2013-19']['dd']:.1f}% · {f(a['2013-19']['calmar'])} | {p(a['2020-26']['cagr'])} · {100*a['2020-26']['dd']:.1f}% · {f(a['2020-26']['calmar'])} | {100*m['avg_invested']:.1f}% (approximate) |")
E3 = ["| Live plan version | Trades | Worst trade (account) | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | 2023-26 growth · DD |", "|---|---:|---:|---:|---:|---:|"]
for nm, o in X2.items():
    a = o["acct"]; E3.append(f"| {nm} | {o['trades']} | {p(o['worst_trade_acct'])} | {p(a['2013-19']['cagr'])} · {100*a['2013-19']['dd']:.1f}% · {f(a['2013-19']['ratio'])} | {p(a['2020-26']['cagr'])} · {100*a['2020-26']['dd']:.1f}% · {f(a['2020-26']['ratio'])} | {p(a['2023-26']['cagr'])} · {100*a['2023-26']['dd']:.1f}% |")
T = lambda rows: "\n".join(rows)
md = open(os.path.join(H, "RESULTS_head.md")).read() + f"""
## Part A1: the live plan with a near stop (plan book engine, 5 x 5%, 2013-26)
{T(A1)}

## Part A2: the current entry with a near stop, price-only setup, per trade
Each cell: trades · win rate · payoff (average win / average loss) · expectancy in R (R = the stop distance) · average net per trade.
{T(A2)}

## Part B: entries built for a near stop, price-only setup, per trade
Each cell: trades · win rate · payoff · expectancy in R (t, clustered by 40-session blocks) · profit factor.
B1 = break of yesterday's high, B2 = inside/NR4-day break, B3 = B1 inside the market-turn window; X1 = 3R bracket, X2 = break-even + 3 ATR
trail, X3 = half at 2R + X2; ·re = one re-entry after a stop-out. The "lib 2013-19" column repeats Era 2 on the library data (a check).
{T(B)}

## Part B: the account with the live signals and 0.5% of the account risked per trade
{T(BA)}

## Stress (0.80% round trip, every stop filled 0.5% worse) and the frozen acceptance
{T(ST)}

## Extra 1 (not judged): entry-day stops counted on the day's low (pessimistic)
Daily bars cannot tell whether a dip below the stop on the entry day came before or after the buy-stop fill. As tested, only a close below
the stop counts on the entry day; the pessimistic rule counts any low below the stop as a stop-out.
{T(E1)}

## Extra 2 (not judged): the account at the risk per trade that matches the live plan's 2013-19 worst drawdown
{T(E2)}

## Extra 3 (not judged): the live plan with a -3% stop order and bigger positions
{T(E3)}
"""
open(os.path.join(H, "RESULTS.md"), "w").write(md); print(len(md))
