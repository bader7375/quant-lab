"""Environment diagnostics.

When a run fails on someone else's machine, the useful information is almost
never in the traceback alone -- it is in the library versions and whether the
data provider is reachable at all. ``preflight()`` collects both into one
block that can be pasted straight into a bug report.
"""
from __future__ import annotations

import platform
import sys
import traceback

PACKAGES = ["numpy", "pandas", "scipy", "sklearn", "lightgbm", "yfinance", "pyarrow"]


def versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for name in PACKAGES:
        try:
            out[name] = __import__(name).__version__
        except Exception as exc:  # noqa: BLE001
            out[name] = f"NOT AVAILABLE ({type(exc).__name__})"
    return out


def check_yahoo(ticker: str = "AAPL") -> dict[str, str]:
    """Try one tiny download and report precisely what happened."""
    result: dict[str, str] = {"ticker": ticker}
    try:
        import yfinance as yf

        df = yf.download(
            ticker, period="5d", auto_adjust=False, progress=False, threads=False
        )
        if df is None or df.empty:
            result["status"] = "REACHABLE BUT EMPTY"
            result["meaning"] = (
                "Yahoo answered but sent no rows. This is almost always "
                "rate-limiting of your IP address, not a code bug. Wait 10-15 "
                "minutes, or use provider='synthetic' in the meantime."
            )
        else:
            result["status"] = "OK"
            result["rows"] = str(len(df))
            result["columns"] = str(list(df.columns)[:6])
    except Exception as exc:  # noqa: BLE001
        result["status"] = "FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["meaning"] = (
            "The request itself raised. If this mentions 429, 'Too Many "
            "Requests', or a timeout, it is rate-limiting. If it mentions SSL "
            "or DNS, the network is blocking Yahoo Finance."
        )
    return result


def preflight(exc: BaseException | None = None) -> str:
    """Return a diagnostic report, optionally describing a failure."""
    lines = ["=" * 68, "  QUANT-LAB DIAGNOSTIC REPORT", "=" * 68, "", "Versions:"]
    for k, v in versions().items():
        lines.append(f"  {k:<12} {v}")

    lines += ["", "Yahoo Finance reachability:"]
    for k, v in check_yahoo().items():
        lines.append(f"  {k:<12} {v}")

    if exc is not None:
        lines += ["", "The failure:", f"  {type(exc).__name__}: {exc}", "", "Traceback:"]
        lines += [
            "  " + ln
            for ln in "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).splitlines()[-15:]
        ]

    lines += ["", "=" * 68, "  Copy everything above into the chat.", "=" * 68]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print(preflight())
