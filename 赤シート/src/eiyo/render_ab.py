"""形式A（一問一答・穴埋め）／形式B（まとめノート）の赤シートPDFを作る
usage: FORMAT=a|b COURSE=course1|course2 [ONLY=m1,m2] [PARTPAGES=json] python3 render_ab.py out.pdf
"""
import importlib, re, subprocess, sys, os, json
import figtool, webimg

RED = "#ff3300"
FMT = os.environ.get("FORMAT", "a")
course = importlib.import_module(os.environ.get("COURSE", "course1"))
ONLY = [x for x in os.environ.get("ONLY", "").split(",") if x]
PAGES = json.loads(os.environ.get("PARTPAGES", "{}"))
out_pdf = sys.argv[1]
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
FMT_NAME = {"a": "一問一答（穴埋め）", "b": "まとめノート"}[FMT]


def ruby(t):
    """語|よみ → ルビ"""
    return re.sub(r"([^|{}《》<>、。・（）()\s]+)\|([ぁ-んァ-ヶー・]+)", r"<ruby>\1<rt>\2</rt></ruby>", t)


def red(t):
    t = re.sub(r"《([^《》]*)》", lambda m: ruby(m.group(1)), t)              # 黒字のルビ
    return re.sub(r"\{([^{}]*)\}", lambda m: f"<span class='r'>{ruby(m.group(1))}</span>", t)


def resolve_img(ref, cap):
    """(パス, キャプション) を返す。ネット画像は出典を付ける"""
    if ref.startswith("web:"):
        path, credit = webimg.fetch(ref[4:])
        return path, (cap + "　" if cap else "") + f"<span class='cr'>{credit}</span>"
    return figtool.render(ref), cap


def figs_a(html):
    def rep(m):
        path, cap = resolve_img(m.group(2), m.group(3) or "")
        cap = f"<span class='sfc'>{cap}</span>" if cap else ""
        return f"<span class='sf'><img src='file://{path}'>{cap}</span>"
    return re.sub(r"\[\[(fig)\|((?:figA?|web):[^|\]]+)(?:\|([^\]]*))?\]\]", rep, html)


def render_a(amod):
    out, n, ids = [], 0, {}
    for _, items in amod.SECTIONS:
        for it in items:
            if it[0] == "FIG":
                continue
            n += 1
            if len(it) > 4:
                ids[it[4]] = n
    resolve = lambda t: re.sub(r"No\.@([A-Za-z]+)", lambda m: f"No.{ids[m.group(1)]}", t)
    n = 0
    for title, items in amod.SECTIONS:
        out.append(f"<tr class='sec'><td colspan='3'>{title}</td></tr>")
        for it in items:
            if it[0] == "FIG":
                cap = f"<div class='cap'>{red(it[2])}</div>" if len(it) > 2 and it[2] else ""
                out.append(f"<tr class='fig'><td colspan='3'><img src='file://{figtool.render(it[1])}'>{cap}</td></tr>")
                continue
            star, sent, answers, note = it[:4]
            sent, note = resolve(sent), resolve(note)
            n += 1
            def blank(m):
                i = int(m.group(1))
                mark = "<span class='bst'>★★★</span>" if star else ""
                return f"<span class='blank'>{CIRC[i-1]}{mark}</span>"
            s = red(re.sub(r"［(\d+)］", blank, sent))
            ans = "<br>".join(f"<span class='an'>{CIRC[i]}</span><span class='r'>{ruby(re.sub(r'《([^《》]*)》', lambda m: ruby(m.group(1)), a))}</span>" for i, a in enumerate(answers))
            if note:
                ans += f"<div class='expl'>{figs_a(red(note))}</div>"
            no = f"{n}" + ("<span class='st'>★</span>" if star else "")
            out.append(f"<tr><td class='no'><span class='ck'>□□□</span><br>{no}</td><td class='q'>{s}</td><td class='a'>{ans}</td></tr>")
    return n, "<table class='ta'><colgroup><col class='no'><col class='q'><col class='a'></colgroup>" + "\n".join(out) + "</table>"


