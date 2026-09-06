"""Cross-sectional and market-regime features.

These are computed from the same OHLCV panel -- no extra data source. They
matter because a stock's own history says little about tomorrow, while its
position *relative to the cross-section* and the market's current regime say
considerably more.

All aggregates are equal-weighted over the names available on each date, so a
name that has not yet entered the sample cannot contribute to a past date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12

#: Features that get an additional cross-sectional rank/z transform.
RANKED = [
    "ret_1d",
    "ret_5d",
    "ret_21d",
    "mom_21_1",
    "mom_63_5",
    "mom_252_21",
    "rev_1d",
    "rev_5d",
    "vol_21",
    "vol_ratio_short_long",
    "dollar_vol_log",
    "volume_ratio_21",
    "rsi_14",
    "dist_sma_50",
    "pct_of_52w_range",
    "amihud_21",
]


def cs_rank(x: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile rank in [0, 1], computed per date."""
    return x.rank(axis=1, pct=True)


def cs_zscore(x: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score, per date, winsorised at +/-5 sigma."""
    mu = x.mean(axis=1)
    sd = x.std(axis=1)
    return ((x.sub(mu, axis=0)).div(sd + EPS, axis=0)).clip(-5, 5)


def build_cross_sectional(feats: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for name in RANKED:
        if name not in feats:
            continue
        out[f"cs_rank_{name}"] = cs_rank(feats[name])
        out[f"cs_z_{name}"] = cs_zscore(feats[name])
    return out


def build_market(close: pd.DataFrame, feats: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Date-indexed market/regime features derived from the panel itself."""
    ret1 = np.log(close).diff()
    mkt = ret1.mean(axis=1)  # equal-weighted market return

    out = pd.DataFrame(index=close.index)
    out["mkt_ret_1d"] = mkt
    out["mkt_ret_5d"] = mkt.rolling(5, min_periods=3).sum()
    out["mkt_ret_21d"] = mkt.rolling(21, min_periods=10).sum()

    mkt_vol = mkt.ewm(halflife=21, min_periods=21).std()
    out["mkt_vol_21"] = mkt_vol
    out["mkt_vol_ratio"] = mkt.ewm(halflife=5, min_periods=5).std() / (mkt_vol + EPS)
    out["mkt_vol_z"] = (mkt_vol - mkt_vol.rolling(252, min_periods=126).mean()) / (
        mkt_vol.rolling(252, min_periods=126).std() + EPS
    )

    # Breadth and dispersion: how uniform is the cross-section today?
    out["breadth_up"] = (ret1 > 0).sum(axis=1) / ret1.notna().sum(axis=1).clip(lower=1)
    out["breadth_up_5d"] = out["breadth_up"].rolling(5, min_periods=3).mean()
    out["cs_dispersion"] = ret1.std(axis=1)
    out["cs_dispersion_z"] = (
        out["cs_dispersion"] - out["cs_dispersion"].rolling(252, min_periods=126).mean()
    ) / (out["cs_dispersion"].rolling(252, min_periods=126).std() + EPS)

    # Average pairwise correlation proxy: variance of the mean vs mean of the
    # variances. High values mean the market is trading as one asset.
    var_of_mean = mkt.rolling(21, min_periods=10).var()
    mean_of_var = ret1.rolling(21, min_periods=10).var().mean(axis=1)
    out["avg_corr_proxy"] = (var_of_mean / (mean_of_var + EPS)).clip(0, 1)

    # Market trend / stress regime.
    mkt_px = mkt.cumsum()
    out["mkt_dist_sma_200"] = mkt_px - mkt_px.rolling(200, min_periods=100).mean()
    out["mkt_drawdown"] = mkt_px - mkt_px.cummax()
    out["mkt_streak"] = np.sign(mkt).groupby((np.sign(mkt) != np.sign(mkt).shift()).cumsum()).cumsum()

    return out


def build_beta(close: pd.DataFrame, window: int = 63) -> dict[str, pd.DataFrame]:
    """Rolling market beta and the idiosyncratic residual return."""
    ret1 = np.log(close).diff()
    mkt = ret1.mean(axis=1)

    cov = ret1.rolling(window, min_periods=window // 2).cov(mkt)
    var = mkt.rolling(window, min_periods=window // 2).var()
    beta = cov.div(var + EPS, axis=0).clip(-4, 4)

    idio = ret1.sub(beta.mul(mkt, axis=0))
    idio_vol = idio.ewm(halflife=21, min_periods=21).std()

    return {
        "beta_63": beta,
        "idio_ret_1d": idio / (idio_vol + EPS),
        "idio_ret_5d": idio.rolling(5, min_periods=3).sum() / (idio_vol * np.sqrt(5) + EPS),
        "idio_mom_21_1": idio.shift(1).rolling(20, min_periods=10).sum()
        / (idio_vol * np.sqrt(20) + EPS),
        "idio_vol_share": idio_vol / (ret1.ewm(halflife=21, min_periods=21).std() + EPS),
    }
