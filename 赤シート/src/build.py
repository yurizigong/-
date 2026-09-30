"""赤シート用 一問一答 PDF ビルダー
usage: python3 build.py <data_module> <out_dir>
"""
import importlib, re, subprocess, sys, html, os

RED = "#ff3300"  # 赤シートで消える明るい赤〜朱色

mod = importlib.import_module(sys.argv[1])
out_dir = sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

# 番号付け・ID解決
rows, ids, n = [], {}, 0
for title, qs in mod.SECTIONS:
    rows.append(("sec", title))
    for item in qs:
        n += 1
        star, q, a = item[:3]
        if len(item) > 3:
            ids[item[3]] = n
        rows.append(("q", n, star, q, a))
total = n

def resolve(t):
    return re.sub(r"No\.@([A-Za-z]+)", lambda m: f"No.{ids[m.group(1)]}", t)

def red(a):
    return re.sub(r"\{([^{}]*)\}", r"<span class='r'>\1</span>", a)

body = []
for r in rows:
    if r[0] == "sec":
        body.append(f"<tr class='sec'><td colspan='4'>{r[1]}</td></tr>")
    else:
        _, num, star, q, a = r
        mark = "<span class='st'>★</span>" if star else ""
        body.append(
            f"<tr><td class='no'>{num}{mark}</td><td class='q'>{resolve(q)}</td>"
            f"<td class='a'>{red(a)}</td><td class='ck'>□<br>□<br>□</td></tr>")

page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>{mod.SHORT} 赤シート</title>
<style>
@page {{ size: A4; margin: 11mm 10mm 13mm 10mm;
  @bottom-center {{ content: counter(page) " / " counter(pages); font-size: 8pt; color: #555; }}
  @top-right {{ content: "{mod.SHORT}　赤シート一問一答"; font-size: 7pt; color: #777; }} }}
@page :first {{ @top-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "IPAPGothic", "IPAGothic", sans-serif; font-size: 9.4pt;
  line-height: 1.5; color: #111; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ font-size: 13pt; margin: 0 0 2mm; }}
.meta {{ font-size: 8.3pt; color: #333; margin: 0 0 3mm; line-height: 1.6; border: 0.6pt solid #999; padding: 2mm 3mm; }}
.meta .r {{ font-weight: bold; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
col.no {{ width: 9mm; }} col.a {{ width: 41%; }} col.ck {{ width: 6mm; }}
th, td {{ border: 0.6pt solid #888; padding: 2.2px 4px; vertical-align: top; }}
thead th {{ background: #e6e6e6; font-size: 8pt; font-weight: bold; text-align: left; }}
thead {{ display: table-header-group; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
tr.sec td {{ background: #f3f3f3; color: {RED}; font-weight: bold; font-size: 9.6pt; border-left: 3pt solid #222; padding: 2px 6px; }}
tr.sec {{ break-after: avoid; page-break-after: avoid; }}
td.no {{ text-align: center; font-size: 8.5pt; color: #333; }}
.st {{ display: block; font-size: 9pt; color: #111; }}
td.ck {{ text-align: center; font-size: 7.5pt; line-height: 1.35; color: #777; padding: 2px 0; }}
.r {{ color: {RED}; font-weight: bold; }}
.note {{ font-size: 7.6pt; color: #555; }}
</style></head><body>
<h1>{mod.SHORT}　赤シート一問一答</h1>
<div class="meta">
出典：{mod.SOURCE}（スライド{mod.SLIDES}枚）　全{total}問<br>
使い方：<span class="r">赤い文字</span>（答えと見出し）を赤シートで隠して答える。正解したら右の□に✓（3回分）。<br>
{getattr(mod,"LEGEND","★＝スライドで太字、または先生が「重要」「よく理解しておくこと」と書いている所（最優先で覚える）")}
</div>
<table>
<colgroup><col class="no"><col class="q"><col class="a"><col class="ck"></colgroup>
<thead><tr><th>No.</th><th>問題</th><th>答え（赤シートで隠す）</th><th>✓</th></tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table>
</body></html>"""

base = os.path.join(out_dir, mod.OUTNAME)
open(base + ".html", "w", encoding="utf-8").write(page)

# 検証用プレーンテキスト
with open(os.path.join(os.path.dirname(__file__), sys.argv[1] + "_qa.txt"), "w", encoding="utf-8") as f:
    for r in rows:
        if r[0] == "sec":
            f.write(f"\n## {r[1]}\n")
        else:
            _, num, star, q, a = r
            strip = lambda t: re.sub(r"<[^>]+>", " / ", resolve(t))
            f.write(f"Q{num}{'★' if star else ''}: {strip(q)}\n   A: {strip(re.sub(r'[{}]', '', a))}\n")

chrome = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={base}.pdf", "file://" + os.path.abspath(base + ".html")],
               check=True, capture_output=True)
print("total questions:", total, "->", base + ".pdf")
