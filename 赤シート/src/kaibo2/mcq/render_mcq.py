"""四択問題（mcq_<m>.json）→ iPad用の赤シートPDF。usage: python3 render_mcq.py out.pdf [verified]"""
import importlib, json, os, random, re, subprocess, sys
import course2

RED = "#ff3300"
CIRC = "①②③④"
out_pdf = sys.argv[1]
mods = [m for m, _ in course2.PARTS]
names = dict(course2.PARTS)
partno = {m: i for i, (m, _) in enumerate(course2.PARTS, 1)}


def ruby(t):
    return re.sub(r"([^|{}《》<>、。・（）()\s]+)\|([ぁ-んァ-ヶー・]+)", r"<ruby>\1<rt>\2</rt></ruby>", t)


def esc(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"《([^《》]*)》", lambda m: ruby(m.group(1)), t)
    return t


items = []
for m in mods:
    p = f"mcq_{m}.json"
    for q in json.load(open(p, encoding="utf-8")):
        items.append((m, q))
n = len(items)
# 正解の位置を ①〜④ に均等に（再現できる乱数）
rnd = random.Random(20261019)
pos = [i % 4 for i in range(n)]
while True:                                   # 同じ番号が3問続かないようにする
    rnd.shuffle(pos)
    if not any(pos[i] == pos[i + 1] == pos[i + 2] for i in range(n - 2)):
        break
rows, last = [], None
for k, ((m, q), a) in enumerate(zip(items, pos), 1):
    if m != last:
        rows.append(f"<tr class='sec'><td colspan='3'>第{partno[m]}回　{names[m]}</td></tr>")
        last = m
    ds = list(q["distractors"]); rnd.shuffle(ds)
    ch = ds[:a] + [q["answer"]] + ds[a:]
    cs = "".join(f"<div class='ch'><span class='cn'>{CIRC[i]}</span>{esc(c)}</div>" for i, c in enumerate(ch))
    src = f"第{partno[m]}回 {names[m]}　No.{q['src']}"
    ans = f"<div class='ak'><span class='an'>{CIRC[a]}</span><span class='r'>{esc(q['answer'])}</span></div>"
    ex = f"<div class='expl'>{esc(q['explain'])}</div>" if q.get("explain") else ""
    rows.append(f"<tr><td class='no'><span class='ck'>□□□</span><br>{k}</td>"
                f"<td class='q'><div class='srcn'>出典：{src}</div><div class='st'>{esc(q['stem'])}</div>{cs}</td>"
                f"<td class='a'>{ans}{ex}</td></tr>")
import collections
cnt = collections.Counter(m for m, _ in items)
toc = "".join(f"<tr><td>第{partno[m]}回</td><td>{names[m]}</td><td class='num'>{cnt[m]}問</td></tr>" for m in mods)
page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
@page {{ size: 168mm 240mm; margin: 6mm 5mm 8mm 5mm;
  @bottom-center {{ content: counter(page) " / " counter(pages); font-size: 8pt; color: #555; }}
  @top-right {{ content: "{course2.TITLE}　赤シート 四択問題"; font-size: 7pt; color: #777; }} }}
@page :first {{ @top-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "IPAPGothic", "IPAGothic", sans-serif; font-size: 9.6pt; line-height: 1.6; color: #111; background: #fff;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ font-size: 15pt; margin: 0 0 3mm; }}
.meta {{ font-size: 8.5pt; color: #333; margin: 0 0 4mm; line-height: 1.7; border: 0.6pt solid #999; padding: 2mm 3mm; }}
.r {{ color: {RED}; font-weight: bold; }}
table.ta {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
table.ta col.no {{ width: 10mm; }} table.ta col.a {{ width: 38%; }}
table.ta td {{ vertical-align: top; padding: 1.8mm 2mm; border-bottom: 0.5pt dotted #999; }}
table.ta td.a {{ border-left: 1.2pt solid #333; background: #fff7f5; }}
table.ta tr {{ break-inside: avoid; }}
table.ta tr.sec td {{ background: #f3f3f3; color: {RED}; font-weight: bold; font-size: 9.6pt; border-left: 3pt solid #222; border-bottom: none; padding: 1mm 2mm; }}
table.ta tr.sec {{ break-after: avoid; }}
td.no {{ text-align: center; font-size: 10pt; font-weight: bold; color: #222; padding-left: 0.8mm; padding-right: 0.8mm; }}
td.no .ck {{ font-size: 7pt; color: #777; font-weight: normal; letter-spacing: -0.5px; }}
.srcn {{ font-size: 7pt; color: #555; margin-bottom: 0.8mm; }}
.st {{ font-weight: bold; margin-bottom: 1.2mm; }}
.ch {{ margin: 0 0 0.6mm 0; padding-left: 5mm; text-indent: -5mm; }}
.cn {{ display: inline-block; width: 5mm; text-indent: 0; font-weight: bold; }}
.an {{ font-weight: bold; margin-right: 2px; }}
.ak {{ font-size: 10pt; }}
.expl {{ margin-top: 1mm; font-size: 7.8pt; color: #333; line-height: 1.5; border-top: 0.4pt dashed #bbb; padding-top: 0.8mm; }}
ruby rt {{ font-size: 55%; font-weight: normal; }}
table.toc {{ border-collapse: collapse; width: 70%; font-size: 9.5pt; }}
table.toc td {{ border-bottom: 0.5pt solid #bbb; padding: 1mm 2mm; }}
table.toc td.num {{ text-align: right; width: 18%; }}
</style></head><body>
<h1>{course2.TITLE}　赤シート 四択問題（最頻出・{n}問）</h1>
<div class="meta">看護の定期試験・国家試験で出やすい最頻出の事項から、四択問題を{n}問作りました。各問題の「出典」は、一問一答の<b>第何回（パート番号）・何問目（No.）</b>の問題から作ったかを示します。<br>
使い方：問題と①〜④を読んで答えを選ぶ。右側の<span class="r">赤い文字</span>（答えと解説）を赤シートで隠す。正解したら□に✓（3回分）。※必ずカラーで印刷する（白黒だと答えが隠れない）</div>
<table class="toc">{toc}</table>
<table class="ta" style="margin-top:4mm"><colgroup><col class="no"><col class="q"><col class="a"></colgroup>
{chr(10).join(rows)}
</table></body></html>"""
html_path = os.path.splitext(out_pdf)[0] + ".html"
open(html_path, "w", encoding="utf-8").write(page)
chrome = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}", "file://" + os.path.abspath(html_path)], check=True, capture_output=True)
print(n, "問 ->", out_pdf)
