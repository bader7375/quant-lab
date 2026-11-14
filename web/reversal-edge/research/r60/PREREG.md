# Round 60 plan (written 2026-11-06 before any result of this round): a momentum indicator from stretch-Z level touches
User: "Let's create a momentum indicator from Z score. From how many it touches levels 1 and 2 and 3, -1 and -2 and -3 ...
as AI make it in reality the best. And is it helping the trades?"

## The indicator family ("Z touch momentum"), from the scanner's daily stretch Z (average of z10, z20, z60)
- Up-touch at level k (k = 1, 2, 3): the close where Z first reaches +k (Z_t >= k and Z_t-1 < k).
  Down-touch: Z_t <= -k and Z_t-1 > -k. Deeper levels weigh more: weight k.
- N_L  (net touches)  = sum over k of k x (up-touches - down-touches) in the last L sessions.
- B_L  (touch balance) = N_L / sum over k of k x (up-touches + down-touches); 0 when there was no touch. Range -1 .. +1.
- O_L  (time beyond levels) = sum over k of k x (sessions with Z >= k - sessions with Z <= -k) / L.
- L = 60, 120, 250 sessions -> 9 variants. Only closes up to the signal day are used; trades start at the next open.

## T1 - is it a return signal by itself? (ML universe of round 27/58, every session)
IC = daily rank correlation with the next-20-session return; top-minus-bottom decile 20-session spread; plus the IC left after
removing what r20, r60, r120 and 12-1 momentum already explain (cross-sectional regression residual each day).
Pick on DESIGN 2013-19: the variant with the largest |IC|; its sign says whether it works as momentum (+) or reversal (-).
CONFIRM 2020-26 passes if the IC has the same sign with t >= 2 (t = mean / sd x sqrt(days / 20)).

## T2 - does it help the Z swing trades? (live triggers and filters, next open, hold 40, 0.4% costs)
For each variant: split DESIGN signals at their DESIGN median; pick the variant and side with the largest DESIGN per-trade gap
(each side >= 30 trades). Filter = keep only that side. Live sizing (5 slots x 5%).
"Helps" only if: CONFIRM per-trade gap has the same sign and is >= 2 points, AND the sleeve's return / drawdown ratio is higher
than the live rule's in DESIGN and in CONFIRM, AND 2023-26 is not worse.

## T3 - does it help the ML ranker? (C + the T1 pick's type at L = 60, 120, 250 as 3 extra daily-rank features)
Same walk-forward as C (5/10/20/60-session models, quarterly refits, purge, every 2nd training day).
"Helps" only if DESIGN IC > C's and, on CONFIRM, round 58's four conditions hold vs C: IC higher, Core ML Sharpe higher,
top-decile excess higher, Z-swing per-trade average >= C's - 0.5 points.

Anything that passes becomes an option for the user (no live change without consent). The TradingView indicator is built either way.
