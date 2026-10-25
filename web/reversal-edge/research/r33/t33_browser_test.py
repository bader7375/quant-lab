import asyncio, json, re, pandas as pd, numpy as np
from playwright.async_api import async_playwright
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
ML = open(f"{SP}/r27/today27.json").read(); SC = open(f"{SP}/ml26/sectors.json").read()
def doc(code):
    d = pd.read_csv(f"{SP}/edge26/data/d/{code}.SR.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & (d.volume > 0)].loc["2019-02":]; k = d.adjclose / d.close
    rows = [[int(t.strftime("%Y%m%d")), round(float(o), 4), round(float(h), 4), round(float(l), 4), round(float(c), 4), int(v)] for t, o, h, l, c, v in zip(d.index, d.open * k, d.high * k, d.low * k, d.adjclose, d.volume)]
    return {"sym": code, "source": "Yahoo test", "fetched_at": "2026-10-24T11:00:00Z", "adjusted": True, "rows": rows}
CODES = ["6010", "3020", "1302"]
BARS = {c: doc(c) for c in CODES}
MOCK = """window.__ML=%s;window.__SC=%s;window.__B=%s;window.claude={use:async k=>k==='db'?{collection:n=>{const q={onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML},{id:'sectors',data:()=>window.__SC}]:n==='bars'?Object.entries(window.__B).map(([id,b])=>({id,data:()=>b})):[]}),1500);return()=>{}},orderBy:()=>q,limit:()=>q};return q}}:null};""" % (ML, SC, json.dumps(BARS))
ZW = pd.read_pickle(f"{SP}/r33/zb_weekly.pkl"); ZM = pd.read_pickle(f"{SP}/r33/zb_monthly.pkl")
async def done(pg): await pg.wait_for_function("document.getElementById('runmsg').textContent.startsWith('Done') && !document.getElementById('run').disabled", timeout=400000)
def num(pat, t):
    m = re.search(pat, t); return float(m.group(1).replace("−", "-")) if m else None
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = await b.new_page(viewport={"width": 1400, "height": 2200}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.add_init_script(MOCK)
        await pg.goto(f"file://{SP}/QuantLab-ReversalEdge-v19.html"); await done(pg); await pg.wait_for_timeout(2500)
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300)
        for c in CODES: await pg.check(f'#lib-t input[data-lib="{c}"]'); await pg.wait_for_timeout(1500); await done(pg); await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(3000); await done(pg)
        await pg.click("#tabs button[data-t=chart]"); await pg.wait_for_timeout(800)
        await pg.select_option("#sym", "6010"); await pg.wait_for_timeout(2500)
        sb = await pg.inner_text("#sigbar"); print("SIGNAL BAR 6010:", sb[:520].replace("\n", " | "))
        ins = await pg.inner_text("#inspbody"); k = ins.find("weekly stretch Z"); print("INSPECTOR weekly/accounts:", ins[k:k + 330].replace("\n", " | "))
        for tf in ("W", "M"):
            await pg.click(f"#tf-{tf}"); await pg.wait_for_timeout(1500)
            for c in CODES:
                await pg.select_option("#sym", c); await pg.wait_for_timeout(1800); await pg.mouse.move(3, 3); await pg.wait_for_timeout(300)
                leg = await pg.inner_text("#htf-legend"); z = num(r"Stretch Z \((?:weekly|monthly)\)\s*([−\-]?\d+\.\d+)", leg)
                Z = ZW if tf == "W" else ZM; py = round(float(Z[c].dropna().iloc[-1]), 3) if c in Z.columns else None
                print(tf, c, "page:", z, "python:", py, "| legend:", leg[:150].replace("\n", " "))
            await pg.screenshot(path=f"{SP}/v19_{tf}.png")
            print(tf, "daily chart hidden:", await pg.evaluate("getComputedStyle(document.getElementById('lwc-wrap')).display"), "| note:", (await pg.inner_text("#htf-note"))[:120])
        await pg.click("#tf-D"); await pg.wait_for_timeout(1500); print("back to daily, lwc display:", await pg.evaluate("getComputedStyle(document.getElementById('lwc-wrap')).display"), "htf:", await pg.evaluate("getComputedStyle(document.getElementById('htf-wrap')).display"))
        await pg.click("#tabs button[data-t=scan]"); await pg.wait_for_timeout(800)
        cn = await pg.inner_text("#core-note"); j = cn.find("Weekly stretch-Z"); print("CORE weekly:", cn[j:j + 300].replace("\n", " "))
        rows = await pg.evaluate("[...document.querySelectorAll('#plan-t tr')].slice(0,5).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,300))"); print("PLAN:"); [print("  ", r) for r in rows]
        await pg.set_viewport_size({"width": 390, "height": 900}); await pg.click("#tabs button[data-t=chart]"); await pg.click("#tf-W"); await pg.wait_for_timeout(1200)
        print("phone weekly hscroll:", await pg.evaluate("document.documentElement.scrollWidth>innerWidth")); await pg.screenshot(path=f"{SP}/v19_phone.png")
        await pg.click("#tf-D"); print("errors:", errs[:5]); await b.close()
asyncio.run(main())
