# Round 70 plan (written 2026-11-10 before any result of the variants): test and improve the Z score strategy
User: "Let's go back to previous strategy stretch with ML. Test it, improve it".
Done before this plan (z70a.py, z70b.py; descriptions of the live rule, no variant was run):
- The Z score account, rebuilt with the verified plan book: 5 x 5%, 2013-19 +3.2% a year / drawdown 6.1%, 2020-26 +4.9% / 4.9%; 69 trades.
- Seen, and the reason for families B-D: the account takes 53 of its 69 trades on the first day of a sell-off cluster (signals there:
  69% winners, +8.5%), and almost none of the later signals (sessions 6-15: 89%, +23.3%; 16-40: 94%, +15.7%) because the 5 slots are
  already full. Only 18 clusters since 2013. Because this was seen on the whole history, families B-D are hypotheses born in-sample;
  the checks below (two eras, yearly walk-forward, the US) are what can still fail them.

## Base and measure
Live rule = paper book of the Z score rule (planbook.py: loss filter, one 40-session paper trade per stock), plan = its trades, 5 slots,
most volatile first, 5% each, 0.4% costs, T-bill interest on idle money. Whole-account growth per year, worst drawdown, their ratio.
Every variant keeps the paper book and only changes which paper trades are bought or how they are sold, unless stated.

## Families (23 variants)
A market turn: at most c positions bought before the market turn at once, c = 4, 3, 2, 1, 0 (0 = plan A at this size).
B sell-off day: buy only from session k of a sell-off cluster on (cluster = Z score signal days with no gap above 20 sessions; the day
  of its first signal is session 0), k = 1, 3, 5, 10.
C pacing: at least n sessions between two new positions, n = 2, 3, 5, 10.
D deeper market: buy only when market momentum is at or below -1.5, -2.0, -2.53 (live gate -1.18).
E exit: E1 sell half at the open after the first close with stretch Z >= 0, the rest after 40 sessions (one slot);
  E2 two books as tested in rounds 49-67 (half held 40 sessions, half sold at stretch Z >= 0 within 60 sessions, 5 slots each);
  E3 a new signal in a held stock restarts its 40 sessions (at most 120 in all); E4 hold 30; E5 hold 60.
F ML bar 60%, 70% (changes the paper book).

## Rule (fixed now)
"Better than live" in an era = growth per year not lower, worst drawdown not more than 0.2 points higher, and a higher return / drawdown.
Family pick = among the settings better than live in 2013-19, the best 2013-19 return / drawdown; CONFIRMED if better than live in 2020-26.
Stress for each confirmed pick, on 2013-26 (pass = return / drawdown above live under the same stress): 0.8% costs; ML order in the slots;
idle money earning nothing; and both neighbouring settings of its family (where they exist) better than live on 2013-26. Needs all but one.
Mechanism check for families A-D in an independent market: in the US sell-off swing (rounds 34-38), the average trade of signals 6 or
more sessions into a US cluster must be higher than that of first-day signals, or the timing families are not adopted.
Honesty check: each January from 2016 choose the best return / drawdown on the years before from the whole menu and live, hold it one
year (yearly returns spliced); 2016-26 must be at least as good as live.
Combination: the confirmed and stress-passing picks of different families are combined once; it is adopted over the single picks only
if it is better than the best single pick in both eras.
Sizes: the final choice is shown at 5% and 10% positions; the size is the user's risk decision. Nothing goes live without the user's yes.
