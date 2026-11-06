"use strict";
/* "What the engine thinks": Stockfish's line after a move, five plies deep, as numbered arrows 1-5 on the board and a
   numbered list that says what each move does, then where the line ends (material, chances). The line can also be played
   on the board step by step, and "back to my position" restores the board exactly as it was. Computed in the page. */
function stepWhy(fen, san, mine) {
  const g = new Chess(fen); const m = g.move(san, { sloppy: true }); if (!m) return [];
  const N = Facts.NAME_AR; const out = [];
  if (mine) out.push(...bestMoveWhy(fen, m.san, m.from + m.to + (m.promotion || ""), null));
  else {
    if (m.captured) out.push(`يأخذ ${N[m.captured]} على ${m.to}.`);
    if (m.san.includes("#")) out.push("كش مات.");
    else if (m.san.includes("+")) out.push("كش.");
    const before = new Set(Facts.hanging(Facts.grid(new Chess(fen)), m.color).map((h) => h.sq));
    if (before.has(m.from) && !Facts.hanging(Facts.grid(g), m.color).some((h) => h.sq === m.to)) out.push(`ينقذ ${N[m.piece]} الذي كان مهدَّدًا.`);
  }
  const tags = Tech.tagsOf(fen, m.from + m.to + (m.promotion || ""));
  for (const t of tags) if (TAG_AR[t] && t !== "check") out.push(mine ? TAG_AR[t] : TAG_AR[t].replace("تقنية: ", "فكرة الخصم: "));
  if (!out.length) out.push(mine ? "نقلة تحسّن الموقف وتحضّر الخطوة التالية." : "أفضل رد عند Stockfish.");
  return [...new Set(out)];
}

/* Build the line: the move, then Stockfish's best play for both sides (up to 5 plies). */
async function engineLine(fen, uci, plies = 5) {
  const g = new Chess(fen); const me = g.turn(); const first = g.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci[4] || "q" }); if (!first) return null;
  const a = await Engine.analyse(g.fen(), { depth: 15, movetime: 1500 });
  const sans = [first.san, ...pvToSan(g.fen(), a.lines[0] ? a.lines[0].pv : [], plies - 1)];
  const steps = []; const h = new Chess(fen);
  for (const s of sans) { const f = h.fen(); const m = h.move(s, { sloppy: true }); if (!m) break; steps.push({ san: m.san, uci: m.from + m.to, fenBefore: f, fenAfter: h.fen(), mine: m.color === me, why: stepWhy(f, m.san, m.color === me) }); }
  const pc = Prob.ctx(fen, 30); const before = await Engine.analyse(fen, { depth: 12, movetime: 800 });
  const end = a.lines[0] ? a.lines[0].cpWhite : null;
  const mat = (f) => { const x = Facts.material(Facts.grid(new Chess(f))); return me === "w" ? x.diff : -x.diff; };
  return { fen, me, steps, esNow: before.lines[0] ? Math.round(Prob.esFor(before.lines[0].cpWhite, me, pc)) : null, esEnd: end != null ? Math.round(Prob.esFor(end, me, pc)) : null,
    matGain: steps.length ? mat(steps[steps.length - 1].fenAfter) - mat(fen) : 0, mate: a.lines[0] && a.lines[0].mate != null ? -a.lines[0].mate : null };
}

/* The panel. board: the Board to draw on; restore() is called on "back to my position". */
async function ThinkPanel(el, board, fen, uci, { title = "ماذا يفكر المحرك؟", verdict = "لماذا هي ممتازة" } = {}) {
  const snap = { ...board.state }; const keep = { fen: snap.fen, last: snap.last, arrows: snap.arrows, marks: snap.marks, interactive: snap.interactive, orient: snap.orient, onMove: snap.onMove };
  el.innerHTML = `<div class="think"><p class="note">Stockfish يحسب السلسلة...</p></div>`;
  const L = await engineLine(fen, uci).catch(() => null);
  if (!L || !L.steps.length) { el.innerHTML = `<p class="note">تعذّر حساب السلسلة.</p>`; return; }
  const N = Facts.NAME_AR; let k = 0; // 0 = all arrows on the starting position; 1..n = after step k
  const arrowsAll = L.steps.map((s, i) => ({ from: s.uci.slice(0, 2), to: s.uci.slice(2, 4), color: s.mine ? "good" : "bad", n: i + 1 }));
  const res = L.mate != null && L.mate > 0 ? `السلسلة تنتهي بكش مات بعد ${L.mate} نقلات.` : L.matGain > 0 ? `بعد ${L.steps.length} نقلات تكون كسبت ما يعادل ${L.matGain} ${L.matGain === 1 ? "بيدقًا" : "بيادق"}.` : L.matGain < 0 ? `بعد ${L.steps.length} نقلات تكون قد أعطيت ما يعادل ${-L.matGain} ${-L.matGain === 1 ? "بيدقًا" : "بيادق"} مقابل نشاط أو هجوم.` : "المادة متساوية في نهاية السلسلة: الكسب في الموقف (نشاط، مساحة، أمان).";
  el.innerHTML = `<div class="think">
    <div class="fh"><b>${esc(title)}</b><span class="note">الأخضر نقلاتك، الأحمر ردود الخصم</span></div>
    <ol class="tsteps">${L.steps.map((s, i) => `<li data-k="${i + 1}"><span class="tnum ${s.mine ? "me" : "op"}">${i + 1}</span> <bdi class="mv">${esc(moveLabel(s.fenBefore, s.san))}</bdi> <span class="note">${s.mine ? "أنت" : "الخصم"}</span><div class="note">${s.why.map(fmtNote).join(" ")}</div></li>`).join("")}</ol>
    <p><b>${esc(verdict)}:</b> ${esc(res)}${L.esNow != null && L.esEnd != null ? ` فرصك الآن <bdi class="mono">${L.esNow}%</bdi>، وفي نهاية السلسلة <bdi class="mono">${L.esEnd}%</bdi>.` : ""}</p>
    <div class="row"><button class="ctl" data-t="all">كل الأسهم</button><button class="ctl" data-t="prev">→ السابقة</button><button class="ctl main" data-t="next">التالية ←</button><button class="btn quiet" data-t="back">عودة إلى موقفي</button></div></div>`;
  const show = () => {
    if (k === 0) board.update({ fen, last: null, interactive: false, arrows: arrowsAll, marks: {} });
    else { const s = L.steps[k - 1]; const nx = L.steps[k]; board.update({ fen: s.fenAfter, last: s.uci, interactive: false, marks: {}, arrows: nx ? [{ from: nx.uci.slice(0, 2), to: nx.uci.slice(2, 4), color: nx.mine ? "good" : "bad", n: k + 1 }] : [] }); }
    for (const li of $$(".tsteps li", el)) li.classList.toggle("on", +li.dataset.k === k);
  };
  $('[data-t="all"]', el).onclick = () => { k = 0; show(); };
  $('[data-t="prev"]', el).onclick = () => { k = Math.max(0, k - 1); show(); };
  $('[data-t="next"]', el).onclick = () => { k = Math.min(L.steps.length, k + 1); show(); };
  for (const li of $$(".tsteps li", el)) li.onclick = () => { k = +li.dataset.k; show(); };
  $('[data-t="back"]', el).onclick = () => { board.update(keep); el.innerHTML = ""; };
  show();
}
