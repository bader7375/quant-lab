# Round 62 plan (written 2026-11-07 before any result of this round): meta-labeling for Z swing
User: "I want to add something to favor the trade. I mean like momentum to favor the long or meta labeling."

Already known: waiting for momentum confirmation hurts Z swing (round 42 green candle, round 57 VWAP/close entries), and a simple
win-probability model in round 28 (AUC 0.61 / 0.56) failed in 2023-26. This round is a stronger second attempt.

## Primary signal and the meta question
Primary = the live Z swing signal (daily -2.62 / weekly -2.08 first touch, ML rank (ranker C) >= 50%, market model > 0,
market momentum <= -1.18, liquid), next open, hold 40 sessions, 0.4% costs. Meta question: will this trade end positive?

## Training events and label
All stretch-Z dip events in liquid stocks from 2011: first close <= -2.0, first close <= -2.62, or a weekly first touch of -2.08
(no other filter, so the model also sees dips outside the gates). Label = 1 if the 40-session trade from the next open is positive
after 0.4% costs.

## Features (all known at the signal close)
- the 42 stock features of the ML ranker (daily ranks: returns 1-120 days, 12-1 momentum, RSI, volatility, size, liquidity, ...);
- Z family: stretch Z, z10, z20, z60, curve slope (z10 - z60), 5-day change of Z, weekly Z, touch momentum (60 and 250 sessions),
  rebound memory, traded value vs its 60-day median;
- momentum state: Momentum-Pulse-style 5/10/20/60-day vol-scaled returns are inside the 42 (r5..r60, vol); plus 12-1 momentum;
- market: market model, market momentum, turn gate G4, share of liquid stocks with stretch Z <= -2, equal-weight market 20-day return;
- the ML rank (ranker C) and the sector.

## Model
LightGBM classifier (300 trees, learning rate 0.03, 15 leaves, at least 50 events per leaf, 80% rows / 80% features per tree).
Walk-forward: refit every January 2013..2026 on events whose 40-session trade had ended before that January (purged).

## Uses tested on the live Z swing trades (5 slots x 5%)
U1 filter: take a signal only if p >= the DESIGN median of p over Z swing signals.
U2 priority: when more signals than free slots, take the highest p first (instead of the highest ML rank).
U3 sizing: weight = 5% x p / (DESIGN mean p over Z swing signals), clipped to 2.5% .. 7.5%.

## Pass rule (DESIGN 2013-19 chooses nothing new; CONFIRM 2020-26 judges)
Meta-labeling "favors the trade" only if: (1) AUC on Z swing signals >= 0.55 in DESIGN and in CONFIRM;
(2) for U1, the kept trades beat the dropped ones by >= +2 pts per trade in DESIGN and CONFIRM;
(3) the use's sleeve return/drawdown ratio beats both the live rule and pending option 1 (ML bar 70%) in DESIGN and in CONFIRM;
(4) 2023-26 return not lower and drawdown not deeper than live. Any pass becomes an option for the user (no live change without consent).
Feature importance and the momentum features' direction are reported whatever the result.
