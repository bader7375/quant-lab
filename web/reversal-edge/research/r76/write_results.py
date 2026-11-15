"""Writes RESULTS.md for round 76 from the saved outputs (r76_summary.json, r76_design_families.csv, r76_map_*.{json,csv}, r76_overlap.*)."""
import json, numpy as np, pandas as pd
S = json.load(open("r76_summary.json")); M = json.load(open("r76_map_summary.json")); D = pd.read_csv("r76_design_families.csv")
FM = pd.read_csv("r76_map_features.csv"); LL = pd.read_csv("r76_map_lucklist.csv"); OV = pd.read_csv("r76_overlap.csv"); NLIVE = json.load(open("r76_overlap.json"))["live_signals"]
KEYS = ("raw10", "exc10", "raw40", "exc40"); SETS = ("saudi_2020_26", "saudi_2004_12", "us_2010_26")
KN = {"raw10": "10 sessions, net", "exc10": "10 sessions, vs market", "raw40": "40 sessions, net", "exc40": "40 sessions, vs market", "all": "all four"}
NAME = dict(zc="stretch Z", z10="stretch Z 10-day part", z20="stretch Z 20-day part", z60="stretch Z 60-day part", z250="250-day Z", vol60="60-day volatility",
            atrp="daily range (ATR %)", ret1="1-day return", ret5="5-day return", ret20="20-day return", ret60="60-day return", dhi="distance from the 1-year high",
            dlo="distance from the 1-year low", volz="volume z", rsi="RSI(14)", M="Momentum Pulse", acc="Momentum Pulse acceleration", pre="prior momentum",
            ms="market momentum", ms5="market momentum 5-day change", bounce="market bounce from its 20-day low", dd250="market fall from its 1-year high",
            gate="market-turn window", breadth="breadth", nft="number of first touches", secz="industry Z", selloff_days="sessions into the sell-off",
            loglq="traded value", logp="price level", gap="opening gap", rng="day range", clv="close location in the day", vtrend="volume trend (20 vs 60 days)",
            d20="distance from the 20-day average", d50="distance from the 50-day average", d200="distance from the 200-day average", ndown="down closes in a row",
            ret250="12-month return", rel20="20-day return minus the market's")
pc = lambda x: f"{100 * x:.1f}%"; pp = lambda x: f"{100 * x:+.2f}%"
P = pd.DataFrame(S["placebo"]); thr = S["threshold"]; rb = S["real_best"]
FA = pd.read_csv("r76_map_families.csv"); FA["margin"] = (FA.t_real - FA.t_luck_median) / (FA.t_luck_max - FA.t_luck_median)
def best_for(f):
    x = FA[FA.feats.str.split("&").apply(lambda v: f in v) & (FA.t_real > 0) & (FA.t_luck_max > FA.t_luck_median)]; return x.loc[x.margin.idxmax()]
L = []; w = L.append
w("# Round 76 results: a million-rule search that knows how lucky it can get (plan in PREREG.md, addendum written before its run)")
w("Scripts: r76.py (engine), r76_run.py (the planned run, log r76.out), r76_map.py (addendum: engine check, information test, feature map, luck-list test; log")
w("r76_map.out), r76_overlap.py (overlap with the live plan's signals), r76_lag.py (which stocks inside a sell-off), write_results.py (this file).")
w("Outputs: r76_summary.json, r76_design_families.csv, r76_families.csv (empty: nothing reached confirmation), r76_map_summary.json,")
w("r76_map_features.csv, r76_map_families.csv, r76_map_lucklist.csv, r76_overlap.csv, r76_overlap.json, r76_lag.csv.")
w("")
w("## Verdict")
w(f"- No new signal. {S['n_rules']:,} rules per search, 21 searches (1 real, 20 with the dates scrambled): {21 * S['n_rules'] / 1e6:.1f} million rule tests on")
w("  197,902 liquid Saudi stock-days of 2013-19. The best real rules score no higher than the best rules the same search finds on scrambled data,")
w(f"  where nothing can work. One rule cleared the luck bar by a hair ({rb['exc10']:.2f} against {thr['exc10']:.2f}) and failed the honest check. Nothing reached")
w("  the unseen data as a candidate; nothing is traded from this round. The live plan stays as it is.")
w(f"- What the search did learn (description only): its best 40-session rules are the plan's own territory. The top one (market sell-off, the most")
o1 = OV[(OV.key == "raw40") & (OV["rank"] == 1)].iloc[0]
w(f"  volatile 20% of stocks, market 16%+ below its 1-year high) holds {o1.share_of_live:.0%} of the plan's {NLIVE} signals of 2013-26, and all 20 of the top 40-session")
w("  rules beat the average stock-day on all three unseen sets. Buying volatile stocks while the market is weak is the one robust pattern.")
w("- \"Oversold\" alone (stretch Z, RSI, short returns) carries no broad information outside sell-offs. Trend and calm do (60-day return, strength")
w("  against the market, distance from the 1-year high, daily range), but only weakly: a calm-near-the-high pattern held in Saudi 2004-12 and 2020-26,")
w("  not in the US, and scrambled searches find similar rules.")
w("")
w("## 1. The engine")
c = M["engine_check"]
w(f"- 39 features, single and paired decile conditions, 3 market states, 2 horizons, 2 targets: {S['n_rules']:,} rules per search; a rule needs 1,500 stock-days.")
w(f"- Engine check: {c['rules']:,} rules (all rules on 3 features) recomputed one by one: worst difference {c['worst_mean_diff']:.0e} in the average, {c['worst_t_rel_diff']:.0e} in t;")
w(f"  counts identical ({c['count_mismatches']} mismatches). The addendum's rerun reproduced every best score of the planned run.")
w("")
w("## 2. Luck bars and the real search (the planned decision)")
w("Score = plain t of a rule's average. It only ranks rules: overlapping holding periods and stocks moving together make it far too large, which is")
w("why the bar comes from scrambled searches (returns shifted in time against the features by 250+ sessions, the same shift for every stock).")
w("")
w("| target | luck bar (best of 20 scrambled) | scrambled median | real best | real rank of 21 |")
w("|---|---|---|---|---|")
for k in KEYS:
    rank = 1 + int((P[k] >= rb[k]).sum()); w(f"| {KN[k]} | {thr[k]:.1f} | {P[k].median():.1f} | {rb[k]:.1f} | {rank} |")
