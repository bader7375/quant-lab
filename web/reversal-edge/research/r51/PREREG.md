# Round 51: Z swing v2 inside the whole account (pre-registered 2026-11-03, before any result of this round)
The Z swing is invested only about 5% of the time. Round 45 found the account return comes from what the idle money does, using
Core v2 (ML ranking sleeve at half size + trend breakouts). Here the Z component is either the live rule or v2 (round 50). The Z sleeve
gets money first and Core v2 fills the rest; the account earns T-bills on unused cash; costs are 0.20% per side.

Portfolios (r51.py):
- P0 Core v2 alone.
- P1 Core v2 + Z live (5 x 5%).
- P2 Core v2 + Z v2 (2 x 5 x 2.5%).
- P3 Core v2 + Z live at 5 x 10%.
- P4 Core v2 + Z v2 at 2 x 5 x 5%.
- Also: Z live alone and Z v2 alone (rest in T-bills).

## Decisions
- **v2 is the better Z component inside the account** if P2's Sharpe is higher than P1's in DESIGN 2013-19 and in CONFIRM 2020-26 (P4 vs P3 reported).
- **A Z component adds to Core** (round 45's rule) if all three hold in both eras:
  - CAGR above the Z sleeve alone;
  - Sharpe above Core v2 alone;
  - max drawdown no more than 5 points worse than Core v2 alone.
