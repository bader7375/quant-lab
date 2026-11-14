import asyncio, json, re, sys, pandas as pd, numpy as np
from playwright.async_api import async_playwright
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"; CUT = sys.argv[1] if len(sys.argv) > 1 else None
ML = open(f"{SP}/r27/today27.json").read(); SC = open(f"{SP}/ml26/sectors.json").read()
def doc(code, path):
    d = pd.read_csv(path, index_col=0, parse_dates=True); d = d[(d.close > 0)].loc["2015":(CUT or "2100")]; k = d.adjclose / d.close
    rows = [[int(t.strftime("%Y%m%d")), round(float(o), 4), round(float(h), 4), round(float(l), 4), round(float(c), 4), int(v)] for t, o, h, l, c, v in zip(d.index, d.open * k, d.high * k, d.low * k, d.adjclose, d.volume)]
    return {"sym": code, "source": "Yahoo test", "fetched_at": "2026-10-24T11:00:00Z", "adjusted": True, "rows": rows}
BARS = {"SPY": doc("SPY", f"{SP}/edge26/data/idx/SPY.csv"), "QQQ": doc("QQQ", f"{SP}/edge26/data/idx/QQQ.csv"), "1302": doc("1302", f"{SP}/edge26/data/d/1302.SR.csv")}
MOCK = """window.__ML=%s;window.__SC=%s;window.__B=%s;window.claude={use:async k=>k==='db'?{collection:n=>{const q={onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML},{id:'sectors',data:()=>window.__SC}]:n==='bars'?Object.entries(window.__B).map(([id,b])=>({id,data:()=>b})):[]}),1500);return()=>{}},orderBy:()=>q,limit:()=>q};return q}}:null};""" % (ML, SC, json.dumps(BARS))
async def done(pg): await pg.wait_for_function("document.getElementById('runmsg').textContent.startsWith('Done') && !document.getElementById('run').disabled", timeout=400000)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = await b.new_page(viewport={"width": 1400, "height": 1600}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.add_init_script(MOCK)
        await pg.goto(f"file://{SP}/QuantLab-ReversalEdge-v20.html"); await done(pg); await pg.wait_for_timeout(2500)
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300)
        for c in ("SPY", "QQQ"):
            el = await pg.query_selector(f'#lib-t input[data-lib="{c}"]')
            if el: await el.check(); await pg.wait_for_timeout(1500); await done(pg); await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(200)
            else: print("no library row for", c)
        await pg.wait_for_timeout(3000); await done(pg)
        await pg.click("#tabs button[data-t=chart]"); await pg.wait_for_timeout(800)
        for c in ("SPY", "QQQ"):
            try:
                await pg.select_option("#sym", c); await pg.wait_for_timeout(2500); sb = await pg.inner_text("#sigbar"); k = sb.find("US index dip rule"); print(c, "CARD:", sb[k:k + 900].split("Now:")[-1][:260].replace("\n", " ") if k >= 0 else "no US note: " + sb[:200])
            except Exception as ex: print(c, "select failed", ex)
        await pg.click("#tabs button[data-t=scan]"); await pg.wait_for_timeout(800)
        cn = await pg.inner_text("#core-note"); j = cn.find("US index dip rule"); print("CORE US:", cn[j:j + 330].replace("\n", " "))
        print("errors:", errs[:5]); await b.close()
asyncio.run(main())