w("")
d = D.iloc[0]
w(f"- Rules above the bar: {S['n_above']}. Families: {S['n_families']}. Passed the honest design check (clustered t >= 3, both halves positive): {S['n_design_ok']}.")
w(f"- The one rule: 10 sessions vs market, normal market, 60-day volatility in its lowest 10% and market momentum in its lowest 30% (between -1.18 and")
w(f"  -0.49). Design: {pp(d.design_mean)} over the market, n {d.design_n:,}, clustered t {d.design_t_cl:.2f} (needed 3), 2013-16 {pp(d.h1)}, 2017-19 {pp(d.h2)}. Failed.")
w("  Plain meaning: in a soft market the calmest stocks fall less than the rest. A defensive effect, not a buy signal.")
w("- Luck alone reached t 56-83 on 40-session returns and 30-60 on 10-session returns. A single period can make almost any market-timing rule")
w("  look excellent; earlier one-period results should be read with this in mind.")
w("")
w("## 3. What the search learned (addendum, description only)")
w("### 3a. Information test: does the real data beat all 20 scrambled versions of a rule family?")
w("With no information this happens in about 4.8% of families (1 in 21).")
w("")
w("| target | families | real | scrambled range | scrambled median | real rank of 21 |")
w("|---|---|---|---|---|---|")
for k in list(KEYS) + ["all"]:
    i = M["information"][k]; w(f"| {KN[k]} | {i['families']:,} | {pc(i['real'])} | {pc(i['placebo_min'])}-{pc(i['placebo_max'])} | {pc(i['placebo_median'])} | {i['real_rank']} |")
w("")
w("- Scrambled searches lose 2.4% of rows (returns missing after the shift), about 1.2% of t. Corrected, the real share is 14.8%, still far above the scrambled median.")
w("- Reading: the features carry some information, spread thin over many families. It is clearest for 10-session returns against the market")
w("  (rank 1). No single rule stands out from luck.")
w("")
w("### 3b. Feature map")
w("Share of each feature's 468 families (alone or paired, 3 market states, 4 targets) where the real data beats all 20 scrambled versions; luck max =")
w("the highest share any scrambled search reached; best family = its real family with the largest margin over its own 20 scrambled versions")
w("((real t - their median) / (their max - their median); above 1 = beats all 20).")
w("")
w("| feature | share | luck max | rank of 21 | net returns (real / luck max) | vs market (real / luck max) | best family (real t / scrambled max t) |")
w("|---|---|---|---|---|---|---|")
for r in FM.itertuples():
    b = best_for(r.feature)
    w(f"| {NAME[r.feature]} | {pc(r.share)} | {pc(r.luck_max)} | {r.rank} | {pc(r.share_raw)} / {pc(r.luck_raw_max)} | {pc(r.share_exc)} / {pc(r.luck_exc_max)} | {b.rule.replace('|', '/')} ({b.t_real:.1f} / {b.t_luck_max:.1f}) |")
