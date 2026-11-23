# Round 53 results: which Z-swing tweaks are general? (pre-registered in PREREG.md; r53.py, r53.out)
Each market's own base rule (Saudi live; US sell-off swing; India and GCC with Saudi lines, no ML), hold 40, 5 x 5%. Ten market-eras.
Ratio = sleeve return per year / max drawdown; * = beats base.

| tweak | Saudi 13-19 | Saudi 20-26 | US 05-09 | US 10-17 | US 18-26 | India 05-09 | India 10-17 | India 18-26 | GCC 11-17 | GCC 18-26 | beats | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 0.28 | 0.34 | -0.09 | 0.12 | 0.48 | -0.02 | 0.96 | 0.18 | 0.72 | 0.03 | | |
| K1 shadow turn gate (v2) | 0.34* | 0.57* | -0.10 | 0.33* | 0.15 | 0.08* | 0.51 | 0.25* | 0.41 | 0.03 | 5/10 | not general |
| **K2 split exit** | 0.28* | 0.38* | -0.04* | 0.16* | 0.51* | 0.01* | 0.78 | 0.16 | 0.59 | 0.06* | **7/10** | **GENERAL** |
| K3 deep window (momentum <= -2.53) | 0.38* | 0.41* | 0.07* | 0.19* | 0.18 | 0.16* | 0.42 | 0.27* | 0.48 | -0.01 | 6/10 | not general |
| K4 hold 60 | 0.36* | 0.24 | -0.00* | 0.28* | 0.29 | 0.03* | 0.53 | 0.16 | 0.46 | 0.03 | 4/10 | not general |
| K5 sell at Z back to 0 | 0.27 | 0.43* | 0.01* | 0.20* | 0.40 | 0.03* | 0.51 | 0.12 | 0.42 | 0.08* | 5/10 | not general |
| K6 10 x 2.5% | 0.31* | 0.32 | -0.04* | 0.15* | 0.49* | 0.04* | 0.91 | 0.14 | 0.64 | 0.02 | 5/10 | not general |
| K7 12% stop order | 0.46* | 0.23 | -0.01* | 0.07 | 0.48 | 0.14* | 0.82 | 0.17 | 0.62 | 0.01 | 3/10 | not general |

**Only the split exit is general.** It beats base in 7 of 10 market-eras, including both Saudi eras. Its return is at least 90% of base in 6 of 10.

The effect is modest: it mostly lowers drawdown; returns are a little lower in strong periods:

| market-era | base return | split-exit return |
|---|---|---|
| India 2010-17 | +3.4%/yr | +2.7%/yr |
| GCC 2011-17 | +5.5%/yr | +4.3%/yr |

The turn gate (v2's key part) helps in 5 of 10 market-eras: both Saudi eras, US 2010-17, India 2005-09 and India 2018-26. Every tweak hurts in the two strongest base periods (India 2010-17, GCC 2011-17), where buying every early signal paid.
