# Round 54 results: split exit + deep window (pre-registered in PREREG.md; r54.py, r54.out)

| version | Saudi 13-19 | Saudi 20-26 | US 05-09 | US 10-17 | US 18-26 | India 05-09 | India 10-17 | India 18-26 | GCC 11-17 | GCC 18-26 | beats base | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 0.28 | 0.34 | -0.09 | 0.12 | 0.48 | -0.02 | 0.96 | 0.18 | 0.72 | 0.03 | | |
| K2 split | 0.28 | 0.38 | -0.04 | 0.16 | 0.51 | 0.01 | 0.78 | 0.16 | 0.59 | 0.06 | 7/10 | GENERAL |
| split + deep window -2.53 | 0.33 | 0.42 | 0.07 | 0.30 | 0.20 | 0.21 | 0.29 | 0.19 | 0.42 | 0.01 | 6/10 | not general |
| split + deep window -1.85 | 0.46 | 0.43 | -0.07 | 0.04 | 0.40 | 0.13 | 0.43 | 0.22 | 0.70 | 0.05 | 6/10 | not general |

Neither combination is general, and neither beats the split exit alone in at least 6 of 10 (6 and 5). The deep window helps in Saudi and in the 2008-type bear markets, but costs a lot in strong periods (US 2018-26, India 2010-17, GCC 2011-17).

**The split exit alone stays the one general change.**
