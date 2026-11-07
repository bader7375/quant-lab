s = open("app3.js").read()
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:80], s.count(a)); s = s.replace(a, b)
rep('''  else if(s.zwatch&&s.zwatch[c]){cls="long";lab="Deep-value watch";say=`<b>Long-term Z turned up through −2.5</b> (now ${fmt(z,2)}). Such turns averaged +5.0% net, 68% winners, about 39 days (sell at Z −1 or after 60 days), but they cluster in sell-offs: small size only.`}''',
'''  else if(s.zcx&&s.zcx[c]){const zz=s.zc[c],pct0=typeof MLPF!=="undefined"&&MLPF&&MLPF.ranks?MLPF.ranks[st.sym]:NaN,on=typeof MLPF!=="undefined"&&MLPF&&MLPF.pm>0,cem=typeof sectorInfo==="function"&&(sectorInfo(st.sym)||{}).g==="Cement",ok=pct0>=.5&&on&&!cem;
   cls=ok?"long":"";lab=ok?"Z rebound (small)":"Z extreme";
   say=`<b>Stretch Z reached an extreme</b> (${fmt(zz,2)}, ${zcRareTxt(zz)}). `+(ok?"With the ML rank ≥ 50% and the market model positive, first touches like this averaged +7.2% net over 20 days in 2020–26 (+11.4% in 2013–19), about 3 in 4 winners. Plan: buy small (5% of the account) at the next open and sell 20 sessions later. Act at the extreme rather than waiting for a bounce: late entries gave the edge away in every test period."
    :cem?"Cement stocks at extremes kept lagging other cement stocks in 2004–12, 2013–19 and 2020–26: no rebound trade here.":`Not a trade: it needs ${[!(pct0>=.5)?"an ML rank of at least 50%":"",!on?"the market model positive":""].filter(Boolean).join(" and ")}.`)}''')
rep('''  say+=` Long-term Z (250d): <b>${fmt(z,2)}</b>.`;''', '''  {const zz=s.zc?s.zc[c]:NaN;say+=` Stretch Z: <b>${fmt(zz,2)}</b> (${zcRareTxt(zz)}).`}''')
rep('''  h+=`<div class="top2"><div><div class="lab">long-term Z (250 days)</div><div class="bigp" style="color:${z<=-2.5?"#4f96f0":z>=2.5?"#e66767":"inherit"}">${fmt(z,2)}</div><div class="note">${z<=-2.5?"deep below its yearly mean":z>=2.5?"far above its yearly mean":"within ±2.5 of its yearly mean"}${s.zwatch&&s.zwatch[i]?" · deep-value watch fired":""}</div></div>''',
'''  const zs=s.zc?s.zc[i]:NaN,zo=zcOutcome(zs),own=s.zc?zcOwnPct(s.zc,i):NaN;
  h+=`<div class="top2"><div><div class="lab">stretch Z (10/20/60 days)</div><div class="bigp" style="color:${zcColor(zs)}">${fmt(zs,2)}</div><div class="note">${zcRareTxt(zs)}${s.zcx&&s.zcx[i]?" · extreme touched today":""}</div></div>''')
rep('''  if(ARR&&ARR.zbArr&&isF(ARR.zbArr.m[i])){const m=ARR.zbArr.m[i],sd=ARR.zbArr.sd[i],P=f=>fp(Math.exp(m+f*sd));h+=`<div class="sec">long-term Z price levels (250 days)</div>''',
'''  if(isF(zs)&&zo){h+=`<div class="sec">stretch Z: how unusual, and what followed</div><table class="t"><tr><td>how rare (liquid Saudi stocks 2004–2026)</td><td class="n">${zcRareTxt(zs)}</td></tr>
   <tr><td>this stock's own history</td><td class="n">${isF(own)?(own<=.5?`lower than ${Math.round(100*(1-own))}% of its days`:`higher than ${Math.round(100*own)}% of its days`):"—"}</td></tr>
   <tr><td>next 20 days at this level (all stocks)</td><td class="n"><b class="${cl(zo.xs)}">${spct(zo.xs,1)}</b> vs market · beat it ${Math.round(100*zo.beat)}% · avg ${spct(zo.net,1)} net</td></tr>
   <tr><td>long-term Z 250d (context)</td><td class="n">${fmt(z,2)}</td></tr></table>
   <div class="note">Stretch Z = how many of its own normal daily moves the stock has travelled over 10, 20 and 60 days (averaged). Unlike the 250-day price Z, its lower tail rebounded in all three test eras (2004–12, 2013–19, 2020–26). Act at the extreme: waiting for Z to recover to −1 gave the edge away.</div>`}
  if(ARR&&ARR.zbArr&&isF(ARR.zbArr.m[i])){const m=ARR.zbArr.m[i],sd=ARR.zbArr.sd[i],P=f=>fp(Math.exp(m+f*sd));h+=`<div class="sec">long-term Z price levels (250 days, context)</div>''')
