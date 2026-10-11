# PROGRESS.md

Handoff notes so any later session can continue without re-deriving context.

## What exists

A single-page coaching app (`index.html`) published as a claude.ai Artifact. Everything runs in the browser:

| Piece | Where | Notes |
|---|---|---|
| Board + move logic | `chess.js` (chess.js 0.10.3, published next to the page) | own click-to-pick board; pieces are cburnett SVGs embedded as data URIs |
| Engine | `stockfish.js` (Stockfish.js 10, asm.js build, runs in a Web Worker) | ~380k nodes/s in Node; no WASM needed |
| Storage | Artifact `db` capability, owner-only rules | falls back to browser storage when `db` is unavailable |
| Coach | Artifact `sample` capability (Claude on the viewer's account) | every prompt carries Stockfish lines and forbids inventing variations |

### Why not Python/FastAPI/SQLite as the brief described
The user asked for an Artifact connected to Claude. So the stack maps like this:
- SQLite → the Artifact `db`. Same data model, and Claude Code sessions can read and write it with the `ArtifactData` tool.
- Local Stockfish → Stockfish.js in a worker. Weaker than native SF 16+, but fine for beginner-level diagnosis. Upgrading to a WASM NNUE build is a later step.
- Claude API → `sample` capability. No API key; it uses the viewer's Claude account and asks for consent on first use.
- Lichess/Chess.com APIs → **not reachable** from the Artifact (CSP blocks fetch) or from this cloud container (egress policy returned 403 for lichess.org and api.chess.com). The user downloads PGN from links the page builds from their username, then uploads or pastes it.

## Data model (Artifact db)

- `coach/profile`: `{username, platform, created, stats: <buildProfile output>, report, reportAt}`
- `games/<id>`: one analysed game. `evals[]` (white-POV cp per ply), `mistakes[]` (`ply, fen, played, best, bestLine, refutation, drop, sev, causes[], phase, clock, lastMove`), `accuracy`, `acpl`, `maxWp`, `outcome`, `rating`
- `cards/<id>`: SRS card. `g-<gameId>-<ply>` for game mistakes, `lib-<positionId>` for failed library positions. SM-2 fields `ef, reps, interval, lapses, due, history`
- `attempts/<id>`: one think-aloud attempt. `reasoning` (the 6 written fields), `confidence`, `firstCorrect`, `solvedAt`, `tries[]` (with Socratic Q&A), `scores` (5 process steps, 0-2), `process` (0-100), `critique`, `skill`

## Diagnosis engine: how causes are assigned
Win probability uses the Lichess formula `50 + 50*(2/(1+e^(-0.00368208*cp))-1)`. A drop of 10 or more points is a mistake, 15 or more a blunder. For each such move, causes are tested in this order (several can apply):
1. `time`: clock < 30 s or < 10% of the base time
2. `missed_opportunity`: the opponent's previous move dropped ≥15 and the engine's best move here was forcing
3. `missed_threat`: a null-move search shows the opponent already had a threat worth ≥15, and the engine's reply to the user's move is that threat (same move or same target square)
4. `blunder_check`: otherwise, if the opponent's best reply is forcing (the user's own move created the tactic; "hope chess")
5. `visualization`: the error came in the middle of a forcing sequence (the two previous plies were both forcing)
6. `calculation`: otherwise, if the user's move itself was a capture or check
7. `conversion`: added when the user was at ≥75% before the move
8. `opening` (ply < 20) or `plan`: when nothing tactical applies

These are heuristics and the UI says so. Mode 6 (self-analysis) should later let the user re-label causes, and the profile should then prefer user labels where they match the engine.

## Status by module

| # | Module | Status |
|---|---|---|
| D | Diagnosis engine (PGN import, Stockfish per ply, cause classification, weakness profile, Claude report) | **built** |
| 1 | Think-aloud with process critique | **built** |
| 7 | Confidence calibration (curve on the Progress page) | **built** |
| 10 | Socratic coaching (one question per failed try, solution only after 2 failures or 3 tries) | **built** |
| 11 | SRS of own mistakes (SM-2; failed items also come back at the end of the same session) | **built** |
| 9 | Interleaving | partial: sessions mix skills and never show the theme. The full ~45 min daily session waits for the other modes |
| 2 | Calculation (tree vs engine tree) | next |
| 3 | Visualization and blindfold | next |
| 4 | Guess-the-move with master games | next (master games must be embedded as PGN; the explorer API is unreachable) |
| 5 | Play-out sparring vs Stockfish (Skill Level) | next |
| 6 | Self-analysis before the engine | next |
| 8 | Pattern chunking (5+ positions per chunk, then mixed tests) | next |
| 12 | Time pressure | next |

The library holds 14 positions in `LIB` inside `index.html`, each checked with `tools/verify.mjs` at depth 20-22. Two drafts were rejected on verification: one had no black king, and one left a rook hanging.

## Working rules carried forward
- Never show a solution before the user has written reasoning and a move.
- Every chess claim shown to the user must come from Stockfish output (see `LANG_RULES` in the page and `tools/verify.mjs`).
- Explanations in Arabic; notation, opening names and code in English.
- Show data, not encouragement.
- Commit after each working module.

## How to continue
1. Ask the user how the first diagnosis went. Read their data with `ArtifactData` (`list` on `games`, `cards`, `attempts`; `get` on `coach/profile`).
2. Build the next module in order: **2 Calculation**, then 6, 5, 3, 4, 8, 12, then the 45-minute daily session.
3. To add or verify positions: put them in a JSON file and run `node tools/verify.mjs file.json 20`.
4. Republish: Artifact publish of `index.html` with `files: {"chess.js": "chess.js", "stockfish.js": "stockfish.js"}` to the same URL.

## Log
- 2026-10-11: RESEARCH.md written. Diagnosis engine, think-aloud, Socratic loop, SM-2 review, calibration and dashboard built and tested in headless Chromium. Published as an Artifact.
