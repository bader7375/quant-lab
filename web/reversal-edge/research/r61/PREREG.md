# Round 61 plan (written 2026-11-06 before any result of this round): three new ways to read the stretch Z for Z-swing trades
User: "Let's be creative like this and create something help with the Z score."

Stretch Z = average of z10, z20, z60 (each = the move over k sessions in units of the stock's own volatility). Three helpers,
each with its direction fixed here, before looking at results:

H1 Z curve (the shape of the stretch). slope = z10 - z60 at the signal close.
   "Shock" (z10 far below z60: a sudden fall in a stock that was not already falling) vs "grind" (a long decline).
   Hypothesis: shocks rebound better (overreaction), grinds keep falling. Keep the shock side: slope <= DESIGN median.
H2 Z rebound memory (the stock's own record). Average 20-session excess return (next open to the open 20 sessions later,
   minus the average liquid stock) after the stock's own earlier stretch-Z dips (first close <= -2.0, liquid), counting only
   dips whose 20 sessions had ended by the signal; shrunk toward 0: sum / (count + 5).
   Hypothesis: stocks that rebounded after earlier dips rebound again. Keep: memory > DESIGN median.
H3 Capitulation volume. Traded value on the signal day / median traded value of the previous 60 sessions.
   Hypothesis: heavy selling volume marks capitulation and a better rebound. Keep: ratio >= DESIGN median.

## Tests (each helper separately)
A. Z swing trades: live triggers and filters (daily -2.62 / weekly -2.08 first touch, ranker C >= 50%, market model > 0,
   market momentum <= -1.18, liquid), next open, hold 40, 0.4% costs. Gap = kept side minus the other side, per trade.
   DESIGN 2013-19, CONFIRM 2020-26; 95% interval for CONFIRM from a bootstrap over entry weeks.
B. Price-only stretch-Z dips (first close <= -2.0, liquid), same trade (larger sample).
C. Live sleeve 5 slots x 5%: live vs filtered, return / max drawdown, DESIGN, CONFIRM, 2023-26.
D. Robustness: thresholds at the DESIGN 40th and 60th percentiles; correlation with the ML rank at the signals; US sell-off
   swing (H1 and H3 where US data allow), same direction, reported.

## A helper "helps" only if all hold
DESIGN gap >= +2 pts and CONFIRM gap >= +2 pts in the stated direction; B points the same way in both periods; the sleeve's
return/drawdown ratio is higher than live in DESIGN and CONFIRM; 2023-26 return not lower and drawdown not deeper; the CONFIRM gap
stays positive at the 40th and 60th percentile thresholds. Passing helpers become options for the user (no live change without
consent). The terminal gets a view of whatever passes; a helper that fails can still be shown as context only if it is labelled so.

## Addendum 61b (written after the Saudi results above, before any US result): out-of-sample test of the two reversed patterns
The Saudi data pointed AGAINST H1 and H3 (grind dips and quiet dips did better). Those reversed directions were chosen by
looking at Saudi results, so they can only be confirmed on data they have not seen: the US sell-off swing (115 US large caps,
2005-2026, the round-38 rule: first close at the US stretch-Z lines while the US sell-off window is open, hold 40, 0.1% costs).
- H1r "grind beats shock": keep slope (z10 - z60) > median.   H3r "quiet dip": keep traded-value ratio (signal day vs prior
  60-session median) < median. Medians = the US signals' own medians over 2005-2026 (no outcomes used).
- Confirmed in the US if: the kept side beats the other side per trade by >= +2 pts over 2005-2026 AND is ahead in at least
  2 of the 3 US eras (2005-09, 2010-17, 2018-26), AND the US sleeve (5 x 5%) return/drawdown ratio is higher in at least 2 of 3 eras.
