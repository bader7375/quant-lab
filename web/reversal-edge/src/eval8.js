const fs=require('fs');var self={postMessage:()=>{}};globalThis.self=self;require('vm').runInThisContext(fs.readFileSync('engine.js','utf8'));
function csv(p){const L=fs.readFileSync(p,'utf8').replace(/\r/g,'').trim().split('\n');const H=L[0].toLowerCase().split(',');const ix=k=>H.indexOf(k);const d=[],o=[],h=[],l=[],c=[],v=[];
 for(const line of L.slice(1)){const r=line.split(',');d.push(r[ix('date')]);o.push(+r[ix('open')]);h.push(+r[ix('high')]);l.push(+r[ix('low')]);c.push(+r[ix('close')]);v.push(+r[ix('volume')])}return{d,o,h,l,c,v}}
const V=csv('../rdata/VIX.csv');const fear={d:V.d,c:V.c};
const base={side:1,trig:10,stopATR:0,maxHold:10,slippage:5,adapt:true,n0:300,pool:0.5,testDays:63,riskPct:0.02,maxW:1,maxPos:4,sizeMode:"fixed",market:null,mode:"auto",acThr:0.08,entry:"limit",limitATR:0.5,exit:"prevhigh",momTrig:90,momMaxHold:30,scoreThr:0.4356};
const pc=x=>(100*x).toFixed(1)+'%',f=(m,e)=>`total ${pc(m.total_return).padStart(8)} CAGR ${pc(m.cagr).padStart(6)} Sharpe ${m.sharpe.toFixed(2)} MDD ${pc(m.max_drawdown).padStart(6)} trades ${String(m.n_trades).padStart(4)} win ${pc(m.win_rate)} inMkt ${pc(e)}`;
const ex=JSON.parse(process.env.X||"{}");Object.assign(base,ex);const sets=process.argv.slice(2).map(x=>x.split(","));
for(const syms of sets){const ds={};for(const s of syms)ds[s]=csv('../rdata/'+s+'.csv');const r=run(ds,base,fear);
 const nA=syms.reduce((a,s)=>a+(r.symbols[s]?r.symbols[s].aplus.reduce((x,y)=>x+y,0):0),0);
 console.log(syms.join("+").padEnd(42),"\n   top third (v7):",f(r.metrics.portfolioTop,r.btB.exposure),"\n   A+ only (v8)  :",f(r.metrics.portfolioAPlus,r.btA.exposure),` (A+ setups ${nA})`)}
if(process.env.PER){const syms=["TSLA_long","MSFT_long","AMZN_long","AAPL_long","F_long","TASI_long"];
 for(const s of syms){const ds={};ds[s]=csv('../rdata/'+s+'.csv');const r=run(ds,base,fear),S=r.symbols[s];
  const T=r.bt.trades.filter(t=>t.kind!==2&&!t.mom);const ix=new Map(S.d.map((d,i)=>[d,i]));
  const st=(a)=>{const x=a.map(t=>t.exit_price/t.entry_price-1-0.001);return a.length?`${a.length} tr avg ${(100*x.reduce((p,q)=>p+q,0)/x.length).toFixed(2)}% win ${pc(x.filter(v=>v>0).length/x.length)}`:"—"};
  const sg=t=>ix.get(t.entry_date)-1,isA=t=>S.aplus[sg(t)]===1,isRev=t=>S.setup[sg(t)]===1;
  const R=T.filter(isRev);console.log(s.padEnd(10),"reversal trades:",st(R),"| A+:",st(R.filter(isA)),"| not A+:",st(R.filter(t=>!isA(t))))}}
