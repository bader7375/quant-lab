# Proposed scheduled task for the Fable terminal (NOT created; waiting for the user's yes)

It adds one task. The three existing tasks (15:48 data update, 16:41 after-close list, 06:42 morning list) are not changed.

- Name: Fable daily update
- When: `CRON_TZ=Asia/Riyadh 55 16 * * 0-4` (Sunday to Thursday, 16:55 Riyadh, after the 16:41 run has refreshed the work folder)
- Where: the same session as the two list tasks (it reuses their work folder, so nothing is downloaded twice)

Task text:

> Scheduled after the 16:41 Saudi run: update the Fable terminal (the user's second terminal, on paper next to the live one).
> 1. S=/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad. If $S/daily is missing, reply "Fable update skipped: the work folder is missing (the 16:41 run rebuilds it)." and stop.
> 2. Get the Fable code: `rm -rf $S/fable_src && mkdir -p $S/fable_src && git -C /home/user/quant-lab fetch -q origin claude/bold-hamilton-txnvqu && git -C /home/user/quant-lab archive FETCH_HEAD web/reversal-edge/fable web/reversal-edge/research/r72/world72b.json web/reversal-edge/research/r73/r73_results.json web/reversal-edge/research/r73/world73.json | tar -x -C $S/fable_src`
> 3. Run `sh $S/fable_src/web/reversal-edge/fable/run.sh $S` with Bash (about 10 seconds). If it prints FAILED, reply with that line and the last lines of $S/fable_run.log, and stop: do not touch the database.
> 4. Load ArtifactData with ToolSearch ("select:ArtifactData"). At https://claude.ai/artifact/ToMGcTrUag47xRoF1jEZv7: "get" collection "fable" doc_id "latest" to read its version, then "set" it from file_path $S/fable/fable_latest.json with that version as if_version. Then write the day record: read the close date from the "asof" field of that file, "get" collection "days" doc_id <asof>; if it does not exist, "set" it from file_path $S/fable/day_<asof>.json; if it exists, leave it as it is (the record of a day is never rewritten).
> 5. Reply with the brief the run printed, unchanged. Never invent prices or picks. Do nothing else: no commits, no change to the live terminal (HQMRJpu3hpLyj7ahSxSQDn), to daily/settings.json or to any other task.

Once the branch is merged, replace `claude/bold-hamilton-txnvqu` with the branch that holds `web/reversal-edge/fable`.
