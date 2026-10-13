/*
 * Maia Web Worker. Weights: Maia-1 by CSSLab (github.com/CSSLab/maia-chess), GPL-3.0.
 *
 *   const w = new Worker('engines/maia/worker.js');
 *   w.postMessage({type: 'init', rating: 1500});            // -> {type:'ready', rating, ms}
 *   w.postMessage({type: 'eval', id: 1, startFen, moves});    // -> {type:'result', id, policy, value, ms}
 *   errors                                                    // -> {type:'error', id, message}
 *
 * A new 'init' switches the rating; 'eval' messages wait for the most recent 'init' to finish.
 * Optional eval fields: options {temperature, historyFill}. Files are fetched relative to this script.
 */
importScripts('../../chess.js', 'maia.js');

var manifestP = null;   // Promise<manifest>
var ready = null;       // Promise<net> for the latest init
var rating = null;

function getManifest() {
  if (!manifestP) {
    manifestP = fetch('manifest.json').then(function (r) {
      if (!r.ok) throw new Error('manifest.json: HTTP ' + r.status);
      return r.json();
    });
    manifestP.catch(function () { manifestP = null; });   // allow a retry after a failed fetch
  }
  return manifestP;
}

function errMsg(e) { return String((e && e.message) || e); }

self.onmessage = function (ev) {
  var msg = ev.data || {};
  if (msg.type === 'init') {
    var t0 = performance.now(), r = Number(msg.rating);
    ready = getManifest().then(function (man) {
      var f = man.files[String(r)];
      if (!f) throw new Error('no Maia network for rating ' + msg.rating + ' (available: ' + man.ratings.join(', ') + ')');
      return fetch(f.file).then(function (res) {
        if (!res.ok) throw new Error(f.file + ': HTTP ' + res.status);
        return res.arrayBuffer();
      }).then(function (buf) {
        if (buf.byteLength !== f.bytes) throw new Error(f.file + ': expected ' + f.bytes + ' bytes, got ' + buf.byteLength);
        var net = MaiaNet.load(buf, man);
        net.rating = r;
        rating = r;
        self.postMessage({ type: 'ready', id: msg.id, rating: r, ms: performance.now() - t0 });
        return net;
      });
    });
    ready.catch(function (e) { self.postMessage({ type: 'error', id: msg.id, message: errMsg(e) }); });
  } else if (msg.type === 'eval') {
    if (!ready) { self.postMessage({ type: 'error', id: msg.id, message: 'Maia worker: send {type:"init", rating} first' }); return; }
    var mine = ready;
    mine.then(function (net) {
      var res = net.evaluate(msg.startFen, msg.moves || [], msg.options);
      self.postMessage({ type: 'result', id: msg.id, rating: net.rating, policy: res.policy, value: res.value, ms: res.ms,
        terminal: res.terminal });
    }).catch(function (e) { self.postMessage({ type: 'error', id: msg.id, message: errMsg(e) }); });
  } else {
    self.postMessage({ type: 'error', id: msg.id, message: 'Maia worker: unknown message type ' + msg.type });
  }
};
