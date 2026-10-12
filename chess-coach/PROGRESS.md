# PROGRESS.md

Handoff notes so any later session can continue without re-deriving context.

## Refactor to a guided journey (started 2026-10-12)

The approved plan is `REFACTOR_PLAN.md`. User decisions: 17-chapter curriculum as proposed; default repertoire (Italian, 1...e5, QGD); the user knows the rules and can win games but has no plan, so the opponent starts near 1100; commentary on every move; the main odds bar shows the human-level estimate, with engine WDL as a secondary line.

| Step | State |
|---|---|
| 1. Journey map + chapter structure + Stockfish 17.1 | **done** |
| 2. Watch mode | **done** |
| 3. Play mode + Review | **done** |
| 4. Probability engine + Maia + masters | next |
| 5. Chapter 1 end to end | |

### Step 1 (done)
- `data/curriculum/chapters.json`: 4 parts, 17 chapters (goal, topics, Watch/Play descriptions, completion rule). A chapter's `content` field lists ready material; stages without content show "قيد الإعداد".
- `js/journey.js`: map (winding path, nodes done/current/locked, A-B-C-D pips), chapter page (topics, prerequisite, completion rule with data-driven progress, stage cards), journey progress view with settings. State in db doc `journey/state`; coached games in collection `games`.
- `js/app.js`: new shell. Top nav: الرحلة / التقدم / التمرين. Hash routes `#journey`, `#ch-N`, `#progress`, `#practice`.
- Practice: the old modes moved to `js/practice/modes.js` and `js/practice/practice.js` (sub-nav, ids `#pv-*`). Practice cards are the `cards` docs without `kind` (journey warm-ups will use `kind: "warm"`).
- Engine: Stockfish 17.1. `engines/sf17-lite.{js,wasm}` (single-threaded WASM) is tried first; if the worker fails or stays silent for 20 s, `engines/sf17-asm.js` (pure asm.js) takes over. `UCI_ShowWDL` is on; `Engine.analyse` returns `wdl` and per-line `wdlWhite` (per mille, White's view). Foreground requests interrupt background (`low: true`) jobs. Headless Chromium: WASM depth 21 in 2 s; asm.js depth 13 in 2 s.
- Old Stockfish 10 moved to `tools/legacy/stockfish10.js` for the old data tools only.

### Step 2 (done): Watch mode
- Content pipeline (offline, Node): `tools/sfpool.mjs` (4 Stockfish 17.1 WASM processes, ~845k nodes/s each) → `tools/analyse_game.mjs` (per ply: multipv-3 lines with WDL, the opponent's threat by null-move search, the played move's own score, facts before/after) → narration written by Claude in a build session (`tools/demos/*.narr.json`) → `tools/build_demo.mjs` merges and **rejects** the game unless every bracketed move group `[SAN ...]` is a prefix of an engine line, a threat line, the actual game continuation (this ply to +6), or an extra line it evaluates itself (`verify`); it also rejects engine numbers in the text and over-long fields.
- First narrated game: the Opera Game (Morphy 1858) for Chapter 1, `data/curriculum/ch01/demo-opera.json`, depth 20. Narration: what the move does, Morphy's thinking, rejected candidates with their odds, the plan (with plan-change markers), a thinking habit, and the opponent's intent and a verdict for each Black move.
- `js/facts.js`: engine-free facts (SEE hanging pieces, development, king shelter, centre, pawn structure, checks, Chapter-1 opening checklist). Shared by browser and Node.
- `js/prob.js`: odds bar + expected score + move classes (excellent ≤2, good ≤5, inaccuracy ≤10, mistake ≤20, blunder >20 points of expected score; softened when the result is already decided). The human-level model is **provisional** (Lichess curve + small draw rate) until Step 4 fits it.
- `js/chat.js`: Claude chat with a per-position fact sheet; page tools `engine_lines`, `play_line`, `position_facts` when the viewer supports tools; post-check underlines any move in the answer that is not legal here and not in the verified data.
- `js/watch.js`: player (play/pause, step, speed, keyboard), move list, narrated cards, tappable move chips that show the line on the board, "what if" (tap an alternative; Stockfish continues; odds comparison; Claude explanation grounded in both lines), chat with pause-on-focus. Reaching the last move marks the Watch stage done.
- Tested headless: card rendering, chips, branch and return, what-if (8.Qxb7 instead of 8.Nc3 → Stockfish shows Qb4+ trading queens), chat fallback without Claude, stage completion, phone width, dark mode. Claude answers could not be exercised headless.

### Step 3 (done): Play with the coach, and Review
- `js/play.js`, stage C. A full game from the start against `OPP`: for now Stockfish weakened with Skill Level and a shallow search, mapped to a rating **by guess** (labelled "تقريبًا"); Step 4 replaces it with Maia. It starts at 1100 and moves +100 after a win and -100 after a loss (800 to 2000).
- Before your move: "بماذا أفكر الآن؟" lists the phase, the opponent's current threat, how many of your pieces can be won (not which), whether a winning capture exists, the number of checks, undeveloped pieces, and the king. It never names a move; Claude's addition has every SAN token stripped before it is shown.
- After your move: a background multipv-3 search (started when your turn began) plus a search after the move. The class comes from the drop in expected score. When the played move is among the 3 lines, its own score from that search is used, which compares like with like. Each card shows:
  - the class, with your chances before and after;
  - grounded notes: the piece you left en prise and the capture that takes it (only when Stockfish's reply really captures there), an ignored threat, a piece you could have won, an opponent's mistake you did not use;
  - what the move does: captures, checks, a new attack on a piece that is not defended enough, a piece taken out of danger;
  - chapter-1 opening notes, with exceptions marked when the engine agrees with a principle-breaking move;
  - the better move with its line on the board, and one habit.
  Claude (quick tier) explains next to the card, grounded in both Stockfish lines; moves it names are post-checked.
- Mistakes and blunders (drop > 10) stop the game: "تراجع وجرّب مرة أخرى" or "استمر". Inaccuracies are commented on without stopping. **A takeback does not erase the mistake**: metrics count every attempt.
- After the opponent's move:
  - what it captured or whether it gives check, plus chapter-1 notes (queen out early, a piece moved twice);
  - "the opponent erred, look for it" when their move gave you 10+ points, without saying where;
  - the threat from a null-move search (8+ points), shown in the card and as a red arrow;
  - Claude on top.
- Live opening checklist under the board (chapter 1). It uses the same function as the completion metric (`Facts.openingChecklist(..., {partial: true})`), so the live marks and the final judgement cannot disagree.
- Offers: when your chances have been at least 99% for 3 moves, "record the win or play on to mate"; when they have been at most 1% for 3 moves, "resign or play on".
- Saving and resuming:
  - The game is saved after every move (db `games/<id>`). Leaving keeps it open and "أكمل المباراة" resumes it.
  - Starting a new game marks an open one as unfinished.
  - "أنهِ وراجع" ends a game as unfinished. It counts for the chapter only with 20 or more of your moves.
- Metrics per game (`G.metrics`):
  - moves, attempts, takebacks, hints, threats;
  - class counts and okShare (over every attempt);
  - openingScore and openingItems, and openingBlunder (a blunder in your first 10 moves, taken back or not);
  - hanging, missedThreats, gifts and punished.
  `ruleProgress` reads them, and the chapter completes itself when its rule is met.
- `js/review.js`, stage D:
  - KPIs and a chances curve, with moments numbered and taken-back moves drawn hollow.
  - The opening checklist, saying whether the game qualifies and why.
  - Key moments (up to 5):
    - the biggest drops;
    - a missed chance;
    - "only good move" finds (recaptures excluded, they are not found but forced);
    - with fewer than 3, small slips labelled as such.
    Each moment has a mini board with "what you played" and "the better line", step controls, the notes, and "اشرح لي" (Claude).
  - What went well and what to work on, from the metrics only.
  - One lesson, chosen by rule: blunder check first, then the most important missed opening item, then missed chances.
  - Claude's written summary (JSON) with move post-check, cached on the game.
- Every mistake (a drop of 10 or more, taken back or not) becomes a warm-up card `cards/warm-*` (`kind: "warm"`), due from the next day. The warm-up runner itself is Step 5.
- Other changes:
  - The odds bar now follows the setting: the human estimate, or the engine with perfect play, with the other view as a secondary line.
  - `Board.update` keeps a half-made move when only arrows change.
  - `.panel` and `.chat` grids have a `minmax(0, 1fr)` column. **This fixed a Step 2 bug**: on phones, the chat's send button and the coach's bubbles stuck out past the left edge. The earlier check did not see it, because overflow to the left in RTL does not create horizontal scroll. The layout test now checks every element's box.
- Tested headless (`/tmp/claude-0/test/step3.mjs`, `layout.mjs`, `black.mjs`, `mockclaude.mjs`):
  - a 22-move game as White, where the test player uses its own Stockfish, with a deliberate blunder, the line viewer during the takeback choice, and the takeback;
  - the review, saving and resume;
  - playing as Black (board flipped);
  - the engine-failure message;
  - every Claude path, with a stand-in sampler (prompts grounded, unverified moves flagged, the hint stripped of moves);
  - every view at 390 px with no element outside the screen.
  Real Claude answers could not be exercised headless.

## Earlier state (exam-style version, kept as Practice)

All training modes are built. The user asked for two changes, both done:
1. **No typing anywhere.** Every answer is a tap on the board or on a choice.
2. **No analysis of their own games for now** ("we will come to this when I learn"). The game-diagnosis engine from the first commit (`33e8e7f`, old `index.html`: PGN import, per-ply Stockfish, cause classification, weakness profile) is out of the UI. Mode 6 is marked "later". Bring both back when the user asks.

Published Artifact: https://claude.ai/artifact/TadVmUrWnp6NqKukFfP6Fb

## Files

| Path | What |
|---|---|
| `index.html` | markup, design tokens, CSS, piece SVGs (cburnett, data URIs); loads the scripts below |
| `js/core.js` | helpers, `Store` (Artifact db / localStorage), `Engine` (Stockfish worker queue), Claude wrapper (`sample`), data loading, `Board`, `judgeMove`, SM-2, Elo, `Solver` (tap-only puzzle solver with the Socratic ladder) |
| `js/modes.js` | curated `LIB`, `CHUNKS` catalogue (34 patterns), modes: `ThinkMode`, `CalcMode`, `VizMode`/`Blindfold`, `GuessMode`, `PlayoutMode`, `StructQuestion`, `PatternTestItem` |
| `js/app.js` | state `S`, `record()` (attempts, ratings, cards), task runner, daily session builder, hubs, pattern catalogue, dashboard, plan page, boot |
| `data/puzzles.json` | 2,303 Lichess puzzles (CC0) rated 450-1650, 40 per theme where available. Fields: `i` id, `f` FEN (solver to move), `l`/`ls` opponent's last move, `s` solution UCI, `r` rating, `t` themes |
| `data/playout.json` | 45 winning positions: 5 basic mates/endings + 40 puzzle end positions Stockfish rates +3.5 to +25 for the solver |
| `data/structures.json` | 53 positions from real games: IQP (white/black), Carlsbad, and "none" controls, all with abs(eval) < 2.5 |
| `data/opposition.json` | 13 K+P vs K positions where exactly one king move keeps the result (generated and verified by Stockfish) |
| `data/masters.json` | 7 master games, replayed with chess.js (any illegal move aborts the build) |
| `tools/build_data.mjs` | rebuilds the data files from the flattened Lichess puzzle dump |
| `tools/masters.mjs` | builds `masters.json` |
| `tools/verify.mjs` | Stockfish multipv check for any JSON list of `{id, fen, expect}` |

Data source for puzzles: `github.com/mcognetta/lichess-combined-puzzle-game-db` (first 50k Lichess puzzles + games). lichess.org itself is blocked in this container.

## Modes (all tap-only)

| # | Mode | How it works |
|---|---|---|
| 1 | Thought process | 5 steps: opponent's threat (choice; truth from a null-move search), candidates (tap 2-4 on a static board), choose, blunder check (tap the opponent's best reply on the post-move board, may change move), evaluation (5 choices) + confidence. Scored 0-2 per step, then Claude critiques the process |
| 2 | Calculation | Enter up to 3 lines by tapping on a board that does not move (no legal-move dots). Pick main line, evaluate its end, confidence. Engine walks the main line ply by ply: where it broke (own move loses ≥8 points, or assumed reply ≥10 points worse than best), depth, missed candidates. Peeks are counted |
| 3 | Visualization | 10 levels: square colour, find square (white/black side), knight distance, mental lines of 2/4/6/8 plies from master games, blindfold KQK mate, blindfold 10 moves vs weak engine. ≥80% moves up, <50% moves down |
| 4 | Guess the move | Tap prediction + reason chip. 2 pts for the master's move, 1 if Stockfish rates it within 4 points. Claude explains misses |
| 5 | Play-out | vs Stockfish at chosen Skill Level. Success = mate. Fails if eval drops below +1.5, draw, or move limit. Claude reviews the 3 biggest drops |
| 6 | Self-analysis | **later**, by the user's request |
| 7 | Calibration | Confidence 1-5 before every result. Curve and over/under-confidence gap on the dashboard |
| 8 | Patterns | Learn a chunk with 5 labelled positions, then mixed unlabelled tests (identify the pattern, then solve). Structures: identify + choose the plan |
| 9 | Daily session | ~45 min: viz → review → think (weakest skill) → patterns → review → calc → think (2nd weakest) → 4 timed → review → guess 4 moves → play-out → review |
| 10 | Socratic | Fail 1: find the refutation yourself on the board. Fail 2: move-type hint + Claude question + "show solution" button. Fail 3: solution with a stepper |
| 11 | SRS | Any failure (q<4) becomes a card due in 10 minutes, then SM-2 |
| 12 | Timed | 30/45/60 s by rating, no ladder, separate Elo; dashboard compares timed vs untimed accuracy |

## Data model (Artifact db, owner-only rules)

- `coach/profile`: `ratings{tactics,timed}{r,n}`, `rhist[]`, `viz.level`, `chunks{k:{learned,tests,rec,sol}}`, `guess{gameId:{ply,pts,max}}`, `sessions[]`
- `attempts/<id>`: one per task. Common: `mode, itemId, skill, correct, solvedAt, confidence, seconds, review, session`. Mode-specific: `scores` (think), `depth/length/missed/peeks` (calc), `level/acc` (viz), `pts/max` (guess), `result/strength` (playout), `recognized/chunk/learning` (pattern)
- `cards/<id>`: `type` (solve/calc/playout/struct), `item`, SM-2 fields

## Testing
Headless Chromium runs (scripts were in the scratchpad, not committed) drove every mode end to end: think (incl. ladder), calc, viz, guess, play-out, timed, learning two chunks, mixed test, a failure creating a card, the card's review being rescheduled to 24 h, and state surviving reload. No page errors. Claude calls could not be exercised headless (no viewer); they degrade to Stockfish-only text when `sample` is unavailable.

Bugs found and fixed during testing: an engine-queue deadlock, inverted square colours in viz level 1, and a mixed test that returned one item per chunk.

## Next steps
1. Read the user's data (`ArtifactData` list on `attempts`, `cards`; get `coach/profile`) and tune session weights.
2. When the user asks: re-enable game import + diagnosis (from `33e8e7f`) and build mode 6 tap-only (tap the moves you think were mistakes, then compare).
3. More master games for guess-the-move, chosen per concept; more strategic positions (STS-style) for mode 1.
4. Republish: `index.html` with `files` for `chess.js`, `stockfish.js`, `js/*.js`, `data/*.json`, to the same URL.
