# Round 59 plan (written 2026-11-06 before any result was computed): do the signals work better in companies with better financials?
User: "Let's use current data Yahoo. And test during the last two years. Signals better with better financial or not."

## Data (real, point-in-time)
Yahoo annual accounts, FY2022-FY2025 only (quarterly data starts 2025 and is not used). Each fiscal year is usable 91 days after
its fiscal year end (the live rule's loss filter uses the same lag). Share counts are corrected for bonus issues/splits with Yahoo's
split events. Banks and other financials lack some fields; their scores use the items that exist.

## Financial measures (latest usable accounts at the signal date)
Primary - F-score (Piotroski 2000), 9 yes/no items, FY t vs FY t-1: net income > 0; operating cash flow > 0; return on assets up;
cash flow > net income; long-term debt / assets down; current ratio up; no new shares (split-adjusted); gross margin up; sales / assets up.
Scaled to 9 when items are missing (at least 5 needed). Strong = 6 or more, weak = 4 or less (5 = middle, reported).
Secondary (descriptive, many comparisons, so single "significant" results are expected by chance): profitable vs loss; ROE thirds;
earnings up vs down; debt / equity thirds (non-financials); earnings yield thirds (net income / market value at the signal);
cash flow > net income.

## Signals, last two years (entries 2024-11-06 .. 2026-11-05; only trades whose holding period has ended)
A. Z swing: live triggers and filters (daily -2.62 / weekly -2.08 first touch, ML rank >= 50% with ranker C, market model > 0,
   market momentum <= -1.18, liquid), WITHOUT the profit filter; next open, hold 40 sessions, 0.4% costs.
B. Price-only stretch-Z dips: first close <= -2.0, liquid; same trade mechanics (larger sample).
C. ML ranker C top 10% each 5th session; next open to the open 20 sessions later, minus the average liquid stock.
D. Reference: all liquid stocks, same 20-session excess (is financial strength a return factor by itself?).

## Test and decision rule
Statistic: strong minus weak average net return, with a 95% interval from a bootstrap over entry weeks (signals cluster in sell-offs).
"Better financials -> better signals" = YES only if (1) B's interval is above zero, (2) A and C point the same way, and
(3) B points the same way in the earlier piece (F-score usable from 2024-04: entries 2024-04-01 .. 2024-11-05).
Otherwise: NO or NOT PROVEN. Any change to the live rule needs the user's consent; with only ~2 years of accounts a YES would at
most justify showing the score in the daily list, not a hard filter, unless the gap is large and holds in A, B and C.
