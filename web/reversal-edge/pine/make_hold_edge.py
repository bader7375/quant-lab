"""Writes pine/hold_edge.pine from fable/holdedge_model.json, so the TradingView script carries the product's numbers.
Usage: python3 make_hold_edge.py   (run again after the model file changes)"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); X = json.load(open(os.path.join(HERE, "../fable/holdedge_model.json"))); S = X["saudi"]; M = X["live"]; r = S["raw"]; B = S["bands"]; c = r["clips"]
f = lambda v, k=4: f"{v:.{k}f}"; arr = lambda vals, k=3: ", ".join(f(v, k) for v in vals)
src = f'''//@version=6
// Hold Edge (reversal edge, round 82). For a trade you already hold: the average result, in %, of the REST of the trade, from this
// close to the sale, in past trades that stood where this one stands. The sale is the swing's: the open after the first close with
// stretch Z back at 0, or 40 sessions after the buy. The 0.2% cost of the sale is taken off.
// You tell it the buy date; it counts the sessions held and reads the stretch Z now and market momentum now.
// What it draws: a line from the buy to today (red = weak, below {f(100 * S["zones"][0], 1)}%; green = strong, {f(100 * S["zones"][1], 1)}% or more), and a table
// with the reading and, from Saudi trades with a like reading: how many in 100 were sold above today's close, the typical
// sessions to the sale, the typical further dip and the 1-in-10 dip (in % for THIS stock, from its own volatility).
// How it was made: fitted on 23 foreign markets and US large caps ({M["cases"]:,} readings), then adjusted on {S["cases"]:,} Saudi readings.
// What it is NOT: a stop or an exit rule. Tested on Saudi 2013-19 and 2020-26 it separates trades with much left from trades with
// little (top third +6.6% / +7.3%, bottom third -0.5% / -0.9%), but it ranks them no better than market momentum alone, and
// selling when it turned negative made the account worse. Trades further under water had MORE left to gain. Verdict: descriptive.
// It uses the index you choose for market momentum (the terminal uses the equal-weight average of liquid Saudi stocks), and it
// cannot see your gates: tick the input when the terminal says the stock passes them (worth {f(100 * r["gate"], 1)} points).
// Not compiled on TradingView from the research session: if it reports an error, send the message.
indicator("Hold Edge", shorttitle = "Hold Edge", overlay = false)

buyT   = input.time(timestamp("2026-11-01T00:00:00"), "The buy date (the session you bought at the open)", confirm = true)
mktSym = input.symbol("TADAWUL:TASI", "Market index")
gated  = input.bool(true, "The stock passes the gates (ML rank 50%+, market model positive, not loss-making)")
showT  = input.bool(true, "Table")

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
float unit = ta.stdev(clip(math.log(close / close[1]), -0.25, 0.25), 60, false) * math.sqrt(20)

// sessions held so far: 1 on the buy session
var int held = 0
var bool sold = false
if isD and time >= buyT and not sold
    held += 1
// the trade is over once the stretch closed at 0 or higher (sold at the next open) or 40 sessions are done
if held >= 1 and not sold and ((not na(zD) and zD >= 0) or held >= 40)
    sold := true
float left = (40.0 - held) / 40.0
bool  on   = isD and held >= 1 and held < 40 and not sold and not na(zD) and not na(mm) and zD < 0

// ---------------------------------------------------------------- the formula (Saudi weights, in %)
float zc  = clip(zD, {f(c["Z"][0], 2)}, {f(c["Z"][1], 2)})
float mc  = clip(mm, {f(c["MS"][0], 2)}, {f(c["MS"][1], 2)})
float zmc = clip(zD * mm, {f(c["ZMS"][0], 2)}, {f(c["ZMS"][1], 2)})
float lc  = clip(left, {f(c["LEFT"][0], 3)}, {f(c["LEFT"][1], 3)})
float zlc = clip(zD * left, {f(c["ZLEFT"][0], 2)}, {f(c["ZLEFT"][1], 2)})
float edge = {f(100 * r["c0"])} + ({f(100 * r["Z"])}) * zc + ({f(100 * r["MS"])}) * mc + ({f(100 * r["ZMS"])}) * zmc + ({f(100 * r["LEFT"])}) * lc + ({f(100 * r["ZLEFT"])}) * zlc + (gated ? {f(100 * r["gate"])} : 0.0)
float weak   = {f(100 * S["zones"][0], 2)}
float strong = {f(100 * S["zones"][1], 2)}

plot(on ? edge : na, "Hold Edge (%)", style = plot.style_linebr, linewidth = 2, color = edge < weak ? color.new(color.red, 10) : edge >= strong ? color.new(color.teal, 0) : color.new(color.gray, 10))
hline(0, "0", color = color.new(color.gray, 50), linestyle = hline.style_solid)
hline(strong, "Strong", color = color.new(color.teal, 40), linestyle = hline.style_dotted)

// ---------------------------------------------------------------- companions: Saudi trades in ten bands of the reading
var float[] bEdge = array.from({arr([100 * v for v in S["band_edges"]])})
var float[] bUp   = array.from({arr([100 * b["up"] for b in B], 0)})
var float[] bTogo = array.from({arr([b["togo"] for b in B], 0)})
var float[] bDip  = array.from({arr([b["furz_med"] for b in B])})
var float[] bBad  = array.from({arr([b["furz_bad"] for b in B])})
bandOf(float e) =>
    int k = 0
    for i = 0 to array.size(bEdge) - 1
        if e >= array.get(bEdge, i)
            k := i + 1
    k

if showT and barstate.islast
    var table t = table.new(position.top_right, 2, 6, bgcolor = color.new(color.black, 80), border_width = 1, border_color = color.new(color.gray, 70))
    string word = held < 1 ? "not bought yet" : sold ? "the sale is due or done" : not on ? "no reading" : edge < weak ? "WEAK" : edge >= strong ? "STRONG" : "FAIR"
    color  wc   = not on ? color.silver : edge < weak ? #e0623f : edge >= strong ? #3fb59a : color.white
    int    b2   = on ? bandOf(edge) : 0
    table.cell(t, 0, 0, "Hold Edge", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 0, on ? (edge >= 0 ? "+" : "") + str.tostring(edge, "#.0") + "%  " + word : word, text_color = wc, text_size = size.small, text_halign = text.align_right)
    table.cell(t, 0, 1, "Sessions held / left", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 1, str.tostring(held) + " / " + str.tostring(math.max(40 - held, 0)), text_color = color.white, text_size = size.small, text_halign = text.align_right)
    table.cell(t, 0, 2, "Sold above today's close", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 2, on ? str.tostring(array.get(bUp, b2), "#") + " in 100" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
    table.cell(t, 0, 3, "Sessions to the sale, typical", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 3, on ? str.tostring(array.get(bTogo, b2), "#") : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
    table.cell(t, 0, 4, "Typical further dip", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 4, on and not na(unit) ? str.tostring(100 * array.get(bDip, b2) * unit, "#.0") + "%" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
    table.cell(t, 0, 5, "1 trade in 10 dipped below", text_color = color.silver, text_size = size.small, text_halign = text.align_left)
    table.cell(t, 1, 5, on and not na(unit) ? str.tostring(100 * array.get(bBad, b2) * unit, "#.0") + "%" : "", text_color = color.white, text_size = size.small, text_halign = text.align_right)
'''
open(os.path.join(HERE, "hold_edge.pine"), "w").write(src); print("wrote hold_edge.pine:", len(src.splitlines()), "lines")
