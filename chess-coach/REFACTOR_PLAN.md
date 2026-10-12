# REFACTOR_PLAN.md: from exam to guided journey

Status: **proposal, waiting for your approval.** Nothing in the app has changed yet.

## 0. The change in one paragraph

Today the app is a set of exams: a position appears and you find the best move. The new app is a **journey with a teacher**. A map of 17 chapters runs from your first opening moves to master-level study. Every chapter has the same four stages: **Learn** (a short Arabic lesson on an interactive board), **Watch** (I play a full game and explain every move while you can pause, ask, and try "what if"), **Play** (you play a full game and I comment beside you on every move), and **Review** (the 3-5 moments that mattered and one lesson to keep). A chapter is complete when the data from your coached games shows you apply its idea, not when you pass a quiz. Stockfish, the database and spaced repetition stay, but move into the background. The puzzle modes move to an optional Practice tab.

At the end of this file (section 12) there are five decisions I need from you before I start building.

---

## 1. What I read

| Item | State today |
|---|---|
| `index.html` + `js/core.js` (395 lines) | Board (tap to move, hidden/blind, marks), `Store` (Artifact db, owner-only, localStorage fallback), `Engine` (Stockfish 10 asm.js worker, serialized queue), Claude wrapper (`sample`), SM-2, Elo, `Solver` with the 3-rung Socratic ladder |
| `js/modes.js` (632 lines) | 9 exam-style modes: thought-process, calculation, visualization/blindfold, guess-the-move, play-out, patterns (34 chunks), structures, timed |
| `js/app.js` (357 lines) | results bookkeeping, 45-minute mixed session, hubs, dashboard (rating, calibration, accuracy by skill/mode, calc depth, timed gap) |
| `data/` | 2,303 Lichess puzzles in 31 themes, 45 play-out positions, 53 structure positions, 13 opposition studies, 7 master games |
| `tools/` | data build from the Lichess puzzle dump, master-game validator, Stockfish verifier |
| Commit `33e8e7f` | PGN import, per-ply Stockfish analysis, error classification by cause, weakness profile, Claude report. Built, then removed from the UI at your request |
| `RESEARCH.md` | learning-science and chess-pedagogy basis (Arabic) |
| `PROGRESS.md` | handoff notes |

What makes it feel like an exam: every screen opens with a position and a demand. Feedback arrives only after you answer. The headline number is a puzzle rating. Nobody ever shows you a whole game, thinks aloud, or sits next to you while you play.

---

## 2. Keep, change, demote

### Keep (moved into a "services" layer)

| Keep | Role in the new app |
|---|---|
| `Board` | Upgraded: arrows, square highlights, move animation, last-move marks, branch indicator. Used by every stage |
| `Store` (Artifact db, owner-only rules) | Holds journey state, coached games, reviews, chat summaries, cards. Claude Code sessions can still read it with `ArtifactData` |
| `Engine` queue | Same serialized worker design, but upgraded to **Stockfish 17.1** with WDL output (section 6.1) |
| Claude wrapper (`sample`) | Extended to multi-turn chat with **page tools**, so Claude can call the engine before it answers (section 7) |
| SM-2 + cards | Mistakes from coached games become short warm-ups at the start of a session (≤ 5 minutes) |
| PGN import + diagnosis (`33e8e7f`) | Restored as a background service. Recurring mistakes pick which demo games and coaching focus you get, and can suggest revisiting a chapter. Still optional, and still waits until you want it |
| Data tools (`tools/*.mjs`) + Stockfish verifier | Become the content pipeline that verifies every lesson position and every narrated game |
| Socratic ladder | Reused inside Play mode: after a mistake, "take back and try again" first asks you to see the opponent's reply |

### Change

