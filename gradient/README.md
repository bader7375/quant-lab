# Gradient

A personal growth system published as a claude.ai artifact:
https://claude.ai/artifact/AJgU5GzxXpamNw99NsJMuh

`gradient.html` is the whole app. It runs inside claude.ai and uses two platform capabilities:

- **db**: a private store (only the owner can read or write) holding pulses, briefs, forecasts,
  experiments, recall cards, dispatches and Claude's model of you.
- **sample**: calls Claude on the viewer's own account. The Update button sends your history and
  gets back a revised model and today's brief. Drill feedback, experiment reading and Spar use it too.

To change the app, ask Claude Code to edit `gradient.html` and republish it to the same URL.
Your data lives in the store, not in the file, so republishing never erases it.