def figs_b(html):
    def rep(m):
        kind, ref, cap = m.group(1), m.group(2), (m.group(3) or "")
        cls = {"figR": "fr", "figL": "fl", "fig": "fc", "figS": "fs"}[kind]
        path, cap = resolve_img(ref, cap)
        c = f"<figcaption>{red(cap)}</figcaption>" if cap else ""
        return f"<figure class='{cls}'><img src='file://{path}'>{c}</figure>"
    return re.sub(r"\[\[(figR|figL|figS|fig)\|((?:figA?|web):[^|\]]+)(?:\|([^\]]*))?\]\]", rep, html)


def render_b(bmod):
    out = []
    for title, rng, html in bmod.BLOCKS:
        out.append(f"<div class='blk'><div class='bh'><span class='bt'>{title}</span><span class='rng'>問題No.{rng}</span></div>"
                   f"{figs_b(red(html))}<div style='clear:both'></div></div>")
    return "\n".join(out)


parts, summary = [], []
for i, (m, name) in enumerate(course.PARTS, 1):
    if ONLY and m not in ONLY:
        continue
    qmod = importlib.import_module(m)
    nq = sum(len(q) for _, q in qmod.SECTIONS)
    if FMT == "a":
        n, body = render_a(importlib.import_module("a_" + m))
        assert n <= getattr(qmod, "LIMIT", 88), f"{m}: 問題数 {n} が上限を超えている"
    else:
        body, n = render_b(importlib.import_module("b_" + m)), nq
    summary.append((i, name, qmod.SLIDES, n))
    head = (f"<div class='ph'><span class='phn'>{i}</span><span class='pht'>{name}</span></div>" if FMT == "b"
            else f"<h2><span class='pn'>{i}</span>{name}</h2>")
    tab = f"<div class='tab'><b>{i}</b><span>{name}</span></div>" if FMT == "b" else ""
    parts.append(f"<section class='part'>{tab}{head}"
                 f"<div class='src'>出典：{qmod.SOURCE}（スライド{qmod.SLIDES}枚）　全{n}問</div>{body}</section>")

toc = "".join(f"<tr><td>{i}.{name}</td><td class='num'>{s}枚</td><td class='num'>{n}問</td>"
              f"<td class='num'>{PAGES.get(str(i), '')}{'ページ' if PAGES.get(str(i)) else ''}</td></tr>" for i, name, s, n in summary)
howto = {
 "a": "使い方：文中の空欄（①②…）に入る語を答える。右側の<span class='r'>赤い文字</span>（答え・見出し）を赤シートで隠す。正解したら□に✓（3回分）。<br>" + getattr(course, "STAR_NOTE", "空欄の★★★・番号の★＝赤字かつ太字、または先生が「重要」「★」と明記した所（最優先で覚える）"),
 "b": "使い方：本文・表の<span class='r'>赤い文字</span>（重要語句・見出し）を赤シートで隠して読み、隠れた語句を答えながら覚える。<br>各まとめの右上の「問題No.」は、一問一答版の問題番号に対応（内容は同じ）",
}[FMT]

