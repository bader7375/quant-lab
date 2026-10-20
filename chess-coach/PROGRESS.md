# PROGRESS.md

Handoff notes so any later session can continue without re-deriving context.

## Refactor to a guided journey (started 2026-10-12)

The approved plan is `REFACTOR_PLAN.md`. User decisions: 17-chapter curriculum as proposed; default repertoire (Italian, 1...e5, QGD); the user knows the rules and can win games but has no plan, so the opponent starts near 1100; commentary on every move; the main odds bar shows the human-level estimate, with engine WDL as a secondary line.

| Step | State |
|---|---|
| 1. Journey map + chapter structure + Stockfish 17.1 | **done** |
| 2. Watch mode | **done** |
| 3. Play mode + Review | **done** |
| 4. Probability engine + Maia + masters | **done** |
| 5. Chapter 1 end to end | **done** |

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

### Step 4 (done): odds fitted on human games, Maia, masters
- **Odds** (`data/models/odds.json`, `tools/odds/`, report `tools/odds/ODDS_REPORT.md`):
  - An ordered logit per rating band and game phase, in Stockfish 17.1 centipawns. Lichess evals were mapped with sf17 = 3.7 + 0.61·lichess, R² 0.92, from 1,584 positions re-evaluated at depth 14.
  - Fitted on 30,568 rated rapid and classical Lichess games, using only positions after each game's puzzle blunder (the dataset's selection bias makes earlier positions unusable).
  - Held-out log loss is 0.500 (CI 0.484–0.516), against 0.584 for the provisional curve.
  - **Bands under 1500, including the student's 1100, are extrapolated**: the puzzle generator skips games with a player rated 1500 or below. The odds bar says "مستقرأ".
  - `js/prob.js` takes the phase from the FEN and the student's band from `Prob.band` (= the opponent rating, which follows results). A forced mate counts as ±8 pawns (humans miss mates); only checkmate is certain.
  - Move classes are slightly milder (+0.3 → −0.8 is an inaccuracy, was a mistake). `tools/odds/check_prob.mjs`: PASS (442 checks).
- **Maia-1** (`engines/maia/`, `js/human.js`, report `tools/maia/MAIA_REPORT.md`):
  - The nine networks (1100–1900) run in a Web Worker: 1.7 MB each, about 9 ms per move.
  - The JS port matches the numpy reference to 3e-6, with the same top move on all 377 test positions.
  - Move-matching on held-out games: 53.0% [51.8–54.2], in line with the Maia-1 paper. Castling and queen-promotion encodings are confirmed by controls.
  - Not validated at 1000–1499 (no such players in the data).
- **Opponent = Maia**: a move is sampled from Maia's probabilities (T = 1; T = 1.3 below 1100, as fitted for sub-1000 players; never a move under 1%). Weakened Stockfish takes over only if Maia fails, and each such fallback is counted in the game.
- **Players at your level**:
  - Every move card in Play shows how many players at the student's level play the move and their most common choice. It flags a common choice that Stockfish rates as weak ("a position many at your level get wrong") and a common mistake.
  - Watch shows, for each move, what a ~1100 player would have played in that seat. Review key moments show the same line.
  - The data also goes to Claude's explanation.
- **Masters** (`data/masters/`, `js/masters.js`, `tools/masters_tree/`):
  - KingBase 2017: 1,796,809 master games, 1990–2017. The first 24 plies, positions reached in 75+ games: 39,021 positions in 5 shards of about 1.15 MB each, loaded on first use.
  - Opening names come from lichess chess-openings (CC0): 3,865 positions.
  - Play shows the masters' share and score for each move while the game is in the tree, the opening's name above the board, and when the game leaves known positions. Watch shows the same per move; Review shows the opening and how long the student stayed in theory.
- Tested headless: Play as White with Maia (no fallbacks, no errors), Watch cards with both lines, and the odds check.

