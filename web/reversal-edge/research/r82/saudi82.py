"""Round 82 (PREREG.md): Hold Edge on Saudi. Usage: RE_WORK=<work folder> python3 saudi82.py design | confirm
design  = hold cases of trades that ended by 2019-12-31: marks 1 and 2 with M19 (no Saudi data in it), the Saudi adjustment and tables.
confirm = trades bought from 2020-01-01, opened once, everything frozen: marks 1, 2, 3 and the verdict."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import rebound as RB, holdedge as HE, eval80 as EV
MODE = sys.argv[1]; WORK = os.environ["RE_WORK"]; D = pd.read_parquet(os.path.join(WORK, f"r82_saudi_{MODE}.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS) & np.isfinite(D.rest)].reset_index(drop=True)
M19, ALL = HE.load("m19"); M80, _ = RB.load("m19"); e = RB.edge(M19, D); rest = D.rest.values; mon = D.month.values; noclock = RB.edge(M80, dict(Z=D.Z.values, MS=D.MS.values, ZMS=D.ZMS.values)); OUT = dict(mode=MODE, cases=int(len(D)), trades=int(D.case.nunique()))
print(f"Saudi {MODE}: {len(D)} hold cases from {D.case.nunique()} trades, {D.date.min().date()} to {D.date.max().date()}; sold above the close {100 * D.up.mean():.1f}%, average rest of the trade {100 * rest.mean():+.2f}%; passing the gates at that close {100 * D.gated.mean():.0f}%")
def marks(e, D, label, n=600):
    rest = D.rest.values; mon = D.month.values; sep = EV.separation(e, rest, mon, n=n); bt = EV.beats(e, dict(stretch=(D.Z.values, -1), momentum=(D.MS.values, -1), noclock=(RB.edge(M80, dict(Z=D.Z.values, MS=D.MS.values, ZMS=D.ZMS.values)), 1)), rest, mon, n=n)
    m1 = sep[1] > 0; m2 = all(bt[k]["lead_p5"] > 0 for k in ("stretch", "momentum", "noclock"))
    print(f"[{label}] mark 1: top third {100 * sep[3]:+.2f}% vs bottom third {100 * sep[4]:+.2f}% = {100 * sep[0]:+.2f} points, range {100 * sep[1]:+.2f} to {100 * sep[2]:+.2f} -> {'PASS' if m1 else 'FAIL'}")
    print(f"[{label}] mark 2: rank correlation with the rest of the trade: Hold Edge {bt['odds']:.3f} | stretch Z now alone {bt['stretch']['corr']:.3f}, lead {bt['stretch']['lead']:+.3f} (5th pct {bt['stretch']['lead_p5']:+.3f}) | market momentum alone {bt['momentum']['corr']:.3f}, lead {bt['momentum']['lead']:+.3f} ({bt['momentum']['lead_p5']:+.3f}) | "
          f"Rebound Edge with no clock {bt['noclock']['corr']:.3f}, lead {bt['noclock']['lead']:+.3f} ({bt['noclock']['lead_p5']:+.3f}) -> {'PASS' if m2 else 'FAIL'}")
    return dict(separation=sep, beats=bt, mark1=bool(m1), mark2=bool(m2))
OUT["m19"] = marks(e, D, "M19, no Saudi data")
def table(e, D, S, label):
    rest = D.rest.values; q1, q2 = np.quantile(e, [1 / 3, 2 / 3]); th = [(e <= q1), (e > q1) & (e < q2), (e >= q2)]; rows3 = [dict(stated=float(e[m].mean()), realized=float(rest[m].mean()), up=float(D.up.values[m].mean()), n=int(m.sum())) for m in th]
    print(f"[{label}] thirds: " + " | ".join(f"stated {100 * r['stated']:+.1f}% -> {100 * r['realized']:+.1f}% ({100 * r['up']:.0f} in 100 sold above the close)" for r in rows3))
    band = np.searchsorted(np.asarray(S["band_edges"]), e, side="right"); rowsb = []; u = D.unit.values
    for k in range(10):
        m = band == k
        if not m.sum(): continue
        b = S["bands"][k]; ok = m & np.isfinite(u) & (u > 0); rowsb.append(dict(band=k, n=int(m.sum()), stated=float(e[m].mean()), realized=float(rest[m].mean()), up=float(D.up.values[m].mean()), up_stated=b["up"], togo=float(np.median(D.togo.values[m])), togo_stated=b["togo"], worse=float((D.fur.values[ok] < b["furz_bad"] * u[ok]).mean()) if ok.sum() else np.nan))
    for r in rowsb: print(f"   band {r['band']}: {r['n']:6d} | {100 * r['stated']:+5.1f}% -> {100 * r['realized']:+5.1f}% | sold above the close {100 * r['up']:.0f} in 100 (stated {100 * r['up_stated']:.0f}) | sessions to the sale {r['togo']:.0f} ({r['togo_stated']:.0f}) | dipped below the stated 1-in-10 dip: {100 * r['worse']:.0f}%")
    return dict(thirds=rows3, bands=rowsb)
def water(D, label):
    """the stop question: by how far under water the trade is at sessions 5, 10, 20."""
    out = []; cuts = [(-9, -.15, "down 15% or more"), (-.15, -.10, "down 10 to 15%"), (-.10, -.05, "down 5 to 10%"), (-.05, 0, "down 0 to 5%"), (0, 9, "up")]
    for n in (5, 10, 20):
        x = D[D.n == n]
        for lo, hi, nm in cuts:
            m = (x.sofar >= lo) & (x.sofar < hi)
            if m.sum() >= 30: out.append(dict(n=n, state=nm, cases=int(m.sum()), rest=float(x.rest[m].mean()), up=float(x.up[m].mean()), final=float(((1 + x.sofar[m]) * (1 + x.rest[m]) - 1).mean()), edge=float(RB.edge(M19, x[m]).mean())))
    print(f"[{label}] the stop question (rest of the trade from that close): " + " | ".join(f"n={r['n']} {r['state']}: {100 * r['rest']:+.1f}% ({100 * r['up']:.0f} in 100 up, {r['cases']})" for r in out)); return out
def late(D, label):
    out = []
    for n in (25, 30, 35):
        for nm, m in (("still at -1.5 or lower", (D.n == n) & (D.Z <= -1.5)), ("between -1.5 and 0", (D.n == n) & (D.Z > -1.5))):
            if m.sum() >= 30: out.append(dict(n=n, state=nm, cases=int(m.sum()), rest=float(D.rest[m].mean()), up=float(D.up[m].mean())))
    print(f"[{label}] late in the trade: " + " | ".join(f"n={r['n']} {r['state']}: {100 * r['rest']:+.1f}% ({100 * r['up']:.0f} in 100, {r['cases']})" for r in out)); return out
def weather(e, D, label):
    rows = [dict(weather=nm, n=int((D.wx.values == w).sum()), stated=float(e[D.wx.values == w].mean()), realized=float(D.rest.values[D.wx.values == w].mean()), up=float(D.up.values[D.wx.values == w].mean())) for w, nm in ((0, "calm"), (1, "clouds"), (2, "storm"), (3, "deep")) if (D.wx.values == w).sum()]
    print(f"[{label}] by weather at that close: " + " | ".join(f"{r['weather']} {r['n']}: stated {100 * r['stated']:+.1f}% -> {100 * r['realized']:+.1f}% ({100 * r['up']:.0f} in 100)" for r in rows)); return rows
if MODE == "design":
    lo, hi = np.quantile(rest, [.01, .99]); y = np.clip(rest, lo, hi); g = D.gated.values
    def adj(ix, with_c=True):
        A = np.column_stack([np.ones(len(ix)), e[ix]] + ([g[ix]] if with_c else [])); return np.linalg.lstsq(A, y[ix], rcond=None)[0]
    full = adj(np.arange(len(D))); bs = np.array([adj(ix) for ix in EV.month_draws(mon, 600)]); c5, c95 = np.quantile(bs[:, 2], [.05, .95]); keep = bool(c5 > 0 or c95 < 0); co = full if keep else adj(np.arange(len(D)), with_c=False)
    S = dict(a=float(co[0]), b=float(co[1]), c=float(co[2]) if keep else 0.0, c_tried=float(full[2]), c_range=[float(c5), float(c95)], c_kept=keep, b_range=[float(np.quantile(bs[:, 1], .05)), float(np.quantile(bs[:, 1], .95))], fitted_on="Saudi hold cases of trades ended by 2019-12-31", cases=int(len(D)))
    ea = RB.edge(M19, D, saudi=S, gated=g); S["band_edges"], S["bands"] = HE.tables(D, ea, M19); S["zones"] = [float(v) for v in np.quantile(ea, [1 / 3, 2 / 3])]
    print(f"\nSaudi adjustment (2013-19 only): saudi hold edge = {100 * S['a']:+.2f}% + {S['b']:.2f} x hold edge" + (f" {100 * S['c']:+.2f}% when the stock passes the gates" if keep else "") + f" | gate term tried {100 * full[2]:+.2f}% (range {100 * c5:+.2f} to {100 * c95:+.2f}) -> {'kept' if keep else 'not kept'}; slope range {S['b_range'][0]:.2f} to {S['b_range'][1]:.2f}")
    ALL["saudi"] = S; ALL["saudi_tested"] = S; json.dump(ALL, open(HE.MODEL_FILE, "w"), indent=1); OUT["saudi"] = {k: v for k, v in S.items() if k != "bands"}
S = ALL["saudi_tested"]; ea = RB.edge(M19, D, saudi=S, gated=D.gated.values)
OUT["adjusted_marks"] = marks(ea, D, "terminal version: Saudi-adjusted" + (" (fitted on these cases: shown, not a test)" if MODE == "design" else " (frozen on 2013-19: a test)"))
OUT["table"] = table(ea, D, S, "Saudi-adjusted, Saudi tables" + (" (built from these cases)" if MODE == "design" else " (frozen on 2013-19)")); OUT["water"] = water(D, MODE); OUT["late"] = late(D, MODE); OUT["weather"] = weather(ea, D, "Saudi-adjusted")
OUT["by_n"] = [dict(n=int(n), cases=int((D.n == n).sum()), stated=float(ea[(D.n == n).values].mean()), realized=float(D.rest[D.n == n].mean()), up=float(D.up[D.n == n].mean())) for n in HE.GRID]
print("by sessions held (stated -> realized): " + "  ".join(f"n={r['n']}: {100 * r['stated']:+.1f}->{100 * r['realized']:+.1f}" for r in OUT["by_n"]))
OUT["by_year"] = {int(y_): dict(n=int((D.date.dt.year == y_).sum()), corr=EV.rank_corr(e[(D.date.dt.year == y_).values], rest[(D.date.dt.year == y_).values])) for y_ in sorted(D.date.dt.year.unique()) if (D.date.dt.year == y_).sum() >= 1000}
print("rank correlation by year (1,000+ cases): " + "  ".join(f"{y_} {v['corr']:+.2f}" for y_, v in OUT["by_year"].items()))
if MODE == "confirm":
    t = OUT["table"]; th = t["thirds"]; a_ok = th[0]["realized"] < th[1]["realized"] < th[2]["realized"]; b_rows = [r for r in t["bands"] if r["n"] >= 100]; gap = max(abs(r["up"] - r["up_stated"]) for r in b_rows); b_ok = gap <= .10
    print(f"\nmark 3: thirds rise ({100 * th[0]['realized']:+.1f}% < {100 * th[1]['realized']:+.1f}% < {100 * th[2]['realized']:+.1f}%): {'yes' if a_ok else 'NO'} | share sold above the close within 10 points of the stated share in every band: {'yes' if b_ok else 'NO'} (largest gap {100 * gap:.0f}) -> {'PASS' if a_ok and b_ok else 'FAIL'}")
    OUT["mark3"] = dict(a=bool(a_ok), b=bool(b_ok), gap=float(gap), passed=bool(a_ok and b_ok)); late_ = D.date >= "2023-01-01"; OUT["m19_2023_26"] = marks(e[late_.values], D[late_].reset_index(drop=True), "2023-26 check, M19")
    des = json.load(open(os.path.join(HERE, "saudi82_design.json")))["m19"]; m = OUT["m19"]; one = m["mark1"] and des["mark1"]; two = m["mark2"] and des["mark2"]
    OUT["verdict"] = "NOT VALID" if not one else ("USEFUL" if two and OUT["mark3"]["passed"] else "DESCRIPTIVE"); am = OUT["adjusted_marks"]; OUT["verdict_terminal"] = "USEFUL IN THE TERMINAL (one test period)" if (am["mark1"] and am["mark2"] and OUT["mark3"]["passed"]) else OUT["verdict"]
    print(f"\nVERDICT, chart formula: {OUT['verdict']} (mark 1: 2013-19 {'pass' if des['mark1'] else 'fail'}, 2020-26 {'pass' if m['mark1'] else 'fail'}; mark 2: 2013-19 {'pass' if des['mark2'] else 'fail'}, 2020-26 {'pass' if m['mark2'] else 'fail'}; mark 3: {'pass' if OUT['mark3']['passed'] else 'fail'})")
    print(f"VERDICT, terminal version (tested on 2020-26 only): {OUT['verdict_terminal']} (mark 1 {'pass' if am['mark1'] else 'fail'}, mark 2 {'pass' if am['mark2'] else 'fail'}, mark 3 {'pass' if OUT['mark3']['passed'] else 'fail'})")
json.dump(OUT, open(os.path.join(HERE, f"saudi82_{MODE}.json"), "w"), indent=1, default=float)
