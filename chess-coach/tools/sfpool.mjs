// A pool of Stockfish 17.1 (WASM build, run by Node) child processes for offline analysis.
// analyse(fen, {depth, movetime, multipv, searchmoves}) -> {best, lines:[{pv, cp, mate, wdl, cpWhite, wdlWhite, depth}]}
import { spawn } from 'child_process';
import path from 'path';
const root = path.join(path.dirname(new URL(import.meta.url).pathname), '..');

function parseInfo(l) {
  if (/ (lower|upper)bound/.test(l)) return null;
  const d = l.match(/\bdepth (\d+)/), mp = l.match(/\bmultipv (\d+)/), sc = l.match(/\bscore (cp|mate) (-?\d+)/), wd = l.match(/\bwdl (\d+) (\d+) (\d+)/), pv = l.match(/ pv (.+?)(?: bmc .*)?$/);
  if (!d || !sc || !pv) return null;
  return { depth: +d[1], multipv: mp ? +mp[1] : 1, cp: sc[1] === 'cp' ? +sc[2] : null, mate: sc[1] === 'mate' ? +sc[2] : null, wdl: wd ? [+wd[1], +wd[2], +wd[3]] : null, pv: pv[1].trim().split(/\s+/) };
}
export const scoreCp = (s) => (s.mate != null ? (s.mate > 0 ? 10000 - s.mate * 10 : -10000 - s.mate * 10) : s.cp);

class Proc {
  constructor() {
    this.p = spawn(process.execPath, [path.join(root, 'engines/sf17-lite.js')], { stdio: ['pipe', 'pipe', 'inherit'] });
    this.buf = ''; this.onLine = null;
    this.p.stdout.on('data', (d) => { this.buf += d; let i; while ((i = this.buf.indexOf('\n')) >= 0) { const l = this.buf.slice(0, i).trim(); this.buf = this.buf.slice(i + 1); if (this.onLine) this.onLine(l); } });
    this.send('uci'); this.send('setoption name UCI_ShowWDL value true'); this.send('setoption name Hash value 64'); this.send('setoption name Threads value 1');
  }
  send(c) { this.p.stdin.write(c + '\n'); }
  run(fen, { depth = 0, movetime = 0, nodes = 0, multipv = 1, searchmoves = null }) {
    return new Promise((res) => {
      const lines = {}; const white = fen.split(' ')[1] === 'w';
      this.onLine = (l) => {
        if (l.startsWith('info')) { const p = parseInfo(l); if (p) lines[p.multipv] = p; }
        else if (l.startsWith('bestmove')) {
          this.onLine = null;
          const ls = Object.values(lines).sort((a, b) => a.multipv - b.multipv).map((x) => ({ ...x, cpWhite: (white ? 1 : -1) * scoreCp(x), wdlWhite: x.wdl ? (white ? x.wdl : [x.wdl[2], x.wdl[1], x.wdl[0]]) : null }));
          const best = l.split(' ')[1];
          res({ best: best && best !== '(none)' ? best : null, lines: ls });
        }
      };
      this.send('ucinewgame'); this.send('setoption name MultiPV value ' + multipv); this.send('position fen ' + fen);
      let go = 'go'; if (depth) go += ' depth ' + depth; if (movetime) go += ' movetime ' + movetime; if (nodes) go += ' nodes ' + nodes;
      if (searchmoves && searchmoves.length) go += ' searchmoves ' + searchmoves.join(' ');
      this.send(go);
    });
  }
  quit() { try { this.send('quit'); } catch {} }
}

export class Pool {
  constructor(n = 4) { this.procs = Array.from({ length: n }, () => new Proc()); this.free = [...this.procs]; this.waiting = []; }
  async analyse(fen, opts = {}) {
    const p = this.free.pop() || await new Promise((r) => this.waiting.push(r));
    try { return await p.run(fen, opts); } finally { const w = this.waiting.shift(); if (w) w(p); else this.free.push(p); }
  }
  close() { for (const p of this.procs) p.quit(); }
}
