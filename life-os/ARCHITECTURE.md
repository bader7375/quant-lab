# LIFE OS: architecture and design record

Version 1.0.0 · 10 October 2026

## 1. The underlying problem

The brief asks for a productivity app, a tutor, a research feed, a coach and a journal. The common problem underneath is narrower: **each morning, turning a large, scattered set of ambitions into one well-chosen action, and making sure that what you learn and try actually compounds instead of evaporating.**

Three failure modes follow from that, and the design is built against them:

1. **Consumption without application.** Reading feels like progress. LIFE OS asks you to answer before it reveals, tracks *read → understood → applied* for every source, and turns sources into cards or experiments.
2. **Optimising too many things at once.** The wheel has a "maintain" stance and a "check the metric" stance. Priorities are capped at three. A focus guard warns when more than two experiments or seven goals are active.
3. **Unverifiable intelligence.** An AI that invents an alert, a paper or a personal fact is worse than none. LIFE OS separates verified sources from model knowledge, facts from hypotheses, and proposals from approved changes. Every claim about you needs evidence from your own records.

## 2. Verified platform facts (checked 10 October 2026)

- **Model.** Claude Opus 5.5 exists. API id `claude-opus-5-5`, 1M-token context, API price $4 / $20 per million input / output tokens. Thinking is always on and its depth is set by effort (default medium). Claude Sonnet 5.5 (`claude-sonnet-5-5`, $2 / $10) and Claude Haiku 5.5 (`claude-haiku-5-5`, $0.10 / $0.50) are the current cheaper tiers.
- **Claude artifacts** can declare runtime capabilities:
  - `sample` calls Claude on the viewer's own account. A specific model can be requested, and the response reports which model answered.
  - `db` is a persistent document store with a private per-user area.
  - `user` provides the viewer's id.
  - `downloads` lets the page offer a file to save.
- **What the in-page Claude cannot do.** It cannot browse the web, has no memory between calls, and cannot read the viewer's chat history, email or files unless a connector is granted. The only connector on this account is Gmail, and it is not connected.
- **Subscription and API billing are separate.** Inside the artifact, Claude usage counts against the Claude plan, with no API key. A self-hosted server would need an API key and API billing.
- **Conversation history.** Neither ChatGPT nor Claude exposes chat history to third-party pages. Both offer user data exports (`conversations.json`), which is what the import pipeline reads.

## 3. From the Wheel of Life to a product structure

I could not see the attached Wheel of Life image in this session. The structure uses the eight areas you listed, in your order: Personal Growth, Health, Family & Friends, Love & Romance, Fun & Recreation, Spirituality, Career, Finance.

The candidate extra categories become **sub-areas**, not new spokes, so tracking stays light:

| Area | Sub-areas |
|---|---|
| Personal Growth | Communication, confidence & presence, discipline & focus, thinking & decisions, emotional regulation |
| Health | Fitness, sleep, nutrition, cognitive performance |
| Career | Clinical mastery, medication safety, leadership, automation & AI tools |
| Finance | Savings, market understanding, quant research, risk discipline |

Every area carries:
- a vision and a definition of excellence (drafted by Claude from your brief and marked as drafts to edit);
- a six-rung goal ladder: outcome → annual → quarterly → monthly → weekly experiment → daily action;
- indicators and a review cadence;
- a dated score history (now, wanted, previous, trend);
- a stance (improve / doing well / maintain / temporary priority / check the metric);
- Claude's assessment and a change log.

## 4. Three product concepts

| | A. The Almanac | B. The Observatory | C. The Field Notebook *(chosen)* |
|---|---|---|---|
| Feel | Calm editorial morning paper | Dense research terminal | Editorial morning read on top, lab notebook underneath |
| Strength | Pleasant daily ritual | Maximum information and control | Ritual plus measurement: briefing → action → evidence |
| Weakness | Easy to read and not act | Overwhelming at 7 am on a phone | More to build |
| Fits you? | Partly: you want action, not reading | No: you asked for calm and no fifty tasks | Yes: calm first screen, depth one tap away |

**Recommendation: C.** The morning screen is one essay-like briefing that ends in a single decision. The depth (FSRS scheduling, calibration, experiments, evidence grades) sits one tap away for when you want it. The visual identity is a dawn horizon that follows the time of day, a qahwa-gold accent, a serif reading face for content, and a precise grotesk for the interface. Light and dark themes are both designed. It is mobile-first, with a thumb-reach tab bar.

## 5. Architecture

```
 phone / desktop  ──►  claude.ai artifact (one HTML page, vanilla JS, no build step)
                         ├── db (private per-user documents)   ◄── Claude Code (seeding, research runs)
                         ├── sample → Claude (Opus 5.5 for deep work, faster tier for routine)
                         ├── user (your id → private storage path)
                         └── downloads (backup export)
```

