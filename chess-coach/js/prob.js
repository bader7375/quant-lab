"use strict";
/* Probabilities: "your chances at your level" (human estimate from the engine evaluation), engine WDL,
   expected score, and move classes by expected-score drop.
   The human model is fitted on rated Lichess games (data/models/odds.json, tools/odds/fit_odds.py, ODDS_REPORT.md): an ordered
   logit per rating band and game phase, in Stockfish 17.1 centipawns. Bands under 1500 are extrapolated (no data there).
   Without that file it falls back to a PROVISIONAL curve (Lichess win% + a small draw rate). */
const Prob = {
  model: { kind: "provisional", k: 0.00368208, drawBase: 0.06 },
  band: null, // the student's level (set from the journey settings); null = the model's default band
  async load() { try { const r = await fetch("data/models/odds.json"); if (r.ok) this.model = await r.json(); } catch {} },
  /* Context for one position: the student's band and the game phase (the fitted model has per-phase parameters). */
  ctx(fen, ply) {
    let phase = null;
    try { if (fen && typeof Facts !== "undefined") { const p = fen.split(" "); phase = Facts.phaseOf(Facts.grid(new Chess(fen)), ply ?? ((+p[5] || 1) - 1) * 2 + (p[1] === "b" ? 1 : 0)); } } catch {}
    return { band: this.band, phase };
  },
  extrapolated(band) { const e = this.model.meta && this.model.meta.bands_extrapolated; const b = band ?? this.band ?? this.model.defaultBand; return !!(e && e.some((x) => Math.abs(x - b) < 50)); },
  /* Human-level [win, draw, loss] for White (0..1), from Stockfish 17.1 cp (White's view).
     A forced mate found by the engine (|cp| >= 9000) counts as +-clip: players at these levels often miss mates.
     Only checkmate on the board (|cp| >= 10000) is certain. */
  human(cpWhite, ctx = {}) {
    if (cpWhite == null) return [0.5, 0, 0.5];
    const M = this.model;
    if (M.kind === "ordered-logit") {
      if (Math.abs(cpWhite) >= 10000) return cpWhite > 0 ? [1, 0, 0] : [0, 0, 1];
      if (ctx.fen && !ctx.phase) ctx = Object.assign({}, ctx, this.ctx(ctx.fen, ctx.ply));
      const band = ctx.band || this.band || M.defaultBand; const b0 = (M.bands && (M.bands[band] || M.bands[nearestBand(M, band)])) || M;
      const b = (ctx.phase && b0.phases && b0.phases[ctx.phase]) || b0;
      const cp = Math.max(-M.clip, Math.min(M.clip, cpWhite)); const z = b.a * cp / 100 + (b.c || 0);
      const s = (x) => 1 / (1 + Math.exp(-x));
      const pl = s(b.t1 - z), pw = 1 - s(b.t2 - z); const pd = Math.max(0, 1 - pl - pw);
      return [pw, pd, pl];
    }
    if (Math.abs(cpWhite) >= 9000) return cpWhite > 0 ? [1, 0, 0] : [0, 0, 1];
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

/* The odds bar: White's win / draw / Black's win. The main bar follows the setting (default: the human-level estimate);
   the other view is shown as a secondary line. */
const oddsMode = () => (typeof J !== "undefined" && J.state && J.state.settings && J.state.settings.odds) || "human";
function oddsBarHtml(cpWhite, wdlEngine, { label = "", prevCp = null, mover = null, fen = null } = {}) {
  const ctx = fen ? Prob.ctx(fen) : {}; const hum = Prob.human(cpWhite, ctx); const eng = Prob.engine(wdlEngine); const pct = (x) => Math.round(100 * x);
  const useEng = oddsMode() === "engine" && !!eng; const [w, d, l] = useEng ? eng : hum;
  let delta = "";
  if (prevCp != null && mover) {
    const b = Math.round(Prob.esFor(prevCp, mover, ctx)), a = Math.round(Prob.esFor(cpWhite, mover, ctx));
    delta = `<span class="odds-delta">فرص ${mover === "w" ? "الأبيض" : "الأسود"}${useEng ? " بمستواك" : ""}: <bdi class="mono">${b}%</bdi> ← <bdi class="mono">${a}%</bdi></span>`;
  }
  const lvl = Prob.band || (Prob.model.defaultBand ?? "");
  const humLabel = `${label || "تقدير لفرص لاعبين بمستواك"}${lvl ? ` (~${lvl})` : ""}${Prob.model.kind === "provisional" ? " (نموذج مؤقت)" : Prob.extrapolated() ? " (مستقرأ: بيانات اللاعبين تبدأ من 1500)" : ""}`;
  const note = useEng
    ? `مع لعب مثالي من الطرفين (Stockfish) · ${humLabel}: <bdi class="mono">${pct(hum[0])}/${pct(hum[1])}/${pct(hum[2])}</bdi>`
    : `${humLabel}${eng ? ` · مع لعب مثالي (المحرك): <bdi class="mono">${pct(eng[0])}/${pct(eng[1])}/${pct(eng[2])}</bdi>` : ""}`;
  return `<div class="odds" role="img" aria-label="فرص الأبيض ${pct(w)}٪، تعادل ${pct(d)}٪، فرص الأسود ${pct(l)}٪">
    <div class="odds-bar"><i class="ow" style="width:${(100 * w).toFixed(1)}%"></i><i class="od" style="width:${(100 * d).toFixed(1)}%"></i><i class="ol" style="width:${(100 * l).toFixed(1)}%"></i></div>
    <div class="odds-legend"><span><b class="sw"></b>الأبيض <bdi class="mono">${pct(w)}%</bdi></span><span><b class="sd"></b>تعادل <bdi class="mono">${pct(d)}%</bdi></span><span><b class="sl"></b>الأسود <bdi class="mono">${pct(l)}%</bdi></span>${delta}</div>
    <div class="note odds-note">${note}</div></div>`;
}
