"""Round 79 (PREREG.md): every idea as a set of switches for fable/swingbook.simulate. variants(B, gate) -> {name: kwargs}.
gate: None abroad (price-only); in Saudi the live gates as a dates x stocks table."""
import numpy as np
import swingbook as SBk, swing as SW
from feat79 import feats
L, CAP = -2.5, 40
CORE = {2: (L, 0.0, CAP, 1.0), 3: (L, 0.0, CAP, 2.0)}
nz = lambda a, v: np.nan_to_num(a, nan=v, posinf=v, neginf=v)


def variants(B, gate=None):
    F = feats(B); S = SBk.prep(B); Z, wx = S["Z"], S["wx"]; T, N = Z.shape; VOL = B.VOL; MS = F["MS"]; ones = np.ones((T, N))
    g = (lambda extra=None: gate if extra is None else (extra if gate is None else gate & extra))
    V = {"base": dict(wplan=CORE, gate=g())}
    # 1 a zone that widens with the weather
    for nm, (a, b) in {"1a storm -2.5 / deep -2.0": (-2.5, -2.0), "1b storm -3.0 / deep -2.5": (-3.0, -2.5), "1c storm -3.0 / deep -2.0": (-3.0, -2.0)}.items():
        V[nm] = dict(wplan={2: (a, 0.0, CAP, 1.0), 3: (b, 0.0, CAP, 2.0)}, gate=g())
    # 2 a smarter sale
    V["2b target falls with time (+0.5 to -1.0)"] = dict(wplan=CORE, gate=g(), xrule=dict(kind="decay", t0=.5, t1=-1.0))
    V["2c ride the rebound (sell 0.5 under the peak stretch)"] = dict(wplan={2: (L, 0.0, 60, 1.0), 3: (L, 0.0, 60, 2.0)}, gate=g(), xrule=dict(kind="fade", arm=0.0, drop=.5, top=2.0))
    V["2d deep buys sell at +1"] = dict(wplan={2: (L, 0.0, CAP, 1.0), 3: (L, 1.0, CAP, 2.0)}, gate=g())
    V["2e no sale at 0 while the market is deep"] = dict(wplan=CORE, gate=g(), xrule=dict(kind="mkt"))
    # 3 which candidate first
    V["3a largest stock-specific fall first"] = dict(wplan=CORE, gate=g(), rank=-nz(F["resZ"], 9e9))
    V["3b smallest stock-specific fall first"] = dict(wplan=CORE, gate=g(), rank=nz(F["resZ"], -9e9))
    V["3c fastest fall first"] = dict(wplan=CORE, gate=g(), rank=nz(F["z60"] - F["z10"], -9e9))
    V["3d slowest fall first"] = dict(wplan=CORE, gate=g(), rank=nz(F["z10"] - F["z60"], -9e9))
    V["3e rarest stretch first"] = dict(wplan=CORE, gate=g(), rank=-nz(F["pctl"], 9e9))
    # 4 position size from the numbers (never more than 50% held)
    mv = F["medvol"][:, None]
    V["4a equal risk (less in volatile stocks)"] = dict(wplan=CORE, gate=g(), wm=nz(np.clip(mv / VOL, .5, 2), 1.0), maxexp=.5)
    V["4b more in volatile stocks"] = dict(wplan=CORE, gate=g(), wm=nz(np.clip(VOL / mv, .5, 2), 1.0), maxexp=.5)
    V["4c more in the deeper stock"] = dict(wplan=CORE, gate=g(), wm=nz(np.clip(np.abs(Z) / 2.5, 1, 2), 1.0), maxexp=.5)
    V["4d smooth market-depth size (1x to 3x)"] = dict(wplan={2: (L, 0.0, CAP, 1.0), 3: (L, 0.0, CAP, 1.0)}, gate=g(), wm=np.clip(1 + (-MS - 1.18) * (2 / 2.7), 1, 3)[:, None] * ones, maxexp=.5)
    V["4e half size in the first 5 sessions"] = dict(wplan=CORE, gate=g(), wm=np.where(F["age"] < 5, .5, 1.0)[:, None] * ones, maxexp=.5)
    # 5 pace by the state of the market
    V["5a two buys a day in deep weather"] = dict(wplan=CORE, gate=g(), per_day=np.where(wx == 3, 2, 1))
    V["5b two buys a day when the market is turning"] = dict(wplan=CORE, gate=g(), per_day=np.where(F["turning"], 2, 1))
    nc = SBk.candidates(B, CORE, gate=g()).sum(1); V["5c two buys on a panic day"] = dict(wplan=CORE, gate=g(), per_day=np.where((nc >= 5) & (nc >= .03 * B.EL.sum(1)), 2, 1))
    # 6 a calm-weather layer: the dip in an uptrend
    W6 = {0: (L, -1.0, 20, .5), 1: (L, -1.0, 20, .5), 2: CORE[2], 3: CORE[3]}; sto = np.isin(wx, (2, 3))[:, None]
    for nm, cond in {"6a calm dips: stock and market in an uptrend": F["up_stock"] & F["up_mkt"][:, None], "6b calm dips: market in an uptrend": F["up_mkt"][:, None] & (ones > 0), "6c calm dips: stock in an uptrend": F["up_stock"]}.items():
        V[nm] = dict(wplan=W6, gate=g(sto | cond))
    # 7 universe
    V["7a seasoned stocks only (500 sessions)"] = dict(wplan=CORE, gate=g(F["hist"] >= 500))
    # 10 two speeds of the stretch
    V["10a fast swing (10-session stretch only)"] = dict(wplan={2: (L, 0.0, 20, 1.0), 3: (L, 0.0, 20, 2.0)}, gate=g(), Zx=F["z10"])
    V["10b also sell on a sharp short bounce"] = dict(wplan=CORE, gate=g(), xrule=dict(kind="fast", ZF=F["z10"], a=1.0))
    V["10c plus fast candidates (10-session stretch -3.0)"] = dict(wplan=CORE, gate=g(), extra=SW.cross_in(F["z10"], -3.0))
    # 11 no quick return
    V["11a no re-buy for 20 sessions"] = dict(wplan=CORE, gate=g(), cooldown=20)
    # 12 money follows depth
    V["12a exposure ceiling by market depth"] = dict(wplan=CORE, gate=g(), maxexp=np.where(MS > -1.85, .125, np.where(MS > -2.53, .25, .5)))
    # 13 rotate into the deeper stock
    V["13a rotate out a holding at -1.0 or higher"] = dict(wplan=CORE, gate=g(), rotate=-1.0)
    V["13b rotate out a holding at -0.5 or higher"] = dict(wplan=CORE, gate=g(), rotate=-.5)
    return V
