// Engine harness: node run.js <set> <single|portfolio> '<cfg json>' <out.json> [symbols comma list]
const fs=require('fs'),path=require('path');var self={postMessage:()=>{}};globalThis.self=self;
require('vm').runInThisContext(fs.readFileSync(path.join(__dirname,process.env.ENGINE||'engine_lab.js'),'utf8'));
const ROOT=path.join(__dirname,'..');
function csv(p){const L=fs.readFileSync(p,'utf8').replace(/\r/g,'').trim().split('\n');const H=L[0].toLowerCase().split(',');const ix=k=>H.indexOf(k);const d=[],o=[],h=[],l=[],c=[],v=[];
 for(const line of L.slice(1)){const r=line.split(',');d.push(r[ix('date')]);o.push(+r[ix('open')]);h.push(+r[ix('high')]);l.push(+r[ix('low')]);c.push(+r[ix('close')]);v.push(+r[ix('volume')])}return{d,o,h,l,c,v}}
const V=csv(path.join(ROOT,'rdata/VIX.csv'));const fear=process.env.NOFEAR?null:{d:V.d,c:V.c};
const BASE={side:1,trig:10,stopATR:0,maxHold:10,slippage:5,adapt:true,n0:300,pool:0.5,testDays:63,riskPct:0.02,maxW:1,maxPos:4,sizeMode:"fixed",market:null,mode:"auto",acThr:0.08,entry:"limit",limitATR:0.5,exit:"prevhigh",momTrig:90,momMaxHold:30,scoreThr:0.4356,aplusMult:1,otherMult:1,grade:"all"};
const [set,how,cj,out,only]=process.argv.slice(2);const cfg=Object.assign({},BASE,JSON.parse(cj||"{}"));
const dir=path.join(ROOT,'eng',set);let files=fs.readdirSync(dir).filter(f=>f.endsWith('.csv')).map(f=>f.slice(0,-4));if(only)files=files.filter(f=>only.split(',').includes(f));
function pm(eq,d,from,to){const ix=d.map((x,i)=>x>=from&&x<to?i:-1).filter(i=>i>=0);if(ix.length<60)return null;const e=ix.map(i=>eq[i]);
 const r=e.slice(1).map((v,i)=>v/e[i]-1),m=r.reduce((a,b)=>a+b,0)/r.length,sd=Math.sqrt(r.reduce((a,v)=>a+(v-m)**2,0)/(r.length-1));let pk=-1e99,mdd=0;e.forEach(v=>{pk=Math.max(pk,v);mdd=Math.min(mdd,v/pk-1)});
 const tot=e[e.length-1]/e[0]-1;return{sharpe:sd>0?m/sd*Math.sqrt(252):0,cagr:Math.pow(1+tot,252/r.length)-1,mdd,tot,days:r.length}}
const PER=[["all","0000","9999"],["design","0000","2013-01-01"],["test","2013-01-01","9999"]];
function summarize(res,syms){const bt=res.bt;const o={syms,cfg,periods:{},bh:{},exposure:bt.exposure,eq:bt.eq.map(v=>+v.toFixed(0)),bheq:bt.bh.map(v=>+v.toFixed(0)),d:bt.d,inv:(bt.inv||[]).map(v=>+v.toFixed(4)),trades:bt.trades.map(t=>({s:t.symbol,k:t.direction==="momentum"?2:1,e:t.entry_date,x:t.exit_date,b:t.bars_held,r:t.exit_price/t.entry_price-1,w:t.weight,why:t.exit_reason}))};
 for(const [nm,a,b] of PER){o.periods[nm]=pm(bt.eq,bt.d,a,b);o.bh[nm]=pm(bt.bh,bt.d,a,b)}
 // in-market flags per day for exposure by period
 return o}
const t0=Date.now();const R=[];
if(how==="portfolio"){const ds={};for(const s of files)ds[s]=csv(path.join(dir,s+'.csv'));const res=run(ds,cfg,fear);R.push(summarize(res,files))}
else for(const s of files){const ds={};ds[s]=csv(path.join(dir,s+'.csv'));try{const res=run(ds,cfg,fear);R.push(summarize(res,[s]))}catch(e){R.push({syms:[s],err:String(e)})}}
fs.writeFileSync(out,JSON.stringify(R));console.error(`${set} ${how} ${files.length} syms ${((Date.now()-t0)/1000).toFixed(0)}s -> ${out}`);
