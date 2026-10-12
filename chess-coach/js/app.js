"use strict";
/* App shell: boot, top navigation, routing, status chips. */

const VIEWS = ["journey", "chapter", "progress", "practice"];
let VIEW = "journey", VIEW_ARG = null;
function go(view, arg) {
  if (!VIEWS.includes(view)) view = "journey";
  VIEW = view; VIEW_ARG = arg ?? null;
  const tab = view === "chapter" ? "journey" : view;
  for (const b of $$("#nav button")) { if (b.dataset.view === tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); }
  for (const v of VIEWS) $("#v-" + v).hidden = v !== view;
  if (view === "journey") renderJourney();
  else if (view === "chapter") renderChapter(arg);
  else if (view === "progress") renderJourneyProgress();
  else if (view === "practice") renderPractice();
  const hash = view === "chapter" ? "ch-" + arg : view;
  if (location.hash.slice(1) !== hash) { try { history.replaceState(null, "", "#" + hash); } catch {} }
  try { localStorage.setItem("cc:route", hash); } catch {}
  window.scrollTo?.(0, 0);
}
function routeFrom(hash) {
  const m = /^ch-(\d+)$/.exec(hash || ""); if (m) return ["chapter", +m[1]];
  return [VIEWS.includes(hash) ? hash : "journey", null];
}
async function boot() {
  $("#brandimg").src = PIECES.wn;
  for (const b of $$("#nav button")) b.onclick = () => go(b.dataset.view);
  const stS = $("#st-store"), stE = $("#st-engine"), stC = $("#st-claude");
  Engine.start().then(() => { stE.textContent = `Stockfish 17.1 (${Engine.kind === "wasm" ? "WASM" : "asm.js"}): جاهز`; stE.className = "chip ok"; })
    .catch(() => { stE.textContent = "Stockfish: تعذّر التشغيل"; stE.className = "chip bad"; });
  await Promise.all([Store.init(), loadData(), loadCurriculum()]);
  stS.textContent = { db: "التقدم محفوظ (يقرؤه Claude)", local: "التقدم في هذا المتصفح فقط", memory: "التقدم مؤقت" }[Store.kind]; stS.className = "chip " + (Store.kind === "db" ? "ok" : "warn");
  await Promise.all([journeyInit(), practiceInit()]);
  let route = location.hash.slice(1); if (!route) { try { route = localStorage.getItem("cc:route") || ""; } catch {} }
  const [v, a] = routeFrom(route); go(v, a);
  window.addEventListener("hashchange", () => { const [v2, a2] = routeFrom(location.hash.slice(1)); if (v2 !== VIEW || a2 !== VIEW_ARG) go(v2, a2); });
  try { SAMPLE = window.claude ? await window.claude.use("sample") : null; } catch { SAMPLE = null; }
  stC.textContent = SAMPLE ? "Claude: متصل" : "Claude: غير متاح هنا، الشرح من البيانات فقط"; stC.className = "chip " + (SAMPLE ? "ok" : "warn");
}
boot();
