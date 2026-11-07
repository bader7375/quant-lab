# Round 53: which Z-swing tweaks are general? (pre-registered 2026-11-03, before any result of this round)
Each market runs its own base rule:
- **Saudi:** the live Z swing.
- **US:** the US sell-off swing, lines -1.67 / -1.13.
- **India and GCC:** round 52's version (Saudi lines, no ML).

Each base rule: first touch inside the market's sell-off window (momentum <= -1.18), buy the next open, hold 40, 5 x 5%.

Ten market-eras: Saudi 2013-19 and 2020-26; US 2005-09, 2010-17 and 2018-26; India 2005-09, 2010-17 and 2018-26; GCC (Qatar + Dubai + Kuwait summed) 2011-17 and 2018-26.

Tweaks (r53.py), each vs its market's base, judged by the sleeve ratio (return per year / max drawdown):
- K1 shadow turn gate (v2's gate).
- K2 split exit (half hold 40, half sell at Z back to 0, max 60).
- K3 deep window: signals only when market momentum <= -2.53.
- K4 hold 60 instead of 40.
- K5 sell when stretch Z is back at 0 (max 60) for the whole position.
- K6 10 slots x 2.5% instead of 5 x 5%.
- K7 12% resting stop order.

A tweak is GENERAL if both hold:
- its ratio beats base in at least 7 of the 10 market-eras; and
- it beats base in both Saudi eras.

The count of market-eras where its return is >= 90% of base is also reported. Most tweaks have been seen in Saudi before, and K1/K2 also in round 52; US, India and GCC are fresh for K3-K7.
