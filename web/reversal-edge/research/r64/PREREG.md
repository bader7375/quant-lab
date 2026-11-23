# Round 64 research loop (plan written 2026-11-09 before any result): something that helps the Z score / Market returned strategy
User: "do looping research to find something help this strategy. take your time and token needed".

## Program rule (fixed for every idea in the loop)
Base: the live Z score rule (daily -2.62 / weekly -2.08 first touch, ranker C >= 50%, market model > 0, market momentum <= -1.18,
liquid), next open, hold 40 sessions, 0.4% costs, 5 slots x 5%, ML-rank priority. Also reported on Market returned (option 7, shadow book).
Eras: DESIGN 2013-19 (choose), CONFIRM 2020-26 (judge), 2023-26 (recent check).
Each idea picks at most one variant on DESIGN (best sleeve return/drawdown ratio). The pick HELPS only if, vs the base:
  1. sleeve ratio higher in DESIGN and in CONFIRM;
  2. return per year at least 90% of the base in DESIGN and CONFIRM;
  3. 2023-26 ratio not lower;
  4. it survives at least 3 of 4 stress variants (nearby setting x2, 0.8% costs, a different slot count) with CONFIRM ratio > base;
  5. where the idea can run on the US sell-off swing (2005-26), it does not make the US worse in 2 of 3 eras.
Because several ideas are tried, every idea and its result is reported, passing or not.

## Ideas, in order (each pre-registered here before its test)
A. Slot priority. When more signals than free slots, which come first? Orderings: ML rank (live), market beta high / low (120-day
   beta to the equal-weight market), deepest stretch Z first, highest / lowest 60-day volatility, smallest / largest traded value,
   within-sector loser first (20-day return minus the sector's), ML rank with at most 2 open positions per sector, random (to measure
   what the ML rank is worth; 20 seeds). Hypothesis of record: high beta first (the Z swing edge is the market rebound).
B. Market-recovery exit. Sell when the market has recovered instead of after a fixed 40 sessions: market momentum back above
   0 / above -0.5; market index stretch Z back above 0; each with at least 10 and at most 60 sessions.
C. Two-step entry with the market turn: half at the Z score signal, the other half at the next open after the turn window opens
   (if within 20 sessions and the trade is open); both halves sold at the first half's 40-session exit.
D. Global risk state: S&P 500 20-day return / drawdown at the signal; skip when the S&P 500 is itself in a sell-off (20-day
   return <= -5%) - hypothesis: global crashes keep falling. And the reverse (only global sell-offs).
E. Within-sector vs sector-wide dips: the stock's 20-day return minus its sector's (equal weight) at the signal. Hypothesis:
   within-sector losers rebound more (short-term reversal is a within-industry effect; industry moves persist). Filter: keep the
   more-within-sector half.

## Addendum (written after A and B passed, before running these): control and combination
- Control for B: a fixed hold of 55 sessions (B's median holding). If it does as well as B, the finding is "hold longer", not
  "wait for the market to recover".
- Combination A+B (volatility-first slots + exit when market momentum is back above 0): it is preferred to A alone and B alone
  only if its ratio beats live in DESIGN, CONFIRM and 2023-26 and is not more than 0.05 below the better of A or B in CONFIRM.
  Also reported on Market returned.
