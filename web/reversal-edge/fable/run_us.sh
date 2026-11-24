#!/bin/sh
# Fable US view (round 84): refresh the US 200 prices from Yahoo and write the US documents for the terminal. Independent of the Saudi
# pipeline: it changes nothing in the work folder except edge26/data/us200 and fable/us/. About 2 minutes (200 downloads).
# Run it after the New York close (16:00 New York = 00:00 Riyadh in winter); a bar for a session still open is left out.
# Usage: sh run_us.sh <work folder>      -> <work>/fable/us/us_latest.json, us_market.json, us_chart_<n>.json
W=${1:?usage: sh run_us.sh <work folder>}; H=$(cd "$(dirname "$0")" && pwd); export RE_WORK=$(cd "$W" && pwd)
python3 "$H/fetch_us.py" || { echo "FAILED at the US price refresh"; exit 1; }
python3 "$H/export_us.py" || { echo "FAILED at the US export"; exit 1; }
