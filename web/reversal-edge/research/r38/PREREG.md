# Round 38: ML together with stretch Z, Saudi and US (pre-registered 2026-10-30, before any result of this round)

User request: "Test ML with Z score, backtest and walk forward, for Saudi stocks and US."
Already known (not re-decided here): round 27 - a ranker that also sees Z features (M1) did not beat M0 on IC; round 28 - Z swing with
ML >= 0.5 chosen, a win-probability model on dips (AUC 0.61/0.56) not adopted; round 34-36 - US Z dips: timing edge only.
This round asks the questions again on the current rule (daily + weekly Z, market-momentum gate) and with walk-forward ML on US stocks.

## Common mechanics
Signal at the close of day t, buy at the open of t+1, sell at the open 40 sessions later, no stop. One open trade per stock (a new signal
while held is ignored). Costs: Saudi 0.40% round trip, US 0.10%. Every ML score is walk-forward: a model scoring year Y is trained only on
data that was known before 1 January of Y (rankers: targets ending at least 22 sessions before; dip models: trades that had exited).
Benchmark for every trade list: a random eligible stock (Saudi: liquid, 60-day median value >= SAR 3m) bought and sold on the same days,
same costs (mean of 20 draws per signal day). US also: SPY on the same days.
Saudi eras: DESIGN 2013-19, CONFIRM 2020-26, recent 2023-26 (the 2001-12 library is not available after the machine reset).
US eras (us100 = 115 large caps, today's list, survivorship-biased): STRESS 2005-09, DESIGN 2010-17, CONFIRM 2018-26.

## Saudi
Base events: first daily close at stretch Z <= -2.62, or first weekly close (weeks end Thursday) at weekly stretch Z <= -2.08; liquid;
market model > 0; market momentum <= -1.18 (the shipped rule without its ML filter; the loss-maker rule is left out because accounts
exist only from 2023).
S1 ML filter ladder (M0 walk-forward rank): none, >= 0.3, >= 0.5 (current), >= 0.7, >= 0.85.
S2 Z-aware ranker: the same ladder with M1 (M0 features + the Z family, walk-forward) instead of M0.
S3 Dip model: walk-forward LightGBM classifier (win after costs) trained each year on all liquid first touches of daily Z <= -2.0
or weekly Z <= -1.6 in any market state, features = the 42 ranker features + Z family + 16 market features + market model + market
momentum + M0 rank + daily and weekly Z; logistic regression on the same features as a control. Applied to the current rule's events
(base + M0 >= 0.5): keep the half with the higher predicted chance.
Decisions:
- "ML helps the Z swing" if M0 >= 0.5 beats no filter by >= +1.0 pt per trade in both DESIGN and CONFIRM (>= 30 trades each).
- Another threshold (or M1) replaces M0 >= 0.5 only if it beats it by >= +1.0 pt per trade with a win rate at least as high in DESIGN
  and CONFIRM (>= 30 trades each) and is not worse in 2023-26.
- The dip model is added only if its kept half beats all rule events by >= +1.5 pts per trade and +5 pts win rate in DESIGN and
  CONFIRM (>= 30 trades each) and is not worse in 2023-26.

## US
U0 Walk-forward US ranker (round 35 design: LightGBM on 20 cross-sectional ranked features, target = 20-day forward rank, yearly refit
from 2005, trained on 2000 onwards).
Events: first daily close at stretch Z <= -1.67 or first weekly close (weeks end Friday) at weekly Z <= -1.13 (round 34 lines, not
refitted), two versions: (a) any market state, (b) only inside the US sell-off window (us100 market momentum <= -1.18).
U1 ML ladder as S1 on both versions. U2 dip model as S3 (US features: the 20 ranker features + Z + market momentum + SPY trend).
Decision: a US stock-level ML + Z rule is accepted only if its edge over random large caps bought on the same days is >= +1.0 pt per
trade in both DESIGN and CONFIRM (>= 30 trades each) and its average trade is >= 0 in STRESS (if it has >= 10 trades there).
Otherwise the US stays timing-only (sell-off window, SPY/QQQ dip).
