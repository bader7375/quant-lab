"""v20 -> v21 (round 36): the user's rule - no Z-swing buys in loss-making companies (plan + signal card), research notes."""
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../v21"))
def patch(fn, pairs):
    s = open(fn).read()
    for a, b in pairs:
        assert s.count(a) == 1, (fn, a[:100], s.count(a)); s = s.replace(a, b)
    open(fn, "w").write(s)
LOSSY = "lossy=!!(typeof MLPF!==\"undefined\"&&MLPF&&MLPF.fin&&MLPF.fin[st.sym]&&MLPF.fin[st.sym].ni<=0)"
s = open("app3.js").read(); a = "msv=msAt(d.d[c]),mok=!(msv>MS_GATE),ok=pct0>=.5&&on&&mok;"; assert s.count(a) == 2
s = s.replace(a, "msv=msAt(d.d[c]),mok=!(msv>MS_GATE)," + LOSSY + ",ok=pct0>=.5&&on&&mok&&!lossy;"); open("app3.js", "w").write(s)
LT = '!lossy?"":`a profitable company (your rule: its latest annual result, FY${String(MLPF.fin[st.sym].fy).slice(0,4)}, is a loss)`'
patch("app3.js", [
 ('!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)}: the market is not falling, and dips like this kept falling: 28% winners in 2013–19, 39% in 2020–26)`:""',
  '!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)}: the market is not falling, and dips like this kept falling: 28% winners in 2013–19, 39% in 2020–26)`:"",' + LT),
 ('!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)})`:""', '!mok?`market momentum at or below −1.18 (now ${fmt(msv,2)})`:"",' + LT),
])
patch("app6.js", [
 ("msv=msAt(s.d[i]),mok=!(msv>MS_GATE),ok=pct>=.5&&on&&mok;", "msv=msAt(s.d[i]),mok=!(msv>MS_GATE),lossy=!!(MLPF&&MLPF.fin&&MLPF.fin[sym]&&MLPF.fin[sym].ni<=0),ok=pct>=.5&&on&&mok&&!lossy;"),
 ("if(f&&f.ni<=0)warn.push(`loss-making company (FY${String(f.fy).slice(0,4)}): in 2023–26 dips in loss-makers won 35–50% of the time vs 51–72% for profitable ones (one period only)`)}",
  "if(f&&f.ni<=0)warn.push(`skipped by your rule: loss-making company (FY${String(f.fy).slice(0,4)}); in 2023–26 the daily list's Z-swing picks won 83% of the time without loss-makers vs 64% with them (one short period)`)}"),
 ("- US EDGE SEARCH (round 35, pre-registered):", "- US STOCK SWING (round 36, pre-registered): earnings-style gaps on 3x volume, 52-week-high breakouts, leader pullbacks and +4% volume days vs random stocks bought on the same days in us100, KDD17 and CMIN-US: none beat random by a full point per trade (leader pullbacks and earnings gaps positive everywhere but +0.2..+1.8). A walk-forward US market model did not stop the 2008 losses of the market-timed dip swing. So for US stocks the edge is WHEN (after market sell-offs), not WHICH stock. Saudi: the user chose to skip loss-making companies; in 2023-26 (the only years with accounts) the daily list's Z-swing picks then won 83% (+6.7%/trade) vs 64% (+3.3%). saudiexchange.sa refuses this cloud server (Akamai 'Access Denied'), so no longer accounts history yet.\n- US EDGE SEARCH (round 35, pre-registered):"),
])
patch("body.html", [("reversal edge v20 · Saudi Z swing + US index dip", "reversal edge v21 · Saudi Z swing (profitable companies) + US")])
SEC = '''<h2>v21 (round 36): US stock swings, and swinging only profitable Saudi companies</h2>
<p><b>US stocks.</b> Four US-style swing setups were tested against random stocks bought and sold on the same days (the honest yardstick, because every US stock list we have is made of survivors): earnings-style gaps of 5%+ on triple volume, 52-week-high breakouts on double volume, pullbacks in the strongest stocks, and +4% days on triple volume.</p>
<table class="t"><tr><th style="text-align:left">setup</th><th>us100 2010–17</th><th>us100 2018–26</th><th>KDD17 2007–16</th><th>CMIN-US 2018–21</th></tr>
<tr><td style="text-align:left">earnings-style gap (trailing stop)</td><td>+1.8 pts vs random</td><td>+0.3</td><td>+4.9</td><td>+0.4</td></tr>
<tr><td style="text-align:left">leader pullback (hold 20)</td><td>+0.7</td><td>+0.3</td><td>+0.3</td><td>+0.2</td></tr>
<tr><td style="text-align:left">52-week-high breakout</td><td>+0.4</td><td>0.0</td><td>+0.4</td><td>+0.1</td></tr>
<tr><td style="text-align:left">+4% day on volume</td><td>+0.4</td><td>+0.8</td><td>−0.2</td><td>+0.9</td></tr></table>
<p>None reached the required +1 point per trade with statistical confidence in 2018–26. Buying after US market sell-offs still wins often (76% of trades in 2018–26), but random large caps on the same days did almost as well, and a walk-forward US market model did not stop the 2008 losses. The daily message therefore shows the US sell-off window (open when US large-cap market momentum is −1.18 or lower) and the SPY/QQQ dip rule, labelled as timing edges. (Data note: bad opening prints in the US files were corrected; conclusions unchanged.)</p>
<p><b>Saudi: profitable companies only.</b> Your rule now applies in the daily list, the plan and the signal card: no Z-swing buy in a company whose latest annual result is a loss. Accounts exist only from FY2022 (Yahoo), so the check covers April 2023 onward: the daily list's Z-swing picks won <b>83% (+6.7% per trade)</b> without loss-makers vs 64% (+3.3%) with them; about 23 trades, so a short record. saudiexchange.sa refuses this cloud server ("Access Denied" from its Akamai edge), so the full accounts history is not reachable yet.</p>
'''
s = open("app5.js").read(); a = "<h2>v20 (round 35)"; assert s.count(a) == 1; open("app5.js", "w").write(s.replace(a, SEC + a))
print("patched v21")
