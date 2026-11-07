# Round 43 results: rules from the books and papers on the live Z swing (pre-registered in PREREG.md)
r43.py / r43.out; sleeve = at most 5 positions x 5%; ratio = return per year / maximum drawdown.

| rule (source) | 2013-19 win / avg | sleeve %/y, ratio | 2020-26 win / avg / worst5 | sleeve | 2023-26 sleeve ratio |
|---|---|---|---|---|---|
| baseline (next open, hold 40) | 84% / +19.5% | +2.8, 0.55 | 72% / +7.6% / -12.3% | +1.7, 0.31 | 0.26 |
| K1 buy at the signal close (Connors) | 81% / +17.9% | +2.6, 0.44 | 72% / +7.0% / -12.6% | +1.4, 0.26 | 0.26 |
| K2 Turtle Soup + its stop (Connors & Raschke) | 46% / +16.1% (39 trades) | +3.1, 0.54 | 73% / +10.0% / -6.0% (37) | +1.2, 0.37 | n<10 |
| K3 buy close when RSI(2) < 5 (Connors) | 79% / +17.0% | +2.1, 0.35 | 78% / +9.3% / -10.0% | +1.2, 0.29 | 0.39 |
| F1 only above the 200-day average (Connors) | fewer than 10 trades: Z-swing stocks are almost never above it | | | | |
| F2 no limit-down day in 20 sessions (Bulkowski) | 69% / +10.4% | +1.6, 0.26 | 81% / +10.6% / -11.4% | +1.0, 0.18 | 0.21 |
| F3 market volatility high (Nagel) | 83% / +19.7% | +2.8, 0.54 | 73% / +7.8% | +1.6, 0.31 | 0.29 |
| F4 not at a 52-week low (George & Hwang) | 81% / +17.1% | +3.2, 0.66 | 76% / +7.0% | +1.2, 0.28 | 0.03 |
| X1 exit: close above the 5-day average (Connors) | 64% / +2.0% | +0.1, 0.01 | 60% / +0.8% | +0.8, 0.25 | 0.52 |
| X2 exit: RSI(2) above 70 (Connors) | 68% / +2.8% | +0.4, 0.08 | 66% / +1.9% | +1.4, 0.41 | 0.81 |
Choice: family K and X - nothing beats the baseline in 2013-19; family F pick F4 fails 2020-26 (ratio 0.28 vs 0.31). NOTHING ADOPTED.
F3 changes almost nothing: the market-momentum gate already trades only in stressed markets (Nagel's finding is already in the rule).
Pattern across rounds 41 and 43: quick exits (Z back to 0, RSI(2) > 70) are the worst choice in 2013-19 and the best in 2023-26.

Context (split43.py, not a new decision; both exits already seen in both periods): each position split in two halves, one held 40
sessions and one sold when stretch Z is back at 0 (two sub-sleeves of 5 x 2.5%):
| exit | 2013-19 return, DD, ratio | 2020-26 | 2023-26 |
|---|---|---|---|
| hold 40 (live) | +2.8%, 5.1%, 0.55 | +1.7%, 5.6%, 0.31 | +1.5%, 5.6%, 0.26 |
| Z back to 0 | +1.7%, 5.5%, 0.32 | +2.8%, 4.4%, 0.64 | +3.2%, 2.0%, 1.60 |
| split half / half | +2.3%, 5.1%, 0.45 | +2.3%, 4.4%, 0.51 | +2.3%, 2.7%, 0.85 |
The split has the best worst-period ratio (0.45 vs 0.31 and 0.32) and the same return in every period: the robust choice if the next
years could look like either regime.