**Why this and not a hosted web app with a server.**

- **No credentials to protect.** No API key exists, so none can leak.
- **No server to run.** There is no hosting, database administration, or authentication code. Sign-in is claude.ai's.
- **Persistence is real.** Data survives sessions, restarts and republishing the page.
- **It suits someone with little coding experience.** The whole app is one file. Updating it means editing that file and republishing.

Trade-offs accepted: the page cannot run on a timer or browse the web. Scheduled research is handled by Claude Code (see §8), which can search and verify. A move to a hosted app would make sense only if you need fully autonomous scheduled briefings without opening Claude, or embeddings-based search over thousands of notes (see §11).

**Model routing** (Settings lets you change it):

| Task | Model | Why |
|---|---|---|
| Briefing, intelligence update (2 calls), area assessment, reviews, coach | `claude-opus-5-5`, high effort | Synthesis across your whole model; quality matters most |
| Grading answers, import extraction | Balanced tier | Short, well-specified tasks |
| Card generation | Opus for clinical or level 4–5; balanced otherwise | Clinical accuracy deserves the stronger model |

The model is a setting, not code. Swapping it changes one value. If the named model is unavailable, the platform answers on the requested tier and LIFE OS shows which one answered.

**Cost.** Inside the artifact there are no API charges; usage counts toward your Claude plan. For comparison, the same workload on the API with Opus 5.5 would be roughly $0.20 per Standard briefing, $0.50 per intelligence update and about $0.01–0.02 per graded answer on Sonnet 5.5. That comes to about $10–20 per month for daily use. These are estimates, because thinking tokens vary.

## 6. Data model

All personal data lives under `data/users/<your id>/`. That area is private by platform rule: shared viewers cannot read it, including the artifact's owner viewing someone else's.

| Path | One document per | Key fields |
|---|---|---|
| `profile` | — | name, role, context, priorities (≤3), dimensions{vision, excellence, indicators, cadence, draft, assessment} |
| `settings` | — | deepModel, deepEffort, routineTier, briefMode, newPerDay, sessionSize, privacy{relationships, financeNumbers, health, journal} |
| `os/wheel/w-YYYY-MM-DD` | scoring day | scores{area: {score, desired, status, note}} |
| `os/goals/*` | goal | dim, horizon, title, measure, due, status (proposed / active / done / paused / dropped), why, origin |
| `os/memory/*` | memory item | text, kind (fact / preference / observation / hypothesis), category, dim, source (you / import / claude / seen), status (pending / approved), evidence, confidence, verdict, edits[] |
| `os/cards/*` | learning card | track, type (case / concept / problem / scenario), concept, prompt, answer, explanation, source, sourceUrl, level, importance, related[], rubric[], srs{s, d, last, due, reps, lapses}, log[last 30: t, g, conf, ok, partial, score] |
| `os/checkins/YYYY-MM-DD` | day | energy, mood, sleep, focus, oneThing, note |
| `os/experiments/*` | experiment | problem, hypothesis, intervention, measure, unit, duration, confounders, success, phase, logs[{date, v, phase}], results, decision, lessons |
| `os/decisions/*` | decision | context, options, choice, assumptions, expected, confidence, reviewOn, outcome, asExpected, lessons |
| `os/library/*` | source | title, topic, category, evidence, source, published, accessed, url, verified, clinical, finding, limitations, implication, confidence, relevance, related, read / understood / applied, reviewOn |
| `os/briefings/b-DATE-MODE` | day × mode | data (sections A–H), model, done{} |
| `os/updates/u-*` | update run | fingerprint, status, step, report, model, error |
| `os/reviews/{w,m,q,y}-PERIOD` | period | answers[], ai, stats |
| `os/queue/q-*` | research request | question, topic, why, status, origin |
| `os/history/h-YYYY-MM` | month | entries[{t, kind, text, ref}] |

Ids derived from dates or content hashes make repeated operations idempotent: one check-in per day, one briefing per day and mode, one scoring snapshot per day, and no duplicate cards or proposals.

## 7. Learning engine

- **Scheduler:** FSRS-4.5 with default weights. Target retention is 0.90, so the next interval equals stability. "Again" re-queues the card within the session.
- **Priority:** due cards are ranked by forgetting risk × importance × recent errors × the weight of their area (priority areas weigh more). New cards are capped per day. Tracks are interleaved.
- **Per-card flow:**
  1. Answer from memory.
  2. Rate confidence (four levels).
  3. Reveal the reference answer.
  4. Optionally get Claude's feedback: what was right, gaps, misconceptions, a transfer question, and per-criterion rubric scores for communication scenarios, with a retry.
  5. Rate recall.
