# Round 81 plan: the swing with and without Rebound Edge, and Rebound Edge alone (written 2026-11-14, before any run)
The user asked: show the result with and without Rebound Edge, and can I rely only on Rebound Edge.
Round 80 said Rebound Edge would not be tested as a filter. The user now asks for it, so it is tested here, once, as planned below.

## The rules compared (same engine, same sizes: one buy a day, 12 positions of 2.1%, 4.2% in deep weather, sold at stretch Z 0 or after 40 sessions)
- **A. The swing as it is** (without Rebound Edge).
- **B. The swing, strong edge only**: a swing candidate is bought only if its Rebound Edge is at the strong line or higher.
- **C. The swing, weak edge skipped**: a swing candidate is bought unless its Rebound Edge is below the weak line.
- **D. Rebound Edge alone, terminal version**: no buy zone, no weather rule, no separate gates. A stock is a candidate on the first
  close its Rebound Edge is at the strong line or higher; the highest edge first.
- **E. Rebound Edge alone, chart version**: the same with the formula that knows no gates (what TradingView shows).

## Which Rebound Edge
The TESTED copy, never the product copy: the formula fitted on other markets with trades ended by 2019 (M19), with the Saudi
adjustment fitted on Saudi 2013-19 (rules B, C, D) or without it (rule E). Lines: the tested copy's own thirds (weak / strong),
fixed in round 80. No line is tuned here.

## What is honest and what is not
- Saudi 2013-19: the Saudi adjustment was fitted on these years, so B, C, D are flattered there. E is not.
- Saudi 2020-26: the indicator had not seen these years, but I have looked at them in rounds 73, 78 and 80. Not a blind test.
- Other markets (64 market-eras): each market is traded with a formula fitted on the other markets only (rules A, B, E; there
  are no gates abroad, so D = E). This is the cleanest evidence here.

## Verdict (fixed now)
A rule is "better than the swing" only if, on Saudi 2013-19 AND 2020-26, growth is not lower, the worst drawdown is not higher by
more than 0.2 point, and the return per drawdown is higher; and abroad it beats the swing in at least 60% of the market-eras
where the two differ, sign test p <= 0.05. "Rely only on Rebound Edge" is answered yes only if D or E is better than the swing by
this rule. Every rule is reported, pass or fail.
