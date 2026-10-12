"use strict";
/* Probabilities: "your chances at your level" (human estimate from the engine evaluation), engine WDL,
   expected score, and move classes by expected-score drop.
   The human model starts PROVISIONAL (Lichess win% curve + a small beginner draw rate) and is replaced by the
   model fitted on rated human games in step 4 (data/models/odds.json). */
const Prob = {
  model: { kind: "provisional", k: 0.00368208, drawBase: 0.06 },
  async load() { try { const r = await fetch("data/models/odds.json"); if (r.ok) this.model = await r.json(); } catch {} },
  /* Human-level [win, draw, loss] for White (0..1), from Stockfish cp (White's view). */
  human(cpWhite, ctx = {}) {
    if (cpWhite == null) return [0.5, 0, 0.5];
    if (Math.abs(cpWhite) >= 9000) return cpWhite > 0 ? [1, 0, 0] : [0, 0, 1];
    const M = this.model;
    if (M.kind === "ordered-logit") {
      // P(Black wins) = s(t1 - z), P(White wins) = 1 - s(t2 - z), z = a*cp (+ phase/band terms)
      const band = ctx.band || M.defaultBand; const b = (M.bands && (M.bands[band] || M.bands[nearestBand(M, band)])) || M;
      const cp = Math.max(-M.clip, Math.min(M.clip, cpWhite)); const z = b.a * cp / 100 + (b.c || 0);
      const s = (x) => 1 / (1 + Math.exp(-x));
      const pl = s(b.t1 - z), pw = 1 - s(b.t2 - z); const pd = Math.max(0, 1 - pl - pw);
      return [pw, pd, pl];
    }
    const cp = Math.max(-2000, Math.min(2000, cpWhite));
    const wc = 2 / (1 + Math.exp(-M.k * cp)) - 1; const es = (wc + 1) / 2;
    const d = M.drawBase * (1 - Math.abs(wc));
    const w = Math.max(0, es - d / 2); return [w, d, Math.max(0, 1 - w - d)];
  },
  engine(wdlWhite) { return wdlWhite ? wdlWhite.map((x) => x / 1000) : null; },
  es(wdl) { return wdl[0] + wdl[1] / 2; },
  /* Expected score (0..100) for `side` given White-view cp. */
  esFor(cpWhite, side, ctx) { const e = 100 * this.es(this.human(cpWhite, ctx)); return side === "w" ? e : 100 - e; },
  classify(before, after) {
    const drop = Math.max(0, before - after);
    let c = drop <= 2 ? "excellent" : drop <= 5 ? "good" : drop <= 10 ? "inaccuracy" : drop <= 20 ? "mistake" : "blunder";
    if ((before >= 97 && after >= 97) || (before <= 3 && after <= 3)) c = drop <= 2 ? "excellent" : "good"; // the result was already decided
    return { cls: c, drop: Math.round(drop) };
  },
};
function nearestBand(M, band) { const ks = Object.keys(M.bands || {}).map(Number); return ks.sort((a, b) => Math.abs(a - band) - Math.abs(b - band))[0]; }
const CLASS_AR = { excellent: "ممتازة", good: "جيدة", inaccuracy: "غير دقيقة", mistake: "خطأ", blunder: "خطأ فادح" };

/* The odds bar: White's win / draw / Black's win, with the engine's view as a secondary line. */
function oddsBarHtml(cpWhite, wdlEngine, { label = "", prevCp = null, mover = null } = {}) {
  const [w, d, l] = Prob.human(cpWhite); const pct = (x) => Math.round(100 * x);
  const eng = Prob.engine(wdlEngine);
  let delta = "";
  if (prevCp != null && mover) {
    const b = Math.round(Prob.esFor(prevCp, mover)), a = Math.round(Prob.esFor(cpWhite, mover));
    delta = `<span class="odds-delta">فرص ${mover === "w" ? "الأبيض" : "الأسود"}: <bdi class="mono">${b}%</bdi> ← <bdi class="mono">${a}%</bdi></span>`;
  }
  return `<div class="odds" role="img" aria-label="فرص الأبيض ${pct(w)}٪، تعادل ${pct(d)}٪، فرص الأسود ${pct(l)}٪">
    <div class="odds-bar"><i class="ow" style="width:${(100 * w).toFixed(1)}%"></i><i class="od" style="width:${(100 * d).toFixed(1)}%"></i><i class="ol" style="width:${(100 * l).toFixed(1)}%"></i></div>
    <div class="odds-legend"><span><b class="sw"></b>الأبيض <bdi class="mono">${pct(w)}%</bdi></span><span><b class="sd"></b>تعادل <bdi class="mono">${pct(d)}%</bdi></span><span><b class="sl"></b>الأسود <bdi class="mono">${pct(l)}%</bdi></span>${delta}</div>
    <div class="note odds-note">${label || "تقدير لفرص لاعبين بمستواك"}${Prob.model.kind === "provisional" ? " (نموذج مؤقت)" : ""}${eng ? ` · مع لعب مثالي (المحرك): <bdi class="mono">${pct(eng[0])}/${pct(eng[1])}/${pct(eng[2])}</bdi>` : ""}</div></div>`;
}
