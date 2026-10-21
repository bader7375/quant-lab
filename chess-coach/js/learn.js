"use strict";
/* Learn (stage A): a short lesson on the board. Each slide sets up a position (moves from the start), explains one idea and
   usually asks for a move. Accepted moves and every "why" text were checked with Stockfish 17.1 (tools/verify_lesson.mjs).
   A move outside the lists is judged live by Stockfish. The lesson ends with the chapter's "what do I think about" checklist. */
STAGE_RUNNERS.learn = async (n) => {
  const c = chapter(n); const file = content(c).learn; const root = $("#v-chapter");
  root.innerHTML = `<div class="panel"><p class="note">جارٍ تحميل الدرس...</p></div>`;
  let L; try { L = await loadJSON("data/curriculum/" + file); } catch { root.innerHTML = `<div class="panel"><p class="err">تعذّر تحميل الدرس.</p></div>`; return; }
  LessonPlayer(root, L, n);
};

function LessonPlayer(root, L, n) {
  const c = chapter(n); const S = L.slides; let i = 0; let tries = 0; let solved = new Set(chState(n).learn.solved || []);
  root.innerHTML = `
    <div class="whead"><button class="btn quiet" id="l-back">→ الفصل ${n}</button><div class="wtitle"><b>${esc(L.title)}</b><span class="note" id="l-prog"></span></div></div>
    <div class="watch">
      <div class="wboard"><div class="boardcap"><span class="turn" id="l-turn"></span></div><div class="board" id="l-board"></div>
        <div class="wctrl"><button class="ctl" id="l-prev">→ السابق</button><button class="ctl main" id="l-next">التالي ←</button></div>
        <div class="steps" id="l-steps"></div></div>
      <div class="wside"><div class="panel ncard" id="l-card" aria-live="polite"></div><div class="panel" id="l-chat"></div></div>
    </div>`;
  const board = Board($("#l-board", root), { interactive: false });
  const card = $("#l-card", root);
  $("#l-back", root).onclick = () => go("chapter", n);
  $("#l-prev", root).onclick = () => show(i - 1);
  $("#l-next", root).onclick = () => show(i + 1);
  const fenOf = (s) => { const g = new Chess(s.fen || START_FEN); for (const m of s.moves) g.move(m); return g.fen(); }; // a slide starts from the initial position or its own fen
  function show(k) {
    i = Math.max(0, Math.min(S.length, k)); tries = 0;
    $("#l-prog", root).textContent = i < S.length ? `الشريحة ${i + 1} من ${S.length}` : "الخلاصة";
    $("#l-steps", root).innerHTML = [...S.map((s, j) => `<span class="${j === i ? "on" : solved.has(j) || !s.task ? "done" : ""}">${j + 1}</span>`), `<span class="${i === S.length ? "on" : ""}">✓</span>`].join("");
    $("#l-prev", root).disabled = i === 0; $("#l-next", root).hidden = i === S.length;
    if (i === S.length) return summary();
    const s = S[i]; const fen = fenOf(s); const g = new Chess(fen); const stm = g.turn();
    $("#l-turn", root).innerHTML = `<i class="${stm}"></i>الدور ${stm === "w" ? "للأبيض" : "للأسود"}`;
    const last = s.moves.length ? (() => { const h = new Chess(s.fen || START_FEN); let mv; for (const m of s.moves) mv = h.move(m); return mv.from + mv.to; })() : null;
    board.update({ fen, orient: stm, last, marks: s.marks || {}, arrows: s.arrows || [], interactive: !!s.task && !solved.has(i), onMove: (m) => tryMove(s, fen, m) });
    card.innerHTML = `<h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>${s.task ? `<div class="callout"><b>مهمة:</b> ${esc(s.task.prompt)}</div><div id="l-fb"></div>` : ""}`;
    if (s.task && solved.has(i)) $("#l-fb", card).innerHTML = `<div class="callout good">${esc(s.task.success)}</div>`;
  }
  async function tryMove(s, fen, m) {
    const fb = $("#l-fb", card); const san = m.san.replace(/[+#]/g, "");
    const acc = s.task.accept.map((x) => x.replace(/[+#]/g, ""));
    board.update({ fen: m.fenAfter, last: m.uci, interactive: false, arrows: [] });
    if (acc.includes(san)) {
      solved.add(i); chState(n).learn.solved = [...solved]; saveJourney();
      fb.innerHTML = `<div class="callout good"><b>${mv(m.san)}</b> ${esc(s.task.success)}${acc.length > 1 ? `<p class="note">نقلات صحيحة أخرى هنا: ${acc.filter((x) => x !== san).map(mv).join("، ")}</p>` : ""}</div>`;
      $("#l-steps span:nth-child(" + (i + 1) + ")", root).className = "done";
      return;
    }
    tries++;
    const why = Object.entries(s.task.why || {}).find(([k]) => k.replace(/[+#]/g, "") === san);
    if (why) fb.innerHTML = `<div class="callout bad"><b>${mv(m.san)}</b> ${esc(why[1])}</div>`;
    else {
      fb.innerHTML = `<div class="callout"><b>${mv(m.san)}</b>: Stockfish يقيّم النقلة...</div>`;
      const j = await judgeMove(fen, m.uci, { tol: 5 }).catch(() => null);
      fb.innerHTML = `<div class="callout bad"><b>${mv(m.san)}</b> ليست ما يطلبه هذا التمرين.${j && j.refutation.length ? ` بعدها يرد Stockfish بـ ${mv(numberedLine(m.fenAfter, j.refutation.slice(0, 3)))}.` : ""}</div>`;
    }
    fb.insertAdjacentHTML("beforeend", tries >= 2 ? `<p class="note">الجواب: ${acc.map(mv).join(" أو ")}. جرّبه على الرقعة.</p>` : `<p class="note">جرّب مرة أخرى.</p>`);
    setTimeout(() => { if (S[i] === s) board.update({ fen, last: null, interactive: true, arrows: s.arrows || [] }); }, 900);
  }
  function summary() {
    board.update({ fen: START_FEN, last: null, marks: {}, arrows: [], interactive: false });
    const tasks = S.filter((s) => s.task).length; const done = [...solved].length;
    card.innerHTML = `<h3>${esc(L.checklistTitle || "بماذا أفكر في أول عشر نقلات")}</h3><ul class="checklist">${L.checklist.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      <p class="note">حللت ${done} من ${tasks} تمارين.${done < tasks ? " يمكنك العودة إلى أي شريحة." : ""}</p>
      <div class="row"><button class="btn" id="l-done">أنهيت الدرس: احفظ القائمة</button></div>`;
    $("#l-done", card).onclick = () => { const st = chState(n); st.learn.done = true; st.learn.checklist = L.checklist; st.learn.at = now(); saveJourney(); go("chapter", n); };
  }
  Chat($("#l-chat", root), { level: c.level, chips: ["لماذا هذه القاعدة مهمة؟", "ما الخطأ الشائع هنا؟"], getContext: () => { const s = S[Math.min(i, S.length - 1)]; return { fen: fenOf(s), ply: s.fen ? 60 : s.moves.length, start: s.fen || START_FEN, moves: s.moves, extra: `LESSON SLIDE: ${s.title}. ${s.text}` }; } });
  show(0);
}