| Today | New |
|---|---|
| Home = "today's mixed session" | Home = **Journey Map** |
| Win% from a centipawn formula (Lichess, fitted on strong players) | Engine WDL from Stockfish 17.1 **plus** a "your chances at your level" estimate calibrated on rated human games (section 6.2) |
| Move judged by "loss ≤ 5 points" | Five classes by expected-score drop: excellent / good / inaccuracy / mistake / blunder (section 6.3) |
| Explanations built from Stockfish lines only | One **fact sheet** per position: engine lines, WDL, human-level odds, Maia's "what players at your level play", computed facts (threats, hanging pieces, development, king shelter, pawn structure), masters statistics. Claude explains only from it |
| Opponent = Stockfish with Skill Level | Opponent = **Maia** (a network trained to play like humans at a given rating), so it makes human mistakes |
| Progress = puzzle rating and quiz accuracy | Progress = chapter completion from coached-game data, plus move-quality trends |

### Demote to an optional "Practice" tab

All nine exam modes (thought-process, calculation, visualization, guess-the-move, play-out, patterns, structures, timed, review) stay working and unchanged in a **Practice** tab. They are no longer in the main flow. The confidence prompt also moves there: the main journey never asks you to rate your confidence.

### Remove

- The 45-minute mixed session as the home screen.
- The puzzle rating as the headline number.

---

## 3. App structure

```
Journey Map (home)
 └─ Chapter page: goal · prerequisite · completion criteria with live progress · 4 stages
     ├─ A  Learn   : lesson steps on an interactive board → "what to think about" checklist
     ├─ B  Watch   : narrated demo game · play/pause/step/speed · chat · "what if" branches
     ├─ C  Play    : your game vs Maia · hint before move · rating + explanation after move
     │               · opponent-move commentary · takeback · chat
     └─ D  Review  : 3-5 key moments · did well · work on · one lesson · new warm-up cards
Session start: 3-5 warm-up cards from your past mistakes (≤ 5 min), then back to the chapter
Practice (optional tab): the old exam modes
My games (background, later): PGN import + diagnosis
Progress: chapter metrics, move-quality trend, odds-swing charts, warm-up backlog
```

**Journey Map design.** A vertical winding path (phone-first) with the 17 chapters grouped into four regions (Foundations, Playing with a plan, Middlegame craft, Toward mastery). Each node shows its state: completed (filled, with its date), current (highlighted ring), or locked (muted with a lock and its prerequisite). Each node also carries four small A-B-C-D pips. A banner at the top always says where you are and what comes next, e.g. "Chapter 2, Play stage: 1 of 3 qualifying games".

---

## 4. The curriculum

### 4.1 Research basis

