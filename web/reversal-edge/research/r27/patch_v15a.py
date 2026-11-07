import json
Z = json.load(open("../r27/z_scale.json"))
edges = Z["edges"]; out = [[round(r["xs20"], 4), round(r["beat_mkt"], 4), round(r["net20"], 4), round(r["up"], 4)] for r in Z["rows"]]
q = sorted((round(v, 3), float(k)) for k, v in Z["quantiles"].items())
helpers = '''// ------------------------------------------------ v15 stretch Z: the 10/20/60-day move in units of the stock's own volatility, with an intuitive scale
// scale = all liquid Saudi stocks 2004-2026 (Tadawul library 2004-12 + Yahoo 2013-26), round-27 research
const ZC_LINE=-2.68,ZC_EDGES=@E@,ZC_OUT=@O@,ZC_Q=@Q@;
function stretchZ(c){const n=c.length,rr=new Array(n).fill(NaN),sd=new Array(n).fill(NaN),out=new Array(n).fill(NaN);
 for(let i=1;i<n;i++){const a=Math.log(c[i]),b=Math.log(c[i-1]);if(isF(a)&&isF(b))rr[i]=Math.max(-.25,Math.min(.25,a-b))}
 for(let i=59;i<n;i++){let s1=0,s2=0,m=0;for(let k=i-59;k<=i;k++)if(isF(rr[k])){s1+=rr[k];s2+=rr[k]*rr[k];m++}if(m>=40)sd[i]=Math.sqrt(Math.max(1e-12,(s2-s1*s1/m)/(m-1)))}
 const zk=K=>{const z=new Array(n).fill(NaN);for(let i=K;i<n;i++){let s1=0,m=0;for(let k=i-K+1;k<=i;k++)if(isF(rr[k])){s1+=rr[k];m++}if(m>=.8*K&&isF(sd[i-K])&&sd[i-K]>0)z[i]=s1/(sd[i-K]*Math.sqrt(K))}return z};
 const a=zk(10),b=zk(20),e=zk(60);for(let i=0;i<n;i++)if(isF(a[i])&&isF(b[i])&&isF(e[i]))out[i]=(a[i]+b[i]+e[i])/3;return out}
function zcCdf(z){if(!isF(z))return NaN;const Q=ZC_Q;if(z<=Q[0][0])return Q[0][1]/2;if(z>=Q[Q.length-1][0])return 1-(1-Q[Q.length-1][1])/2;
 for(let k=1;k<Q.length;k++)if(z<=Q[k][0]){const [x0,p0]=Q[k-1],[x1,p1]=Q[k];return p0+(p1-p0)*(z-x0)/(x1-x0)}return NaN}
function zcRareTxt(z){const p=zcCdf(z);if(!isF(p))return "—";if(p<=.5){const n=Math.round(1/p);return `lower than ${(100*(1-p)).toFixed(p<.02?1:0)}% of days${p<.1?` (about 1 day in ${n})`:""}`}
 const n=Math.round(1/(1-p));return `higher than ${(100*p).toFixed(p>.98?1:0)}% of days${p>.9?` (about 1 day in ${n})`:""}`}
function zcOutcome(z){if(!isF(z))return null;let k=0;while(k<ZC_OUT.length-1&&z>ZC_EDGES[k+1])k++;const [xs,beat,net,up]=ZC_OUT[k];return {xs,beat,net,up,lo:ZC_EDGES[k],hi:ZC_EDGES[k+1]}}
function zcOwnPct(arr,i){const v=arr[i];if(!isF(v))return NaN;let a=0,b=0;for(let k=0;k<=i;k++)if(isF(arr[k])){b++;if(arr[k]<=v)a++}return b>=250?a/b:NaN}
function zcColor(z){return !isF(z)?"inherit":z<=ZC_LINE?"#4f96f0":z<=-1.5?"#7fb2f0":z>=3?"#e66767":z>=2?"#f0a0a0":"inherit"}
'''.replace("@E@", json.dumps(edges)).replace("@O@", json.dumps(out)).replace("@Q@", json.dumps([list(x) for x in q]))
s = open("app2.js").read()
assert "ZC_LINE" not in s
s = helpers + s
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a)); s = s.replace(a, b)
rep('A.zlArr=m.map((x,i)=>isF(x)?(Math.log(c[i])-x)/sd[i]:NaN)}', 'A.zlArr=m.map((x,i)=>isF(x)?(Math.log(c[i])-x)/sd[i]:NaN);A.zsArr=s&&s.zc?s.zc:stretchZ(d.c)}')
rep('A.zl=L(s&&s.z250?s.z250:A.zlArr);', 'A.zl=L(s&&s.z250?s.z250:A.zlArr);A.zs=L(A.zsArr);')
rep('["zl","Long-term Z (250d)"]', '["zs","Stretch Z (10/20/60d)"],["zl","Long-term Z (250d)"]')
rep(''' if(UI.pn.zl){P.zl=pane++;''', ''' if(UI.pn.zs){P.zs=pane++;SER.zs=chart.addSeries(LW.BaselineSeries,{baseValue:{type:"price",price:0},lineWidth:2,priceLineVisible:false,title:"Stretch Z",topLineColor:"#e66767",topFillColor1:"rgba(230,103,103,.12)",topFillColor2:"rgba(230,103,103,0)",bottomLineColor:"#4f96f0",bottomFillColor1:"rgba(57,135,229,0)",bottomFillColor2:"rgba(57,135,229,.18)",priceFormat:{type:"price",precision:2,minMove:.01}},P.zs);
  for(const [p,c,t] of [[3,"rgba(230,103,103,.7)","+3 top 1%"],[ZC_LINE,"rgba(79,150,240,.9)","−2.7 extreme"],[-3.5,"rgba(79,150,240,.5)","−3.5"]])SER.zs.createPriceLine({price:p,color:c,lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:true,title:t})}
 if(UI.pn.zl){P.zl=pane++;''')
