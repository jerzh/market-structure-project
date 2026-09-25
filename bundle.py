"""Inline CSS, data, D3 and app.js into a single self-contained HTML file."""
import pathlib, urllib.request

root = pathlib.Path(__file__).parent / "site"
html = (root / "index.html").read_text()
css = (root / "style.css").read_text()
data = (root / "data" / "industries.json").read_text()
app = (root / "app.js").read_text().replace(
    'await (await fetch("data/industries.json")).json()', "window.__DATA__")
d3 = urllib.request.urlopen("https://cdn.jsdelivr.net/npm/d3@7").read().decode()

html = html.replace('<link rel="stylesheet" href="style.css">', f"<style>\n{css}\n</style>")
html = html.replace('<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
                    f"<script>{d3}</script>\n<script>window.__DATA__ = {data};</script>")
html = html.replace('<script src="app.js"></script>', f"<script>\n{app}\n</script>")
out = pathlib.Path(__file__).parent / "concentration_vs_labor_share.html"
out.write_text(html)
print(out, out.stat().st_size // 1024, "KB")