top = FM[FM["rank"] == 1]
w("")
w(f"- Above their luck range ({len(top)} of 39): " + ", ".join(NAME[f] for f in top.feature) + ".")
w(f"- Inside their luck range ({int((FM['rank'] > 1).sum())} of 39): " + ", ".join(NAME[f] for f in FM[FM['rank'] > 1].feature) + ".")
w("- The \"oversold\" measures (stretch Z and its parts, RSI, short returns, Momentum Pulse) are all inside their luck range. These cuts are much")
w("  broader than the plan's signal (stretch Z <= -2.62 is rarer than its lowest decile, -1.19), so this says nothing against the plan's rule; it says")
w("  \"oversold\" alone, outside a sell-off, is not an edge.")
w("")
w("### 3c. Luck-list test: do the real search's top rules hold on unseen data better than scrambled searches' top rules?")
w("Top 20 families per target from each search, applied unchanged to Saudi 2020-26, Saudi 2004-12 (built-in library) and US 2010-26 (115 large caps).")
w("Lift = the rule's average minus the average liquid stock-day of that set (same costs). A list's rules are near-duplicates, so 20 rules are a few ideas.")
w("")
w("| target | real: beat the average in all 3 sets | scrambled lists: mean (max) | real rank of 21 | Saudi 2020-26 real / scrambled | Saudi 2004-12 | US | average lift real / scrambled |")
w("|---|---|---|---|---|---|---|---|")
for k in list(KEYS) + ["all"]:
    x = M["luck_list"][k]; r0, sm, mx = x["real"], x["scrambled_mean"], x["scrambled_max"]
    w(f"| {KN[k]} | {r0['all3']:.0%} | {sm['all3']:.0%} ({mx['all3']:.0%}) | {x['real_rank_all3']} | " + " | ".join(f"{r0[s]:.0%} / {sm[s]:.0%}" for s in SETS) + f" | {pp(r0['avg_lift'])} / {pp(sm['avg_lift'])} |")
w("")
w("- 40 sessions, net: the real list wins (rank 1). The best scrambled list (90%) had landed on \"market momentum in its lowest 20%\": right on unseen")
w("  data for the wrong reason. Both say the same thing: buying while the market is weak pays over 40 sessions.")
r10 = LL[(LL.search == 0) & (LL.key == "raw10")]; nod = int((r10.lift_saudi_2020_26.isna() | r10.lift_us_2010_26.isna()).sum())
w(f"- 10 sessions, net: {nod} of the 20 real rules need a market more than 37% below its 1-year high; that never happened in Saudi 2020-26 or in")
w("  the US, so they could not be tested there (counted as misses).")
w("- Against the market: the real 10-session list is second of 21 (60% against a best scrambled 65%); the 40-session list is ordinary (7th): its")
w("  rules held in both unseen Saudi eras but lost in the US.")
w("- Against the market, the lift is before the 0.40% round trip a rule pays and holding the market does not: a 10-session lift of +0.4% to +1.0%")
w("  leaves 0% to +0.6% per trade after costs; a 40-session lift of +0.6% to +2.6% leaves +0.2% to +2.2%.")
w("")
w("### 3d. The real top rules on unseen data (lift per trade over the average stock-day)")
w("| target | rule (design 2013-19) | t | design average | Saudi 2020-26 | Saudi 2004-12 | US 2010-26 |")
w("|---|---|---|---|---|---|---|")
fmt = lambda v, n: "no days" if not np.isfinite(v) else f"{pp(v)} (n {n:,})"
for k in KEYS:
    for r in LL[(LL.search == 0) & (LL.key == k)].head(5).itertuples():
        rule = r.rule.split(" | ", 1)[1].replace(" | ", ": ")
        w(f"| {KN[k]} | {rule} | {r.t:.1f} | {pp(r.design_mean)} | {fmt(r.lift_saudi_2020_26, r.n_saudi_2020_26)} | {fmt(r.lift_saudi_2004_12, r.n_saudi_2004_12)} | {fmt(r.lift_us_2010_26, r.n_us_2010_26)} |")
