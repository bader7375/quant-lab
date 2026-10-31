from ideas import *
up_y = C > VWy; rising_y = VWy > VWy.shift(20)
tests = {
 # sigma bands, reversion to the VWAP
 "V1  monthly VWAP: close < VWAPm - 2σ -> exit at VWAPm (max 20d)": (C < VWm - 2 * SDm, VWm, None, 20),
 "V1r rolling 21d VWAP: close < VWAP - 2σ -> exit at VWAP (max 20d)": (C < VWr21 - 2 * SDr21, VWr21, None, 20),
 "V2  yearly VWAP: close < VWAPy - 2σ -> exit at VWAPy (max 60d)": (C < VWy - 2 * SDy, VWy, None, 60),
 "V2r rolling 250d VWAP: close < VWAP - 2σ -> exit at VWAP (max 60d)": (C < VWr250 - 2 * SDr250, VWr250, None, 60),
 "V2b yearly VWAP: close < VWAPy - 1σ -> exit at VWAPy (max 60d)": (C < VWy - SDy, VWy, None, 60),
 # trend use of VWAP
 "V3  reclaim yearly VWAP (cross up, VWAPy rising) -> exit close < VWAPy": ((C > VWy) & (C.shift() <= VWy.shift()) & rising_y, None, VWy, 120),
 "V4  monthly breakout: close > VWAPm + 2σ & above VWAPy -> exit < VWAPm": ((C > VWm + 2 * SDm) & up_y, None, VWm, 60),
 "V4r rolling breakout: close > VWAP21 + 2σ & above VWAP250 -> exit < VWAP21": ((C > VWr21 + 2 * SDr21) & (C > VWr250), None, VWr21, 60),
 "V5  pullback: above VWAPy, close < VWAPm - 1σ -> exit > VWAPm + 1σ (20d)": (up_y & (C < VWm - SDm), VWm + SDm, None, 20),
 # ATR bands
 "V6  ATR: close < VWAPm - 2 ATR -> exit at VWAPm (max 20d)": (C < VWm - 2 * ATR, VWm, None, 20),
 "V6y ATR: close < VWAPy - 3 ATR -> exit at VWAPy (max 60d)": (C < VWy - 3 * ATR, VWy, None, 60),
 "V7  ATR trend: close > VWAPy + 1 ATR (cross) -> exit < VWAPy (120d)": ((C > VWy + ATR) & (C.shift() <= (VWy + ATR).shift()), None, VWy, 120),
 "V8  ATR pullback: above VWAPy, close < VWAPm - 1 ATR -> exit at VWAPm + 1 ATR": (up_y & (C < VWm - ATR), VWm + ATR, None, 20),
}
for nm, (sg, tg, sp, mh) in tests.items():
    rep(nm, trades(sg, tg, sp, mh))
    rep("     + ML>=50% & market model positive", trades(sg & (PCT >= .5) & MKT, tg, sp, mh))
