# Proposed scheduled task for the Fable terminal (NOT created: the user said no on 2026-11-13)
Kept for reference. The terminal is filled by hand from a research session until the user asks for the task.

It adds one task. The three existing tasks (15:48 data update, 16:41 after-close list, 06:42 morning list) are not changed.

- Name: Fable daily update
- When: `CRON_TZ=Asia/Riyadh 55 16 * * 0-4` (Sunday to Thursday, 16:55 Riyadh, after the 16:41 run has refreshed the work folder)
- Where: the same session as the two list tasks (it reuses their work folder, so nothing is downloaded twice)
- Cost: about 10 seconds of computing and seven database calls a day. It uses the same 5-hour usage allowance as the live tasks.
  On 2026-11-11 the live 16:41 run stopped at that allowance while a long research session was running; a heavy day can do that again.

Task text:

> Scheduled after the 16:41 Saudi run: update the Fable terminal (the user's second terminal, on paper next to the live one).
> 1. S=/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad. If $S/daily is missing, reply "Fable update skipped: the work folder is missing (the 16:41 run rebuilds it)." and stop.
> 2. Get the Fable code: `rm -rf $S/fable_src && mkdir -p $S/fable_src && git -C /home/user/quant-lab fetch -q origin claude/bold-hamilton-txnvqu && git -C /home/user/quant-lab archive FETCH_HEAD web/reversal-edge/fable web/reversal-edge/research/r72/world72b.json web/reversal-edge/research/r73/r73_results.json web/reversal-edge/research/r73/world73.json web/reversal-edge/research/r76/map76.json web/reversal-edge/research/r78/r78_confirm.json web/reversal-edge/research/r78/world78.json web/reversal-edge/research/r79/world79.json web/reversal-edge/research/r79/saudi79.json web/reversal-edge/research/r80/saudi80_design.json web/reversal-edge/research/r80/saudi80_confirm.json web/reversal-edge/research/r80/fit80.json | tar -x -C $S/fable_src`
> 3. Run `sh $S/fable_src/web/reversal-edge/fable/run.sh $S` with Bash (about 10 seconds). If it prints FAILED, reply with that line and the last lines of $S/fable_run.log, and stop: do not touch the database.
> 4. Load ArtifactData with ToolSearch ("select:ArtifactData"). Everything below is at https://claude.ai/artifact/ToMGcTrUag47xRoF1jEZv7. Use file_path for every document; never type a document's content.
>    a. Chart documents first. "list" collection "chart" with out_dir $S/fable_db to learn each document's version. Then "batch" sets, at most 4 chart documents in one batch: doc_id "market" from $S/fable/market.json and doc_id "c<n>" from $S/fable/chart_<n>.json for every chart_<n>.json that exists, each with its listed version as if_version (no if_version for a document that is not listed). If a listed "c<n>" has no file any more, delete it.
>    b. Then the export: "get" collection "fable" doc_id "latest" with out_dir $S/fable_db to read its version, then "set" it from file_path $S/fable/fable_latest.json with that version as if_version.
>    c. Then the day record: read the close date from the "asof" field of $S/fable/fable_latest.json; "get" collection "days" doc_id <asof>; if it does not exist, "set" it from file_path $S/fable/day_<asof>.json; if it exists, leave it as it is (the record of a day is never rewritten).
>    If a write fails, say which one and stop; the terminal then shows the older picture with its date.
> 5. Reply with the brief the run printed, unchanged. Never invent prices or picks. Do nothing else: no commits, no change to the live terminal (HQMRJpu3hpLyj7ahSxSQDn), to daily/settings.json or to any other task.

Once the branch is merged, replace `claude/bold-hamilton-txnvqu` with the branch that holds `web/reversal-edge/fable`.
