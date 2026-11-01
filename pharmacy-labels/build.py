"""Builds label-studio.html: one self-contained file (works offline)."""
import base64, json, pathlib
src = pathlib.Path(__file__).parent / "src"
html = (src / "app.template.html").read_text()
b64 = lambda f: "data:image/png;base64," + base64.b64encode((src / f).read_bytes()).decode()
labels = json.loads((src / "labels.json").read_text())
html = (html.replace("/*__QRCODE__*/", (src / "vendor/qrcode-generator-1.4.4.js").read_text())
            .replace("/*__JSPDF__*/", (src / "vendor/jspdf-2.5.1.umd.min.js").read_text())
            .replace("__LABELS_JSON__", json.dumps(labels, ensure_ascii=False))
            .replace("__LOGO_L__", b64("logo-left.png"))
            .replace("__LOGO_R__", b64("logo-right.png")))
out = pathlib.Path(__file__).parent / "label-studio.html"
out.write_text(html)
print(out, len(html) // 1024, "KB")
