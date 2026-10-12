// Merge a demo game's analysis with its narration, verify every chess reference, write the app's demo file.
// usage: node tools/build_demo.mjs analysis.json narration.json out.json
//
// Grounding rule: every bracketed move group in the narration, e.g. [Qxb7 Qb4+], must be a prefix of one of:
//   the engine lines before this move, the engine lines after it, the opponent's threat (null-move search) before
//   or after it, the actual game continuation from this ply or any of the next 6 plies, or an extra line listed under
//   "verify" (which this tool evaluates with Stockfish). A group that is not valid alone may continue the previous
//   group in the same text (for a candidate's "why", the chain starts with the candidate itself).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { Pool } from './sfpool.mjs';
const require = createRequire(import.meta.url);
const root = path.join(path.dirname(new URL(import.meta.url).pathname), '..');
const { Chess } = require(path.join(root, 'chess.js'));
const Facts = require(path.join(root, 'js/facts.js'));
const [, , aFile, nFile, outFile] = process.argv;
const A = JSON.parse(fs.readFileSync(aFile, 'utf8'));
const N = JSON.parse(fs.readFileSync(nFile, 'utf8'));
const pool = new Pool(4);
const norm = (s) => s.replace(/[+#!?]/g, '');
const nullFen = (fen) => { const p = fen.split(' '); p[1] = p[1] === 'w' ? 'b' : 'w'; p[3] = '-'; return p.join(' '); };
function uciToSan(fen, pv) { const g = new Chess(fen); const out = []; for (const u of pv || []) { const m = g.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); if (!m) break; out.push(m.san); } return out; }
function legalSeq(fen, sans) { const g = new Chess(fen); const out = []; for (const s of sans) { const m = g.move(s, { sloppy: true }); if (!m) return null; out.push(m.san); } return { sans: out, fen: g.fen() }; }
const P = A.plies; const problems = [];
const LIMITS = { does: 240, think: 460, plan: 220, habit: 170, intent: 280, note: 280, why: 230 };

// 1. extra lines to verify, evaluated with Stockfish
const extra = {};
for (const [k, lines] of Object.entries(N.verify || {})) {
  extra[k] = [];
  for (const line of lines) {
    const seq = legalSeq(P[+k].fenBefore, line.split(' '));
    if (!seq) { problems.push(`ply ${k}: verify line "${line}" is illegal`); continue; }
    const a = await pool.analyse(seq.fen, { depth: 18, multipv: 1 });
    const end = a.lines[0] ? { cp: a.lines[0].cpWhite, wdl: a.lines[0].wdlWhite } : { cp: null, wdl: null };
    extra[k].push({ san: seq.sans, ...end });
  }
}
// 2. candidates: legal, with an evaluation
for (const [k, n] of Object.entries(N.plies)) {
  for (const c of n.cands || []) {
    const p = P[+k]; const seq = legalSeq(p.fenBefore, [c.san]);
    if (!seq) { problems.push(`ply ${k}: candidate ${c.san} is illegal`); continue; }
    c.san = seq.sans[0];
    const inLines = p.lines.find((l) => norm(l.san[0]) === norm(c.san));
    if (inLines) { c.cp = inLines.cp; c.wdl = inLines.wdl; c.line = inLines.san.slice(0, 6); continue; }
    const g = new Chess(p.fenBefore); const m = g.move(c.san); const uci = m.from + m.to + (m.promotion || '');
    const a = await pool.analyse(p.fenBefore, { depth: 18, multipv: 1, searchmoves: [uci] });
    if (a.lines[0]) { c.cp = a.lines[0].cpWhite; c.wdl = a.lines[0].wdlWhite; c.line = uciToSan(p.fenBefore, a.lines[0].pv).slice(0, 6); }
  }
}
pool.close();
// 3. grounding check
function roots(k) {
  const R = []; const p = P[k], q = P[k + 1];
  for (const l of p.lines) R.push(l.san);
  if (q) for (const l of q.lines) R.push(l.san);
  if (p.threat) R.push(p.threat.san); if (q && q.threat) R.push(q.threat.san);
  for (let j = k; j <= Math.min(P.length - 1, k + 6); j++) R.push(P.slice(j).map((x) => x.san));
  for (const e of extra[k] || []) R.push(e.san);
  if (p.after && p.after.line) R.push(p.after.line);
  return R.map((r) => r.map(norm));
}
const isPrefix = (T, R) => T.length <= R.length && T.every((t, i) => t === R[i]);
function checkText(k, field, text, chain0) {
  if (!text) return;
  if (LIMITS[field] && text.length > LIMITS[field]) problems.push(`ply ${k} ${field}: ${text.length} chars (limit ${LIMITS[field]})`);
  const outside = text.replace(/\[[^\]]*\]/g, '');
  if (/[+-]\d+\.\d|\d+\s*‰|\bcp\b/i.test(outside)) problems.push(`ply ${k} ${field}: engine numbers in text`);
  const R = roots(k); let chain = chain0 ? [norm(chain0)] : [];
  for (const m of text.matchAll(/\[([^\]]+)\]/g)) {
    const T = m[1].trim().split(/\s+/).map(norm);
    const cont = [...chain, ...T];
    if (chain.length && R.some((r) => isPrefix(cont, r))) { chain = cont; continue; } // continuing the line being described wins
    if (R.some((r) => isPrefix(T, r))) { chain = T; continue; }
    problems.push(`ply ${k} ${field}: [${m[1]}] is not grounded`);
  }
}
for (const [k, n] of Object.entries(N.plies)) {
  for (const f of ['does', 'think', 'plan', 'habit', 'intent', 'note']) checkText(+k, f, n[f]);
  for (const c of n.cands || []) checkText(+k, 'why', c.why, c.san);
}
for (const f of ['intro', 'outro']) if (/\[/.test(N[f] || '')) problems.push(`${f}: no move brackets allowed here`);
// every narrated-side move needs does/think/plan; every opponent move needs an intent
P.forEach((p, i) => { const n = N.plies[i]; if (!n) return problems.push(`ply ${i}: no narration`); if (p.color === A.narrated) { for (const f of ['does', 'think', 'plan']) if (!n[f]) problems.push(`ply ${i}: missing ${f}`); } else if (!n.intent) problems.push(`ply ${i}: missing intent`); });

if (problems.length) { console.error('NARRATION CHECK FAILED:\n  ' + problems.join('\n  ')); process.exit(1); }

// 4. compact output for the app
const slimFacts = (f) => ({ phase: f.phase, mat: f.material.diff, w: { hang: f.w.hanging.map((h) => h.type + h.sq), dev: f.w.dev.developed, castled: f.w.dev.castled, kc: f.w.dev.kingCenter, katt: f.w.king ? f.w.king.attackers : 0, cp: f.w.center.pawns }, b: { hang: f.b.hanging.map((h) => h.type + h.sq), dev: f.b.dev.developed, castled: f.b.dev.castled, kc: f.b.dev.kingCenter, katt: f.b.king ? f.b.king.attackers : 0, cp: f.b.center.pawns } });
const sans = P.map((p) => p.san);
const out = {
  id: A.id, chapter: A.chapter, kind: A.kind, narrated: A.narrated, white: A.white, black: A.black, event: A.event, start: A.start, engine: A.engine, depth: A.depth,
  title: N.title, intro: N.intro, outro: N.outro,
  checklist: { w: Facts.openingChecklist(sans, 'w', A.start), b: Facts.openingChecklist(sans, 'b', A.start) },
  plies: P.map((p, i) => ({
    san: p.san, uci: p.uci, color: p.color, fenBefore: p.fenBefore, fen: p.fen,
    lines: p.lines.map((l) => ({ san: l.san.slice(0, 8), cp: l.cp, wdl: l.wdl })),
    threat: p.threat ? { san: p.threat.san, cp: p.threat.cp } : null,
    played: p.played ? { cp: p.played.cp, wdl: p.played.wdl } : null,
    after: p.after, facts: slimFacts(p.factsAfter), before: slimFacts(p.factsBefore),
    n: N.plies[i], extra: extra[i] || null,
  })),
};
fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(out));
console.log(`OK: ${P.length} plies, every bracketed move grounded. ${fs.statSync(outFile).size} bytes -> ${outFile}`);
process.exit(0);
