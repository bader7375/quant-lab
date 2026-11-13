"""Writes pine/rebound_edge.pine from fable/rebound_model.json, so the numbers in the TradingView script are the product's numbers.
Usage: python3 make_rebound_edge.py   (run again after the model file changes)"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); X = json.load(open(os.path.join(HERE, "../fable/rebound_model.json"))); S = X["saudi"]; M = X["live"]; r = S["raw"]; B = S["bands"]; H = X["horizons"]
f = lambda v, k=4: f"{v:.{k}f}"; arr = lambda vals, k=4: ", ".join(f(v, k) for v in vals); flat = lambda q: arr([v for b in B for v in b["cone"][q]], 3)
src = f'''//@version=6
// Rebound Edge (reversal edge, round 80). For a stretched stock (stretch Z {X["line"]} or lower): the average net result, in %, of a buy
// at the next open in past cases with the same market momentum and stretch. The trade is sold at the open after the first close
// with stretch Z back at 0, or after 40 sessions; 0.4% costs are taken off.
// What it draws:
//   - Pane: a column on every session the stock is stretched. Red = weak (below {f(100 * S["zones"][0], 1)}%), grey = fair, green = strong ({f(100 * S["zones"][1], 1)}% or more).
//   - Table: the edge, and from Saudi cases with a like edge: profit in 100, typical sessions, the typical dip and the 1-in-10 dip
//     (in % for THIS stock, from its own volatility).
//   - Cone, on the price chart: where such cases stood 1 to 40 sessions after the buy (middle line, 25-75% and 10-90% bands).
// How it was made: fitted on 23 foreign markets and US large caps ({M["cases"]:,} cases), then adjusted on {S["cases"]:,} Saudi cases.
// What it is NOT: a new source of edge. Tested on Saudi 2013-19 and 2020-26 it separates good setups from bad ones (top third
// +7.7% / +8.9% a trade, bottom third -3.7% / -2.4%) but it ranks them no better than market momentum alone. Verdict: descriptive.
// Differences from the Fable terminal: the terminal uses the equal-weight average of liquid Saudi stocks for market momentum; this
// script uses the index you choose (TASI is weighted by size), so readings differ a little. It cannot see your gates: tick the
// input when the terminal says the stock passes them (that is worth {f(100 * r["gate"], 1)} points).
// Not compiled on TradingView from the research session: if it reports an error, send the message.
indicator("Rebound Edge", shorttitle = "Rebound Edge", overlay = false, max_lines_count = 100)

grpM   = "Market"
mktSym = input.symbol("TADAWUL:TASI", "Market index", group = grpM)
grpG   = "Your gates (the script cannot see them)"
gated  = input.bool(true, "The stock passes the gates (ML rank 50%+, market model positive, not loss-making)", group = grpG)
grpV   = "View"
showC  = input.bool(true, "Cone on the price chart", group = grpV)
showT  = input.bool(true, "Table", group = grpV)

// ---------------------------------------------------------------- the scanner's formulas
clip(float x, float lo, float hi) => math.max(math.min(x, hi), lo)
stretchZ(float src) =>
    float r  = clip(math.log(src / src[1]), -0.25, 0.25)
    float sd = ta.stdev(r, 60, false)
    (math.sum(r, 10) / (sd[10] * math.sqrt(10)) + math.sum(r, 20) / (sd[20] * math.sqrt(20)) + math.sum(r, 60) / (sd[60] * math.sqrt(60))) / 3
momentum(float src) =>
    float r  = clip(math.log(src / src[1]), -0.25, 0.25)
    float sd = ta.stdev(r, 60, false)
    math.sum(r, 60) / (sd[60] * math.sqrt(60))

bool  isD  = timeframe.isdaily and timeframe.multiplier == 1
float zD   = stretchZ(close)
float mm   = request.security(mktSym, "D", momentum(close), ignore_invalid_symbol = true)
float dr   = clip(math.log(close / close[1]), -0.25, 0.25)
float unit = ta.stdev(dr, 60, false) * math.sqrt(20)              // the stock's normal 20-session swing

// ---------------------------------------------------------------- the formula (Saudi weights, in %)
float zc   = clip(zD, {f(r["clips"]["Z"][0], 2)}, {f(r["clips"]["Z"][1], 2)})
float mc   = clip(mm, {f(r["clips"]["MS"][0], 2)}, {f(r["clips"]["MS"][1], 2)})
float zmc  = clip(zD * mm, {f(r["clips"]["ZMS"][0], 2)}, {f(r["clips"]["ZMS"][1], 2)})
float edge = {f(100 * r["c0"])} + ({f(100 * r["Z"])}) * zc + ({f(100 * r["MS"])}) * mc + ({f(100 * r["ZMS"])}) * zmc + (gated ? {f(100 * r["gate"])} : 0.0)
bool  on   = isD and not na(zD) and not na(mm) and zD <= {X["line"]}
float weak   = {f(100 * S["zones"][0], 2)}
float strong = {f(100 * S["zones"][1], 2)}

plot(on ? edge : na, "Rebound Edge (%)", style = plot.style_columns, color = edge < weak ? color.new(color.red, 20) : edge >= strong ? color.new(color.teal, 10) : color.new(color.gray, 30))
hline(0, "0", color = color.new(color.gray, 50), linestyle = hline.style_solid)
hline(strong, "Strong", color = color.new(color.teal, 40), linestyle = hline.style_dotted)

// ---------------------------------------------------------------- companions: Saudi cases in ten bands of edge
var float[] bEdge = array.from({arr([100 * v for v in S["band_edges"]], 3)})
var float[] bWin  = array.from({arr([100 * b["win"] for b in B], 0)})
var float[] bDays = array.from({arr([b["days"] for b in B], 0)})
var float[] bDip  = array.from({arr([b["dipz_med"] for b in B], 3)})
var float[] bBad  = array.from({arr([b["dipz_bad"] for b in B], 3)})
var int[]   hz    = array.from({", ".join(str(h) for h in H)})
// the cone in units of the stock's 20-session swing: 10 bands x {len(H)} horizons
var float[] c10 = array.from({flat("q10")})
var float[] c25 = array.from({flat("q25")})
var float[] c50 = array.from({flat("q50")})
var float[] c75 = array.from({flat("q75")})
var float[] c90 = array.from({flat("q90")})
bandOf(float e) =>
    int k = 0
    for i = 0 to array.size(bEdge) - 1
        if e >= array.get(bEdge, i)
            k := i + 1
    k

var line[] cone = array.new_line()
drawPath(float[] q, int band, color col, int wd) =>
    float y0 = close
    int   x0 = bar_index
    for i = 0 to array.size(hz) - 1
        float y1 = close * (1 + array.get(q, band * array.size(hz) + i) * unit)
        int   x1 = bar_index + array.get(hz, i)
        array.push(cone, line.new(x0, y0, x1, y1, xloc = xloc.bar_index, color = col, width = wd, force_overlay = true))
        y0 := y1
        x0 := x1

if barstate.islast
    for l in cone
        line.delete(l)
    array.clear(cone)
    if on and showC and not na(unit)
        int b = bandOf(edge)
        drawPath(c10, b, color.new(#1d4f7c, 70), 1)
        drawPath(c90, b, color.new(#1d4f7c, 70), 1)
        drawPath(c25, b, color.new(#1d4f7c, 40), 1)
        drawPath(c75, b, color.new(#1d4f7c, 40), 1)
        drawPath(c50, b, color.new(#1d4f7c, 0), 2)
    if showT
        var table t = table.new(position.top_right, 2, 6, bgcolor = color.new(color.black, 80), border_width = 1, border_color = color.new(color.gray, 70))
        string word = not on ? "not stretched" : edge < weak ? "WEAK" : edge >= strong ? "STRONG" : "FAIR"
        color  wc   = not on ? color.silver : edge < weak ? #e0623f : edge >= strong ? #3fb59a : color.white
        int    b2   = on ? bandOf(edge) : 0
        table.cell(t, 0, 0, "Rebound Edge", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 0, on ? (edge >= 0 ? "+" : "") + str.tostring(edge, "#.0") + "%  " + word : word, text_color = wc, text_size = size.small, text_halign = text.align_right)
        table.cell(t, 0, 1, "Stretch Z / market momentum", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 1, str.tostring(zD, "#.00") + " / " + (na(mm) ? "n/a" : str.tostring(mm, "#.00")), text_color = color.white, text_size = size.small, text_halign = text.align_right)
        table.cell(t, 0, 2, "Ended in profit", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 2, on ? str.tostring(array.get(bWin, b2), "#") + " in 100" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
        table.cell(t, 0, 3, "Sessions, typical", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 3, on ? str.tostring(array.get(bDays, b2), "#") : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
        table.cell(t, 0, 4, "Typical dip on the way", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 4, on and not na(unit) ? str.tostring(100 * array.get(bDip, b2) * unit, "#.0") + "%" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
        table.cell(t, 0, 5, "1 case in 10 dipped below", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
        table.cell(t, 1, 5, on and not na(unit) ? str.tostring(100 * array.get(bBad, b2) * unit, "#.0") + "%" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)

alertcondition(on and edge >= strong and not (on[1] and edge[1] >= strong), "Rebound Edge turns strong", "{{{{ticker}}}}: Rebound Edge is strong. Descriptive only: check the Fable terminal (gates, one buy a day) before any buy.")
'''
open(os.path.join(HERE, "rebound_edge.pine"), "w").write(src); print("wrote rebound_edge.pine:", len(src.splitlines()), "lines")
