"use strict";
/* Chapter 8: the repertoire (data/curriculum/ch08/repertoire.json, built from the masters tree and checked with Stockfish
   by tools/repertoire/build_rep.mjs). A trainer that asks your repertoire move in positions from the tree, a check of how
   long a game stayed in the repertoire, and notes during Play. No Claude calls. */
let REP = null;
async function loadRep() { if (!REP) REP = (await loadJSON("data/curriculum/ch08/repertoire.json")).positions; return REP; }
const repAt = (fen) => (REP ? REP[Masters.keyOf(fen)] || null : null);
const REP_GROUP_AR = { w: "بالأبيض: Italian Game", e5: "بالأسود ضد 1.e4: 1...e5", qgd: "بالأسود ضد 1.d4: QGD", "b-other": "بالأسود ضد 1.c4 و1.Nf3" };

/* How long a game stayed in the repertoire: your moves that matched it, and whether you or the opponent left it first. */
function repWalk(G) {
  if (!REP) return null;
  const g = new Chess(G.start); let own = 0, left = null, ended = null;
  for (let i = 0; i < G.sans.length; i++) {
    const fen = g.fen(); const mine = g.turn() === G.color; const r = REP[Masters.keyOf(fen)];
    const m = g.move(G.sans[i], { sloppy: true }); if (!m) break;
    if (!mine) continue;
    if (!r) { ended = { ply: i, by: "book" }; break; } // the opponent left the repertoire (or it ended)
    if (m.san.replace(/[+#]/g, "") === r.m.replace(/[+#]/g, "")) own++; else { left = { ply: i, played: m.san, rep: r.m }; break; }
  }
  return { own, left, ended };
}

/* ---------- the repertoire trainer ---------- */
function RepSession(root, n, T, opts = {}) {
  const ts = techState(T.id); let token = 0, fen = null, r = null, board, solved = false, t0 = 0; const S = { n: 0, ok: 0 };
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="t-back">${opts.onBack ? "→ جلسة اليوم" : `→ الفصل ${n}`}</button><div class="wtitle"><b>${esc(T.title)}</b><span class="note" id="t-prog"></span></div></div>
    <div class="panel tlesson"><p><b>القاعدة:</b> ${esc(T.rule)}</p><p><b>لماذا:</b> ${esc(T.why)}</p><p><b>لا تفعل:</b> ${esc(T.dont)}</p><p><b>كيف تراها:</b> ${esc(T.see)}</p>${methodHtml(T)}</div>
    <div class="watch">
      <div class="wboard"><div class="boardcap"><span class="turn" id="t-turn"></span><span class="note" id="t-status"></span></div><div class="note" id="t-src"></div>
        <div class="board" id="t-board"></div></div>
      <div class="wside"><div class="panel" id="t-card" aria-live="polite"></div><div class="panel" id="t-x"></div></div>
    </div>`;
  board = Board($("#t-board", root), { interactive: false });
  const alive = (t) => t === token && document.body.contains(root) && $("#t-board", root);
  const setStatus = (t) => { $("#t-status", root).textContent = t; };
  $("#t-back", root).onclick = () => { token++; opts.onBack ? opts.onBack() : go("chapter", n); };
  const prog = () => { const m = techMastery(ts); $("#t-prog", root).textContent = opts.count ? `الموقف ${Math.min(S.n + (solved ? 0 : 1), opts.count)} من ${opts.count} · صحيحة ${S.ok}` : `${m.mastered ? "متقنة · " : ""}صحيحة ${m.ok} من آخر ${m.of || 0} · المجموع ${ts.n}`; };
  const lastOne = () => opts.count && S.n >= opts.count;
  const record = (ok, s) => { S.n++; if (ok) S.ok++; ts.n++; ts.last.push(ok ? 1 : 0); if (ts.last.length > 20) ts.last.shift(); ts.times = (ts.times || []).concat(s).slice(-10); (ts.miss = ts.miss || {}); saveJourney(); prog(); };
  async function next() {
    if (lastOne()) { token++; return opts.onDone && opts.onDone({ n: S.n, ok: S.ok, helped: 0 }); }
    const t = ++token; solved = false; prog(); $("#t-x", root).innerHTML = ""; setStatus("أجهّز الموقف...");
    await loadRep(); if (!alive(t)) return;
    // positions you got wrong come back first; otherwise a random one, shallow positions a little more often
    const keys = Object.keys(REP).filter((k) => T.groups.includes(REP[k].g));
    const missed = Object.keys(ts.miss || {}).filter((k) => keys.includes(k) && ts.miss[k] <= now());
    let key = missed.length && Math.random() < 0.5 ? missed[0] : null;
    if (!key) { for (let i = 0; i < 6; i++) { const k = keys[Math.floor(Math.random() * keys.length)]; if (!key || REP[k].p.split(" ").length < REP[key].p.split(" ").length) key = k; } }
    r = REP[key]; const g = new Chess(); const path = r.p ? r.p.split(" ") : []; let last = null;
    for (const s of path) { const m = g.move(s); last = m.from + m.to; }
    fen = g.fen(); const me = g.turn();
    $("#t-src", root).textContent = path.length ? `بعد ${numberedLine(START_FEN, path)}` : "الموقف الأول";
    $("#t-turn", root).innerHTML = `<i class="${me}"></i>${me === "w" ? "الأبيض" : "الأسود"}`;
    $("#t-card", root).innerHTML = `<p><b>${esc(T.prompt)}</b></p><p class="note">${esc(REP_GROUP_AR[r.g])}.</p>`;
    board.update({ fen, orient: me, last, interactive: true, arrows: [], marks: {}, onMove: (m) => answer(m, t, key) });
    setStatus("ما نقلة ذخيرتك هنا؟"); t0 = now();
  }
  async function answer(m, t, key) {
    if (solved) return; solved = true; board.update({ interactive: false, fen: m.fenAfter, last: m.uci });
    const took = Math.max(1, Math.round((now() - t0) / 1000)); const avg = avgTime(ts);
    const norm = (s) => s.replace(/[+#]/g, ""); const ok = norm(m.san) === norm(r.m);
    record(ok, took); if (ok) delete ts.miss[key]; else ts.miss[key] = now() + 10 * 60000; saveJourney();
    setStatus("Stockfish والأساتذة...");
    const me = new Chess(fen).turn(); const pc = Prob.ctx(fen, 10);
    const a = await Engine.analyse(fen, { depth: 13, movetime: 1200, multipv: 1 }); if (!alive(t)) return;
    const repUci = (() => { const h = new Chess(fen).move(r.m); return h.from + h.to + (h.promotion || ""); })();
    const ev = async (u) => (u === a.best ? a.lines[0] : (await Engine.analyse(fen, { depth: 12, movetime: 700, searchmoves: [u] })).lines[0]);
    const lm = await ev(m.uci), lr = await ev(repUci); if (!alive(t)) return;
    const es = (l) => (l ? Math.round(Prob.esFor(l.cpWhite, me, pc)) : null);
    const ms = await Masters.lookup(fen).catch(() => null); if (!alive(t)) return;
    const mineM = ms && ms.moves.find((x) => x.san === m.san), repM = ms && ms.moves.find((x) => x.san === r.m);
    const why = bestMoveWhy(fen, r.m, repUci, null).concat(Tech.tagsOf(fen, repUci).filter((x) => TAG_AR[x] && x !== "check").map((x) => TAG_AR[x]));
    // the line that follows: the masters' main reply, then your next repertoire move
    const h = new Chess(fen); h.move(r.m); const cont = [r.m]; const ms2 = await Masters.lookup(h.fen()).catch(() => null);
    if (ms2 && ms2.moves[0]) { h.move(ms2.moves[0].san); cont.push(ms2.moves[0].san); const r2 = REP[Masters.keyOf(h.fen())]; if (r2) cont.push(r2.m); }
    if (!alive(t)) return;
    const tips = [];
    if (ok) tips.push(`صحيح. ثبّت الفكرة لا النقلة فقط: ${why.length ? plainNote(why[0]) : "هذه نقلة الأساتذة في هذا الموقف."}`);
    else {
      tips.push(es(lm) != null && es(lr) != null && es(lr) - es(lm) <= 2 ? `نقلتك ${m.san} جيدة عند Stockfish، لكنها ليست ذخيرتك. الذخيرة الثابتة تعني أنك تعرف الخطط التي تأتي بعدها.` : `نقلتك ${m.san} أضعف من نقلة الذخيرة (${es(lm)}% مقابل ${es(lr)}%).`);
      tips.push("سيعود هذا الموقف إليك بعد 10 دقائق على الأقل.");
    }
    $("#t-card", root).innerHTML = `<div class="callout ${ok ? "good" : "bad"}"><b>${ok ? "صحيح" : "ليست ذخيرتك"}: <bdi class="mv">${esc(moveLabel(fen, m.san))}</bdi></b>
      <p>ذخيرتك هنا: <bdi class="mv">${esc(r.m)}</bdi>${repM ? ` · لعبها الأساتذة في ${Math.round(100 * repM.share)}% من ${ms.total.toLocaleString("en")} مباراة، وسجّلت ${Math.round(100 * repM.scoreStm)}%` : r.sf ? " · اختارها Stockfish (لا نقلة أساتذة شائعة هنا قريبة من الأفضل)" : ""}.</p>
      ${!ok && mineM ? `<p class="note">نقلتك ${esc(m.san)}: ${Math.round(100 * mineM.share)}% عند الأساتذة، وسجّلت ${Math.round(100 * mineM.scoreStm)}%.</p>` : ""}</div>
      ${why.length ? `<p><b>الفكرة:</b></p><ul class="facts">${[...new Set(why)].map((x) => `<li>${fmtNote(x)}</li>`).join("")}</ul>` : ""}
      <p class="note">ما يأتي بعدها غالبًا: <bdi class="mv">${esc(numberedLine(fen, cont))}</bdi></p>
      ${r.alt && r.alt.length ? `<p class="note">نقلات أساتذة أخرى هنا: ${r.alt.map(([s, sh]) => `${esc(s)} ${Math.round(100 * sh)}%`).join("، ")}.</p>` : ""}
      ${adviceHtml(tips, took, avg, ok, T)}
      <div class="row"><button class="btn" data-a="next">${lastOne() ? "أنهِ المجموعة" : "الموقف التالي"}</button><button class="btn quiet" data-a="think">ماذا يفكر المحرك بعدها؟ (أسهم 1-5)</button></div>`;
    $('[data-a="next"]', root).onclick = () => next();
    $('[data-a="think"]', root).onclick = () => ThinkPanel($("#t-x", root), board, fen, repUci, { title: `ماذا يحدث بعد ${r.m}؟`, verdict: "لماذا هي نقلة الذخيرة" });
    board.update({ fen, last: null, arrows: [{ from: repUci.slice(0, 2), to: repUci.slice(2, 4), color: "good" }, ...(ok ? [] : [{ from: m.uci.slice(0, 2), to: m.uci.slice(2, 4), color: "bad" }])] });
    setStatus(ok ? "أحسنت." : "راجع الفكرة، ثم الموقف التالي.");
  }
  prog(); next();
}
