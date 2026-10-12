"use strict";
/* Human: "what players at a given rating play here", from the Maia-1 networks (CSSLab, GPL-3.0 weights) running in a
   Web Worker (engines/maia/worker.js). One network is loaded at a time; asking for another rating swaps it.
   Every call resolves to null when Maia is unavailable, so callers always have a Stockfish-only path. */
const HUMAN_RATINGS = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900];
const Human = {
  w: null, ok: false, failed: false, rating: null, loading: null, seq: 0, pending: new Map(), chain: Promise.resolve(),
  netFor(r) { return HUMAN_RATINGS.reduce((a, b) => (Math.abs(b - r) < Math.abs(a - r) ? b : a)); },
  start() {
    if (this.w || this.failed) return;
    try { this.w = new Worker("engines/maia/worker.js"); } catch { this.failed = true; return; }
    this.w.onmessage = (e) => {
      const m = e.data || {};
      if (m.type === "ready") { this.ok = true; if (this.loading) { this.loading.res(true); this.loading = null; } return; }
      const p = this.pending.get(m.id);
      if (m.type === "error" && m.id == null && this.loading) { this.loading.res(false); this.loading = null; return; }
      if (!p) return; this.pending.delete(m.id);
      if (m.type === "result") p.res({ policy: m.policy, value: m.value, ms: m.ms, rating: this.rating }); else p.res(null);
    };
    this.w.onerror = () => { this.failed = true; this.ok = false; if (this.loading) { this.loading.res(false); this.loading = null; } for (const p of this.pending.values()) p.res(null); this.pending.clear(); };
  },
  /* Load the network nearest to `rating` (no-op if it is already loaded). Resolves true/false. */
  use(rating) {
    const r = this.netFor(rating);
    const job = () => {
      this.start(); if (this.failed) return false;
      if (this.rating === r && this.ok) return true;
      return new Promise((res) => {
        const t = setTimeout(() => { if (this.loading) { this.loading = null; res(false); } }, 30000);
        this.loading = { res: (v) => { clearTimeout(t); if (v) this.rating = r; res(v); } };
        this.ok = false; this.w.postMessage({ type: "init", rating: r });
      });
    };
    const p = this.chain.then(job, job); this.chain = p.catch(() => {}); return p;
  },
  /* Move probabilities for the side to move: {policy: [{uci, san, p}], value, rating} or null. */
  async predict(startFen, movesUci, rating) {
    if (!(await this.use(rating))) return null;
    return new Promise((res) => {
      const id = ++this.seq; const t = setTimeout(() => { if (this.pending.delete(id)) res(null); }, 15000);
      this.pending.set(id, { res: (v) => { clearTimeout(t); res(v); } });
      this.w.postMessage({ type: "eval", id, startFen, moves: movesUci });
    });
  },
};
