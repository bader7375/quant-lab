/* Gradient brain games.
   Registers five short cognitive drills on window.GradientGames for gradient.html (see openGame there).
   Plain ES2019, no dependencies, no network, no storage. Every game shows an intro, runs one timed
   session after Start, reports through api.onDone exactly once per session, then shows a result screen.
   mount() returns a cleanup function that cancels every timer, frame and listener it created. */
(function () {
  'use strict';
  if (typeof window === 'undefined') return;

  /* ---------- text constants (ASCII source, so the file is safe under any charset) ---------- */
  const TIMES = '\u00d7', DIVIDE = '\u00f7', MINUS = '\u2212', NDASH = '\u2013', MIDDOT = '\u00b7',
    LARR = '\u2190', RARR = '\u2192';

  /* ---------- styles: one shared <style id="gg-styles">, page tokens only ---------- */
  const CSS = [
    '.gg{display:grid;gap:16px;width:100%;max-width:640px;margin-inline:auto;min-width:0;font:15px/1.5 var(--f-body);color:var(--ink);text-align:left}',
    '.gg *,.gg *::before,.gg *::after{box-sizing:border-box}',
    '.gg [hidden]{display:none!important}',
    '.gg p,.gg ul,.gg dl,.gg dd,.gg h3{margin:0}',
    '.gg-screen{display:grid;gap:14px;min-width:0}',
    '.gg-screen:focus,.gg-focus:focus,.gg-head:focus{outline:none}',
    '.gg-kicker{font:500 11px/1.3 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}',
    '.gg-lede{font-size:16px;line-height:1.5}',
    '.gg-how{padding-left:20px;display:grid;gap:8px}',
    '.gg-how li::marker{color:var(--faint)}',
    '.gg-note{font-size:14px;color:var(--muted)}',
    '.gg-prev{font:13px/1.5 var(--f-mono);color:var(--muted)}',
    '.gg-kbd{display:inline-block;min-width:1.7em;padding:1px 5px;border:1px solid var(--rule);border-bottom-width:2px;border-radius:4px;background:var(--raise);color:var(--ink);font:500 12px/1.4 var(--f-mono);text-align:center;vertical-align:middle}',
    '.gg-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}',
    '.gg-meta{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:6px 12px;font:13px/1.4 var(--f-mono);color:var(--muted);font-variant-numeric:tabular-nums}',
    '.gg-btn{-webkit-appearance:none;appearance:none;display:inline-flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:6px 8px;min-height:44px;min-width:44px;margin:0;padding:10px 18px;border:1px solid var(--rule);border-radius:6px;background:var(--surface);color:var(--ink);font:500 15px/1.2 var(--f-body);text-align:center;cursor:pointer;touch-action:manipulation;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}',
    '.gg-btn:hover{border-color:var(--muted)}',
    '.gg-btn:focus{outline:none}',
    '.gg-btn:focus-visible{outline:2px solid var(--ember);outline-offset:2px}',
    '.gg-primary{background:var(--ember);border-color:var(--ember);color:var(--ember-ink);font-weight:600}',
    '.gg-primary:hover{border-color:var(--ink)}',
    '.gg-btn:disabled{opacity:.5;cursor:default}',
    '.gg-big{min-height:64px;min-width:0;padding:12px 10px;font-size:16px}',
    '.gg-btn.gg-hit{border-color:var(--good);background:color-mix(in srgb,var(--good) 22%,var(--surface))}',
    '.gg-btn.gg-fa{border-color:var(--bad);background:color-mix(in srgb,var(--bad) 22%,var(--surface))}',
    '.gg-good{color:var(--good)}.gg-bad{color:var(--bad)}.gg-warn{color:var(--warn)}.gg-muted{color:var(--muted)}',
    '.gg-stage{display:grid;place-items:center;min-height:180px;padding:16px;border:1px solid var(--rule);border-radius:10px;background:var(--ground);text-align:center;overflow:hidden}',
    '.gg-stage>*{grid-area:1/1}',
    '.gg-msg{min-height:1.5em;text-align:center}',
    '.gg-form{display:flex;flex-wrap:wrap;gap:8px;align-items:center}',
    '.gg-input{flex:1 1 130px;min-width:0;min-height:48px;padding:10px 12px;border:1px solid var(--rule);border-radius:6px;background:var(--ground);color:var(--ink);font:500 20px/1.2 var(--f-mono);letter-spacing:.04em}',
    '.gg-input:focus{outline:2px solid var(--ember);outline-offset:1px;border-color:var(--ember)}',
    '.gg-input:disabled{opacity:.6}',
    /* result */
    '.gg-score{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}',
    '.gg-score-num{font:600 clamp(44px,13vw,68px)/1 var(--f-display);font-variant-numeric:tabular-nums;color:var(--ink)}',
    '.gg-score-unit{font:500 16px/1.2 var(--f-mono);color:var(--muted)}',
    '.gg-score-label{flex-basis:100%;font:500 11px/1.3 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}',
    '.gg-summary{font-size:16px}',
    '.gg-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:8px}',
    '.gg-card{min-width:0;padding:10px 12px;border:1px solid var(--rule);border-radius:8px;background:var(--raise)}',
    '.gg-card dt{font:500 10.5px/1.3 var(--f-mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}',
    '.gg-card dd{margin-top:4px;font:500 17px/1.3 var(--f-mono);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}',
    '.gg-sub{display:block;margin-top:2px;font:13px/1.35 var(--f-body);color:var(--muted)}',
    '.gg-sub.gg-good{color:var(--good)}',
    '.gg-table{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:0 12px;padding:6px 12px;border:1px solid var(--rule);border-radius:8px;background:var(--raise)}',
    '.gg-table dt,.gg-table dd{padding:7px 0;border-top:1px solid var(--rule)}',
    '.gg-table dt:first-of-type,.gg-table dd:first-of-type{border-top:0}',
    '.gg-table dt{color:var(--muted);font-size:14px}',
    '.gg-table dd{font:500 15px/1.4 var(--f-mono);font-variant-numeric:tabular-nums;text-align:right}',
    /* n-back */
    '.gg-nb-stage{display:flex;flex-wrap:wrap;justify-content:center;align-items:stretch;gap:12px}',
    '.gg-nb-grid{--gg-nb:clamp(150px,44vw,228px);width:var(--gg-nb);height:var(--gg-nb);display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);gap:6px;padding:6px;border:1px solid var(--rule);border-radius:10px;background:var(--ground)}',
    '.gg-nb-cell{border:1px solid var(--rule);border-radius:6px;background:var(--raise)}',
    '.gg-nb-cell.gg-on{background:var(--glass);border-color:var(--glass)}',
    '.gg-nb-letter{width:clamp(96px,27vw,150px);min-height:96px;display:grid;place-items:center;border:1px solid var(--rule);border-radius:10px;background:var(--ground);font:600 clamp(52px,15vw,84px)/1 var(--f-display);color:var(--ink)}',
    '.gg-resp{display:grid;grid-template-columns:1fr 1fr;gap:10px}',
    '.gg-resp .gg-btn{flex-direction:column;gap:6px}',
    '.gg:not(.gg-rm) .gg-nb-cell{transition:background-color .08s linear,border-color .08s linear}',
    /* digit span */
    '.gg-stack{display:grid;gap:14px;justify-items:center}',
    '.gg-digit{min-height:1em;font:600 clamp(64px,20vw,96px)/1 var(--f-display);font-variant-numeric:tabular-nums;color:var(--ink)}',
    '.gg-pips{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;min-height:10px}',
    '.gg-pip{width:10px;height:10px;border-radius:50%;border:1px solid var(--muted)}',
    '.gg-pip.gg-on{background:var(--ember);border-color:var(--ember)}',
    /* stroop */
    '.gg-st-word{font:700 clamp(34px,11vw,58px)/1.1 var(--f-body);letter-spacing:.06em}',
    '.gg-st-fix{font-weight:400;color:var(--muted)}',
    '.gg-keys4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}',
    '@media (max-width:560px){.gg-keys4{grid-template-columns:repeat(2,minmax(0,1fr))}}',
    /* reaction */
    '.gg-rx-stage{min-height:210px}',
    '.gg-rx-dot{width:12px;height:12px;border-radius:50%;background:var(--muted)}',
    '.gg-rx-arrow{display:block;width:clamp(96px,32vw,150px);height:auto;color:var(--ink)}',
    '.gg-rx-right .gg-rx-arrow{transform:scaleX(-1)}',
    '.gg-rx-btns{display:grid;grid-template-columns:1fr 1fr;gap:10px}',
    '.gg-rx-btns .gg-btn{min-height:88px;font-size:17px}',
    /* calc */
    '.gg-q{display:grid;gap:6px;padding:14px 16px;border:1px solid var(--rule);border-radius:10px;background:var(--ground)}',
    '.gg-qtext{font-size:17px;line-height:1.45;overflow-wrap:anywhere}',
    '.gg-unit{min-width:2ch;font:500 15px/1.2 var(--f-mono);color:var(--muted)}',
    '.gg-timer{font:600 22px/1 var(--f-mono);font-variant-numeric:tabular-nums;color:var(--ink)}',
    '.gg-timer.gg-low{color:var(--warn)}',
    '.gg-fb{display:grid;gap:4px;min-height:64px;padding:10px 12px;border:1px solid var(--rule);border-left-width:3px;border-radius:8px;background:var(--raise)}',
    '.gg-fb.gg-fb-good{border-left-color:var(--good)}',
    '.gg-fb.gg-fb-bad{border-left-color:var(--bad)}',
    '.gg-formula{font:13px/1.5 var(--f-mono);color:var(--muted);overflow-wrap:anywhere}',
    '.gg-rm *{transition:none!important;animation:none!important}',
    '@media (prefers-reduced-motion:reduce){.gg *{transition:none!important;animation:none!important}}'
  ].join('\n');

  function injectStyles() {
    if (document.getElementById('gg-styles')) return;
    const s = document.createElement('style');
    s.id = 'gg-styles';
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  /* ---------- small helpers ---------- */
  function h(tag, attrs) {
    const n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        const v = attrs[k];
        if (v == null || v === false) return;
        if (k === 'class') n.className = v;
        else n.setAttribute(k, v === true ? '' : String(v));
      });
    }
    for (let i = 2; i < arguments.length; i++) add(n, arguments[i]);
    return n;
  }
  function add(n, kid) {
    if (kid == null || kid === false) return;
    if (Array.isArray(kid)) { kid.forEach(function (k) { add(n, k); }); return; }
    n.appendChild(typeof kid === 'object' ? kid : document.createTextNode(String(kid)));
  }
  const kbd = function (k) { return h('kbd', { class: 'gg-kbd' }, k); };
  const clamp = function (v, lo, hi) { return Math.min(hi, Math.max(lo, v)); };
  const round = function (x, dp) { const f = Math.pow(10, dp || 0); return Math.round(x * f) / f; };
  const pct = function (x) { return Math.round(x * 100); };
  const plural = function (n, one, many) { return n + ' ' + (n === 1 ? one : (many || one + 's')); };
  function randInt(lo, hi, rng) { return lo + Math.floor((rng || Math.random)() * (hi - lo + 1)); }
  function pick(arr, rng) { return arr[Math.floor((rng || Math.random)() * arr.length)]; }
  function shuffle(a, rng) {
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor((rng || Math.random)() * (i + 1));
      const t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function median(xs) {
    if (!xs.length) return NaN;
    const s = xs.slice().sort(function (a, b) { return a - b; });
    const m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }
  // Number to display string with thousands separators and at most maxDp decimals.
  function n2s(x, maxDp) {
    return Number(x).toLocaleString('en-US', { maximumFractionDigits: maxDp == null ? 3 : maxDp });
  }
  // "a" or "an" before a number written in digits (an 8, an 11, an 18, an 80...).
  function an(n) { const s = String(n); return s.charAt(0) === '8' || s === '11' || s === '18' ? 'an' : 'a'; }
  function isTypingTarget(t) {
    if (!t || t.nodeType !== 1) return false;
    return t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || !!t.isContentEditable;
  }
  function focusEl(n) { if (n && typeof n.focus === 'function') { try { n.focus(); } catch (e) { /* ignore */ } } }
  let uid = 0;

  /* ---------- Scope: owns every timer, frame and listener of one screen or session ---------- */
  class Scope {
    constructor(alive) {
      this.alive = alive; this.dead = false;
      this.timers = new Set(); this.intervals = new Set(); this.frames = new Set(); this.listeners = [];
    }
    ok() { return !this.dead && (!this.alive || this.alive()); }
    after(ms, fn) {
      if (this.dead) return 0;
      const id = setTimeout(() => { this.timers.delete(id); if (this.ok()) fn(); }, Math.max(0, ms || 0));
      this.timers.add(id);
      return id;
    }
    cancel(id) { if (id) { clearTimeout(id); this.timers.delete(id); } }
    every(ms, fn) {
      if (this.dead) return 0;
      const id = setInterval(() => { if (this.ok()) fn(); }, ms);
      this.intervals.add(id);
      return id;
    }
    frame(fn) {
      if (this.dead) return 0;
      // Without rAF, fall back to a timer; callers guard on their own state, so it needs no frame id.
      if (typeof requestAnimationFrame !== 'function') { this.after(16, fn); return 0; }
      const id = requestAnimationFrame(() => { this.frames.delete(id); if (this.ok()) fn(); });
      this.frames.add(id);
      return id;
    }
    cancelFrame(id) {
      // Only ever cancel a frame this scope still owns: a stale id must not hit anything else.
      if (id && this.frames.has(id)) { cancelAnimationFrame(id); this.frames.delete(id); }
    }
    on(target, type, fn, opts) {
      if (this.dead || !target) return;
      const self = this;
      const wrapped = function (e) { if (self.ok()) fn.call(this, e); };
      target.addEventListener(type, wrapped, opts);
      this.listeners.push([target, type, wrapped, opts]);
    }
    clear() {
      this.dead = true;
      this.timers.forEach(function (id) { clearTimeout(id); }); this.timers.clear();
      this.intervals.forEach(function (id) { clearInterval(id); }); this.intervals.clear();
      this.frames.forEach(function (id) { try { cancelAnimationFrame(id); } catch (e) { /* ignore */ } }); this.frames.clear();
      this.listeners.forEach(function (l) { try { l[0].removeEventListener(l[1], l[2], l[3]); } catch (e) { /* ignore */ } });
      this.listeners.length = 0;
    }
  }

  /* ---------- shell: intro -> session -> result, shared by all games ---------- */
  function card(label, value, sub, cls) {
    return h('div', { class: 'gg-card' }, h('dt', null, label),
      h('dd', null, value, sub ? h('span', { class: 'gg-sub' + (cls ? ' ' + cls : '') }, sub) : null));
  }

  function runShell(cfg, el, api) {
    api = api || {};
    injectStyles();
    const rm = !!api.reducedMotion;
    const onDone = typeof api.onDone === 'function' ? api.onDone : null;
    let last = api.last && typeof api.last.score === 'number' && isFinite(api.last.score) ? api.last : null;
    let best = typeof api.best === 'number' && isFinite(api.best) ? api.best : null;
    let dead = false, session = null;
    const root = h('div', { class: 'gg' + (rm ? ' gg-rm' : ''), 'data-gg': cfg.id });
    // If the host removes our node without calling cleanup, the next tick of any timer cleans up.
    const alive = function () {
      if (dead) return false;
      if (!root.isConnected) { cleanup(); return false; }
      return true;
    };
    let ui = new Scope(alive);
    const higher = cfg.metric.better !== 'lower';
    const beats = function (a, b) { return higher ? a > b : a < b; };

    function resetUi() { ui.clear(); ui = new Scope(alive); }
    function setScreen(node) { root.textContent = ''; root.appendChild(node); }
    function endSession() { if (session) { session.clear(); session = null; } }

    function showIntro() {
      resetUi();
      const start = h('button', { type: 'button', class: 'gg-btn gg-primary' }, 'Start');
      const prev = [];
      if (last) prev.push('Last: ' + cfg.fmt(last.score));
      if (best != null) prev.push('Best: ' + cfg.fmt(best));
      setScreen(h('section', { class: 'gg-screen', 'aria-label': cfg.name + ': how to play' },
        h('p', { class: 'gg-kicker' }, 'Trains ' + cfg.skill.toLowerCase() + ' ' + MIDDOT + ' about ' + cfg.minutes + ' min'),
        h('p', { class: 'gg-lede' }, cfg.trains),
        h('ul', { class: 'gg-how' }, cfg.how({ last: last, best: best }).map(function (item) { return h('li', null, item); })),
        prev.length ? h('p', { class: 'gg-prev' }, prev.join('   ' + MIDDOT + '   ')) : null,
        cfg.note ? h('p', { class: 'gg-note' }, cfg.note) : null,
        h('div', { class: 'gg-row' }, start)));
      ui.on(start, 'click', startSession);
    }

    function startSession() {
      if (dead) return;
      resetUi();
      endSession();
      const s = new Scope(alive);
      session = s;
      let finished = false;
      const stage = h('section', { class: 'gg-screen gg-focus', tabindex: '-1', 'aria-label': cfg.name + ' session' });
      setScreen(stage);
      focusEl(stage);
      const ctx = {
        el: stage, s: s, rm: rm, last: last, best: best,
        keys: function (fn) {
          s.on(document, 'keydown', function (e) {
            if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || isTypingTarget(e.target)) return;
            fn(e);
          });
        },
        finish: function (r) {
          if (finished || s.dead || dead) return;
          finished = true;
          s.clear();
          if (session === s) session = null;
          showResult(r);
        }
      };
      try { cfg.play(ctx); } catch (err) {
        s.clear(); session = null;
        setScreen(h('p', { class: 'gg-note' }, 'This game hit an error and stopped. Close it and try again.'));
        if (window.console) console.error(err);
      }
    }

    function showResult(r) {
      resetUi();
      const score = r.score, dp = cfg.dp || 0;
      const prevLast = last, prevBest = best;
      last = { score: score, detail: r.detail, summary: r.summary };
      if (best == null || beats(score, best)) best = score;

      const cmp = [];
      if (prevLast) {
        const d = round(score - prevLast.score, dp);
        if (d === 0) cmp.push(card('Last session', cfg.fmt(prevLast.score), 'same as this one'));
        else {
          const imp = beats(score, prevLast.score);
          cmp.push(card('Last session', cfg.fmt(prevLast.score), cfg.delta(Math.abs(d), imp) + ' this time', imp ? 'gg-good' : ''));
        }
      } else cmp.push(card('Last session', 'None', 'this is the first on record'));
      if (prevBest == null) cmp.push(card('Best', cfg.fmt(score), 'first best set', 'gg-good'));
      else if (beats(score, prevBest)) cmp.push(card('Best', cfg.fmt(score), 'new best (was ' + cfg.fmt(prevBest) + ')', 'gg-good'));
      else if (round(score - prevBest, dp) === 0) cmp.push(card('Best', cfg.fmt(prevBest), 'you matched it', 'gg-good'));
      else cmp.push(card('Best', cfg.fmt(prevBest), cfg.gap(Math.abs(round(score - prevBest, dp))) + ' off it'));

      const head = h('h3', { class: 'gg-kicker gg-head', tabindex: '-1' }, 'Session complete');
      const again = h('button', { type: 'button', class: 'gg-btn gg-primary' }, 'Play again');
      setScreen(h('section', { class: 'gg-screen', 'aria-label': cfg.name + ' result' },
        head,
        h('div', { class: 'gg-score' },
          h('span', { class: 'gg-score-num' }, cfg.big(score)),
          cfg.metric.unit ? h('span', { class: 'gg-score-unit' }, cfg.metric.unit) : null,
          h('span', { class: 'gg-score-label' }, cfg.metric.label)),
        h('p', { class: 'gg-summary' }, r.summary),
        h('dl', { class: 'gg-cards' }, cmp),
        r.stats && r.stats.length ? h('dl', { class: 'gg-cards' }, r.stats.map(function (st) { return card(st[0], st[1], st[2], st[3]); })) : null,
        r.table && r.table.rows.length ? h('dl', { class: 'gg-table', 'aria-label': r.table.label }, r.table.rows.map(function (row) { return [h('dt', null, row[0]), h('dd', null, row[1])]; })) : null,
        h('div', { class: 'gg-row' }, again)));
      ui.on(again, 'click', startSession);
      focusEl(head);
      if (onDone) {
        try {
          const p = onDone({ score: score, detail: r.detail, summary: r.summary });
          if (p && typeof p.then === 'function') p.then(null, function (e) { if (window.console) console.error(e); });
        } catch (e) { if (window.console) console.error(e); }
      }
    }

    function cleanup() {
      if (dead) return;
      dead = true;
      endSession();
      ui.clear();
      if (root.parentNode) root.parentNode.removeChild(root);
    }

    el.appendChild(root);
    showIntro();
    return cleanup;
  }

  function defineGame(cfg) {
    const game = {
      id: cfg.id, name: cfg.name, skill: cfg.skill, minutes: cfg.minutes, metric: cfg.metric,
      mount: function (el, api) { return runShell(cfg, el, api); }
    };
    if (cfg.expose) game._test = cfg.expose;
    const list = (window.GradientGames = window.GradientGames || []);
    const at = list.findIndex(function (g) { return g && g.id === cfg.id; });
    if (at >= 0) list[at] = game; else list.push(game);
  }

  /* =====================================================================================
     1. Dual N-back
     ===================================================================================== */
  const NB_LETTERS = ['B', 'F', 'H', 'K', 'L', 'R', 'S', 'T'];
  const NB_TRIAL_MS = 2500, NB_SHOW_MS = 600;
  function nbStartN(last) {
    const v = last && last.detail ? Number(last.detail.nextN) : NaN;
    return clamp(Math.round(v) || 2, 1, 9);
  }
  // One channel of T stimuli drawn from k values; exactly `matches` of the scorable trials (i >= N) repeat i-N.
  function nbChannel(T, N, k, matches, rng) {
    const idx = [];
    for (let i = N; i < T; i++) idx.push(i);
    shuffle(idx, rng);
    const match = new Array(T).fill(false);
    idx.slice(0, matches).forEach(function (i) { match[i] = true; });
    const seq = [];
    for (let i = 0; i < T; i++) {
      if (i < N) seq.push(Math.floor(rng() * k));
      else if (match[i]) seq.push(seq[i - N]);
      else { let v; do { v = Math.floor(rng() * k); } while (v === seq[i - N]); seq.push(v); }
    }
    return { seq: seq, match: match };
  }

  defineGame({
    id: 'nback', name: 'Dual N-back', skill: 'Working memory', minutes: 3,
    metric: { label: 'N-back level', unit: '', better: 'higher' },
    trains: 'Keeping two streams of information updated in mind at once, the core of working memory.',
    how: function (ctx) {
      const n = nbStartN(ctx.last);
      return [
        ['This session runs at ', h('strong', null, n + '-back'), ': ' + (20 + n) + ' trials, one every 2.5 seconds.'],
        'Each trial one square of the 3' + TIMES + '3 grid lights up and a letter appears in the panel beside it.',
        ['Press ', h('strong', null, 'Position match'), ' (key ', kbd('A'), ') when the square is in the same place as ' + plural(n, 'trial') + ' back.'],
        ['Press ', h('strong', null, 'Letter match'), ' (key ', kbd('L'), ') when the letter is the same as ' + n + ' back. Both can match on one trial.'],
        '80% or better on both moves the next session up a level; under 50% on either moves it down.'
      ];
    },
    fmt: function (v) { return v + '-back'; },
    big: function (v) { return String(v); },
    delta: function (a, imp) { return (imp ? 'up ' : 'down ') + plural(a, 'level'); },
    gap: function (a) { return plural(a, 'level'); },
    play: function (c) {
      const rng = Math.random;
      const N = nbStartN(c.last), T = 20 + N, scorable = T - N, M = Math.round(scorable * 0.3);
      const P = nbChannel(T, N, 9, M, rng), L = nbChannel(T, N, NB_LETTERS.length, M, rng);
      const resp = { pos: new Array(T).fill(false), let: new Array(T).fill(false) };
      let cur = -1, t0 = 0;

      const trialEl = h('span', null, 'Get ready');
      const cells = [];
      for (let i = 0; i < 9; i++) cells.push(h('div', { class: 'gg-nb-cell', 'data-cell': i }));
      const letterEl = h('div', { class: 'gg-nb-letter', 'aria-hidden': 'true' });
      const bPos = h('button', { type: 'button', class: 'gg-btn gg-big', 'aria-keyshortcuts': 'A' }, 'Position match', kbd('A'));
      const bLet = h('button', { type: 'button', class: 'gg-btn gg-big', 'aria-keyshortcuts': 'L' }, 'Letter match', kbd('L'));
      const hint = h('p', { class: 'gg-note gg-msg', 'aria-live': 'polite' },
        'Just watch the first ' + plural(N, 'trial') + '; matches can start at trial ' + (N + 1) + '.');
      add(c.el, [
        h('div', { class: 'gg-meta' }, h('span', null, N + '-back'), trialEl),
        h('div', { class: 'gg-nb-stage' }, h('div', { class: 'gg-nb-grid', 'aria-hidden': 'true' }, cells), letterEl),
        h('div', { class: 'gg-resp' }, bPos, bLet),
        hint
      ]);

      function hide() { cells.forEach(function (x) { x.classList.remove('gg-on'); }); letterEl.textContent = ''; }
      function trial(i) {
        cur = i;
        bPos.classList.remove('gg-hit', 'gg-fa'); bLet.classList.remove('gg-hit', 'gg-fa');
        hide();
        if (i >= T) { finish(); return; }
        cells[P.seq[i]].classList.add('gg-on');
        letterEl.textContent = NB_LETTERS[L.seq[i]];
        trialEl.textContent = 'Trial ' + (i + 1) + ' / ' + T;
        if (i === N) hint.textContent = 'Matches can appear from now on.';
        c.s.after(NB_SHOW_MS, hide);
        // Schedule against the session start so timing does not drift.
        c.s.after(t0 + (i + 1) * NB_TRIAL_MS - performance.now(), function () { trial(i + 1); });
      }
      function respond(ch) {
        if (cur < 0 || cur >= T) return;
        if (cur < N) { hint.textContent = 'No match is possible yet: matches start at trial ' + (N + 1) + '.'; return; }
        if (resp[ch][cur]) return;
        resp[ch][cur] = true;
        const isMatch = (ch === 'pos' ? P : L).match[cur];
        (ch === 'pos' ? bPos : bLet).classList.add(isMatch ? 'gg-hit' : 'gg-fa');
      }
      c.s.on(bPos, 'click', function () { respond('pos'); });
      c.s.on(bLet, 'click', function () { respond('let'); });
      c.keys(function (e) {
        const k = String(e.key || '').toLowerCase();
        if (k !== 'a' && k !== 'l') return;
        e.preventDefault();
        if (!e.repeat) respond(k === 'a' ? 'pos' : 'let');
      });

      function tally(ch, chan) {
        let hits = 0, cr = 0, miss = 0, fa = 0;
        for (let i = N; i < T; i++) {
          const m = chan.match[i], r = resp[ch][i];
          if (m && r) hits++; else if (m) miss++; else if (r) fa++; else cr++;
        }
        return { acc: (hits + cr) / scorable, hits: hits, miss: miss, fa: fa };
      }
      function finish() {
        const p = tally('pos', P), l = tally('let', L);
        let nextN = N;
        if (p.acc >= 0.8 && l.acc >= 0.8) nextN = Math.min(9, N + 1);
        else if (p.acc < 0.5 || l.acc < 0.5) nextN = Math.max(1, N - 1);
        const held = p.acc >= 0.5 && l.acc >= 0.5;
        const score = held ? N : Math.max(1, N - 1);
        const pp = pct(p.acc), lp = pct(l.acc);
        const summary = held
          ? 'Held ' + N + '-back at ' + pp + '% position and ' + lp + '% letter accuracy; next session starts at ' + nextN + '-back.'
          : 'Dropped below 50% at ' + N + '-back (' + pp + '% position, ' + lp + '% letter); next session starts at ' + nextN + '-back.';
        const line = function (t) { return t.hits + ' hit' + (t.hits === 1 ? '' : 's') + ', ' + t.miss + ' missed, ' + t.fa + ' false'; };
        c.finish({
          score: score,
          detail: { n: N, posAcc: round(p.acc, 3), letterAcc: round(l.acc, 3), nextN: nextN },
          summary: summary,
          stats: [
            ['Position', pp + '%', line(p)],
            ['Letter', lp + '%', line(l)],
            ['Next session', nextN + '-back', nextN > N ? 'moving up' : nextN < N ? 'stepping down' : 'holding steady']
          ]
        });
      }
      c.s.after(1200, function () { t0 = performance.now(); trial(0); });
    }
  });

  /* =====================================================================================
     2. Digit span
     ===================================================================================== */
  function genDigits(len, rng) {
    const out = [];
    while (out.length < len) {
      const d = Math.floor(rng() * 10);
      if (out.length && d === out[out.length - 1]) continue;
      out.push(d);
    }
    return out;
  }
  const spaced = function (s) { return s.split('').join(' '); };

  defineGame({
    id: 'span', name: 'Digit span', skill: 'Short-term memory', minutes: 2,
    metric: { label: 'Span (forward + backward)', unit: 'digits', better: 'higher' },
    trains: 'Holding a sequence for a few seconds, then reversing it in your head.',
    how: function () {
      return [
        'Digits appear one at a time in the panel. When they stop, type them in the box and press Enter or tap Submit.',
        ['Forward phase first: type them ', h('strong', null, 'in the order shown'), '. Backward phase next: type them ', h('strong', null, 'in reverse'), '.'],
        'Sequences start at 4 digits and grow by one each time you get one right. Two misses in a row at the same length ends the phase.'
      ];
    },
    fmt: function (v) { return plural(v, 'digit'); },
    big: function (v) { return String(v); },
    delta: function (a, imp) { return (imp ? 'up ' : 'down ') + plural(a, 'digit'); },
    gap: function (a) { return plural(a, 'digit'); },
    play: function (c) {
      const MAX = 12, START = 4, rng = Math.random;
      let phase = 'fwd', len = START, errs = 0, seqs = 0, expected = '', awaiting = false;
      const longest = { fwd: 0, bwd: 0 };
      const phaseEl = h('span'), lenEl = h('span');
      const digitEl = h('div', { class: 'gg-digit', 'aria-hidden': 'true' });
      const pips = h('div', { class: 'gg-pips', 'aria-hidden': 'true' });
      const prompt = h('p', { class: 'gg-msg', 'aria-live': 'polite' });
      const input = h('input', {
        class: 'gg-input', type: 'text', inputmode: 'numeric', pattern: '[0-9]*', autocomplete: 'off',
        autocapitalize: 'off', spellcheck: 'false', enterkeyhint: 'done', maxlength: '24', 'aria-label': 'Digits'
      });
      const submit = h('button', { type: 'submit', class: 'gg-btn gg-primary' }, 'Submit');
      const form = h('form', { class: 'gg-form', novalidate: true, hidden: true }, input, submit);
      const fb = h('p', { class: 'gg-msg', 'aria-live': 'polite' });
      add(c.el, [
        h('div', { class: 'gg-meta' }, phaseEl, lenEl),
        h('div', { class: 'gg-stage' }, h('div', { class: 'gg-stack' }, digitEl, pips)),
        prompt, form, fb
      ]);
      const setFb = function (t, cls) { fb.textContent = t; fb.className = 'gg-msg' + (cls ? ' ' + cls : ''); };

      function round_() {
        phaseEl.textContent = phase === 'fwd' ? 'Forward' : 'Backward';
        lenEl.textContent = plural(len, 'digit');
        form.hidden = true; awaiting = false; digitEl.textContent = '';
        prompt.textContent = 'Watch the digits.';
        const seq = genDigits(len, rng);
        expected = (phase === 'fwd' ? seq : seq.slice().reverse()).join('');
        seqs++;
        pips.textContent = '';
        const dots = seq.map(function () { return h('span', { class: 'gg-pip' }); });
        add(pips, dots);
        let k = 0;
        const show = function () {
          if (k >= seq.length) { ask(); return; }
          digitEl.textContent = String(seq[k]);
          dots[k].classList.add('gg-on');
          c.s.after(800, function () { digitEl.textContent = ''; k++; c.s.after(200, show); });
        };
        c.s.after(700, show);
      }
      function ask() {
        prompt.textContent = phase === 'fwd'
          ? 'Type the ' + len + ' digits in the order shown.'
          : 'Type the ' + len + ' digits in reverse order.';
        setFb('', '');
        input.value = '';
        form.hidden = false; awaiting = true;
        focusEl(input);
      }
      c.s.on(form, 'submit', function (e) {
        e.preventDefault();
        if (!awaiting) return;
        const typed = input.value.replace(/\D/g, '');
        if (!typed) { setFb('Type the digits you saw, then press Enter.', 'gg-warn'); return; }
        awaiting = false; form.hidden = true;
        if (typed === expected) {
          longest[phase] = Math.max(longest[phase], len); errs = 0;
          setFb('Correct: ' + plural(len, 'digit') + '.', 'gg-good');
          if (len >= MAX) { c.s.after(1300, endPhase); return; }
          len++;
          c.s.after(1300, round_);
        } else {
          errs++;
          setFb('Not quite. It was ' + spaced(expected) + '; you typed ' + spaced(typed) + '.', 'gg-bad');
          c.s.after(1900, errs >= 2 ? endPhase : round_);
        }
      });

      function endPhase() {
        if (phase === 'bwd') { finish(); return; }
        form.hidden = true; digitEl.textContent = ''; pips.textContent = ''; setFb('', '');
        phaseEl.textContent = 'Forward done'; lenEl.textContent = '';
        prompt.textContent = 'Forward span: ' + plural(longest.fwd, 'digit') + '. Next, the backward phase: type each sequence in reverse order.';
        const go = h('button', { type: 'button', class: 'gg-btn gg-primary' }, 'Start backward phase');
        const row = h('div', { class: 'gg-row' }, go);
        c.el.insertBefore(row, form);
        c.s.on(go, 'click', function () {
          if (row.parentNode) row.parentNode.removeChild(row);
          phase = 'bwd'; len = START; errs = 0;
          round_();
        });
        focusEl(go);
      }
      function finish() {
        const f = longest.fwd, b = longest.bwd;
        c.finish({
          score: f + b,
          detail: { forward: f, backward: b },
          summary: 'Forward span ' + f + ' and backward span ' + b + ', ' + plural(f + b, 'digit') + ' in total.',
          stats: [['Forward', plural(f, 'digit')], ['Backward', plural(b, 'digit')], ['Sequences', String(seqs)]]
        });
      }
      round_();
    }
  });

  /* =====================================================================================
     3. Stroop
     ===================================================================================== */
  const ST_COLORS = [
    { name: 'Red', v: '--bad' }, { name: 'Green', v: '--good' },
    { name: 'Blue', v: '--growth' }, { name: 'Yellow', v: '--warn' }
  ];
  function stroopTrials(rng) {
    const t = [];
    for (let k = 0; k < 4; k++) for (let r = 0; r < 4; r++) t.push({ word: k, ink: k, cong: true });
    for (let k = 0; k < 4; k++) {
      const others = shuffle([0, 1, 2, 3].filter(function (x) { return x !== k; }), rng);
      for (let r = 0; r < 4; r++) t.push({ word: others[r % 3], ink: k, cong: false });
    }
    // Random order, avoiding the exact same word-and-ink twice in a row.
    for (let tries = 0; tries < 60; tries++) {
      shuffle(t, rng);
      if (t.every(function (x, i) { return i === 0 || x.word !== t[i - 1].word || x.ink !== t[i - 1].ink; })) break;
    }
    return t;
  }

  defineGame({
    id: 'stroop', name: 'Stroop', skill: 'Attention control', minutes: 2,
    metric: { label: 'Interference cost', unit: 'ms', better: 'lower' },
    trains: 'Overriding an automatic response (reading the word) to follow the rule you chose: name the ink.',
    how: function () {
      return [
        ['A colour word appears in coloured ink. Answer with the ', h('strong', null, 'ink colour'), ', not the word.'],
        ['Keys ', kbd('1'), ' Red, ', kbd('2'), ' Green, ', kbd('3'), ' Blue, ', kbd('4'), ' Yellow, or tap the buttons.'],
        '32 words, half matching and half clashing. Go fast but stay accurate; a word times out after 3 seconds.',
        'Your score is how much slower you are on clashing words. Lower is better.'
      ];
    },
    fmt: function (v) { return v + ' ms'; },
    big: function (v) { return String(v); },
    delta: function (a, imp) { return a + ' ms ' + (imp ? 'lower' : 'higher'); },
    gap: function (a) { return a + ' ms'; },
    play: function (c) {
      const LIMIT = 3000, trials = stroopTrials(Math.random), T = trials.length;
      let i = -1, state = 'idle', onset = 0, limitId = 0, correct = 0, wrong = 0, slow = 0;
      const rts = { cong: [], inc: [] };
      const prog = h('span', null, 'Get ready'), tallyEl = h('span');
      const word = h('div', { class: 'gg-st-word gg-st-fix', 'aria-live': 'off' }, '+');
      const fb = h('p', { class: 'gg-msg gg-muted', 'aria-live': 'polite' }, 'Answer with the ink colour.');
      const btns = ST_COLORS.map(function (col, k) {
        return h('button', { type: 'button', class: 'gg-btn gg-big', 'aria-keyshortcuts': String(k + 1), 'data-ink': k }, kbd(String(k + 1)), col.name);
      });
      add(c.el, [
        h('div', { class: 'gg-meta' }, prog, tallyEl),
        h('div', { class: 'gg-stage' }, word),
        h('div', { class: 'gg-keys4' }, btns),
        fb
      ]);
      const setFb = function (t, cls) { fb.textContent = t; fb.className = 'gg-msg ' + cls; };

      function next() {
        i++;
        if (i >= T) { finish(); return; }
        state = 'fix';
        prog.textContent = 'Word ' + (i + 1) + ' / ' + T;
        word.className = 'gg-st-word gg-st-fix'; word.style.color = ''; word.textContent = '+';
        c.s.after(450, function () { c.s.frame(show); });
      }
      function show() {
        const t = trials[i];
        word.className = 'gg-st-word';
        word.textContent = ST_COLORS[t.word].name.toUpperCase();
        word.style.color = 'var(' + ST_COLORS[t.ink].v + ')';
        word.setAttribute('data-ink', t.ink);
        onset = performance.now();
        state = 'go';
        limitId = c.s.after(LIMIT, function () { answer(-1); });
      }
      function answer(k) {
        if (state !== 'go') return;
        const rt = performance.now() - onset;
        state = 'fb';
        c.s.cancel(limitId);
        const t = trials[i];
        word.textContent = ''; word.removeAttribute('data-ink');
        if (k === t.ink) {
          correct++;
          (t.cong ? rts.cong : rts.inc).push(rt);
          setFb('Correct', 'gg-good');
          c.s.after(300, next);
        } else {
          if (k < 0) slow++; else wrong++;
          setFb((k < 0 ? 'Too slow. ' : 'Not that one. ') + 'The ink was ' + ST_COLORS[t.ink].name.toLowerCase() + '.', 'gg-bad');
          c.s.after(900, next);
        }
        tallyEl.textContent = correct + ' correct';
      }
      btns.forEach(function (b, k) { c.s.on(b, 'click', function () { answer(k); }); });
      c.keys(function (e) {
        const k = e.key && e.key.length === 1 ? '1234'.indexOf(e.key) : -1;
        if (k < 0) return;
        e.preventDefault();
        if (!e.repeat) answer(k);
      });

      function finish() {
        const congRaw = rts.cong.length ? median(rts.cong) : LIMIT;
        const incRaw = rts.inc.length ? median(rts.inc) : LIMIT;
        const cm = Math.round(congRaw), im = Math.round(incRaw);
        const score = Math.round(incRaw - congRaw);
        const acc = correct / T;
        let summary = score > 0
          ? 'Clashing words cost you ' + score + ' ms (' + im + ' vs ' + cm + ' ms median) at ' + pct(acc) + '% accuracy'
          : 'Clashing words did not slow you this time (' + im + ' vs ' + cm + ' ms median) at ' + pct(acc) + '% accuracy';
        summary += acc < 0.7 ? ', so treat this reading as rough.' : '.';
        c.finish({
          score: score,
          detail: { accuracy: round(acc, 3), congruentMs: cm, incongruentMs: im },
          summary: summary,
          stats: [
            ['Matching words', cm + ' ms', 'median, correct only'],
            ['Clashing words', im + ' ms', 'median, correct only'],
            ['Accuracy', pct(acc) + '%', wrong + ' wrong, ' + slow + ' too slow']
          ]
        });
      }
      c.s.after(900, next);
    }
  });

  /* =====================================================================================
     4. Choice reaction
     ===================================================================================== */
  function arrowSvg() {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('class', 'gg-rx-arrow');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', 'M6 50 L46 12 L46 35 L94 35 L94 65 L46 65 L46 88 Z'); // points left
    p.setAttribute('fill', 'currentColor');
    svg.appendChild(p);
    return svg;
  }

  defineGame({
    id: 'reaction', name: 'Choice reaction', skill: 'Processing speed', minutes: 1,
    metric: { label: 'Median reaction', unit: 'ms', better: 'lower' },
    trains: 'How fast you see, decide and act when there are two possible answers.',
    how: function () {
      return [
        'Watch the dot. After a short, random pause an arrow points left or right.',
        ['Press ', kbd(LARR), ' or ', kbd(RARR), ' on the keyboard, or tap the matching big button, as fast as you can.'],
        'Pressing before the arrow is a false start: you will see "Too soon" and the trial repeats.',
        '20 trials. A wrong side, or no answer within 2 seconds, counts as an error.'
      ];
    },
    fmt: function (v) { return v + ' ms'; },
    big: function (v) { return String(v); },
    delta: function (a, imp) { return a + ' ms ' + (imp ? 'faster' : 'slower'); },
    gap: function (a) { return a + ' ms'; },
    play: function (c) {
      const TOTAL = 20, LIMIT = 2000;
      let done = 0, errors = 0, falseStarts = 0, state = 'idle', side = 0, onset = 0, timer = 0, frameId = 0;
      const rts = [];
      const prog = h('span', null, 'Get ready'), fsEl = h('span');
      const dot = h('div', { class: 'gg-rx-dot', 'aria-hidden': 'true' });
      const arrow = h('div', { class: 'gg-rx-wrap', hidden: true }, arrowSvg());
      const msg = h('p', { class: 'gg-msg gg-muted', 'aria-live': 'polite' }, 'Wait for the arrow.');
      const bL = h('button', { type: 'button', class: 'gg-btn', 'aria-label': 'Left', 'aria-keyshortcuts': 'ArrowLeft' }, LARR + ' Left');
      const bR = h('button', { type: 'button', class: 'gg-btn', 'aria-label': 'Right', 'aria-keyshortcuts': 'ArrowRight' }, 'Right ' + RARR);
      add(c.el, [
        h('div', { class: 'gg-meta' }, prog, fsEl),
        h('div', { class: 'gg-stage gg-rx-stage' }, dot, arrow),
        msg,
        h('div', { class: 'gg-rx-btns' }, bL, bR)
      ]);
      const setMsg = function (t, cls) { msg.textContent = t; msg.className = 'gg-msg ' + cls; };

      function arm() {
        state = 'wait';
        prog.textContent = 'Trial ' + (done + 1) + ' / ' + TOTAL;
        arrow.hidden = true; dot.hidden = false;
        setMsg('Wait for the arrow.', 'gg-muted');
        timer = c.s.after(randInt(900, 2600), function () { frameId = c.s.frame(go); });
      }
      function go() {
        if (state !== 'wait') return;
        side = Math.random() < 0.5 ? -1 : 1;
        arrow.classList.toggle('gg-rx-right', side > 0);
        arrow.setAttribute('data-side', side > 0 ? 'right' : 'left');
        dot.hidden = true; arrow.hidden = false;
        onset = performance.now();
        state = 'go';
        timer = c.s.after(LIMIT, function () { respond(0); });
      }
      function respond(dir) {
        const now = performance.now();
        if (state === 'wait') {
          c.s.cancel(timer); c.s.cancelFrame(frameId);
          falseStarts++;
          state = 'fb';
          setMsg('Too soon. Wait for the arrow; this trial repeats.', 'gg-warn');
          fsEl.textContent = plural(falseStarts, 'false start');
          c.s.after(1200, arm);
          return;
        }
        if (state !== 'go') return;
        c.s.cancel(timer);
        state = 'fb';
        arrow.hidden = true; dot.hidden = true;
        let ok = false;
        if (dir === 0) { errors++; setMsg('Too slow: no answer within 2 seconds.', 'gg-bad'); }
        else if (dir === side) { ok = true; rts.push(now - onset); setMsg(Math.round(now - onset) + ' ms', 'gg-good'); }
        else { errors++; setMsg('Wrong side.', 'gg-bad'); }
        done++;
        c.s.after(ok ? 700 : 1000, function () { if (done >= TOTAL) finish(); else arm(); });
      }
      [[bL, -1], [bR, 1]].forEach(function (pair) {
        const b = pair[0], d = pair[1];
        // Respond on press, not release, so tap latency is not added to the reaction time.
        c.s.on(b, 'pointerdown', function (e) {
          if (e.pointerType === 'mouse' && e.button !== 0) return;
          e.preventDefault();
          respond(d);
        });
        // Keyboard activation of a focused button (Enter / Space) arrives as a click with detail 0.
        c.s.on(b, 'click', function (e) { if (e.detail === 0) respond(d); });
      });
      c.keys(function (e) {
        const k = e.key;
        if (k !== 'ArrowLeft' && k !== 'ArrowRight' && k !== 'Left' && k !== 'Right') return;
        e.preventDefault();
        if (!e.repeat) respond(k === 'ArrowLeft' || k === 'Left' ? -1 : 1);
      });

      function finish() {
        const med = rts.length ? Math.round(median(rts)) : LIMIT;
        const fastest = rts.length ? Math.round(Math.min.apply(null, rts)) : null;
        const summary = rts.length
          ? 'Median ' + med + ' ms over ' + plural(rts.length, 'correct trial') + ', with ' + plural(errors, 'error') + ' and ' + plural(falseStarts, 'false start') + '.'
          : 'No correct responses this time, so the score is set to the 2-second limit.';
        c.finish({
          score: med,
          detail: { errors: errors, falseStarts: falseStarts, fastest: fastest },
          summary: summary,
          stats: [
            ['Fastest', fastest == null ? NDASH : fastest + ' ms'],
            ['Errors', String(errors), 'wrong side or too slow'],
            ['False starts', String(falseStarts), 'repeated trials']
          ]
        });
      }
      c.s.after(800, arm);
    }
  });

  /* =====================================================================================
     5. Pharmacy calc sprint
     ===================================================================================== */
  const CALC_TYPES = ['dose', 'infusion', 'titration', 'crcl', 'dilution', 'mental'];
  const CALC_LABEL = {
    dose: 'Weight-based dose', infusion: 'Infusion rate', titration: 'mcg/kg/min to mL/h',
    crcl: 'Creatinine clearance', dilution: 'Dilution', mental: 'Mental arithmetic'
  };
  const CALC_NAME = {
    dose: 'weight-based doses', infusion: 'infusion rates', titration: 'mcg/kg/min conversions',
    crcl: 'Cockcroft' + NDASH + 'Gault', dilution: 'dilutions', mental: 'mental arithmetic'
  };

  // Standard adult and paediatric weight-based doses.
  const DOSE_DRUGS = [
    { d: 'Gentamicin', per: [5, 7], u: 'mg' },              // extended-interval aminoglycoside
    { d: 'Tobramycin', per: [7], u: 'mg' },
    { d: 'Vancomycin', per: [15, 20], u: 'mg' },
    { d: 'Enoxaparin', per: [1], u: 'mg' },                 // treatment dose, every 12 h
    { d: 'Acyclovir IV', per: [10], u: 'mg' },
    { d: 'Rocuronium', per: [0.6, 1.2], u: 'mg' },          // intubating / RSI
    { d: 'Ketamine IV', per: [1, 2], u: 'mg' },             // induction
    { d: 'Heparin IV bolus', per: [80], u: 'units' },       // VTE weight-based nomogram
    { d: 'Acetaminophen', per: [15], u: 'mg', child: true },
    { d: 'Ibuprofen', per: [10], u: 'mg', child: true },
    { d: 'Amoxicillin', per: [45], u: 'mg', child: true, extra: ' per dose' } // high-dose, twice daily
  ];
  // Continuous infusions ordered in mg/h (or g/h).
  const INF_DRUGS = [
    { d: 'Nicardipine', amt: 25, u: 'mg', vol: 250, rates: [5, 7.5, 10, 12.5, 15] },
    { d: 'Nicardipine', amt: 40, u: 'mg', vol: 200, rates: [5, 7.5, 10, 12.5, 15] },
    { d: 'Amiodarone', amt: 900, u: 'mg', vol: 500, rates: [30, 60] },   // 0.5 or 1 mg/min
    { d: 'Amiodarone', amt: 360, u: 'mg', vol: 200, rates: [30, 60] },
    { d: 'Lidocaine', amt: 2000, u: 'mg', vol: 500, rates: [60, 120, 180, 240] }, // 1-4 mg/min
    { d: 'Pantoprazole', amt: 80, u: 'mg', vol: 100, rates: [8] },
    { d: 'Clevidipine', amt: 50, u: 'mg', vol: 100, rates: [2, 4, 6, 8, 10, 12] },
    { d: 'Diltiazem', amt: 125, u: 'mg', vol: 125, rates: [5, 10, 15] },
    { d: 'Magnesium sulfate', amt: 20, u: 'g', vol: 500, rates: [1, 2] }
  ];
  // Weight-based titratable infusions in mcg/kg/min, with standard bag concentrations.
  const TIT_DRUGS = [
    { d: 'Norepinephrine', mg: 4, vol: 250, doses: [0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3] },  // 16 mcg/mL
    { d: 'Norepinephrine', mg: 8, vol: 250, doses: [0.1, 0.15, 0.2, 0.3, 0.4, 0.5] },          // 32 mcg/mL
    { d: 'Epinephrine', mg: 4, vol: 250, doses: [0.02, 0.05, 0.1, 0.15, 0.2] },                // 16 mcg/mL
    { d: 'Dopamine', mg: 400, vol: 250, doses: [3, 5, 7.5, 10, 15] },                          // 1600 mcg/mL
    { d: 'Dobutamine', mg: 500, vol: 250, doses: [2.5, 5, 7.5, 10] },                          // 2000 mcg/mL
    { d: 'Esmolol', mg: 2500, vol: 250, doses: [50, 100, 150, 200] },                          // 10000 mcg/mL
    { d: 'Milrinone', mg: 20, vol: 100, doses: [0.25, 0.375, 0.5] },                           // 200 mcg/mL
    { d: 'Nitroprusside', mg: 50, vol: 250, doses: [0.3, 0.5, 1, 2] },                         // 200 mcg/mL
    { d: 'Propofol', mg: 1000, vol: 100, doses: [10, 20, 30, 40, 50] }                         // 10000 mcg/mL
  ];

  function q(text, answer, unit, formula) { return { text: text, answer: answer, unit: unit, formula: formula }; }

  const GEN = {
    dose: function (rng) {
      const x = pick(DOSE_DRUGS, rng), per = pick(x.per, rng);
      const w = x.child ? randInt(8, 40, rng) : randInt(48, 110, rng);
      const ans = per * w;
      return q(x.d + ' ' + n2s(per) + ' ' + x.u + '/kg' + (x.extra || '') + ' for ' + an(w) + ' ' + w + ' kg ' + (x.child ? 'child' : 'patient') + '. Dose in ' + x.u + '?',
        ans, x.u, n2s(per) + ' ' + x.u + '/kg ' + TIMES + ' ' + w + ' kg = ' + n2s(ans, 1) + ' ' + x.u);
    },
    infusion: function (rng) {
      const x = pick(INF_DRUGS, rng), rate = pick(x.rates, rng);
      const conc = x.amt / x.vol, ans = rate / conc;
      return q(x.d + ' ' + n2s(x.amt) + ' ' + x.u + ' in ' + n2s(x.vol) + ' mL at ' + n2s(rate) + ' ' + x.u + '/h. Rate in mL/h?',
        ans, 'mL/h',
        n2s(x.amt) + ' ' + x.u + ' ' + DIVIDE + ' ' + n2s(x.vol) + ' mL = ' + n2s(conc, 3) + ' ' + x.u + '/mL; ' +
        n2s(rate) + ' ' + x.u + '/h ' + DIVIDE + ' ' + n2s(conc, 3) + ' ' + x.u + '/mL = ' + n2s(ans, 1) + ' mL/h');
    },
    titration: function (rng) {
      let x, dose, w, conc, ans;
      do {
        x = pick(TIT_DRUGS, rng); dose = pick(x.doses, rng); w = randInt(50, 110, rng);
        conc = x.mg * 1000 / x.vol;                 // mcg/mL
        ans = dose * w * 60 / conc;                 // mL/h
      } while (ans < 3);
      return q(x.d + ' ' + n2s(x.mg) + ' mg in ' + n2s(x.vol) + ' mL at ' + n2s(dose) + ' mcg/kg/min for ' + an(w) + ' ' + w + ' kg patient. Rate in mL/h?',
        ans, 'mL/h',
        n2s(x.mg) + ' mg ' + DIVIDE + ' ' + n2s(x.vol) + ' mL = ' + n2s(conc) + ' mcg/mL; ' +
        n2s(dose) + ' ' + TIMES + ' ' + w + ' kg ' + TIMES + ' 60 ' + DIVIDE + ' ' + n2s(conc) + ' = ' + n2s(ans, 1) + ' mL/h');
    },
    crcl: function (rng) {
      const age = randInt(25, 90, rng), female = rng() < 0.5, w = randInt(45, 110, rng);
      const scr = randInt(7, 28, rng) / 10;
      const ans = (140 - age) * w / (72 * scr) * (female ? 0.85 : 1);
      return q('Cockcroft' + NDASH + 'Gault: ' + an(age) + ' ' + age + '-year-old ' + (female ? 'woman' : 'man') +
        ', actual body weight ' + w + ' kg, SCr ' + n2s(scr) + ' mg/dL. Use actual body weight. CrCl in mL/min?',
        ans, 'mL/min',
        '(140 ' + MINUS + ' ' + age + ') ' + TIMES + ' ' + w + ' ' + DIVIDE + ' (72 ' + TIMES + ' ' + n2s(scr) + ')' +
        (female ? ' ' + TIMES + ' 0.85' : '') + ' = ' + n2s(ans, 1) + ' mL/min');
    },
    dilution: function (rng) {
      const kind = randInt(0, 5, rng);
      const v1f = function (c1, c2, v2) { return 'C1V1 = C2V2, so V1 = ' + n2s(c2) + '% ' + TIMES + ' ' + n2s(v2) + ' mL ' + DIVIDE + ' ' + n2s(c1) + '%'; };
      const v2f = function (c1, v1, c2) { return 'C1V1 = C2V2, so V2 = ' + n2s(c1) + '% ' + TIMES + ' ' + n2s(v1) + ' mL ' + DIVIDE + ' ' + n2s(c2) + '%'; };
      if (kind === 0) {
        const c2 = pick([5, 10, 12.5, 20, 25], rng), v2 = pick([100, 250, 500, 1000], rng), v1 = c2 * v2 / 50;
        return q('How many mL of 50% dextrose are needed to make ' + n2s(v2) + ' mL of ' + n2s(c2) + '% dextrose?',
          v1, 'mL', v1f(50, c2, v2) + ' = ' + n2s(v1, 1) + ' mL');
      }
      if (kind === 1) {
        const c2 = pick([60, 70], rng), v2 = pick([100, 250, 500], rng), v1 = c2 * v2 / 95;
        return q('How many mL of 95% ethanol are needed to make ' + n2s(v2) + ' mL of ' + c2 + '% ethanol?',
          v1, 'mL', v1f(95, c2, v2) + ' = ' + n2s(v1, 1) + ' mL');
      }
      if (kind === 2) {
        const v1 = pick([10, 20, 50], rng), v2 = 8.4 * v1 / 4.2;
        return q(v1 + ' mL of 8.4% sodium bicarbonate is diluted to 4.2%. Final volume in mL?',
          v2, 'mL', v2f(8.4, v1, 4.2) + ' = ' + n2s(v2, 1) + ' mL');
      }
      if (kind === 3) {
        const v1 = pick([5, 10, 20], rng), c2 = pick([0.5, 1], rng), v2 = 2 * v1 / c2;
        return q(v1 + ' mL of lidocaine 2% is diluted to ' + n2s(c2) + '%. Final volume in mL?',
          v2, 'mL', v2f(2, v1, c2) + ' = ' + n2s(v2, 1) + ' mL');
      }
      if (kind === 4) {
        const v1 = pick([50, 100], rng), v2 = 25 * v1 / 5;
        return q(v1 + ' mL of 25% albumin is diluted with 0.9% sodium chloride to 5%. Final volume in mL?',
          v2, 'mL', v2f(25, v1, 5) + ' = ' + n2s(v2, 1) + ' mL');
      }
      let v1, v2, c2;
      do { v1 = pick([50, 100], rng); v2 = pick([250, 500, 1000], rng); c2 = 50 * v1 / v2; } while (c2 < 5);
      return q(v1 + ' mL of 50% dextrose is made up to ' + n2s(v2) + ' mL with sterile water. Final concentration in %?',
        c2, '%', 'C1V1 = C2V2, so C2 = 50% ' + TIMES + ' ' + v1 + ' mL ' + DIVIDE + ' ' + n2s(v2) + ' mL = ' + n2s(c2, 1) + '%');
    },
    mental: function (rng) {
      const kind = randInt(0, 2, rng);
      if (kind === 0) {
        let a, b;
        do { a = randInt(12, 98, rng); b = randInt(12, 98, rng); } while (a % 10 === 0 || b % 10 === 0);
        const tens = b - b % 10, ones = b % 10;
        return q(a + ' ' + TIMES + ' ' + b + ' = ?', a * b, '',
          a + ' ' + TIMES + ' ' + tens + ' + ' + a + ' ' + TIMES + ' ' + ones + ' = ' + n2s(a * tens) + ' + ' + n2s(a * ones) + ' = ' + n2s(a * b));
      }
      if (kind === 1) {
        let p, n, ans;
        do { p = pick([5, 12.5, 15, 20, 25, 30, 35, 40, 45, 60, 65, 75, 80, 85], rng); n = 8 * randInt(5, 120, rng); ans = p * n / 100; } while (ans < 3);
        return q('What is ' + n2s(p) + '% of ' + n2s(n) + '?', ans, '',
          n2s(p) + ' ' + DIVIDE + ' 100 ' + TIMES + ' ' + n2s(n) + ' = ' + n2s(ans, 2));
      }
      const whole = 20 * randInt(2, 25, rng), p = 5 * randInt(1, 19, rng), part = whole * p / 100;
      return q(n2s(part) + ' is what percent of ' + n2s(whole) + '?', p, '%',
        n2s(part) + ' ' + DIVIDE + ' ' + n2s(whole) + ' ' + TIMES + ' 100 = ' + p + '%');
    }
  };

  function makeQuestion(rng, avoid, force) {
    rng = rng || Math.random;
    let type = force;
    if (!type) { do { type = pick(CALC_TYPES, rng); } while (type === avoid); }
    const out = GEN[type](rng);
    out.type = type;
    return out;
  }
  // Within 2% of the answer, or within 0.5 for small answers.
  function isCorrect(v, ans) { return Math.abs(v - ans) <= Math.max(0.02 * Math.abs(ans), 0.5) + 1e-9; }
  function parseAnswer(raw) {
    let s = String(raw == null ? '' : raw).replace(/\s+/g, '');
    s = s.replace(/[^0-9.,\-]+$/, '');                 // trailing unit, e.g. "360mg" or "25%"
    if (!s) return null;
    if (/^-?\d*,\d{1,2}$/.test(s)) s = s.replace(',', '.'); // decimal comma: "16,7"
    else s = s.replace(/,/g, '');                           // thousands: "1,500"
    if (!/^-?(\d+\.?\d*|\.\d+)$/.test(s)) return null;
    const v = parseFloat(s);
    return isFinite(v) ? v : null;
  }
  function fmtAns(x) { return n2s(x, Math.abs(x) < 10 ? 2 : 1); }

  defineGame({
    id: 'calc', name: 'Pharmacy calc sprint', skill: 'Numeracy under time pressure', minutes: 2,
    metric: { label: 'Correct per minute', unit: '/min', better: 'higher' },
    trains: 'Fast, accurate dosing arithmetic: the calculations you do at the bench, against the clock.',
    how: function () {
      return [
        '90 seconds of mixed questions: weight-based doses, infusion rates, mcg/kg/min to mL/h, Cockcroft' + NDASH + 'Gault, dilutions and mental arithmetic.',
        ['Type a number and press ', kbd('Enter'), ' or tap Submit. Answers within 2% count (within 0.5 for small numbers).'],
        'Each answer shows the correct value and the formula. Skip shows the answer and counts as a miss.'
      ];
    },
    note: 'Arithmetic practice only. Check real doses against your local protocols.',
    dp: 1,
    fmt: function (v) { return Number(v).toFixed(1) + '/min'; },
    big: function (v) { return Number(v).toFixed(1); },
    delta: function (a, imp) { return (imp ? 'up ' : 'down ') + Number(a).toFixed(1) + '/min'; },
    gap: function (a) { return Number(a).toFixed(1) + '/min'; },
    expose: { makeQuestion: makeQuestion, isCorrect: isCorrect, parseAnswer: parseAnswer, types: CALC_TYPES.slice() },
    play: function (c) {
      const DURATION = 90000;
      let correct = 0, attempted = 0, cur = null, lastType = '', over = false, endAt = 0;
      const byType = {};
      const qid = 'gg-calc-q-' + (++uid);
      const timerEl = h('span', { class: 'gg-timer', role: 'timer', 'aria-label': 'Time left' }, '1:30');
      const scoreEl = h('span', null, '0 correct');
      const kindEl = h('p', { class: 'gg-kicker' });
      const textEl = h('p', { class: 'gg-qtext', id: qid });
      const input = h('input', {
        class: 'gg-input', type: 'text', inputmode: 'decimal', autocomplete: 'off', autocapitalize: 'off',
        spellcheck: 'false', enterkeyhint: 'done', maxlength: '16', 'aria-label': 'Your answer', 'aria-describedby': qid
      });
      const unitEl = h('span', { class: 'gg-unit' });
      const submit = h('button', { type: 'submit', class: 'gg-btn gg-primary' }, 'Submit');
      const skip = h('button', { type: 'button', class: 'gg-btn' }, 'Skip');
      const form = h('form', { class: 'gg-form', novalidate: true }, input, unitEl, submit, skip);
      const warn = h('p', { class: 'gg-note gg-warn', 'aria-live': 'polite', hidden: true }, 'Enter a number, e.g. 12.5');
      const fb = h('div', { class: 'gg-fb', 'aria-live': 'polite' }, h('p', { class: 'gg-muted' }, 'The answer and formula for each question appear here.'));
      add(c.el, [
        h('div', { class: 'gg-meta' }, timerEl, scoreEl),
        h('div', { class: 'gg-q' }, kindEl, textEl),
        form, warn, fb
      ]);

      function nextQ() {
        cur = makeQuestion(Math.random, lastType);
        lastType = cur.type;
        kindEl.textContent = CALC_LABEL[cur.type];
        textEl.textContent = cur.text;
        unitEl.textContent = cur.unit;
        input.value = '';
      }
      function record(ok) {
        attempted++;
        if (ok) correct++;
        const b = byType[cur.type] || (byType[cur.type] = { correct: 0, attempted: 0 });
        b.attempted++;
        if (ok) b.correct++;
        scoreEl.textContent = correct + ' correct ' + MIDDOT + ' ' + attempted + ' tried';
      }
      function showFb(ok, given) {
        const ans = fmtAns(cur.answer) + (cur.unit ? (cur.unit === '%' ? '%' : ' ' + cur.unit) : '');
        fb.className = 'gg-fb ' + (ok ? 'gg-fb-good' : 'gg-fb-bad');
        fb.textContent = '';
        add(fb, [
          h('p', { class: 'gg-kicker' }, 'Previous ' + MIDDOT + ' ' + CALC_LABEL[cur.type]),
          h('p', null,
            h('strong', { class: ok ? 'gg-good' : 'gg-bad' }, ok ? 'Correct' : given == null ? 'Skipped' : 'Not quite'),
            ok ? ': ' + ans : ': the answer is ' + ans + (given == null ? '' : ' (you entered ' + n2s(given, 4) + ')')),
          h('p', { class: 'gg-formula' }, cur.formula)
        ]);
      }
      function timeUp() { return performance.now() >= endAt; }
      c.s.on(form, 'submit', function (e) {
        e.preventDefault();
        if (over) return;
        if (timeUp()) { end(); return; }
        const v = parseAnswer(input.value);
        if (v == null) { warn.hidden = false; focusEl(input); return; }
        warn.hidden = true;
        const ok = isCorrect(v, cur.answer);
        record(ok);
        showFb(ok, v);
        nextQ();
        focusEl(input);
      });
      c.s.on(skip, 'click', function () {
        if (over) return;
        if (timeUp()) { end(); return; }
        warn.hidden = true;
        record(false);
        showFb(false, null);
        nextQ();
        focusEl(input);
      });

      function tick() {
        const rem = endAt - performance.now();
        if (rem <= 0) { timerEl.textContent = '0:00'; end(); return; }
        const sec = Math.ceil(rem / 1000);
        timerEl.textContent = Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0');
        timerEl.classList.toggle('gg-low', rem <= 10000);
      }
      function end() {
        if (over) return;
        over = true;
        input.disabled = true;
        const score = Math.round(correct / 1.5 * 10) / 10;
        let worst = null;
        Object.keys(byType).forEach(function (t) {
          const miss = byType[t].attempted - byType[t].correct;
          if (miss > 0 && (!worst || miss > worst.miss)) worst = { t: t, miss: miss };
        });
        const summary = attempted === 0
          ? 'No answers submitted in the 90 seconds.'
          : correct + ' of ' + attempted + ' correct in 90 seconds (' + score.toFixed(1) + ' per minute)' +
            (worst ? '; most misses on ' + CALC_NAME[worst.t] + '.' : ', with no misses.');
        const rows = CALC_TYPES.filter(function (t) { return byType[t]; })
          .map(function (t) { return [CALC_LABEL[t], byType[t].correct + '/' + byType[t].attempted]; });
        c.finish({
          score: score, detail: { correct: correct, attempted: attempted, byType: byType }, summary: summary,
          stats: [['Correct', correct + '/' + attempted, attempted ? pct(correct / attempted) + '% accuracy' : 'none answered']],
          table: { label: 'Correct by question type', rows: rows }
        });
      }

      endAt = performance.now() + DURATION;
      nextQ();
      tick();
      c.s.every(200, tick);
      focusEl(input);
    }
  });
})();
