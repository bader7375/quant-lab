import asyncio, json, pandas as pd, numpy as np
from playwright.async_api import async_playwright
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"
ML = open(f"{SP}/r27/today27.json").read(); SC = open(f"{SP}/ml26/sectors.json").read()
def doc(code):
    d = pd.read_csv(f"{SP}/edge26/data/d/{code}.SR.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & (d.volume > 0)].loc["2015":]; k = d.adjclose / d.close
    rows = [[int(t.strftime("%Y%m%d")), round(float(o), 4), round(float(h), 4), round(float(l), 4), round(float(c), 4), int(v)] for t, o, h, l, c, v in zip(d.index, d.open * k, d.high * k, d.low * k, d.adjclose, d.volume)]
    return {"sym": code, "source": "Yahoo test", "fetched_at": "2026-10-24T11:00:00Z", "adjusted": True, "rows": rows}
CODES = ["3020", "3030", "1302", "1140"]
BARS = {c: doc(c) for c in CODES}
MOCK = """window.__ML=%s;window.__SC=%s;window.__B=%s;window.claude={use:async k=>k==='db'?{collection:n=>{const q={onSnapshot:(cb)=>{setTimeout(()=>cb({docs:n==='ml'?[{id:'latest',data:()=>window.__ML},{id:'sectors',data:()=>window.__SC}]:n==='bars'?Object.entries(window.__B).map(([id,b])=>({id,data:()=>b})):[]}),1500);return()=>{}},orderBy:()=>q,limit:()=>q};return q}}:null};""" % (ML, SC, json.dumps(BARS))
F = pd.read_pickle(f"{SP}/r27/F27y.pkl"); VZ = pd.read_pickle(f"{SP}/r31/vz.pkl")
import sys; NEG = len(sys.argv) > 1
if NEG:
    _m = json.loads(ML); _m["ms"] = -0.5; _m["ms_hist"]["v"][-1] = -0.5; ML = json.dumps(_m)
    MOCK = MOCK.split(";window.__SC=")[0].split("window.__ML=")[0] + "window.__ML=" + ML + ";window.__SC=" + MOCK.split(";window.__SC=", 1)[1]
async def done(pg): await pg.wait_for_function("document.getElementById('runmsg').textContent.startsWith('Done') && !document.getElementById('run').disabled", timeout=400000)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = await b.new_page(viewport={"width": 1400, "height": 2600}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); await pg.add_init_script(MOCK)
        await pg.goto(f"file://{SP}/QuantLab-ReversalEdge-v18.html"); await done(pg); await pg.wait_for_timeout(2500)
        await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(300)
        for c in CODES: await pg.check(f'#lib-t input[data-lib="{c}"]'); await pg.wait_for_timeout(1500); await done(pg); await pg.click("#tabs button[data-t=data]"); await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(3000); await done(pg)
        print("updates:", (await pg.inner_text("#upd-t"))[:400].replace("\n", " | "))
        await pg.click("#tabs button[data-t=chart]"); await pg.wait_for_timeout(800)
        for c in CODES:
            await pg.select_option("#sym", c); await pg.wait_for_timeout(2500)
            leg = await pg.inner_text("#legend") if await pg.query_selector("#legend") else ""
            ins = await pg.inner_text("#inspbody")
            import re
            m = re.search(r"Stretch Z\s*([−\-]?\d+\.\d+)", leg); zpage = float(m.group(1).replace("−", "-")) if m else None
            m2 = re.search(r"VWAP Z\s*([−\-]?\d+\.\d+)", leg); vpage = float(m2.group(1).replace("−", "-")) if m2 else None
            m3 = re.search(r"mkt mom\s*([−\-]?\d+\.\d+)", leg); mpage = float(m3.group(1).replace("−", "-")) if m3 else None
            print(c, "Stretch Z page/python:", zpage, round(float(F["zc"].loc["2026-10-22", c]), 3), "| VWAP Z page/python:", vpage, round(float(VZ.loc["2026-10-22", c]), 3), "| mkt mom page:", mpage, "| date:", re.findall(r"2026-\d\d-\d\d", leg)[:1])
        i0 = ins.find("VWAP stretch Z"); print("INSPECTOR VWAP/MS:", ins[i0:i0+700].replace("\n", " | "))
        await pg.select_option("#sym", "3020"); await pg.wait_for_timeout(2500); sb = await pg.inner_text("#sigbar"); k = sb.find("Momentum Pulse"); print("PULSE ADVICE:", sb[k:k+400].replace("\n", " | ")); hud = await pg.inner_text("#pulse-hud"); print("PULSE HUD:", hud.replace("\n", " ")); print("SIGNAL BAR 3020:", sb[:300].replace("\n", " | "))
        await pg.screenshot(path=f"{SP}/v18_chart.png")
        await pg.click("#tabs button[data-t=scan]"); await pg.wait_for_timeout(800)
        cn = await pg.inner_text("#core-note"); j = cn.find("Market momentum"); print("CORE NOTE:", cn[max(0, j-200):j+400].replace("\n", " "))
        rows = await pg.evaluate("[...document.querySelectorAll('#plan-t tr')].slice(0,6).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,420))"); print("PLAN:"); [print("  ", r) for r in rows]
        print("CORE REC:", (await pg.inner_text("#core-rec"))[:500].replace("\n", " | "))
        el = await pg.query_selector("#core-box"); await el.screenshot(path=f"{SP}/v18_core.png")
        await pg.set_viewport_size({"width": 390, "height": 900}); await pg.wait_for_timeout(600)
        for t in ("data", "chart", "scan"):
            await pg.click(f"#tabs button[data-t={t}]"); await pg.wait_for_timeout(500); print(t, "hscroll:", await pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        await pg.click("#tabs button[data-t=chart]"); await pg.wait_for_timeout(800); await pg.screenshot(path=f"{SP}/v18_phone.png", full_page=False)
        print("errors:", errs[:5]); await b.close()
asyncio.run(main())
