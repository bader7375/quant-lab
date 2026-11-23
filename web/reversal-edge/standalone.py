"""Build one self-contained HTML file from a terminal folder (index.html + engine.js + lwc.js + plotly.min.js + CSVs)."""
import sys, pathlib
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); label = sys.argv[3] if len(sys.argv) > 3 else ""
rd = lambda n: (src / n).read_text(encoding="utf-8")
safe = lambda s: s.replace("</script", "<\\/script")
page = rd("index.html")
reps = [
 ('<script src="lwc.js"></script>', '<script>' + safe(rd("lwc.js")) + '</script>'),
 ('new Worker("engine.js")', 'new Worker(URL.createObjectURL(new Blob([document.getElementById("eng-src").textContent],{type:"text/javascript"})))'),
 ('s.src="plotly.min.js"', 's.src=URL.createObjectURL(new Blob([document.getElementById("plotly-src").textContent],{type:"text/javascript"}))'),
 ('await (await fetch("sample_TSLA.csv")).text()', 'document.getElementById("tsla-src").textContent'),
 ('await (await fetch("VIX.csv")).text()', 'document.getElementById("vix-src").textContent'),
]
for a, b in reps:
    assert a in page, a; page = page.replace(a, b)
extra = ""
if (src / "tadawul_gz_base64.txt").exists():
    extra = f'<script type="text/plain" id="tadawul-b64">{rd("tadawul_gz_base64.txt")}</script>\n<script type="application/json" id="tadawul-meta">{safe(rd("tadawul_meta.json"))}</script>\n'
blobs = extra + "".join(f'<script type="text/plain" id="{i}">{safe(rd(n))}</script>\n' for i, n in (("eng-src", "engine.js"), ("plotly-src", "plotly.min.js"), ("tsla-src", "sample_TSLA.csv"), ("vix-src", "VIX.csv")))
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>[hidden]{display:none!important}body{margin:0;background:#0d0d0d}</style></head><body>\n'
        f'<!-- QuantLab Reversal Edge terminal · saved version {label} · open this file in Chrome, Edge, Firefox or Safari; everything runs offline except Google Fonts. -->\n')
out.write_text(head + blobs + page + "\n</body></html>\n", encoding="utf-8")
print(out, round(out.stat().st_size / 1e6, 2), "MB")