w("")
r40 = LL[(LL.search == 0) & (LL.key == "raw40")]
w(f"All 20 real 40-session rules: lift {pp(r40.lift_saudi_2020_26.min())} to {pp(r40.lift_saudi_2020_26.max())} in Saudi 2020-26, {pp(r40.lift_saudi_2004_12.min())} to")
w(f"{pp(r40.lift_saudi_2004_12.max())} in Saudi 2004-12, {pp(r40.lift_us_2010_26.min())} to {pp(r40.lift_us_2010_26.max())} in the US (average stock-day: +0.68%, +2.73%, +2.56% per 40 sessions).")
w("")
w("### 3e. Overlap with the live plan (Saudi 2013-26)")
w("| target | top-20 rules: share of the plan's signals inside (median, range) | plan signals as a share of the rule's stock-days (median) |")
w("|---|---|---|")
for k in KEYS:
    x = OV[OV.key == k]; w(f"| {KN[k]} | {x.share_of_live.median():.0%} ({x.share_of_live.min():.0%}-{x.share_of_live.max():.0%}) | {x.share_of_rule_days_live.median():.2%} |")
w("")
w(f"The best 40-session rule covers {o1.rule_days:,} stock-days and holds {o1.live_signals_inside} of the plan's {NLIVE} signals: the plan picks a thin slice")
w("(first stretch-Z touches with the ranker and the market model) of the territory the search found. The calm-near-the-high rules hold none of the")
w("plan's signals: they live in normal markets, when the plan is in cash.")
w("")
w("### 3f. Inside a sell-off: which stocks? (40-session net return per trade, clustered t, winners; design and three unseen sets)")
LG = pd.read_csv("r76_lag.csv"); SN4 = ["design 2013-19", "Saudi 2020-26", "Saudi 2004-12", "US 2010-26"]
w("| stocks bought on sell-off days | " + " | ".join(SN4) + " | plan signals inside (of " + str(NLIVE) + ") |")
w("|---|---|---|---|---|---|")
INSIDE = {"sell-off, 20-day lag behind the market in the lowest 10%": 316, "sell-off, daily range (ATR %) in the top 20%": 587, "sell-off, all liquid stocks": NLIVE}
for name in ["sell-off, all liquid stocks", "sell-off, daily range (ATR %) in the top 20%", "sell-off, 20-day lag behind the market in the lowest 10%"]:
    d = LG[(LG.rule == name) & (LG.key == "raw40")].set_index("set")
    w(f"| {name.replace('sell-off, ', '')} | " + " | ".join(f"{pp(d.loc[s_, 'mean'])} (t {d.loc[s_, 't_cl']:.1f}, {d.loc[s_, 'win']:.0%})" for s_ in SN4) + f" | {INSIDE[name]} |")
ex = LG[LG.key == "exc40"].set_index(["rule", "set"])
w("")
w("- Most of the gain is the market's own rebound: the average liquid stock made +2.6% to +7.5% in the 40 sessions after a sell-off day.")
w("- Against the market (40 sessions, before costs), the extra is small and not reliable on unseen data: most volatile " + ", ".join(f"{pp(ex.loc[('sell-off, daily range (ATR %) in the top 20%', s_), 'mean'] + .004)}" for s_ in SN4[1:])
  + "; biggest laggards " + ", ".join(f"{pp(ex.loc[('sell-off, 20-day lag behind the market in the lowest 10%', s_), 'mean'] + .004)}" for s_ in SN4[1:]) + " (Saudi 2020-26, Saudi 2004-12, US).")
w("- The biggest laggards looked best in design (+14.7%). On unseen data neither group is clearly better: the most volatile made more in Saudi")
w("  2020-26 and the US, the laggards beat the market by a little more in all three sets, and no gap is reliable (t about 1 or less against the")
w("  market). The plan's order (most volatile first) stays; changing it would need its own test.")
w("")
w("## 4. What it means")
w("1. The search found nothing new that survives luck. The \"million rounds\" protect against overfitting exactly as planned: without the scrambled")
w("   searches, its best rules (t 47-79) would have looked like sure things.")
w("2. Its strongest unseen-data result is the plan's own idea: weak market + volatile stock + 40-session hold. This supports the live plan; it")
w("   adds no new filter (the plan already buys the most volatile first, only in sell-offs).")
w("3. A weaker, Saudi-only pattern: calm stocks near their 1-year high beat the market a little in normal markets. Its unseen-data evidence is")
w("   now used, so any further test could only measure an account, not prove the pattern.")
w("4. \"Oversold\" measures help only inside a sell-off. Outside one, a low stretch Z or RSI is not a reason to buy.")
w("5. Inside a sell-off, most of the gain is the market's rebound; the most volatile stocks add a few points of net return, mostly by moving")
w("   more than the market. Nothing here clearly beats the plan's order.")
w("")
w("## 5. Status")
w("Nothing live changes. Nothing was confirmed, so there is no account test from the plan. Offered to the user: an account test of the calm-near-the-")
w("high pattern as a separate sleeve for idle cash (new pre-registered round), or nothing.")
open("RESULTS.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
