const fs = require('fs');
const src = fs.readFileSync('/home/user/quant-lab/web/reversal-edge/src/engine.js', 'utf8');
const self = { postMessage() {}, addEventListener() {} };
const E = new Function('self', 'importScripts', src + '\n;return {volSuite, pulseCalc, wilderRSI};')(self, () => {});
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
for (const [s, x] of Object.entries(D)) {
  const R = E.volSuite(x.o, x.h, x.l, x.c), P = E.pulseCalc(R, x.h, x.l, x.c), rsi = E.wilderRSI(x.c, 14);
  const cmp = (a, b) => { let mx = 0, nb = 0; for (let i = 0; i < a.length; i++) { const u = Number.isFinite(a[i]) ? a[i] : -999; if ((u === -999) !== (b[i] === -999)) nb++; else if (u !== -999) mx = Math.max(mx, Math.abs(u - b[i])); } return `max diff ${mx.toExponential(1)}, NaN mismatches ${nb}`; };
  console.log(s, 'bars', x.c.length, '| M:', cmp(P.M, x.M), '| acc:', cmp(P.acc, x.acc), '| RSI14:', cmp(rsi, x.rsi));
}
