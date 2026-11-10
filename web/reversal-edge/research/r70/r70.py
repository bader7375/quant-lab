"""Round 70 (PREREG.md): improvements to the Z score account. Families A-F, DESIGN -> CONFIRM, stress, honesty check."""
import os, sys, json, numpy as np, pandas as pd
H70 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H70); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H70); d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01")); VR = np.nan_to_num(PB.VOL, nan=-9e9); MLR = np.nan_to_num(PB.PCTv, nan=-1.0)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
def cut(SH): return SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
SIG = PB.signals(); SH0 = cut(PB.shadow(SIG))
# sell-off clusters from the qualifying signal days of the live rule (no look-ahead: age uses past signal days only)
sd = np.where(SIG.any(1))[0]; AGE = np.full(T_, -1); st = None; prev = None
for i in sd:
    if prev is None or i - prev > 20: st = i
    AGE[i] = i - st; prev = i
half_z = PB.zexit_fn(0.0, cap=10 ** 6)
def build(spec, rank=None, side=.002, cash=True, w=.05):
    """spec: dict(fam, ...) -> (plan trades, equity)"""
    k = spec.get("kind", "live"); rk = VR if rank is None else rank; kw = dict(gate=PB.ALL, rank=rk)
    if k == "E2":
        Pa = PB.plan(SH0, **kw); Pb = PB.plan(cut(PB.shadow(SIG, exit_fn=PB.zexit_fn(0.0, 60))), **kw)
        Pa = Pa[Pa.taken].assign(w=w / 2); Pb = Pb[Pb.taken].assign(w=w / 2); PL = pd.concat([Pa, Pb], ignore_index=True); PL["taken"] = True
        return PL, PB.account(PL, w=w / 2, side=side, cash=cash)
    SH = SH0
    if k == "A": kw["pre_cap"] = spec["c"]
    elif k == "B": kw["gate"] = AGE >= spec["k"]
    elif k == "C": kw["pace"] = spec["n"]
    elif k == "D": kw["gate"] = np.nan_to_num(PB.MS, nan=9) <= spec["x"]
    elif k == "E1": kw["half"] = lambda i, j, d1, ex: half_z(i, j, d1)
    elif k == "E3": SH = cut(PB.shadow(SIG, renew=True))
    elif k in ("E4", "E5"): SH = cut(PB.shadow(SIG, hold=spec["h"]))
    elif k == "F": SH = cut(PB.shadow(PB.signals(ml=spec["ml"])))
    elif k == "combo":
        if "ml" in spec or spec.get("renew") or "h" in spec: SH = cut(PB.shadow(PB.signals(ml=spec.get("ml", .5)), hold=spec.get("h", PB.HOLD), renew=bool(spec.get("renew"))))
        g = PB.ALL
        if "k" in spec: g = g & (AGE >= spec["k"])
        if "x" in spec: g = g & (np.nan_to_num(PB.MS, nan=9) <= spec["x"])
        kw["gate"] = g
        if "c" in spec: kw["pre_cap"] = spec["c"]
        if "n" in spec: kw["pace"] = spec["n"]
        if spec.get("half"): kw["half"] = lambda i, j, d1, ex: half_z(i, j, d1)
    PL = PB.plan(SH, **kw); return PL, PB.account(PL, w=w, side=side, cash=cash)
MENU = {"live": dict(kind="live")}
for c in (4, 3, 2, 1, 0): MENU[f"A at most {c} before the turn"] = dict(kind="A", c=c)
for k in (1, 3, 5, 10): MENU[f"B from sell-off session {k}"] = dict(kind="B", k=k)
for n in (2, 3, 5, 10): MENU[f"C {n} sessions between buys"] = dict(kind="C", n=n)
for x in (-1.5, -2.0, -2.53): MENU[f"D momentum <= {x}"] = dict(kind="D", x=x)
MENU["E1 half out at Z 0"] = dict(kind="E1"); MENU["E2 two books (half Z 0)"] = dict(kind="E2"); MENU["E3 renew on a new signal"] = dict(kind="E3")
MENU["E4 hold 30"] = dict(kind="E4", h=30); MENU["E5 hold 60"] = dict(kind="E5", h=60)
for m in (.6, .7): MENU[f"F ML bar {int(100 * m)}%"] = dict(kind="F", ml=m)
FAM = lambda nm: nm[0]
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
RES = {}; EQ = {}; TR = {}
def tstats(PL):
    tk = PL[PL.taken]; n = pd.Series(PB.trade_net(tk)).dropna()
    return dict(n=int(len(tk)), win=float((n > 0).mean()), avg=float(n.mean()), worst5=float(n.quantile(.05)), worst=float(n.min()))