### Step 5 (done): Chapter 1 end to end
- **Learn** (`data/curriculum/ch01/learn.json`, `js/learn.js`): six slides on the board (centre, development, "what is attacked?" before castling, castling, the early queen, Scholar's mate), each with a task. The lesson ends with the chapter checklist, which is saved to the chapter page.
  - Every accepted move and every explanation was checked by `tools/verify_lesson.mjs` with Stockfish 17.1 at depth 20: each accepted move is within 60 cp of best, and every concrete claim holds (legal, check, mate). Result: PASS.
  - The verifier corrected four draft claims: 5.O-O there loses e4 to Nxe4; 2...Nf6 against Qh5 is not a mistake; 3...Qf6 and 2.Bb5 were removed from the accepted moves.
  - A move outside the lists is judged live by Stockfish, and the answer is shown after two tries.
- **Watch**: two new narrated coach-vs-Maia-1100 games, generated by `tools/gen_demo.mjs` and chosen because Black breaks opening principles and gets punished:
  - "عقاب الوزير المبكر" (2...Qf6, pawn moves, White develops and wins material);
  - "الملك المكشوف بعد f6" (2...f6, Nxe5 sacrifice, Qh5+ wins the rook).
  - Analysed at depth 20; every bracketed move passes `build_demo.mjs`. Before building, the narration was checked by hand against the lines, which caught two overstatements.
  - The outros say honestly that the coach never castled, because both games were won first.
- **Warm-ups** (`js/warmup.js`): mistake cards from coached games (drop ≥ 10) appear on the journey page when due, up to 5 per session. They are solved with the tap solver (move-type hint ladder, refutation) and scheduled by SM-2.
- **Completion rule**: a game that ends before the student's 10th move cannot be judged on the checklist, so it now neither counts nor takes a slot in the "last 3" window. (The run-through exposed this: a 7-move mating win had been counted as non-qualifying.)
- **Full run-through** (headless, fresh profile), all with no page errors:
  - the lesson was solved and all three demos were watched to the end;
  - three games against Maia, a mate in 7 and two 20-move games each scoring 5/5 on the checklist, and the reviews rendered;
  - all four stages show done;
  - the rule logic was checked separately: an unjudgeable game is skipped, a 3/5 game breaks the run, and three qualifying games complete Chapter 1 and unlock Chapter 2;
  - every view at 390 px with nothing off-screen.
- Not testable headless: Claude's live answers (the stand-in test in Step 3 covers the code paths).
- Next: chapters 2–17, one at a time. Each needs its lesson, demos, play configuration and the rule metric its completion depends on.

### Chapter 2 (done): الأمان أولًا (safety first)
- **Learn** (`data/curriculum/ch02/learn.json`): six slides. Four positions come from real Lichess games between players rated about 1600, found by scanning the puzzle-game dataset for early pieces that were left hanging and then won. The slides cover:
  - taking a bishop left hanging (London, 5...Bf5?? Qxf5);
  - the Ng5 threat against f7 in the Two Knights (4...d5);
  - two threats at once (Qg6 saves the queen and defends Bh3 indirectly);
  - counting attackers and defenders on f6 (Be7; 6...Nd4 is the hope-chess move from the real game);
  - "who takes after me?" before Nxe5 in the Italian;
  - a blunder check, replaying slide 1's position from Black's side before the mistake.
  - `verify_lesson.mjs` now reads each slide's claims from the lesson JSON (Chapter 1's claims were moved there). An accepted move now fails only when it is more than 60 cp from best or clearly losing (below −150), because the blunder-check slide starts at about −0.7. Both lessons PASS at depth 20.
- **Watch**: two new games from `gen_demo.mjs`, which now takes the coach's colour and logs "safety events":
  - "الملك يحمي قطعتين" (coach as White): Nxe5 removes the knight attacking c4; then the king is the only defender of both d8 and f7, so Bxf7+ Kxf7 Qxd8; then Qd5+ forks a knight left hanging. At the end the coach does not take a8, because the h8 rook defends it (`verify` line Qxa8 Rxa8).
  - "الوزير أمام الملك" (coach as Black with 1...e5): White opens the e-file in front of Qe2/Ke1, and Re8 wins the queen.
  - Both games pass `build_demo.mjs`. Every candidate's "why" was compared with its Stockfish score, and three texts were softened.
- **Play** (only in the safety chapter):
  - The opponent's threats are not announced. After every opponent move the coach asks the safety questions instead. "بماذا أفكر الآن؟" reveals the threat with an arrow and counts as a hint.
  - Claude's comment on the opponent's move is told not to name threats or attacked pieces.
  - A tap-only blunder check runs before each move: the move is shown but not played, with three questions and the buttons "play it" / "change it". It can be switched off in the panel, and changed moves are counted.
  - A live safety counter shows the pieces left hanging and the threats missed against the limit of one each, plus the chapter streak.
- **Review**: a safety panel lists every hanging piece and missed threat with the coach's note (taken-back attempts still count) and gives this game's verdict. Hanging pieces and missed threats are always key moments.
- **Rule**:
  - A game is judged after 15 of your moves; a shorter game counts only if it already broke a limit.
  - A game you end early never counts for you, but if it broke a limit it still resets the streak, so abandoning a bad game cannot hide it.
  - 3 judged games in a row are needed.
- **Tests** (headless, no page errors):
  - rule logic on synthetic games;
  - the lesson solved, including a wrong Bf5 showing its explanation;
  - both demos watched to the end;
  - one game with the check step and a "change it", hidden threats (no "يهدد:" in the feed; the hint shows it), and a deliberate hanging move taken back that still counted as 1;
  - three 22-move games by a Stockfish-depth-11 student (0 hanging, 0 missed, 2 and 4 threats handled) that complete Chapter 2 and unlock Chapter 3;
  - learn, play and review at 390 px with nothing off-screen.
- **Hint button (all chapters, 2026-10-20, by request)**: "تلميح: أفضل نقلة" now shows Stockfish's best move with a green arrow, your chances after it, why it is good, the line Stockfish expects and any moves close in strength. The explanation is built in the page from the move and the position (capture, check, the threat it answers, development, castling, centre, "the only good move"), so it makes no Claude call and costs no usage. The questions that help you find the move yourself sit under it, folded. Each hint is still counted.
- Limitation: a piece is counted as "hanging" or a threat as "missed" only when the move costs 10+ points and Stockfish's reply actually wins that material, so a hang the opponent cannot exploit is not counted.

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
