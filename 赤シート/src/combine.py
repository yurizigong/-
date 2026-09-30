"""全パートを1つの赤シートPDFにまとめる
usage: python3 combine.py <out.pdf>
"""
import importlib, re, subprocess, sys, os, json

RED = "#ff3300"
_course = importlib.import_module(os.environ.get("COURSE", "course1"))
PARTS = _course.PARTS
CTITLE = _course.TITLE
out_pdf = sys.argv[1]


def red(a):
    return re.sub(r"\{([^{}]*)\}", r"<span class='r'>\1</span>", a)


def render(mod):
    rows, ids, n = [], {}, 0
    for title, qs in mod.SECTIONS:
        rows.append(("sec", title))
        for item in qs:
            n += 1
            if len(item) > 3:
                ids[item[3]] = n
            rows.append(("q", n) + tuple(item[:3]))
    resolve = lambda t: re.sub(r"No\.@([A-Za-z]+)", lambda m: f"No.{ids[m.group(1)]}", t)
    body = []
    for r in rows:
        if r[0] == "sec":
            body.append(f"<tr class='sec'><td colspan='4'>{r[1]}</td></tr>")
        else:
            _, num, star, q, a = r
            mark = "<span class='st'>★</span>" if star else ""
            body.append(f"<tr><td class='no'>{num}{mark}</td><td class='q'>{resolve(q)}</td>"
                        f"<td class='a'>{red(a)}</td><td class='ck'>□<br>□<br>□</td></tr>")
    return n, "\n".join(body)


parts_html, summary = [], []
for i, (m, name) in enumerate(PARTS, 1):
    try:
        mod = importlib.import_module(m)
    except ModuleNotFoundError:
        print("MISSING", m); continue
    n, body = render(mod)
    summary.append((i, name, mod.SLIDES, n))
    parts_html.append(f"""<section class="part">
<h2>{i}.{name}</h2>
<div class="src">出典：{mod.SOURCE}（スライド{mod.SLIDES}枚）　全{n}問</div>
<table><colgroup><col class="no"><col class="q"><col class="a"><col class="ck"></colgroup>
<thead><tr><th>No.</th><th>問題</th><th>答え（赤シートで隠す）</th><th>✓</th></tr></thead>
<tbody>
{body}
</tbody></table></section>""")

PAGES = dict(json.loads(os.environ.get("PARTPAGES","{}")))
toc = "".join(f"<tr><td>{i}.{name}</td><td class='num'>{s}枚</td><td class='num'>{n}問</td><td class='num'>{PAGES.get(str(i), '')}{'ページ' if PAGES.get(str(i)) else ''}</td></tr>" for i, name, s, n in summary)
total_q = sum(x[3] for x in summary)
total_s = sum(x[2] for x in summary)

page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>{CTITLE} 赤シート一問一答</title>
<style>
@page {{ size: A4; margin: 11mm 10mm 13mm 10mm;
  @bottom-center {{ content: counter(page) " / " counter(pages); font-size: 8pt; color: #555; }}
  @top-right {{ content: "{CTITLE}　赤シート一問一答"; font-size: 7pt; color: #777; }} }}
@page :first {{ @top-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "IPAPGothic", "IPAGothic", sans-serif; font-size: 9.4pt;
  line-height: 1.5; color: #111; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ font-size: 15pt; margin: 0 0 3mm; }}
.meta {{ font-size: 8.5pt; color: #333; margin: 0 0 4mm; line-height: 1.7; border: 0.6pt solid #999; padding: 2mm 3mm; }}
table.toc {{ border-collapse: collapse; width: 75%; font-size: 9.5pt; }}
table.toc td {{ border-bottom: 0.5pt solid #bbb; padding: 1.2mm 2mm; }}
table.toc td.num {{ text-align: right; width: 18%; }}
section.part {{ break-before: page; }}
h2 {{ font-size: 13pt; margin: 0 0 1.5mm; }}
.src {{ font-size: 8pt; color: #444; margin: 0 0 2mm; }}
section.part table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
col.no {{ width: 9mm; }} col.a {{ width: 41%; }} col.ck {{ width: 6mm; }}
th, td {{ vertical-align: top; }}
section.part th, section.part td {{ border: 0.6pt solid #888; padding: 2.2px 4px; }}
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
<h1>{CTITLE}　赤シート一問一答</h1>
<div class="meta">
全{len(PARTS)}パート（スライド{total_s}枚）　全{total_q}問<br>
使い方：<span class="r">赤い文字</span>（答えと見出し）を赤シートで隠して答える。正解したら右の□に✓（3回分）。<br>
スライドの赤字・青字・太字・下線と、先生が「重要」と書いた所から作成。★＝赤字かつ太字、または先生が「重要」「★」と明記した所（最優先で覚える）<br>
※必ずカラーで印刷する（白黒だと答えが隠れない）
</div>
<table class="toc">{toc}</table>
{''.join(parts_html)}
</body></html>"""

html_path = os.path.splitext(out_pdf)[0] + ".html"
open(html_path, "w", encoding="utf-8").write(page)
chrome = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}", "file://" + os.path.abspath(html_path)], check=True, capture_output=True)
for i, name, s, n in summary:
    print(f"{i}.{name}\tスライド{s}枚\t{n}問")
print("合計", total_s, "枚", total_q, "問 ->", out_pdf)
