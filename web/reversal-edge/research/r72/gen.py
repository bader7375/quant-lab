"""Builds the markdown tables of round 72 from r72_results.json (no hand-copied numbers)."""
import json, math, os
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(H, "r72_results.json")))
fin = lambda x: x is not None and isinstance(x, (int, float)) and math.isfinite(x)
pc = lambda x, s=True: (f"{100 * x:+.1f}%" if s else f"{100 * x:.0f}%") if fin(x) else "–"
def dt(b, t): return (f"{100 * b:+.1f} (t {t:+.1f})" if fin(t) else f"{100 * b:+.1f} (t n/a)") if fin(b) else "–"
SHORT = {"unfiltered (Z <= -2.62)": "Unfiltered (Z ≤ −2.62)", "ms <= -1.18 baseline": "**ms ≤ −1.18 baseline**", "H1 pulseAcc < -0.5": "H1 pulseAcc < −0.5",
         "H1b z10 <= -2.8": "H1b z10 ≤ −2.8", "H2 preMom > 0 & Z250 > -2.5": "H2 preMom > 0, Z250 > −2.5", "H3 secZ <= -1.0": "H3 secZ ≤ −1.0",
         "H3b secZ <= -1.2": "H3b secZ ≤ −1.2", "H3 contrast secZ > -0.5": "H3 contrast: secZ > −0.5", "H4 RSI14 <= 25 & volz > 1": "H4 RSI14 ≤ 25, volz > 1",
         "combined (ms+secZ+acc+preMom)": "Combined: H1 + preMom > 0 + H3", "combined + ML >= 50%": "Combined + ML ≥ 50%"}