rep('const DKEYS=["sect",', 'const DKEYS=["zs","sect",')
rep('''   else if(s.zwatch&&s.zwatch[i]&&UI.ov.sys&&saudiSym(st.sym))mk.push({time:d.d[i],position:"belowBar",shape:"circle",color:"#4f96f0",text:"Z",size:1});''',
    '''   else if(s.zcx&&s.zcx[i]&&UI.ov.sys&&saudiSym(st.sym))mk.push({time:d.d[i],position:"belowBar",shape:"circle",color:"#4f96f0",text:"Z",size:1});''')
rep(''',zl=ARR&&ARR.zlArr?ARR.zlArr[i]:NaN;''', ''',zl=ARR&&ARR.zlArr?ARR.zlArr[i]:NaN,zs=ARR&&ARR.zsArr?ARR.zsArr[i]:NaN;''')
rep('''<span><b>Z250</b> <span style="color:${isF(zl)?(zl<=-2.5?"#4f96f0":zl>=2.5?"#f08c8c":"inherit"):"inherit"};font-weight:600">${fmt(zl,2)}</span></span>''',
    '''<span title="10/20/60-day move in units of its own volatility; ${esc(zcRareTxt(zs))}"><b>Stretch Z</b> <span style="color:${zcColor(zs)};font-weight:600">${fmt(zs,2)}</span></span><span class="lk">Z250 ${fmt(zl,2)}</span>''')
open("app2.js", "w").write(s)
a = open("app1.js").read(); x = 'UI.pn=Object.assign({pulse:true,edge:true,rsi:true,z:true,zl:true,'; assert a.count(x) == 1
open("app1.js", "w").write(a.replace(x, 'UI.pn=Object.assign({pulse:true,edge:true,rsi:true,z:true,zs:true,zl:false,'))
print("ok")