open("app3.js", "w").write(s)
s = open("app6.js").read()
rep(''' if(s&&i>=0&&s.z250&&isF(s.z250[i])){const z=s.z250[i];
  out.push(`Long-term Z (250 days): <b>${z.toFixed(2)}</b> — ${z<=-2.5?"deep below its yearly mean: watch for a turn back above −2.5 (the deep-value watch)":z>=2.5?"far above its yearly mean: stretched, but in the 2013–2026 test skipping stretched breakouts did not help":z<=-1?"below its yearly mean":z>=1?"above its yearly mean":"near its yearly mean"}.`);
  if(s.zwatch&&s.zwatch[i])out.push("<b>Deep-value watch fired today:</b> the long-term Z turned back up through −2.5. Such turns (ML rank ≥ 50%) averaged +5.0% net, 68% winners, about 39 days, exit when Z reaches −1 or after 60 days. They cluster in market sell-offs, so as an automatic portfolio they lost; use small size (≤ 5%) and judgment.")}''',
''' if(s&&i>=0&&s.zc&&isF(s.zc[i])){const z=s.zc[i],o=zcOutcome(z);
  out.push(`Stretch Z: <b>${z.toFixed(2)}</b> (${zcRareTxt(z)}); at this level stocks went on to ${o?`${spct(o.xs,1)} vs the market over 20 days`:"—"}.${z<=ZC_LINE?" <b>At the extreme line</b>: first touches with ML rank ≥ 50% and the market model positive are the optional Z-rebound trade.":z>=3?" Stretched up: in tests, skipping or exiting stretched stocks did not help the Core.":""}`);
  if(s.zcx&&s.zcx[i])out.push("<b>Stretch Z touched the extreme line today.</b>")}''')
rep(''' if(saudiSym(sym)&&s.z250&&isF(s.z250[i]))good.push(`long-term Z ${s.z250[i].toFixed(2)}`);''',
    ''' if(saudiSym(sym)&&s.zc&&isF(s.zc[i]))good.push(`stretch Z ${s.zc[i].toFixed(2)} (${zcRareTxt(s.zc[i])})`);''')
rep(''' else if(s.zwatch&&s.zwatch[i]&&saudiSym(sym)){const pct=MLPF&&MLPF.ranks?MLPF.ranks[sym]:NaN;Object.assign(o,{kind:"zwatch",rank:2.8,action:"deep-value watch (small size)",entry:c,exitTxt:"sell when the 250-day Z reaches −1, or after 60 days",maxHold:60,edge:null});
  good.push(`long-term Z turned up through −2.5 (now ${s.z250[i].toFixed(2)}): such turns averaged +5.0% net, 68% winners, about 39 days`);
  if(!(pct>=.5))warn.push(isF(pct)?`ML rank ${Math.round(100*pct)}th percentile: below 50%, where these turns did worse (+3.5% vs +5.0%)`:"no ML rank for this stock");
  warn.push("not an automatic trade: in a portfolio these signals clustered in sell-offs and lost; keep it to 5% or less")}''',
''' else if(s.zcx&&s.zcx[i]&&saudiSym(sym)&&!isIndex){const pct=MLPF&&MLPF.ranks?MLPF.ranks[sym]:NaN,on=MLPF&&MLPF.pm>0,cem=typeof sectorInfo==="function"&&(sectorInfo(sym)||{}).g==="Cement",ok=pct>=.5&&on&&!cem;
  Object.assign(o,{kind:ok?"rev":"weak",rank:ok?1.8:4,action:ok?"Z-rebound buy (small size)":"skip: stretch-Z extreme without the filters",entry:ok?c:null,exitTxt:ok?"sell at the open 20 trading days later":null,maxHold:ok?20:null,edge:null});
  good.push(`stretch Z touched the extreme line today (${s.zc[i].toFixed(2)}, ${zcRareTxt(s.zc[i])}). First touches with ML rank ≥ 50% and the market model positive averaged +7.2% net in 20 days, 78% winners (2020–26; 2013–19 +11.4%, 79%)`);
  if(!(pct>=.5))warn.push(isF(pct)?`ML rank ${Math.round(100*pct)}th percentile: needs 50% or more`:"no ML rank for this stock");
  if(!on)warn.push("market model negative: the Z rebound is only taken when it is positive");
  if(cem)warn.push("cement: stocks at extremes kept lagging other cement stocks in 2004–12, 2013–19 and 2020–26");
  warn.push("optional sleeve: 5% per position, at most 5 at once, hold 20 sessions; next to the Core it added about +1.5%/yr at the same Sharpe (worst drawdown −19% vs −17%)")}''')
open("app6.js", "w").write(s)
print("ok")
