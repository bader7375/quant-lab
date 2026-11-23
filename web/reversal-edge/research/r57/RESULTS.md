# Round 57 results: using 1-hour and 5-minute bars to execute the daily Z swing (pre-registered in PREREG.md)

## A. Entry timing with hourly bars (a57.py, a57.out): keep buying at the open
Daily first touches in the sell-off window, liquid stocks, with a complete 40-day trade: 63 (DESIGN Nov 2024-Oct 2025) and 57 (CONFIRM Nov 2025-Nov 2026). Exit fixed at the live rule's exit.

| entry on day 1 | entry price vs the open, DESIGN / CONFIRM | trade average, DESIGN / CONFIRM |
|---|---|---|
| open (live) | 0 / 0 | +0.94% / +1.75% |
| day-1 VWAP | -1.13% / -0.91% (dearer) | -0.29% / +0.71% |
| day-1 close | -1.50% / -0.95% | -0.65% / +0.61% |
| limit 1% under the open, else the close | 0.00% / -1.14% (hit 70% / 33%) | +0.89% / +0.46% |
| hourly stretch trigger (Z <= -2.62 within 2 days) | +0.55% / -1.49% (hit 62% / 40%) | +1.43% / +0.10% |

Nothing passes. After a daily signal the stock tends to rise from the first bar of the next day (day-1 VWAP and close are about 1% above the open), so waiting costs money. The live subset shows the same: in CONFIRM, 17 trades, +9.0% from the open vs +7.1% to +8.6% for the later entries.

## B. Hourly complement (bc57.py, bc57.out): not adopted
Hourly signals (line -3.0, hold 40 bars, live gates) only on stocks the daily book does not hold (128 of 158 hourly signals). 5 x 5% sleeves:

| | daily alone | daily + all hourly | daily + hourly complement |
|---|---|---|---|
| DESIGN | +1.54%/y, DD 4.38%, ratio 0.35 | +6.43%, 4.22%, 1.52 | +6.63%, 4.22%, 1.57 (11 trades taken, all winners) |
| CONFIRM | +3.15%/y, DD 2.12%, ratio 1.49 | +5.08%, 3.58%, 1.42 | +4.41%, 3.63%, 1.21 (12 trades, 58% win, +2.1%) |

More return in both periods, but the CONFIRM ratio is lower (1.21 vs 1.49), so it fails the rule. The samples are small: 11-12 complement trades a year.

## C. Exploratory: 5-minute entry (last 60 days, 76 daily signals)
Rule: buy at the open of the bar after the first 5-minute close above the session VWAP (after 10:30); otherwise at the close.

| entry | price vs the open | return to the day-5 close (before costs) |
|---|---|---|
| open | 0 | +10.87% |
| VWAP-reclaim | -0.35% on average, median 0.00% | +11.31% |

A small gain in one regime (Aug-Oct 2026, mostly the October sell-off). Promising enough to paper-track, not enough to adopt.

## What this means for 1-hour and 5-minute use
- Do not trade them as separate strategies (rounds 55-56).
- Buy daily signals at the open (A).
- The hourly complement adds return with more risk (B).
- The only execution idea still standing is the 5-minute "wait for the price to reclaim VWAP" entry. It needs a forward test: log it for each live signal for a few months before trusting it.
