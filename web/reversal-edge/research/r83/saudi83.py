"""Round 83 (PREREG.md): Rebound Edge 40 and Hold Edge 40 on Saudi. Usage: RE_WORK=<work folder> python3 saudi83.py design | confirm
design  = trades ended by 2019-12-31: marks 1 and 2 with M19 (no Saudi data in it), the Saudi adjustments and tables (frozen here).
confirm = trades bought from 2020-01-01, opened once, everything frozen; an indicator that failed mark 1 in design is not opened."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
MODE = sys.argv[1]; WORK = os.environ["RE_WORK"]; R19, RALL = RB.load("m19", RB.MODEL_FILE_40); H19, HALL = HE.load("m19", HE.MODEL_FILE_40); OUT = dict(mode=MODE)
DES = json.load(open(os.path.join(HERE, "saudi83_design.json"))) if MODE == "confirm" else None
def rd(nm): x = pd.read_parquet(os.path.join(WORK, f"r83_saudi_{nm}_{MODE}.parquet")); return x[np.isfinite(x.Z) & np.isfinite(x.MS)].reset_index(drop=True)
def marks(e, D, col, comps, label, n=600):
    r = D[col].values; mon = D.month.values; sep = EV.separation(e, r, mon, n=n); bt = EV.beats(e, comps, r, mon, n=n); m1 = sep[1] > 0; m2 = all(bt[k]["lead_p5"] > 0 for k in comps)
    print(f"[{label}] mark 1: top third {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}% = {100 * sep[0]:+.2f} points, range {100 * sep[1]:+.2f} to {100 * sep[2]:+.2f} -> {'PASS' if m1 else 'FAIL'}")
    print(f"[{label}] mark 2: rank correlation: reading {bt['odds']:.3f} | " + " | ".join(f"{k} alone {bt[k]['corr']:.3f}, lead {bt[k]['lead']:+.3f} (5th pct {bt[k]['lead_p5']:+.3f})" for k in comps) + f" -> {'PASS' if m2 else 'FAIL'}")
    return dict(separation=sep, beats=bt, mark1=bool(m1), mark2=bool(m2))
def adjust(D, e, col, label):
    r = D[col].values; lo, hi = np.quantile(r, [.01, .99]); y = np.clip(r, lo, hi); g = D.gated.values
    def fit(ix, with_c=True): A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
    full = fit(np.arange(len(D))); bs = np.array([fit(ix) for ix in EV.month_draws(D.month.values, 600)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0); co = full if keep else fit(np.arange(len(D)), with_c=False)
    S = dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))], fitted_on="Saudi cases of trades ended by 2019-12-31", cases=int(len(D)))
    print(f"[{label}] Saudi adjustment (2013-19 only): saudi = {100 * S['a']:+.2f}% + {S['b']:.2f} x reading" + (f" {100 * S['c']:+.2f}% when the stock passes the gates" if keep else "") + f" | gate term tried {100 * full[2]:+.2f}% (range {100 * c5:+.2f} to {100 * c95:+.2f}) -> {'kept' if keep else 'not kept'}"); return S
def table(e, D, S, col, upcol, stated_up, label):
    r = D[col].values; q1, q2 = np.quantile(e, [1 / 3, 2 / 3]); th = [(e <= q1), (e > q1) & (e < q2), (e >= q2)]; rows3 = [dict(stated=float(e[m].mean()), realized=float(r[m].mean()), up=float(D[upcol].values[m].mean()), n=int(m.sum())) for m in th]
    print(f"[{label}] thirds: " + " | ".join(f"stated {100 * x['stated']:+.1f}% -> {100 * x['realized']:+.1f}% ({100 * x['up']:.0f} in 100)" for x in rows3))
    band = np.searchsorted(np.asarray(S["band_edges"]), e, side="right"); rows = []
    for k in range(10):
        m = band == k
        if m.sum(): rows.append(dict(band=k, n=int(m.sum()), stated=float(e[m].mean()), realized=float(r[m].mean()), up=float(D[upcol].values[m].mean()), up_stated=float(S["bands"][k][stated_up])))
    print(f"[{label}] by band: " + " | ".join(f"{x['band']}: {100 * x['stated']:+.1f}->{100 * x['realized']:+.1f}, {100 * x['up']:.0f} (stated {100 * x['up_stated']:.0f}), {x['n']}" for x in rows)); return dict(thirds=rows3, bands=rows)
def mark3(t, label):
    th = t["thirds"]; a = th[0]["realized"] < th[1]["realized"] < th[2]["realized"]; br = [x for x in t["bands"] if x["n"] >= 100]; gap = max(abs(x["up"] - x["up_stated"]) for x in br) if br else np.nan; b = bool(br) and gap <= .10
    print(f"[{label}] mark 3: thirds rise: {'yes' if a else 'NO'}; shares within 10 points in every band with 100+ cases: {'yes' if b else 'NO'} (largest gap {100 * gap:.0f}) -> {'PASS' if a and b else 'FAIL'}"); return dict(a=bool(a), b=bool(b), gap=float(gap), passed=bool(a and b))
def weather(e, D, col, upcol, label):
    rows = [dict(weather=nm, n=int((D.wx.values == w).sum()), stated=float(e[D.wx.values == w].mean()), realized=float(D[col].values[D.wx.values == w].mean()), up=float(D[upcol].values[D.wx.values == w].mean())) for w, nm in ((0, "calm"), (1, "clouds"), (2, "storm"), (3, "deep")) if (D.wx.values == w).sum()]
    print(f"[{label}] by weather: " + " | ".join(f"{x['weather']} {x['n']}: stated {100 * x['stated']:+.1f}% -> {100 * x['realized']:+.1f}% ({100 * x['up']:.0f} in 100)" for x in rows)); return rows
def verdict(des, con, m3):
    one = des["mark1"] and con["mark1"]; two = des["mark2"] and con["mark2"]; return "NOT VALID" if not one else ("USEFUL" if two and m3["passed"] else "DESCRIPTIVE")
# ================================================================ Rebound Edge 40
if MODE == "design" or DES["rebound40"]["m19"]["mark1"]:
    D = rd("trades"); e = RB.edge(R19, D); X = OUT["rebound40"] = dict(cases=int(len(D)), wins=float(D.win.mean()), net=float(D.net.mean()))
    print(f"Saudi {MODE}, Rebound Edge 40: {len(D)} trades held 40 sessions, {D.date.min().date()} to {D.date.max().date()}; wins {100 * D.win.mean():.1f}%, average net {100 * D.net.mean():+.2f}%; live-plan signals among them {int(D.sig.sum())}")
    X["m19"] = marks(e, D, "net", dict(stretch=(D.Z.values, -1), momentum=(D.MS.values, -1)), "Rebound Edge 40, M19, no Saudi data")
    if MODE == "design":
        S = adjust(D, e, "net", "Rebound Edge 40"); ea0 = RB.edge(R19, D, saudi=S, gated=D.gated.values); S["band_edges"], S["bands"] = RB.saudi_tables(D, ea0, R19); S["zones"] = [float(v) for v in np.quantile(ea0, [1 / 3, 2 / 3])]
        RALL["saudi"] = S; RALL["saudi_tested"] = S; json.dump(RALL, open(RB.MODEL_FILE_40, "w"), indent=1); X["saudi"] = {k: v for k, v in S.items() if k != "bands"}
    S = RALL["saudi_tested"]; ea = RB.edge(R19, D, saudi=S, gated=D.gated.values)
    X["adjusted"] = marks(ea, D, "net", dict(stretch=(D.Z.values, -1), momentum=(D.MS.values, -1)), "Rebound Edge 40, Saudi-adjusted" + (" (fitted here: shown, not a test)" if MODE == "design" else " (frozen: a test)"))
    X["table"] = table(ea, D, S, "net", "win", "win", "Rebound Edge 40"); X["weather"] = weather(ea, D, "net", "win", "Rebound Edge 40")
    sg = D.sig.values > 0; X["signals"] = dict(n=int(sg.sum()), stated=float(ea[sg].mean()) if sg.any() else None, realized=float(D.net.values[sg].mean()) if sg.any() else None, win=float(D.win.values[sg].mean()) if sg.any() else None,
                                               corr=float(EV.rank_corr(ea[sg], D.net.values[sg])) if sg.sum() > 20 else None)
    if sg.any(): print(f"[Rebound Edge 40] inside the live plan's own signals ({sg.sum()}): stated {100 * X['signals']['stated']:+.1f}% -> realized {100 * X['signals']['realized']:+.1f}%, wins {100 * X['signals']['win']:.0f}%, rank correlation {X['signals']['corr']}")
    if MODE == "confirm":
        X["mark3"] = mark3(X["table"], "Rebound Edge 40"); late = (D.date >= "2023-01-01").values; X["m19_2023_26"] = marks(e[late], D[late].reset_index(drop=True), "net", dict(stretch=(D.Z.values[late], -1), momentum=(D.MS.values[late], -1)), "Rebound Edge 40, 2023-26, M19")
        X["verdict"] = verdict(DES["rebound40"]["m19"], X["m19"], X["mark3"]); print(f"\nVERDICT Rebound Edge 40: {X['verdict']}\n")
else: print("Rebound Edge 40 failed mark 1 on 2013-19: 2020-26 not opened for it."); OUT["rebound40"] = dict(skipped=True)
# ================================================================ Hold Edge 40
if MODE == "design" or DES["hold40"]["m19"]["mark1"]:
    D = rd("hold"); D = D[np.isfinite(D.rest)].reset_index(drop=True); e = RB.edge(H19, D); nc = RB.edge(R19, dict(Z=D.Z.values, MS=D.MS.values, ZMS=D.ZMS.values)); X = OUT["hold40"] = dict(cases=int(len(D)), trades=int(D.case.nunique()))
    print(f"\nSaudi {MODE}, Hold Edge 40: {len(D)} hold cases from {D.case.nunique()} trades; sold above the close {100 * D.up.mean():.1f}%, average rest {100 * D.rest.mean():+.2f}%")
    comps = lambda m=None: dict(stretch=(D.Z.values if m is None else D.Z.values[m], -1), momentum=(D.MS.values if m is None else D.MS.values[m], -1), noclock=(nc if m is None else nc[m], 1))
    X["m19"] = marks(e, D, "rest", comps(), "Hold Edge 40, M19, no Saudi data")
    if MODE == "design":
        S = adjust(D, e, "rest", "Hold Edge 40"); ea0 = RB.edge(H19, D, saudi=S, gated=D.gated.values); S["band_edges"], S["bands"] = HE.tables(D, ea0, H19); S["zones"] = [float(v) for v in np.quantile(ea0, [1 / 3, 2 / 3])]
        HALL["saudi"] = S; HALL["saudi_tested"] = S; json.dump(HALL, open(HE.MODEL_FILE_40, "w"), indent=1); X["saudi"] = {k: v for k, v in S.items() if k != "bands"}
    S = HALL["saudi_tested"]; ea = RB.edge(H19, D, saudi=S, gated=D.gated.values)
    X["adjusted"] = marks(ea, D, "rest", comps(), "Hold Edge 40, Saudi-adjusted" + (" (fitted here: shown, not a test)" if MODE == "design" else " (frozen: a test)"))
    X["table"] = table(ea, D, S, "rest", "up", "up", "Hold Edge 40"); X["weather"] = weather(ea, D, "rest", "up", "Hold Edge 40")
    water = []
    for who, sel in (("all stretched-stock trades", np.ones(len(D), bool)), ("the live plan's own signals", D.sig.values > 0)):
        for n in (5, 10, 20):
            for lo, hi, nm in ((-9, -.15, "down 15% or more"), (-.15, -.10, "down 10 to 15%"), (-.10, -.05, "down 5 to 10%"), (-.05, 0, "down 0 to 5%"), (0, 9, "up")):
                m = sel & (D.n.values == n) & (D.sofar.values >= lo) & (D.sofar.values < hi)
                if m.sum() >= 20: water.append(dict(who=who, n=n, state=nm, cases=int(m.sum()), rest=float(D.rest.values[m].mean()), up=float(D.up.values[m].mean())))
    X["water"] = water; print("[Hold Edge 40] the stop question (rest of a 40-session hold from that close): " + " | ".join(f"{w['who'][:3]} n={w['n']} {w['state']}: {100 * w['rest']:+.1f}% ({100 * w['up']:.0f} in 100, {w['cases']})" for w in water))
    X["by_n"] = [dict(n=int(n), stated=float(ea[(D.n == n).values].mean()), realized=float(D.rest[D.n == n].mean())) for n in HE.GRID]; print("[Hold Edge 40] by sessions held: " + "  ".join(f"n={x['n']}: {100 * x['stated']:+.1f}->{100 * x['realized']:+.1f}" for x in X["by_n"]))
    if MODE == "confirm":
        X["mark3"] = mark3(X["table"], "Hold Edge 40"); late = (D.date >= "2023-01-01").values; X["m19_2023_26"] = marks(e[late], D[late].reset_index(drop=True), "rest", comps(late), "Hold Edge 40, 2023-26, M19")
        X["verdict"] = verdict(DES["hold40"]["m19"], X["m19"], X["mark3"]); print(f"\nVERDICT Hold Edge 40: {X['verdict']}")
else: print("Hold Edge 40 failed mark 1 on 2013-19: 2020-26 not opened for it."); OUT["hold40"] = dict(skipped=True)
json.dump(OUT, open(os.path.join(HERE, f"saudi83_{MODE}.json"), "w"), indent=1, default=float)