def ev_table(T):
    out = ["| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in T.items():
        if not v.get("n"): out.append(f"| {SHORT[k]} | 0 | | | | | | |"); continue
        first = k.startswith("unfiltered"); base = k.startswith("ms <=")
        out.append(f"| {SHORT[k]} | {v['n']} | {pc(v['win'], False)} | {pc(v['avg'])} | {pc(v['med'])} | {pc(v.get('p05'))} | "
                   f"{'' if first else dt(v.get('d_base'), v.get('t_base'))} | {'' if first or base else dt(v.get('d_ms'), v.get('t_ms'))} |")
    return "\n".join(out)
L = []
for nm, T in list(R["events"]["saudi"].items()) + list(R["events"]["us"].items()):
    L += [f"#### {nm}", "", ev_table(T), ""]
EVT = "\n".join(L)
# timing
L = ["| Era · set | n | Buy next open: win · avg | Wait for close > prior high: traded · win · avg · wait − now (t) | Wait for Z to turn up: traded · win · avg · wait − now (t) |", "|---|---:|---:|---:|---:|"]
for k, o in R["timing"].items():
    era, st = k.split(" | "); st = "H4 set" if st.startswith("H4") else "RSI ≤ 25 + pulseAcc < −0.5"
    if not o.get("n"): L.append(f"| {era} · {st} | 0 | | | |"); continue
    cell = lambda w: f"{pc(o[w]['triggered'], False)} · {pc(o[w]['win'], False)} · {pc(o[w]['avg'])} · {100 * o[w]['diff']:+.1f} pts ({'t ' + format(o[w]['t'], '+.1f') if fin(o[w]['t']) else 'too few blocks'})"
    L.append(f"| {era} · {st} | {o['n']} | {pc(o['now_win'], False)} · {pc(o['now_avg'])} | {cell('a')} | {cell('b')} |")
TIM = "\n".join(L)
# sleeves
def sl_table(key, eras=("2013-19", "2020-26", "2013-26")):
    out = ["| Sleeve | Trades | " + " | ".join(f"{e}: growth/yr · worst DD · Sharpe · Calmar" for e in eras) + " |", "|---|---:|" + "---:|" * len(eras)]
    for nm, v in R["sleeves"].items():
        if nm.startswith("early") or key not in v: continue
        tr = f"{v['trades']}" + (f" ({v['stopped']} stopped)" if "stop" in nm and v.get("stopped") is not None else "")
        out.append(f"| {nm} | {tr} | " + " | ".join(f"{pc(v[key][e]['cagr'])} · {100 * v[key][e]['dd']:.1f}% · {v[key][e]['sharpe']:.2f} · {v[key][e]['calmar']:.2f}" for e in eras) + " |")
    return "\n".join(out)
SLA, SLC = sl_table("alone"), sl_table("core")
L = ["| Early 2011-12 stand-in sleeve | Trades in 2011-12 | Growth/yr · worst DD · Sharpe · Calmar |", "|---|---:|---:|"]
for nm, v in R["sleeves"].items():
    if nm.startswith("early"): o = v["alone"]["2011-12"]; L.append(f"| {nm[6:]} | {v['trades']} | {pc(o['cagr'])} · {100 * o['dd']:.1f}% · {o['sharpe']:.2f} · {o['calmar']:.2f} |")
SLE = "\n".join(L)
# acceptance
ok = lambda b: "–" if b is None else ("pass" if b else "**fail**")
L = ["| Filter | (1) Era 2 | (1) 2011-12 stand-in | (1) Era 1 | (2) Era 3 ± profitable | (3) sleeve | Verdict |", "|---|---|---|---|---|---|---|"]
for k, a in R["acceptance"].items():
    if "era2" not in a: continue
    L.append(f"| {SHORT[k]} | {ok(a['era2'])} | {'n/a (no ML before 2013)' if a['early_standin'] is None else 'cannot judge (4 events, all winners)'} | missing | {ok(a['era3'])} | {ok(a['sleeve'])} | not adopted |")
for k, a in R["acceptance"].items():
    if "era2" in a: continue
    L.append(f"| {k} | | | | | {ok(a['sleeve'])} | not adopted |")
ACC = "\n".join(L)
# extra A: deltas vs ms baseline, frozen definition vs ms-first definition
L = ["| Filter (inside ms ≤ −1.18) | Era 2 frozen | Era 2 ms-first | Era 3 prof. frozen | Era 3 prof. ms-first | Era 3 all frozen | Era 3 all ms-first |", "|---|---:|---:|---:|---:|---:|---:|"]
F = R["events"]["saudi"]; X = R["extra_ms_first"]
pairs = [("Era 2 2013-19", "Era 2 2013-19"), ("Era 3 2020-26, profitable filter", "Era 3 2020-26 profitable"), ("Era 3 2020-26, no profitable filter", "Era 3 2020-26 all")]
for k in SHORT:
    if k.startswith("unfiltered") or k.startswith("ms <="): continue
    cells = []
    for a, b in pairs:
        u, w = F[a].get(k, {}), X[b].get(k, {})
        cells += [dt(u.get("d_ms"), u.get("t_ms")) if u.get("n") else "–", dt(w.get("d_ms"), w.get("t_ms")) if w.get("n") else "–"]
    L.append(f"| {SHORT[k]} | " + " | ".join(cells) + " |")
EXA = "\n".join(L)
L = ["| Filter | Live trades kept | Kept: win · avg | Removed | Removed: win · avg |", "|---|---:|---:|---:|---:|"]
for k, v in R["extra_inside_live"].items():
    L.append(f"| {k} | {v['kept']} | {pc(v['kept_win'], False)} · {pc(v['kept_avg'])} | {v['removed']} | {pc(v['removed_win'], False)} · {pc(v['removed_avg'])} |")
EXB = "\n".join(L)
open(os.path.join(H, "tables.md"), "w").write("\n\n".join(["## EVT", EVT, "## TIM", TIM, "## SLA", SLA, "## SLC", SLC, "## SLE", SLE, "## ACC", ACC, "## EXA", EXA, "## EXB", EXB]))
print("ok")
