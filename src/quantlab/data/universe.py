"""Universe construction.

IMPORTANT — survivorship bias
-----------------------------
The bundled ticker list is *current* S&P 500 membership. Applying it to a
2005-2025 backtest silently excludes every company that was delisted, acquired
or dropped from the index, which inflates results. The bundled list is a
convenience for research iteration, not a clean backtest universe. For results
you would risk money on, pass a point-in-time membership file via
``--universe-file`` (CSV with columns ``date,ticker``); ``load_universe`` will
then return only the names that were index members on each date.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Current-membership S&P 500 snapshot. Tickers that no longer resolve are
# dropped by the loader rather than failing the run.
SP500 = """
A AAPL ABBV ABNB ABT ACGL ACN ADBE ADI ADM ADP ADSK AEE AEP AES AFL AIG AIZ AJG
AKAM ALB ALGN ALL ALLE AMAT AMCR AMD AME AMGN AMP AMT AMZN ANET ANSS AON AOS APA
APD APH APTV ARE ATO AVB AVGO AVY AWK AXON AXP AZO BA BAC BALL BAX BBWI BBY BDX
BEN BF-B BG BIIB BK BKNG BKR BLDR BLK BMY BR BRK-B BRO BSX BX BXP C CAG CAH CARR
CAT CB CBOE CBRE CCI CCL CDNS CDW CE CEG CF CFG CHD CHRW CHTR CI CINF CL CLX CMA
CMCSA CME CMG CMI CMS CNC CNP COF COO COP COR COST CPAY CPB CPRT CPT CRL CRM CRWD
CSCO CSGP CSX CTAS CTRA CTSH CTVA CVS CVX CZR D DAL DAY DD DE DECK DFS DG DGX DHI
DHR DIS DLR DLTR DOC DOV DOW DPZ DRI DTE DUK DVA DVN DXCM EA EBAY ECL ED EFX EG
EIX EL ELV EMN EMR ENPH EOG EPAM EQIX EQR EQT ES ESS ETN ETR EVRG EW EXC EXPD
EXPE EXR F FANG FAST FCX FDS FDX FE FFIV FI FICO FIS FITB FMC FOX FOXA FRT FSLR
FTNT FTV GD GDDY GE GEHC GEN GEV GILD GIS GL GLW GM GNRC GOOG GOOGL GPC GPN GRMN
GS GWW HAL HAS HBAN HCA HD HES HIG HII HLT HOLX HON HPE HPQ HRL HSIC HST HSY HUBB
HUM HWM IBM ICE IDXX IEX IFF INCY INTC INTU INVH IP IPG IQV IR IRM ISRG IT ITW
IVZ J JBHT JBL JCI JKHY JNJ JNPR JPM K KDP KEY KEYS KHC KIM KKR KLAC KMB KMI KMX
KO KR KVUE L LDOS LEN LH LHX LII LIN LKQ LLY LMT LNT LOW LRCX LULU LUV LVS LW LYB
LYV MA MAA MAR MAS MCD MCHP MCK MCO MDLZ MDT MET META MGM MHK MKC MKTX MLM MMC
MMM MNST MO MOH MOS MPC MPWR MRK MRNA MS MSCI MSFT MSI MTB MTCH MTD MU NCLH NDAQ
NDSN NEE NEM NFLX NI NKE NOC NOW NRG NSC NTAP NTRS NUE NVDA NVR NWS NWSA NXPI O
ODFL OKE OMC ON ORCL ORLY OTIS OXY PANW PARA PAYC PAYX PCAR PCG PEG PEP PFE PFG
PG PGR PH PHM PKG PLD PM PNC PNR PNW PODD POOL PPG PPL PRU PSA PSX PTC PWR PYPL
QCOM QRVO RCL REG REGN RF RJF RL RMD ROK ROL ROP ROST RSG RTX RVTY SBAC SBUX SCHW
SHW SJM SLB SMCI SNA SNPS SO SOLV SPG SPGI SRE STE STLD STT STX STZ SWK SWKS SYF
SYK SYY T TAP TDG TDY TECH TEL TER TFC TGT TJX TMO TMUS TPR TRGP TRMB TROW TRV
TSCO TSLA TSN TT TTWO TXN TXT TYL UAL UBER UDR UHS ULTA UNH UNP UPS URI USB V VICI
VLO VLTO VMC VRSK VRSN VRTX VST VTR VTRS VZ WAB WAT WBA WBD WDC WEC WELL WFC WM
WMB WMT WRB WST WTW WY WYNN XEL XOM XYL YUM ZBH ZBRA ZTS
""".split()

# Liquid sector ETFs used as market/sector context features. These are derived
# purely from the same OHLCV feed -- no extra data source.
MARKET_PROXIES = ["SPY", "QQQ", "IWM"]


def default_universe(name: str = "sp500") -> list[str]:
    """Return the ticker list for a named universe."""
    if name == "sp500":
        return sorted(set(SP500))
    if name == "sp100":
        # A liquid mega-cap subset, useful for fast iteration.
        return sorted(set(SP500[:120]))
    raise ValueError(f"unknown universe: {name!r}")


def load_membership(path: str | Path) -> pd.DataFrame:
    """Load a point-in-time membership file with columns ``date,ticker``."""
    df = pd.read_csv(path)
    missing = {"date", "ticker"} - set(df.columns)
    if missing:
        raise ValueError(f"membership file missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "ticker"]].drop_duplicates()


def apply_membership(panel: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """Restrict a (date, ticker) panel to rows that were index members.

    Membership is forward-filled from each observation date, so a monthly or
    quarterly membership file works as well as a daily one.
    """
    members = membership.copy()
    members["is_member"] = True
    dates = panel.index.get_level_values("date").unique().sort_values()

    frames = []
    for ticker, grp in members.groupby("ticker", sort=False):
        s = (
            grp.set_index("date")["is_member"]
            .sort_index()
            .reindex(dates.union(grp["date"]))
            .ffill()
            .reindex(dates)
        )
        frames.append(pd.DataFrame({"date": dates, "ticker": ticker, "is_member": s.values}))

    flags = pd.concat(frames).set_index(["date", "ticker"])["is_member"]
    keep = flags.reindex(panel.index).fillna(False).astype(bool)
    return panel.loc[keep.values]
