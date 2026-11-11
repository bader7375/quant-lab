#!/bin/sh
# Fable daily step. Run it AFTER the live pipeline (research/daily/run.sh) has refreshed the work folder: it reads that folder and
# changes nothing in it except its own subfolder fable/. About 10 seconds.
# Usage: sh run.sh <work folder>      -> <work>/fable/fable_latest.json, day_<close>.json, brief_<close>.md (printed)
W=${1:?usage: sh run.sh <work folder>}; H=$(cd "$(dirname "$0")" && pwd); export RE_WORK=$(cd "$W" && pwd)
python3 "$H/export.py" > "$RE_WORK/fable_run.log" 2>&1 || { echo "FAILED at fable export"; tail -5 "$RE_WORK/fable_run.log"; exit 1; }
python3 "$H/brief.py" || { echo "FAILED at fable brief"; exit 1; }