print("Z score account 5 x 5% (growth per year, worst drawdown, ratio) and the trades taken 2013-26")
for nm, spec in MENU.items():
    PL, eq = build(spec); EQ[nm] = eq; RES[nm] = dict(acct={e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}, tr=tstats(PL)); t = RES[nm]["tr"]
    print(f"  {nm:30s} 13-19 {fa(RES[nm]['acct']['2013-19'])} | 20-26 {fa(RES[nm]['acct']['2020-26'])} | 23-26 {fa(RES[nm]['acct']['2023-26'])} | 13-26 {fa(RES[nm]['acct']['2013-26'])} | trades {t['n']:3d} win {100 * t['win']:3.0f}% avg {100 * t['avg']:+5.1f}% w5 {100 * t['worst5']:+6.1f}% worst {100 * t['worst']:+6.1f}%")
L = RES["live"]["acct"]
def better(nm, e, res=None):
    r = (res or RES[nm]["acct"])[e]; return r["cagr"] >= L[e]["cagr"] - 1e-9 and r["dd"] <= L[e]["dd"] + .002 and r["ratio"] > L[e]["ratio"]
print("\nfamily picks (better than live in 2013-19 -> best 2013-19 ratio; confirmed if better than live in 2020-26)")
PICKS = {}
for fam in "ABCDEF":
    names = [n for n in MENU if n != "live" and FAM(n) == fam]; ok = [n for n in names if better(n, "2013-19")]
    pick = max(ok, key=lambda n: RES[n]["acct"]["2013-19"]["ratio"]) if ok else None; conf = bool(pick and better(pick, "2020-26")); PICKS[fam] = dict(pick=pick, confirmed=conf)
    print(f"  {fam}: better in 2013-19: {ok or 'none'} | pick: {pick} | confirmed in 2020-26: {conf} | better than live in both eras: {[n for n in names if better(n, '2013-19') and better(n, '2020-26')] or 'none'}")
# ---------------------------------------------------------------- stress for confirmed picks
print("\nstress on 2013-26 (return / drawdown, pick vs live under the same stress)")
STRESS = {"0.8% costs": dict(side=.004), "ML order in the slots": dict(rank=MLR), "idle money earning nothing": dict(cash=False)}
for fam, p in PICKS.items():
    if not p["confirmed"]: continue
    nm = p["pick"]; npass = 0; ntest = 0; line = f"  {nm}:"
    for sn, kw in STRESS.items():
        a = PB.perf(build(MENU[nm], **kw)[1], *ER["2013-26"]); b = PB.perf(build(MENU["live"], **kw)[1], *ER["2013-26"]); ok = a["ratio"] > b["ratio"]; npass += ok; ntest += 1
        line += f" {sn} {a['ratio']:.2f} vs {b['ratio']:.2f} {'pass' if ok else 'FAIL'};"
    names = [n for n in MENU if n != "live" and FAM(n) == fam]; ix = names.index(nm); nb = [names[k] for k in (ix - 1, ix + 1) if 0 <= k < len(names)] if fam != "E" else []
    if nb:
        ok = all(RES[n]["acct"]["2013-26"]["cagr"] >= L["2013-26"]["cagr"] - 1e-9 and RES[n]["acct"]["2013-26"]["dd"] <= L["2013-26"]["dd"] + .002 and RES[n]["acct"]["2013-26"]["ratio"] > L["2013-26"]["ratio"] for n in nb)
        npass += ok; ntest += 1; line += f" neighbours {nb} {'pass' if ok else 'FAIL'};"
    p["stress"] = (int(npass), int(ntest)); p["stress_ok"] = bool(npass >= ntest - 1); print(line + f" -> {npass} of {ntest}: {'PASS' if p['stress_ok'] else 'FAIL'}")
# ---------------------------------------------------------------- honesty check (yearly re-choice, spliced yearly returns)
ch = {Y: max(MENU, key=lambda k: PB.perf(EQ[k], "2013-01-01", f"{Y - 1}-12-31")["ratio"]) for Y in range(2016, 2027)}
r = pd.concat([EQ[ch[Y]].loc[f"{Y - 1}-12-25":f"{Y}-12-31"].pct_change().loc[f"{Y}-01-01":] for Y in range(2016, 2027)]); eqw = (1 + r.fillna(0)).cumprod()
w = PB.perf(eqw, "2016-01-01", "2026-12-31"); wa = PB.perf(eqw, "2016-01-01", "2020-12-31"); wb = PB.perf(eqw, "2021-01-01", "2026-12-31")
la = PB.perf(EQ["live"], "2016-01-01", "2020-12-31"); lb = PB.perf(EQ["live"], "2021-01-01", "2026-12-31")
print(f"\nhonesty check, yearly re-choice from the whole menu: 2016-26 {fa(w)} vs live {fa(L['2016-26'])} -> {'at least as good' if w['ratio'] >= L['2016-26']['ratio'] else 'WORSE than live'} | 2016-20 {fa(wa)} (live {fa(la)}) | 2021-26 {fa(wb)} (live {fa(lb)})")
print("  choices: " + "; ".join(f"{Y}: {c}" for Y, c in ch.items()))
json.dump(dict(res=RES, picks=PICKS, wf=dict(res=w, h1=wa, h2=wb, choice=ch)), open("r70_results.json", "w"), indent=1, default=float)
