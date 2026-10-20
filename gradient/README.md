# Gradient

A private morning learning system, published as a claude.ai artifact:
https://claude.ai/artifact/AJgU5GzxXpamNw99NsJMuh

## How it works

Every morning at 06:54 Riyadh time a scheduled Claude Code routine ("Gradient morning brief")
follows `daily-agent.md`: it reads your progress, researches the web, verifies what it writes,
and saves one "morning" into the page's private store. With your coffee you open the page and
work through six stations, in this order, scaled to the energy you pick (Low, Steady, Sharp):

| Station | What you get |
|---|---|
| Focus | Guided breathing first (cyclic sighing, box, or six breaths a minute), 2 to 5 minutes by energy |
| الروح | An ayah with tafsir and a فائدة, morning adhkar with tasbih counters, and a free مسبحة |
| Pharmacy | A new paper with MCQs, one section of a 50-chapter disease-based curriculum with a 5-question exam, three career ideas |
| Presence | A daily body-language exercise, a daily eye-contact trainer (hold your gaze while you say a line), and one of 28 charisma techniques with a drill and coaching from Claude |
| Mind | Five measured brain games (including untimed pharmacy calculations with "Teach me how"), a 90-second clinical case, a puzzle, a brain-science article and a focus exercise |
| Quant | One trading-strategy concept a day (RSI(2) mean reversion first, then probability, sizing and research hygiene), each tied to a file in quant-lab, with MCQs |

The learning loop: every MCQ you miss becomes a Recall card (spaced repetition). Every Friday the
page builds an exam from the week's questions, the agent's 10 integrative questions and your
overdue misses. Every question has a "Teach me how to answer" button: before you answer it teaches
the method without giving the answer away; after you answer it explains the reasoning in depth.

Likes: "♥ More like this" and "Less" sit on papers, chapter sections, techniques, drills, articles,
puzzles, cases, quant lessons and breathing patterns. The morning agent reads them every day and
leans toward what you like; Update reads them too. The Model of you tab shows the summary.

Update asks Claude to reread your progress, revise its model of you and write review questions on
your weakest topic.

## Files

- `gradient.html`: the page. It uses the artifact `db` capability (private store, owner-only
  rules) and `sample` (calls Claude on your own account).
- `games.js`: the five brain games, loaded by the page.
- `data/`: verified copies of the Arabic content and the quant and charisma curricula seeded into the store.
- `daily-agent.md`: the routine's instructions. The routine stores its own copy of the prompt,
  so after editing this file, ask Claude Code to update the routine too.

To change anything, ask Claude Code to edit the file and republish to the same URL. Your data
lives in the store, not in the files, so republishing never erases it.