- **Steps Method** (Brunia & van Wijgerden): six steps. Tactics are taught as small named ideas that build on each other. First pawn endings arrive in Step 3. Deep strategy only arrives in Step 6. ([newinchess.com](https://www.newinchess.com/learning-chess-workbook-step-3), [chess.co.uk](https://chess.co.uk/products/learning-chess-workbook-step-6-rob-brunia-cor-van-wijgerden))
- **Yusupov, Build Up Your Chess** (9 books in 3 levels): six themes (tactics, strategy, positional play, endgames, calculation, openings) are spread evenly across all nine volumes rather than taught one after another. ([chess.co.uk](https://chess.co.uk/products/build-up-your-chess-1-2-and-3-fundamentals-to-mastery-artur-yusupov))
- **Silman, Complete Endgame Course**: endgames organised by rating class. Below ~1000: mating with K+Q and the "staircase" mate. Then basic pawn endings, opposition, Lucena and Philidor, the two-bishop mate. Triangulation and the principle of two weaknesses come later. ([review](https://patzersreview.substack.com/p/the-only-endgame-book-you-need), [chessdailynews](https://chessdailynews.com/?p=45746))
- **Chernev, Logical Chess: Move by Move**: 33 complete games with every move explained. This is the model for Watch mode. ([mcleodsbooks](https://www.mcleodsbooks.co.nz/p/logical-chess-move-by-move))
- **Heisman** (Novice Nook): beginners lose mostly to safety errors ("hope chess"), so safety and the blunder check come before everything except opening basics. ([chess.com forum summary](https://chess.com/forum/view/for-beginners/structured-learning-1000-to-1800))
- **FIDE trainer system**: training material organised by rating band. ([FIDE annex](https://fide.com/images/stories/NEWS/download/Annexes/GA2005/Annex_42(10pages).pdf))

What this means for the design:
1. Safety and finishing a game come very early (Heisman, Silman).
2. Endgames are spread across the journey at the right level (Silman), not taught in one block.
3. Every chapter keeps two **threads** running from earlier chapters (Yusupov's mix): from Chapter 2 on, every coached game is also scored for safety; from Chapter 6 on, also for plan coherence.
4. Watch mode follows Chernev: a whole game, every move explained.

### 4.2 Changes to your outline, and why

| Change | Why |
|---|---|
| **New Chapter 3: "Finishing the game: basic checkmates"** (K+Q vs K, K+R vs K, the ladder mate, back-rank and common mating nets). Split out of your Chapter 4 and moved earlier | Silman puts these mates below 1000. Without them you cannot convert the winning positions your coached games will produce from Chapter 1 onward |
| Your Chapter 4 becomes **Chapter 5: "Pawn endings and the active king"** (opposition, key squares, square of the pawn, promotion races) | Steps Method introduces pawn endings after the first tactics |
| Your Chapter 10 becomes **"Rook and minor-piece endgames"** (Lucena, Philidor, active rook, bishop vs knight, wrong bishop) | Silman places these one class above the basic pawn endings |
| Your 13+ becomes four chapters: master-game study, deep strategy, advanced endgames, competitive preparation | Silman's higher classes and Steps Method's Step 6 both treat advanced endgames and deep strategy separately |

### 4.3 The 17 chapters

Approximate Lichess rapid ratings are given for orientation only. I will not promise a rating.

| # | Chapter (UI title in Arabic) | Goal | Prerequisite | Watch: demo games show | Play: coached-game setup | Complete when (from your coached games) |
|---|---|---|---|---|---|---|
| **Foundations** (~0-1200) |||||||
| 1 | How a game starts (كيف تبدأ المباراة) | Play the first 10 moves with purpose: centre, development, king safety. Know the beginner opening errors | None | Coach vs a human-like opponent who violates the principles (early queen, pawn moves, not castling) and gets punished | Full games from the start position | 3 of the last 3 Ch.1 games score ≥ 4/5 on the opening checklist (6.5), with no blunder in your first 10 moves |
| 2 | Safety first (الأمان أولًا) | Every move: what changed, what is attacked, is anything hanging, blunder check. Count attackers and defenders | Ch.1 | Games decided by a hanging piece or a missed threat, narrated with the safety questions | Full games | 3 consecutive games with ≤ 1 hanging-piece blunder and ≤ 1 missed threat each |
| 3 | Finishing the game: basic checkmates (إنهاء المباراة: الكش مات الأساسي) | Ladder mate, K+Q vs K, K+R vs K, back-rank and common mating nets | Ch.2 | Mates delivered efficiently, and stalemate traps avoided | Scenario games from mating positions + full games | K+Q vs K in ≤ 10 moves and K+R vs K in ≤ 20 moves, twice each from random starts, with no stalemate |
| 4 | Tactics as ideas (التكتيك كأفكار) | Fork, pin, skewer, discovered attack, removing the defender. Spot targets and create the tactic | Ch.3 | Games where a tactic is prepared (alignment, loose piece) and then executed | Full games | You convert ≥ 60% of tactical chances that arise (minimum 5 chances), safety thread still met |
| 5 | Pawn endings and the active king (نهايات البيادق والملك النشيط) | Opposition, key squares, square of the pawn, promotion races, king centralisation | Ch.4 | Games won by king activity in the ending | Scenario games from pawn endings (results checked against an exact bitbase, 6.4) | 4 of 5 pawn-ending scenarios reach the correct result |
| **Playing with a plan** (~1200-1500) |||||||
| 6 | From opening to middlegame: making a plan (من الافتتاح إلى وسط اللعب: صنع خطة) | After development: find the side to play on, the worst piece, the open file, the pawn break | Ch.5 | Coach narrates the plan explicitly and updates it as the game changes | Full games | Moves 11-30 average expected-score loss ≤ 3.0 across the last 3 games, safety thread met |
| 7 | Pawn structures and their plans (بنى البيادق وخططها) | IQP, Carlsbad/minority attack, open and closed centre, pawn chains, hanging/isolated/doubled/passed pawns | Ch.6 | Real master games for each structure (KingBase) | Scenario games from structure positions | Over ≥ 30 moves played in recognised structures, average loss ≤ 3.0 and you hold or improve your odds |
| 8 | My opening repertoire (ذخيرتي الافتتاحية) | A small repertoire chosen by ideas and plans (default proposal in 12), with masters' statistics | Ch.7 | Model games in your repertoire | Games starting in your openings | 4 of 5 games stay in the repertoire ≥ 6 moves with opening average loss ≤ 2.0 |
| **Middlegame craft** (~1500-1900) |||||||
| 9 | Attacking the king and defending (مهاجمة الملك والدفاع) | Count attackers vs defenders, opposite-side castling, typical sacrifices (Greek gift), defensive principles | Ch.8 | Attacking games, plus one defended successfully | Scenario games: attack and defence | 3 of 4 scenarios succeed. ≤ 1 king-safety blunder per full game |
| 10 | Calculation: candidates and seeing ahead (الحساب: المرشحات والنظر إلى الأمام) | Forcing moves first, 2-3 move lines, compare candidates, deeper blunder check | Ch.9 | Coach's narration shows the candidate tree at critical moments | Full games | In positions with forcing moves, ≥ 80% of your moves lose ≤ 5 points (minimum 40 such moves) |
| 11 | Rook and minor-piece endgames (نهايات الرخ والقطع الخفيفة) | Lucena, Philidor, active rook, rook behind the passer, bishop vs knight, wrong bishop | Ch.10 | Instructive endgame wins and saves | Endgame scenarios | 4 of 5 scenarios reach the correct result |
| 12 | Positional play (اللعب الموضعي) | Weak squares and outposts, good vs bad pieces, prophylaxis ("what does my opponent want?") | Ch.11 | Classical positional games (Capablanca, Karpov) | Full games | In quiet positions (no forcing move among Stockfish's top 3), average loss ≤ 2.5 over the last 3 games |
| 13 | Practical play (اللعب العملي) | Time use, resilience after mistakes, converting advantages, saving bad positions | Ch.12 | Conversions and swindles, narrated | Full games with a clock | ≥ 75% of games where your odds reach 85% are won (minimum 4). No blunder in time trouble |
| **Toward mastery** (1900+) |||||||
| 14 | Master-game study (دراسة مباريات الأساتذة) | Learn plans from themed classics | Ch.13 | Themed master games, narrated Chernev-style | Games vs Maia-1900 | Average loss ≤ 2.0 over the last 5 games vs Maia-1900 |
| 15 | Deep strategy (الاستراتيجية العميقة) | Two weaknesses, exchanges, static vs dynamic factors, positional sacrifices | Ch.14 | Master games | Scenario games | Scenario odds maintained in 4 of 5 games |
| 16 | Advanced endgames (النهايات المتقدمة) | Complex pawn endings (tempo, triangulation), multi-pawn rook endings, queen endings, fortresses | Ch.15 | Master endgames | Endgame scenarios | 4 of 5 scenarios correct |
| 17 | Competitive preparation (الاستعداد للمنافسة) | Preparing against an opponent from their games, analysing your own games, tournament routines | Ch.16 | Coach prepares against a real player's games | Imported games + preparation tasks | You analyse 5 of your own games before the engine, and your error labels match the engine's on ≥ 60% of critical moments (the old mode 6, restored) |

The "Complete when" rules are first drafts. For each chapter I will show you the exact rule and threshold before you play its games. If the thresholds prove too easy or too hard in practice, I will tell you and propose a change, with the data.

---

## 5. The four stages in detail

### A. Learn

- A lesson is 6-10 steps. Each step has Arabic text, a position, arrows and highlights, and optionally a short line that plays on the board when you tap it. You go forward and back at your own pace.
- The lesson ends with a **"what to think about" checklist** (for example in Ch.1: "Did I move a centre pawn? Which piece is still at home? Can I castle next move?"). The same checklist reappears as the hint in Play.
- Every position and every claim in a lesson is checked at build time: positions with Stockfish 17.1, and pawn-ending results against an exact K+P vs K bitbase. Every move named in the text is checked for legality. A lesson that fails the check does not ship.

### B. Watch (narrated demo game)

**How demo games are made (offline, during build sessions):**
1. **The game.** For Chapters 1-6: "coach" = Stockfish 17.1 choosing, among moves within 3 points of expected score of its best, the one that best shows the chapter's idea (for example, a developing move in Chapter 1), vs "opponent" = Maia at a beginner level, sampling human-like moves. The concept appears naturally because the opponent makes typical human errors and the coach punishes them. From Chapter 7 on, I will also use real master games.
2. **Per-move analysis.** Stockfish top 3 lines with WDL, expected score at your level before and after, Maia's top moves with probabilities, masters' statistics while in the opening, and computed facts.
3. **Narration.** I write the narration, in Arabic, from that analysis. For each move:
   - what the move does and why it was chosen
   - what I was thinking: threats I noticed, the candidates I considered, and why each one was rejected
   - the current plan, and a clear marker when the plan changes
   - what the opponent's last move was trying to do
   - win probability before and after (shown as the bar, not as numbers in the text)
4. **Automatic checking.** A script rejects any narration that names a move that is not in the analysed lines or not legal in that position, that cites raw engine numbers, or that exceeds the length limit.

**The player:** play/pause, step forward and back, speed (1-10 s per move), the live odds bar, and expandable "what I was thinking" panels.

**Questions:** pause and ask in the chat panel. Claude answers about the exact position on screen, and can call page tools before answering (engine evaluation, play a line, Maia's prediction, computed facts).

**"What if I play X here?":** tap a move on the board. The game branches: Stockfish plays the best replies for a few moves, Claude explains what happens (grounded in those lines), and a "back to the game" button returns to the main line.

### C. Play with the coach

- **Setup:** you choose colour. The opponent is Maia at a level that challenges you (6.2). It starts at the level you choose and then adjusts ±100 after each game based on results.
- **Before your move (hint button):** the phase we are in, what matters now, and the relevant checklist items. Built from facts (open threats, pieces still at home, king shelter, hanging pieces). It never names a move.
- **After your move:** the class (excellent / good / inaccuracy / mistake / blunder), a plain-language reason, and, if there was a better move, that move and why it is better. When Maia's prediction shows that players at your level usually go wrong here, the explanation says so and explains the trap.
- **After the opponent's move:** what it threatens and what it is planning.
- **Takeback:** after an inaccuracy or worse, "take back and try again". Both attempts are recorded.
- **Questions:** the chat panel works throughout the game.
- **Speed:** an instant explanation built from the fact sheet appears straight away; Claude's richer explanation streams in after it on the fast model tier. A setting chooses between "comment every move" and "comment only important moves" (default: every move, as you asked).

### D. Review

After the game: the 3-5 key moments (the biggest swings in your odds, plus any moment tied to the chapter's idea), what you did well, what to work on, and one clear lesson. Each key mistake becomes a warm-up card that comes back at the start of later sessions (SM-2). The chapter's completion metrics update and show progress honestly, e.g. "opening checklist met in 2 of 3 games".

---

## 6. Probability and intelligence engine

### 6.1 Stockfish 17.1 with WDL (verified in this session)

- The npm package `stockfish@17.1.0` contains a **single-threaded "lite" WASM build (7.3 MB)** and a **pure asm.js build (10.4 MB)**. Single-threaded matters because the Artifact cannot enable the browser features multi-threaded builds need.
- I ran the asm.js build here: about 80k nodes/s, depth 17 in 3 s, and `UCI_ShowWDL` works (`... score cp -28 wdl 10 918 72 ...`).
- I cannot tell from here whether the Artifact allows WebAssembly. At startup the page tests it, uses the WASM build if allowed, and falls back to asm.js otherwise. Both give WDL.
- Stockfish 10 is retired from the main flow. Practice keeps working on 17.1.

### 6.2 "Your chances at your level"

Stockfish's WDL describes engine-vs-engine games: for an ordinary Italian Game position it said 92% draw. Beginners almost never draw such positions, so that number would mislead you. The bar will therefore show:

- **Main bar: win / draw / loss for players at your level (estimate).** An ordered-logit model of the game result given the Stockfish evaluation, the phase and the rating band. It is fitted on the 51,199 rated Lichess games I already have, with 4,071,511 evaluated positions (Lichess-computed evals, per ply).
  - **Honest limitation:** those games are mostly 1400-2600; under 1300 there are only about 2,000 positions. For beginner levels the model extrapolates the trend across bands, and the UI labels it "estimate".
  - **Cross-check:** Maia-1100's value head (trained on games of 1100-1199 players) gives an independent estimate. I will measure both on held-out games and report calibration (Brier score) in RESEARCH.md before choosing.
- **Engine WDL** stays available as a secondary line ("with perfect play").

### 6.3 Move quality by expected-score drop

Expected score = win + ½·draw (0-100), from the human-level model, from your side.

| Class | Drop in expected score |
|---|---|
| excellent | ≤ 2 |
| good | 2-5 |
| inaccuracy | 5-10 |
| mistake | 10-20 |
| blunder | > 20 |

When the position is already decided (expected score above 97 or below 3 both before and after the move), the class is softened, so an over-safe move in a won position is not called a mistake.

### 6.4 Maia (human-like moves)

- **Maia-1** (CSSLab, GPL-3.0): 9 networks, one per rating band from 1100 to 1900, each about 1.3 MB. Architecture: 6 residual blocks × 64 filters with squeeze-excitation, with policy and value heads. That is about 40M multiply-adds per position, roughly 50-100 ms in plain JavaScript. **No WebAssembly is needed, so it works in the Artifact for sure.**
- **Plan:**
  1. Convert the Leela-format weights offline (protobuf, with batch-norm folded) into compact files.
  2. Write a small JavaScript inference engine.
  3. Validate it two ways:
     - (a) compare its outputs with a Python reference implementation on 200 positions;
     - (b) measure how often its top move matches the move actually played in held-out human games at the matching rating. The published figure is about 50%; a buggy port would land near random.
- **Uses:**
  - the opponent in Play, sampling from Maia's move distribution, so it errs like a human;
  - "players at your level play X here (p%)" in Watch and Play;
  - "why beginners go wrong here": when Maia's favourite move loses, that becomes the focus of the explanation.
- **Limitation:** Maia-1's lowest level is 1100. Below that, the opponent is Maia-1100 sampled with a higher "temperature" (more random choices). Its strength is unmeasured, and the UI will say so.
- **Optional upgrade:** the Maia team's own site now runs a 45.7 MB Maia-3 ONNX model through onnxruntime-web, conditioned on both players' ratings and with a value head. Its rating buckets are 100 points wide from 1100 to 2000, plus one "below 1100" bucket, so it models sub-1100 players as a single group. If the Artifact allows WebAssembly, I can add it later as an upgrade (split into ≤ 15 MB files and cached in the browser). It is not on the critical path.

### 6.5 Computed facts (the grounding for every explanation)

| Fact | How |
|---|---|
| Hanging and under-defended pieces | Static exchange evaluation (SEE) |
| Attacked/defended counts | Attack maps |
| Threats | "Null-move" search: what would the opponent do if it were their turn, plus a static check |
| Development count, castling, king shelter | Pawn shield, open files near the king, attackers near the king |
| Opening checklist (Chapter 1) | Centre pawn, minor pieces developed by move 10, castled by move 12, queen not out early, no piece moved twice without reason |
| Pawn structure | Isolated, doubled, backward and passed pawns, islands, IQP/Carlsbad/closed-centre detectors |
| Material, phase, mobility | Direct counts |

Runtime facts are computed with chess.js in the browser. Build-time facts use python-chess (1.11.2 installs fine in a virtual environment here).

### 6.6 Masters statistics

The Lichess masters explorer cannot be reached, from this container or from the Artifact. So I will build an **offline opening tree from KingBase 2017**, which is in the `rozim/ChessData` repository on GitHub (master games, players 2200+):
- positions up to move 12 that occur in at least 10 games, with move frequencies and score;
- target size ≤ 8 MB, split into files;
- opening names from `lichess-org/chess-openings` (CC0).

Limitation: the data stops in 2017, which is fine for opening ideas at our level.

### 6.7 Tablebase

The Lichess tablebase API is unreachable. Endgame claims will be checked with:
- an exact K+P vs K table I compute offline (retrograde analysis);
- deep Stockfish 17.1 searches for everything else;
- Syzygy tables can be added later if a reachable source turns up.

---

## 7. Explanation quality rules, enforced in code

1. **Fact sheet first.** Every Claude request carries the fact sheet: engine lines in SAN, WDL, human-level odds, Maia's top moves with probabilities, computed facts, masters statistics, plus your chapter and the vocabulary allowed at that chapter.
2. **Tools for questions.** In chat, Claude can call page tools before it answers: `engine_lines(fen)`, `play_line(moves)`, `maia_moves(fen, rating)`, `position_facts(fen)`, `masters_stats(fen)`. If the Claude runtime in a given view does not support tools, the page falls back to putting the facts in the prompt.
3. **Post-check.** Every move named in Claude's answer is checked: legal in the position under discussion, and present in the supplied or tool-verified lines. If the check fails, the page asks once for a corrected answer, and otherwise removes the unsupported line and marks it.
4. **Human concepts, no engine numbers.** The prompts forbid evaluations like "+1.3" in the text. Odds appear only in the bar.
5. **Depth by chapter.** Simple words in Chapters 1-5 (centre, develop, safe, hanging, threat); plans and structures from Chapter 6; positional vocabulary from Chapter 12.
6. **A habit every time.** Every explanation ends with a reusable thinking habit tied to the chapter's checklist.

**Who writes what:**
- The Watch narrations and the lessons are written by Claude (me) during build sessions, from the analysis data, and checked by the scripts before they ship.
- Live explanations in Play, chat answers and "what if" branches are written by Claude at runtime through the Artifact's Claude connection, on your Claude account. You will see one consent prompt the first time.

---

## 8. Supporting features (background)

- **Your real games:** PGN import and the cause-based diagnosis from `33e8e7f`, restored as a background service. Lichess and Chess.com cannot be reached directly from the Artifact, so import stays "download the PGN from the link, then upload it". Recurring mistakes adjust demo-game choice and coaching focus, and can suggest revisiting a chapter. This stays switched off until you say you want it.
- **Warm-ups:** at the start of a session, 3-5 cards from your past mistakes (coached games first), taking ≤ 5 minutes. Then straight back to the chapter.
- **Practice tab:** the current modes, unchanged.

---

## 9. Architecture and files

```
index.html               shell, tokens, styles
js/core/                 board.js · store.js · engine.js (SF 17.1, WDL, probe) · claude.js (chat + tools + post-check)
                         · facts.js · prob.js (human odds model, move classes) · maia.js (JS inference)
                         · masters.js · srs.js
js/journey/              map.js · chapter.js · learn.js · watch.js · play.js · review.js · metrics.js
js/practice/             today's modes.js, solver and hubs, moved as they are
data/curriculum/ch01/    lesson.json · demo-*.json (analysis + narration) · scenarios.json · rules.json
data/masters/            opening tree shards
models/                  maia-1100..1900 weights · odds-model.json
engines/                 stockfish-17.1-lite-single.{js,wasm} · stockfish-17.1-asm.js
tools/                   build_demo.mjs · check_narration.mjs · build_masters.py · fit_odds.py
                         · convert_maia.py · kpk_bitbase.py · plus today's tools
```

**Database (owner-only, as now):**
- `journey/state`: current chapter and stage, completed chapters with dates;
- `games/<id>`: each coached game with per-move class, odds and facts summary;
- `reviews/<id>`;
- `cards/<id>`;
- `attempts/<id>` (Practice only);
- `chat/<gameId>`: the question/answer pairs, kept short.

**Size budget:** engines ~18 MB, Maia ~12 MB, masters tree ≤ 8 MB, curriculum data a few MB each. That is well inside the Artifact limits (15 MB per binary file, 256 MB per version).

---

## 10. Build order (each step shown working before the next)

| Step | What you will be able to do | How I test it |
|---|---|---|
| **1. Journey map + chapter structure** | See all 17 chapters with goals, prerequisites and completion rules; Chapter 1 current, others locked; chapter page with the four stages (placeholders where empty); Practice tab with the old modes | Headless browser at phone and desktop width, light and dark |
| **2. Watch mode** | Play one narrated Chapter-1 demo game; pause, step, change speed; ask questions in chat; try "what if" branches | Narration checker passes; branch → return restores the exact position; chat tools return correct engine data |
| **3. Play mode** | Play a full coached game with hints, per-move ratings and explanations, opponent commentary, takeback and chat. Opponent is Stockfish at first | Scripted games covering each move class; takeback restores state; games saved and reloaded |
| **4. Probability engine** | Live odds bar from the human-level model, Stockfish 17.1 WDL, Maia opponent and "players at your level" hints, masters statistics in the opening | Maia port validated (section 6.4); odds model calibration reported; Stockfish 17.1 build chosen by the startup test |
| **5. Chapter 1 end to end** | Lesson, 3 narrated demo games, coached games with the Chapter-1 rule, review, warm-ups, completion | One full run-through by script; every position and narration checked |
| 6-21 | Chapters 2 to 17, one at a time | Same checks per chapter |

After each step: PROGRESS.md updated, commit, push, republish to the same link, and a short note to you on what to try.

---

## 11. Risks and honest limits

| Risk | What I will do |
|---|---|
| The Artifact may block WebAssembly | asm.js Stockfish (tested) and pure-JS Maia-1 need no WebAssembly. Only the optional Maia-3 upgrade depends on it |
| Claude latency and usage on your account (one call per commented move) | Instant fact-sheet explanation first, Claude second, on the fast model tier. "Important moves only" setting. Answers cached per position |
| Human-level odds below 1300 are extrapolated | Labelled "estimate". Cross-checked against Maia-1100's value head |
| Maia-1 starts at 1100 | Higher temperature below that, labelled unmeasured. Maia-3 later if WebAssembly works |
| Masters data ends in 2017 | Fine for opening ideas at our level |
| No tablebase | Exact K+P vs K table plus deep Stockfish checks |
| Writing narrations for ~17 chapters × 3 games is a lot of content | Built chapter by chapter, each checked by script. I will tell you if quality or speed forces a change of method |
| Phones are slower | Engine depth adapts to measured speed. Maia and Stockfish run in background workers so the board never freezes |

---

## 12. Decisions I need from you

1. **Curriculum:** do you accept the 17-chapter version (new early checkmate chapter, endgames split by level, four advanced chapters), or do you want your original 12+ numbering?
2. **Repertoire for Chapter 8:** my default proposal is chosen for clear plans, not memorisation: the Italian Game as White, 1...e5 against 1.e4, and the Queen's Gambit Declined against 1.d4. Keep these, or do you have preferences? (This can wait until Chapter 8.)
3. **Starting level:** roughly how strong are you now? (Never played / know the rules / play online at about ___.) This sets the first opponent level; it adjusts automatically after that.
4. **Commentary density in Play:** every move (your request, my default), or only important moves?
5. **Odds bar:** human-level estimate as the main bar with engine WDL as a secondary line (my recommendation), or engine WDL as the main bar?

When you approve (with any changes), I start with Step 1: the Journey Map and the chapter structure.