- **Signals:**
  - a calibration chart (confidence against accuracy);
  - readiness per track (≥85% over the last 10+ answers means harder material; <60% means slow down);
  - repeatedly forgotten concepts;
  - "read five, applied none".
- **Knowledge constellation:** concepts grouped by track, brightness showing current recall, gold links across disciplines.

## 8. Research runs

The page queues questions. **Claude Code** answers them, because it can search the web. To run: in Claude Code, say *"Run the LIFE OS research queue."* The procedure:

1. Read `data/users/me/os/queue` (status `queued`) and the existing `data/users/me/os/library` ids, using the ArtifactData tool on the artifact URL.
2. For each question, plus a standing watch list (FDA Drug Safety Communications, SFDA safety alerts and signal reports, KDIGO, ISMP, major nephrology trials), search the web. Prefer primary and authoritative sources: regulators, guideline bodies, systematic reviews, original papers.
3. For each source:
   - Record its **publication date** separately from the date of the underlying event, and the date checked.
   - Check for corrections, retractions or superseding guidance where feasible.
   - Set `verified: true` only if the source itself was located.
4. Write each finding to `data/users/me/os/library/<lib-id>` with the schema in §6. Set `clinical: true` for anything that could affect patient care.
5. Mark each queue item `done` and record which library ids answered it, or note that no reliable answer was found.
6. Never invent a source, date, quotation or finding. If nothing new and important turned up, write nothing.

The same procedure can run weekly as a Claude Code Routine. It was not set up automatically; ask Claude to create it if you want it.

## 9. The update workflow

| Step | What happens | Where |
|---|---|---|
| 1 Retrieve | Gathers your records and computes a fingerprint of user-generated changes; if it matches the last run, stops and creates nothing | page |
| 2 Reflect | Claude compares behaviour with goals; patterns need ≥3 instances | Claude call 1 |
| 3 Research | Ranks verified library sources by relevance; queues up to three web-research questions | page |
| 4 Verify | Flags stale time-sensitive items, old guidance, unverified links, disputed findings | page |
| 5–7 Synthesize, propose, plan | New knowledge from cited sources; proposals; ≤4 new cards; ≤2 experiments; candid verdicts; next actions | Claude call 2 |
| 6 Update model | Saves proposals as *pending*; nothing approved automatically | page |
| 8 Report | Timestamped report with sources and the answering model | page |

Interrupted runs are saved with the failed step. A re-run is safe because records are keyed by content hash and fuzzy-matched against existing ones.

## 10. Privacy and reliability

- Per-user private storage. Four sharing switches control what any Claude request may include.
- No identifiable patient data: the import screen says so, and the extraction prompt refuses it.
- Writes are serialised per document. Failures show a clear message; the page never claims success it did not get.
- Scores, decisions and memory edits keep their history. Deletion asks for confirmation.
- Export to JSON, and restore that never overwrites newer records.

## 11. Roadmap and acceptance criteria

| Phase | Scope | Status | Acceptance criteria |
|---|---|---|---|
| 1 Foundation | App shell, design system, wheel, today, navigation, mobile | **Done** | Renders on phone and desktop in both themes without horizontal scroll; wheel scores persist as dated snapshots |
| 2 Memory and briefings | Private storage, profile, memory with facts vs hypotheses, check-ins, Claude briefings in three modes | **Done** | Briefing cites only real library ids and card ids (invalid ids are stripped); one briefing per day × mode |
| 3 Research and update | Verified library, research queue, 8-step update, report history | **Done** (web research runs in Claude Code) | A second run with no new data creates zero records; every library entry has a date, source and verification flag |
| 4 Adaptive learning | FSRS, four tracks, Claude grading, calibration, readiness, constellation, card generation with de-duplication | **Done** | Ratings update the schedule; duplicate generated cards are rejected |
| 5 Analytics and experiments | Experiments with baseline/intervention analysis, decision journal with Brier score, reviews, trends | **Done** | Analysis states its sample size and refuses causal language |
| 6 Next | Weekly research Routine; voice recording in the browser if the microphone capability becomes available; a year-in-review page; a future-self scenario tool; FSRS parameter fitting on your own reviews after about 1,000 answers | Proposed | — |

**Tested before release.** A simulated Claude runtime (`dev/mock.js`) and an end-to-end browser run covered 26 checks, all passing with no console errors:
- briefing, check-in, wheel scoring, goal approval and area assessment;
- a learning session with grading, and card generation with de-duplication;
- an experiment with analysis, and a decision with a Brier score;
- library flags and the research queue;
- memory approval and import with de-duplication;
- review synthesis, settings, export and privacy;
- an update run, an idempotent second run, and a forced re-run without duplicates;
- the coach;
- phone and desktop layouts, the no-runtime fallback, and onboarding from an empty database.

What the simulation cannot prove is how the real Claude answers. The first live briefing and update are the real test.
