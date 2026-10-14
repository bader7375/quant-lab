"use strict";
/* Warm-ups: positions where the student made a mistake in a coached game (cards kind "warm", made by review.js) come back
   as short exercises at the start of a session: find a better move. Judged by Stockfish (the move played in the game is
   wrong by construction; the best move or anything within 3 points of it is right), scheduled by SM-2. */
const WARM = { cards: [] };
async function warmInit() {
  try { WARM.cards = (await Store.list("cards")).filter((c) => c.kind === "warm"); } catch { WARM.cards = []; }
}
const warmDue = () => WARM.cards.filter((c) => (c.due ?? 0) <= now()).sort((a, b) => a.due - b.due);

function warmPanelHtml() {
  const due = warmDue(); if (!due.length) return "";
  const k = Math.min(5, due.length);
  return `<div class="panel warm"><div class="row" style="justify-content:space-between"><div><span class="eyebrow">إحماء قبل أن تبدأ</span>
    <h3>${arCount(k, "موقف واحد", "موقفان", "مواقف", "موقفًا")} من أخطائك</h3>
    <p class="note">مواقف لعبت فيها نقلة ضعيفة في مبارياتك. جد نقلة أفضل. دقيقتان أو ثلاث.${due.length > k ? ` (مستحق الآن: ${due.length})` : ""}</p></div>
    <button class="btn" id="warm-go">ابدأ الإحماء</button></div></div>`;
}
function startWarmup() {
  const list = warmDue().slice(0, 5); let k = 0, right = 0; const root = $("#v-journey");
  const next = () => {
    if (k >= list.length) {
      root.innerHTML = `<div class="panel"><h3>انتهى الإحماء</h3><p>${right} من ${list.length} صحيحة من المحاولة الأولى. المواقف التي أخطأت فيها تعود أقرب، والصحيحة تبتعد.</p><div class="row"><button class="btn" id="warm-back">إلى الرحلة</button></div></div>`;
      $("#warm-back", root).onclick = () => go("journey"); return;
    }
    const c = list[k]; const item = { kind: "puzzle", id: c.id, fen: c.fen, sol: [c.bestUci], themes: [], skill: "tactics", rating: 1100 };
    const label = `<div class="row" style="justify-content:space-between"><span class="eyebrow">إحماء ${k + 1} من ${list.length}</span><button class="btn quiet" id="warm-stop">إيقاف</button></div>
      <p class="note">من مباراتك في الفصل ${c.chapter}: لعبت هنا ${mv(c.played)} (${CLASS_AR[c.cls] || "خطأ"}). جد نقلة أفضل.</p>`;
    Solver(root, item, { askConf: false, ladder: true, labelHtml: label, onDone: (R) => {
      if (R.correct) right++;
      sm2(c, qualityOf(R)); c.last = now(); c.attempts = (c.attempts || 0) + 1; Store.set("cards/" + c.id, c);
      k++; next();
    } });
    $("#warm-stop", root).onclick = () => go("journey");
  };
  next();
}