page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<title>{course.TITLE} 赤シート {FMT_NAME}</title>
<style>
@page {{ size: A4; margin: 11mm 10mm 13mm 10mm;
  @bottom-center {{ content: counter(page) " / " counter(pages); font-size: 8pt; color: #555; }}
  @top-right {{ content: "{course.TITLE}　赤シート {FMT_NAME}"; font-size: 7pt; color: #777; }} }}
@page :first {{ @top-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "IPAPGothic", "IPAGothic", sans-serif; font-size: 9.4pt; line-height: 1.6;
  color: #111; background: #fff; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ font-size: 15pt; margin: 0 0 3mm; }}
.meta {{ font-size: 8.5pt; color: #333; margin: 0 0 4mm; line-height: 1.7; border: 0.6pt solid #999; padding: 2mm 3mm; }}
table.toc {{ border-collapse: collapse; width: 75%; font-size: 9.5pt; }}
table.toc td {{ border-bottom: 0.5pt solid #bbb; padding: 1.2mm 2mm; }}
table.toc td.num {{ text-align: right; width: 16%; }}
section.part {{ break-before: page; }}
h2 {{ font-size: 13pt; margin: 0 0 1.5mm; display: flex; align-items: center; gap: 2mm; }}
.pn {{ display: inline-block; background: #222; color: #fff; font-size: 11pt; padding: 0.5mm 2.2mm; border-radius: 1mm; }}
.src {{ font-size: 8pt; color: #444; margin: 0 0 2mm; }}
.r {{ color: {RED}; font-weight: bold; }}
.note {{ font-size: 7.6pt; color: #555; }}
/* 形式A */
table.ta {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
table.ta col.no {{ width: 10mm; }} table.ta col.a {{ width: 45%; }}
table.ta td {{ vertical-align: top; padding: 1.8mm 2mm; border-bottom: 0.5pt dotted #999; }}
table.ta td.a {{ border-left: 1.2pt solid #333; background: #fff7f5; }}
table.ta tr {{ break-inside: avoid; }}
table.ta tr.sec td {{ background: #f3f3f3; color: {RED}; font-weight: bold; font-size: 9.6pt; border-left: 3pt solid #222; border-bottom: none; padding: 1mm 2mm; }}
table.ta tr.sec {{ break-after: avoid; }}
td.no {{ text-align: center; font-size: 9pt; font-weight: bold; color: #222; }}
td.no .ck {{ font-size: 7pt; color: #777; font-weight: normal; letter-spacing: -0.5px; }}
.st {{ display: block; font-size: 8.5pt; }}
.blank {{ display: inline-block; min-width: 3.4em; border: 1pt solid #333; padding: 0 3px; margin: 0 2px; line-height: 1.3;
  text-align: center; font-size: 8.5pt; font-weight: bold; background: #fff; }}
.bst {{ font-size: 6.5pt; margin-left: 2px; letter-spacing: -1px; }}
.an {{ font-weight: bold; margin-right: 2px; }}
.expl {{ margin-top: 1mm; font-size: 7.8pt; color: #333; line-height: 1.5; border-top: 0.4pt dashed #bbb; padding-top: 0.8mm; }}
table.ta tr.fig td {{ text-align: center; border-bottom: 0.5pt dotted #999; padding: 2mm; background: #fafafa; }}
table.ta tr.fig img {{ max-width: 78%; max-height: 62mm; border: 0.5pt solid #ccc; }}
.cap {{ font-size: 7.5pt; color: #555; margin-top: 0.8mm; }}
ruby rt {{ font-size: 55%; font-weight: normal; }}
.sf {{ display: block; width: 100%; margin: 1.2mm 0 0.5mm; text-align: center; }}
.sf img {{ max-width: 100%; max-height: 78mm; border: 0.5pt solid #ccc; background: #fff; }}
.sfc {{ display: block; font-size: 6.8pt; color: #666; line-height: 1.3; }}
.cr {{ font-size: 6pt; color: #888; }}
.expl table {{ border-collapse: collapse; width: 100%; margin: 1mm 0; font-size: 7.4pt; line-height: 1.35; background: #fff; }}
.expl th, .expl td {{ border: 0.5pt solid #999; padding: 0.4mm 1mm; vertical-align: top; }}
.expl th {{ background: #eee; font-weight: bold; }}
table.ta td.a::after {{ content: ""; display: block; clear: both; }}
/* 形式B */
.ph {{ display: flex; align-items: stretch; margin: 0 0 1mm; }}
.phn {{ background: #d81b60; color: #fff; font-size: 17pt; font-weight: bold; padding: 1mm 4mm; display: flex; align-items: center; }}
.pht {{ flex: 1; border: 1.5pt solid #222; border-left: none; font-size: 15pt; font-weight: bold; padding: 1.5mm 4mm; margin-left: 2mm; border-left: 1.5pt solid #222; }}
section.part {{ position: relative; padding-right: 9mm; }}
.tab {{ position: absolute; right: -2mm; top: 0; width: 8mm; background: #d81b60; color: #fff; text-align: center; border-radius: 1.5mm 0 0 1.5mm; padding: 1.5mm 0; }}
.tab b {{ display: block; font-size: 10pt; }}
.tab span {{ writing-mode: vertical-rl; font-size: 7.5pt; letter-spacing: 1px; display: inline-block; margin-top: 1mm; }}
.sum {{ background: #fde7ef; border-radius: 1mm; padding: 2mm 3.5mm; line-height: 2.0; margin: 0 0 2mm; }}
.sum p {{ margin: 0 0 1mm; text-indent: 1em; }}
.ct {{ color: {RED}; font-weight: bold; font-size: 10pt; margin: 1.5mm 0 1mm; break-after: avoid; page-break-after: avoid; }}
.chart {{ width: 100%; border-collapse: collapse; border: 1.2pt solid #222; margin: 0 0 1.5mm; font-size: 8.8pt; break-inside: avoid; background: #fff; }}
.chart th {{ background: #d81b60; color: #fff; padding: 1mm 1.5mm; border: 0.8pt solid #fff; font-size: 9pt; }}
.chart td {{ padding: 1.2mm 1.8mm; border-bottom: 0.5pt dashed #e6a1bd; vertical-align: middle; line-height: 1.55; }}
.chart td + td {{ border-left: 0.5pt solid #f1c4d6; }}
.chart .lab {{ display: inline-block; background: #fbd3e3; border: 1pt solid #d81b60; color: #d81b60; font-weight: bold; padding: 0.5mm 2mm;
  clip-path: polygon(0 0, 100% 0, 100% 72%, 50% 100%, 0 72%); padding-bottom: 2.2mm; text-align: center; }}
.bar {{ background: #e9e9e9; border: 1pt solid #999; text-align: center; font-weight: bold; padding: 1.2mm; margin: 0 0 2mm; break-inside: avoid; }}
figure.fs {{ margin: 0; text-align: center; }}
figure.fs img {{ width: 100%; max-height: 42mm; object-fit: contain; border: 0.5pt solid #ddd; background: #fff; }}
figure.fs figcaption {{ font-size: 6.8pt; color: #666; }}
.bb figure {{ margin: 0; text-align: center; break-inside: avoid; }}
.bb figure img {{ border: 0.5pt solid #ccc; background: #fff; }}
.bb figure.fr {{ float: right; width: 46%; margin: 0 0 1.5mm 3mm; }}
.bb figure.fl {{ float: left; width: 46%; margin: 0 3mm 1.5mm 0; }}
.bb figure.fc {{ width: 72%; margin: 1.5mm auto; }}
.bb figure img {{ width: 100%; }}
.bb figcaption {{ font-size: 7.3pt; color: #555; margin-top: 0.5mm; }}
.blk {{ margin: 0 0 3.5mm; }}
.bh {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1.5pt solid #c2185b; margin-bottom: 1.2mm; }}
.bt {{ color: {RED}; font-weight: bold; font-size: 10.5pt; }}
.rng {{ font-size: 7.5pt; color: #666; }}
.bb {{ background: #fdeef3; padding: 2mm 3mm; border-radius: 1mm; }}
.bb p {{ margin: 0 0 1.5mm; text-indent: 1em; }}
.bb p:last-child {{ margin-bottom: 0; }}
.bb table {{ width: 100%; border-collapse: collapse; margin: 1.5mm 0; background: #fff; font-size: 8.8pt; break-inside: avoid; }}
.bb th {{ background: #c2185b; color: #fff; font-weight: bold; padding: 1mm 1.5mm; border: 0.6pt solid #c2185b; text-align: left; }}
.bb td {{ border: 0.6pt solid #d9a3b8; padding: 1mm 1.5mm; vertical-align: top; }}
.bb ul, .bb ol {{ margin: 0.5mm 0 1.5mm 5mm; padding: 0; }}
.bb .flow {{ text-align: center; margin: 1mm 0; }}
</style></head><body>
<h1>{course.TITLE}　赤シート {FMT_NAME}</h1>
<div class="meta">全{len(summary)}パート（スライド{sum(x[2] for x in summary)}枚）　全{sum(x[3] for x in summary)}問<br>{howto}<br>
{getattr(course, "BASIS", "スライドの赤字・青字・太字・下線と、先生が「重要」と書いた所から作成。")}※必ずカラーで印刷する（白黒だと答えが隠れない）</div>
<table class="toc">{toc}</table>
{''.join(parts)}
</body></html>"""

html_path = os.path.splitext(out_pdf)[0] + ".html"
open(html_path, "w", encoding="utf-8").write(page)
chrome = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}", "file://" + os.path.abspath(html_path)], check=True, capture_output=True)
for i, name, s, n in summary:
    print(f"{i}.{name}\tスライド{s}枚\t{n}問")
print("合計", sum(x[2] for x in summary), "枚", sum(x[3] for x in summary), "問 ->", out_pdf)
