# LIFE OS

A private personal intelligence system that runs as a Claude artifact.

**Open it:** https://claude.ai/artifact/Jjabm2YpZigKHo11nbizEJ (private to your account)

Nothing to install, no server, no API key. Open the link in Claude on your phone or computer. The first time LIFE OS asks Claude for something, Claude asks you to allow it. Allow it once.

---

## The morning routine (10 minutes with coffee)

1. **Open LIFE OS.** Choose how much time you have (Quick 3–5, Standard 10–15, Deep 20–30) and your energy level.
2. **Press "Prepare my briefing".** Claude reads your goals, wheel, learning record, check-ins and verified library, then writes sections A–H. It ends with three lines: the one thing that matters, the smallest action, and how you will know you did it.
3. **Do the check-in** on the right (20 seconds): energy, mood, sleep, focused minutes, and whether you did yesterday's One Thing.
4. **If you have 10 minutes more:** Learn → Start session. Answer from memory, rate your confidence, reveal, and optionally ask Claude to check your answer.

Weekly: Review → Week, then **Update intelligence**.

## What each section does

| Section | Use it for |
|---|---|
| **Today** | Morning briefing, check-in, what is due, running experiments |
| **Wheel** | Score the eight life areas (1–10, now vs wanted), set the stance for each (improve / doing well / maintain / temporary priority / check the metric), and keep a goal ladder per area, from long-term outcome down to daily action |
| **Learn** | Four tracks: clinical pharmacy, quant & markets, communication & growth, health & cognition. FSRS spaced repetition, Claude feedback on your answers, calibration chart, knowledge constellation |
| **Lab** | Experiments (baseline → intervention → result) and the decision journal (confidence now, outcome later, Brier score) |
| **Library** | Research with publication dates, evidence type, limitations and verification status. Mark read / understood / applied. Turn a source into cards or an experiment |
| **My model** | Everything LIFE OS stores about you: facts, preferences, observations and hypotheses, each labelled with its source. Approve or discard proposals, edit, archive, delete, import conversation exports, see the change history |
| **Review** | Weekly, monthly, quarterly, annual questions with Claude's synthesis, plus trend charts |
| **Settings** | Model routing, privacy (what Claude may read), export / restore / delete |

## The Update Intelligence button

It runs a fixed eight-step workflow: **retrieve → reflect → research → verify → synthesize → update model → next actions → report**. The rules it follows:

- It **proposes** changes to your goals, memory and hypotheses. Nothing changes until you press *Keep* or *Accept* (My model → Proposals).
- It is **idempotent**. If nothing meaningful changed since the last run, it says so and creates nothing. Running it again after a failure is safe because everything is de-duplicated.
- Every run is saved with a timestamp, the sources it used, and the model that answered (Settings → Intelligence updates).

## How LIFE OS is connected to Claude

- The page calls Claude through the artifact's built-in Claude access, **on your own Claude account**. There is no API key and no API bill. Usage counts toward your Claude plan's limits.
- You asked for **Claude Opus 5.5**. It exists, and its API identifier is `claude-opus-5-5`. LIFE OS requests it by name for deep reasoning (briefings, updates, assessments, reviews, the coach) and shows which model actually answered. Routine work (grading answers, extracting memories) uses a faster tier. You can change both in Settings.
- **What Claude can see:** only the compact summary LIFE OS sends with each request, filtered by your privacy settings. Relationship details are off by default.
- **What Claude cannot do from this page:** browse the web, read your chat history, read your email, or remember anything between requests. Your memory lives in LIFE OS's storage, which you can inspect and edit.

## Research: how new sources get in

The page cannot browse, so LIFE OS never invents sources. New research arrives through **Claude Code**, which can search the web:

1. In LIFE OS, use **Library → Request research** (or let an update queue questions for you).
2. In a Claude Code session on this repository, say: **"Run the LIFE OS research queue."**
3. Claude Code reads the queue, searches, checks dates and source quality, and files verified entries into your library. Each entry records the title, source, publication date, date checked, evidence type, main finding, limitations, confidence and what it means for you.

The research routine Claude Code follows is in [ARCHITECTURE.md → Research runs](ARCHITECTURE.md#research-runs). It can also run on a weekly schedule as a Claude Code Routine. Ask Claude to set one up.

## Importing past conversations

ChatGPT and Claude do not let a web page read your history directly. Export instead:

- **ChatGPT:** Settings → Data controls → Export data
- **Claude:** Settings → Privacy → Export data

Unzip the export, then in **My model → Import** choose `conversations.json`. Pick the conversations to use. Only your own messages from those are sent to Claude, which proposes memories. Nothing is stored until you keep it. Do not import anything that contains patient-identifiable information.

## Your data

- **Where it lives:** this artifact's database on claude.ai, inside a per-user private area. If you share the link, the other person gets their own empty LIFE OS and cannot see yours.
- **Backups:** Settings → *Export a full backup (.json)*. Restore adds missing records and replaces older versions, but never overwrites newer ones.
- **Deleting:** individual items anywhere, or Settings → *Delete everything* (type DELETE to confirm).
- **History:** score changes, goal changes, memory edits and imports are logged by month in My model → History.

## Safety boundaries

- Clinical content is educational. LIFE OS never issues patient-specific orders and flags anything that must be checked against current guidance, local protocol and the individual patient.
- Financial content is education and research method, never buy/sell advice. No strategy is called profitable without out-of-sample, cost-aware validation.
- Health and cognition claims are labelled by evidence strength. There are no promises of IQ gains.

## Files in this folder

| File | What it is |
|---|---|
| `index.html` | The whole app: one self-contained page, published as the artifact |
| `ARCHITECTURE.md` | Product concepts, design decisions, data model, AI orchestration, roadmap |
| `seed/starter-data.json` | The starter profile, draft visions, 33 cards and 16 verified sources loaded on day one |
| `dev/` | Test harness (a simulated Claude runtime and an end-to-end browser test) and the seed generator |

To change the app, edit `index.html` and ask Claude to republish it to the same artifact link. Your data is unaffected by republishing.
