# Round 84 plan: 200 US stocks with the most options activity (written 2026-11-24, before any test run)

## Why
The user: "let us add 200 USA stocks. that high in options trade like nvda and aapl and tsla."

## The list (built before this plan; us200_list.json, pull_oi.py, classify.py)
Yahoo only. Every option contract on Yahoo's "Highest Open Interest" option screener (9,781 contracts with 10,000 or more open) and
on its "Most Actives" option screener (20,750 contracts by volume), pulled 2026-11-24 15:55 UTC (US session about 1 hour old, so the
volume half is one partial day). Underlyings kept: Yahoo type EQUITY, US exchange, US dollars; ranked by half their share of open
interest and half their share of contract volume; price at least $5, 1-month median dollar volume at least $20 million, one share
class per company. Top 200: 92% of the eligible stocks' options activity. ETFs (SPY, QQQ, IWM, TLT ...) and indexes are not stocks
and are left out. US-listed foreign companies (BABA, TSM, NU, PBR ...) are in: they trade in the US with US options.

## What is reported (description only: nothing here changes a rule or goes live)
On the 200 (prices from Yahoo, the same cleaning as the other markets, stocks with at least 3 years of history; market momentum = the
equal-weight average of the 200, as for every market), 2001-09, 2010-19, 2020-26, price-only (no ML rank, market model or accounts
exist for the US), idle money earning nothing, 0.4% round trip:
1. The Fable swing as tested abroad (round 78: line -2.5, storm or deep weather, one buy a day, 12 positions of 2.1% / 4.2%, sell at
   the first close with stretch Z at 0 or after 40 sessions).
2. The live plan's shape (round 72's A0: first close at -2.62 or weekly -2.08, market momentum -1.18 or lower, 5 x 5%, hold 40).
3. The equal-weight basket of the 200, held throughout (what simply owning them did).
4. Rebound Edge and Hold Edge (swing versions) on the 200's cases, scored by formulas fitted on the 23 foreign markets only (no US data):
   top third against bottom third, rank link against market momentum alone.

## The bias, stated now
The 200 are chosen by today's options activity. Options traders crowd into stocks that already rose a lot (NVDA, PLTR, MSTR, HOOD,
APP ...). Every number on this list is inflated by that choice, the basket most of all; a rule compared with the basket on the same
stocks is less affected but not free of it. A list picked in 2001 or 2010 would have held other names. No unbiased list exists in
Yahoo's data. These numbers describe; they cannot confirm anything.
