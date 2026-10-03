"""完成したパートだけで、公開用のWebページ（印刷もできる）と、パートごとの印刷用PDFを作る
usage: COURSE=course3 python3 publish_web.py <完成したmodule,...>
  → pub/<course>/index.html（Artifact に出すページ）、pub/<course>/files.json（画像の対応表）
  → out/<科目>_<番号>_<名前>_一問一答.pdf（完成したパートごとのPDF）
"""
import os, re, sys, json, subprocess, importlib, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.environ.get("COURSE", "course3")
course = importlib.import_module(COURSE)
done = [m for m in sys.argv[1].split(",") if m]
order = [m for m, _ in course.PARTS]
done = [m for m in order if m in done]
PUB = os.path.join(HERE, "pub", COURSE)
OUT = os.path.join(HERE, "out")
os.makedirs(PUB, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
env = dict(os.environ, FORMAT="a", COURSE=COURSE)

# 1) 完成パートをまとめて描画（HTMLを取り出す）
tmp = os.path.join(HERE, "preview", f"web_{COURSE}.pdf")
subprocess.run(["python3", "render_ab.py", tmp], env=dict(env, ONLY=",".join(done)), check=True, cwd=HERE,
               capture_output=True)
html = open(tmp[:-4] + ".html", encoding="utf-8").read()
style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
sections = re.findall(r"<section class='part'>.*?</section>", html, re.S)
assert len(sections) == len(done), (len(sections), done)

# 2) 画像を img/ に（相対パス）
files = {}
def img(m):
    p = m.group(1)
    name = os.path.basename(p)
    files["img/" + name] = p
    return f"loading='lazy' src='img/{name}'"
body = []
for k, (m, sec) in enumerate(zip(done, sections)):
    sec = re.sub(r"src='file://([^']+)'", img, sec)
    body.append(sec.replace("<section class='part'>", f"<section class='part' id='{m}'>", 1))

# 3) 目次（未完成のパートは「作成中」）
qn = {}
for m in done:
    a = importlib.import_module("a_" + m)
    qn[m] = sum(1 for _, items in a.SECTIONS for it in items if it[0] != "FIG")
rows = []
for i, (m, name) in enumerate(course.PARTS, 1):
    q = importlib.import_module(m)
    if m in qn:
        rows.append(f"<li><a href='#{m}'><span class='tn'>{i}</span><span class='tt'>{name}</span>"
                    f"<span class='tq'>{qn[m]}問</span></a></li>")
    else:
        rows.append(f"<li class='todo'><span class='tn'>{i}</span><span class='tt'>{name}</span><span class='tq'>作成中</span></li>")
total = sum(qn.values())
star = getattr(course, "STAR_NOTE", "★＝最優先で覚える所")

TITLE = f"{course.TITLE} 赤シート一問一答"
page = f"""<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic:wght@400;700&display=swap">
<style>
/* 紙のプリントそのままの見た目（赤シート用に白地・赤字を固定するため、ライト表示のみ） */
:root {{ color-scheme: light; --paper: #ffffff; --ink: #111111; --red: #ff3300; --rule: #999999; --muted: #555555; --wash: #f4f1ee; }}
{style.replace('"IPAPGothic", "IPAGothic", sans-serif', '"BIZ UDPGothic", "IPAPGothic", "Hiragino Sans", "Yu Gothic", sans-serif')}
body {{ background: var(--paper); color: var(--ink); }}
.wrap {{ max-width: 200mm; margin: 0 auto; padding-inline: 16px; padding-block: 12px 40px; }}
.bar {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--paper); border-bottom: 1px solid var(--rule);
  display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; padding-block: 8px; }}
.bar h1 {{ font-size: 15px; margin: 0; flex: 1 1 14em; min-width: 0; }}
.bar button {{ font: inherit; font-size: 13px; font-weight: 700; border: 1.5px solid var(--red); color: var(--red); background: var(--paper);
  border-radius: 6px; padding: 6px 12px; cursor: pointer; }}
.bar button[aria-pressed="true"] {{ background: var(--red); color: var(--paper); }}
.bar button:focus-visible {{ outline: 2px solid var(--ink); outline-offset: 2px; }}
.lead {{ font-size: 13px; line-height: 1.7; margin: 12px 0; color: var(--ink); }}
.lead p {{ margin: 0 0 6px; }}
ol.toc {{ list-style: none; padding: 0; margin: 8px 0 20px; display: grid; gap: 4px; }}
ol.toc a, ol.toc li.todo {{ display: flex; gap: 10px; align-items: baseline; padding: 6px 8px; border: 1px solid #dddddd; border-radius: 6px;
  color: var(--ink); text-decoration: none; font-size: 14px; }}
ol.toc a:hover {{ border-color: var(--red); }}
ol.toc li.todo {{ color: #9a9a9a; border-style: dashed; }}
.tn {{ font-weight: 700; min-width: 1.6em; font-variant-numeric: tabular-nums; }}
.tt {{ flex: 1; min-width: 0; }}
.tq {{ font-size: 12px; font-variant-numeric: tabular-nums; }}
section.part {{ margin-top: 28px; }}
.ta-wrap {{ overflow-x: auto; }}
/* 赤シートモード：赤字を赤い帯で隠す。タップでその語だけ表示 */
.hide .r {{ background: var(--red); color: var(--red); border-radius: 2px; cursor: pointer; }}
.hide .r:not(.show) rt {{ visibility: hidden; }}
.hide .r.show {{ background: transparent; }}
.hide .r.show, .hide .r.show rt {{ color: var(--red); }}
/* スマホでも「問題＝左、答え・解説＝右」のまま。文字と余白を少し詰める */
@media (max-width: 640px) {{
  .wrap {{ padding-inline: 10px; }}
  table.ta {{ font-size: 12px; line-height: 1.55; }}
  table.ta col.no {{ width: 30px; }}
  table.ta col.a {{ width: 48%; }}
  table.ta > tbody > tr > td {{ padding: 5px 4px; }}
  table.ta > tbody > tr > td.no {{ font-size: 11px; }}
  td.no .ck {{ font-size: 8px; letter-spacing: -1px; }}
  .st {{ font-size: 9px; letter-spacing: -1.5px; }}
  .imp {{ font-size: 8px; padding: 0 2px; }}
  .blank {{ min-width: 2.2em; font-size: 11px; padding: 0 1px; margin: 0 1px; }}
  .expl {{ font-size: 10.5px; }}
  .expl table {{ font-size: 9.5px; }}
  .sfc {{ font-size: 9px; }}
}}
/* 図をタップすると大きく表示 */
.sf img {{ cursor: zoom-in; }}
.zoom {{ position: fixed; inset: 0; z-index: 20; background: rgba(0,0,0,0.82); display: flex; align-items: center; justify-content: center;
  padding: calc(12px + env(safe-area-inset-top, 0px)) 12px calc(12px + env(safe-area-inset-bottom, 0px)); cursor: zoom-out; }}
.zoom img {{ max-width: 100%; max-height: 100%; background: #ffffff; }}
.zoom[hidden] {{ display: none; }}
@media print {{
  .bar button, ol.toc, .lead .web {{ display: none; }}
  .bar {{ position: static; border: none; }}
  .wrap {{ max-width: none; padding: 0; }}
  .hide .r {{ background: transparent; }}
  .zoom {{ display: none; }}
}}
</style>
<div class="wrap" id="top">
<div class="bar"><h1>{TITLE}</h1><button type="button" id="sheet" aria-pressed="false">赤シートモード</button></div>
<div class="lead">
<p>文中の空欄（①②…）に入る語を答え、右側の<span class="r">赤い文字</span>を赤シートで隠して使います。{star}。</p>
<p>{getattr(course, "BASIS", "")}公開済み {len(done)}/{len(course.PARTS)}パート・{total}問。</p>
<p class="web">スマホで見るときは「赤シートモード」で赤字を隠せます（隠れた語をタップするとその語だけ表示）。図はタップすると大きく表示されます。印刷はチャットで送ったPDFを使うと、A4できれいに印刷できます（必ずカラー印刷）。</p>
</div>
<ol class="toc">{''.join(rows)}</ol>
{''.join(body)}
</div>
<div class="zoom" id="zoom" hidden><img alt="拡大した図"></div>
<script>
(function () {{
  var root = document.querySelector('.wrap'), btn = document.getElementById('sheet');
  function set(on) {{ root.classList.toggle('hide', on); btn.setAttribute('aria-pressed', on ? 'true' : 'false'); }}
  try {{ set(localStorage.getItem('sheet') === '1'); }} catch (e) {{}}
  btn.addEventListener('click', function () {{
    var on = !root.classList.contains('hide'); set(on);
    try {{ localStorage.setItem('sheet', on ? '1' : '0'); }} catch (e) {{}}
  }});
  var zoom = document.getElementById('zoom'), zimg = zoom.querySelector('img');
  root.addEventListener('click', function (e) {{
    var im = e.target.closest('.sf img');
    if (im) {{ zimg.src = im.src; zoom.hidden = false; return; }}
    var r = e.target.closest('.r');
    if (r && root.classList.contains('hide')) r.classList.toggle('show');
  }});
  zoom.addEventListener('click', function () {{ zoom.hidden = true; zimg.removeAttribute('src'); }});
  document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape') zoom.hidden = true; }});
}})();
</script>
"""
page = page.replace("<table class='ta'>", "<div class='ta-wrap'><table class='ta'>").replace("</table></section>", "</table></div></section>")
open(os.path.join(PUB, "index.html"), "w", encoding="utf-8").write(page)
json.dump(files, open(os.path.join(PUB, "files.json"), "w"), ensure_ascii=False, indent=0)
size = len(page.encode()) + sum(os.path.getsize(p) for p in files.values())
print(f"page: {os.path.join(PUB, 'index.html')}  images: {len(files)}  total {size/1e6:.1f}MB")

# 4) パートごとのPDF（A4印刷用・iPad用）
for i, (m, name) in enumerate(course.PARTS, 1):
    if m not in done:
        continue
    srcs = [os.path.join(HERE, f) for f in (f"a_{m}.py", f"diff_{m}.py", "render_ab.py", "figtool.py", COURSE + ".py") if os.path.exists(os.path.join(HERE, f))]
    for size, label in (("a4", "A4印刷用"), ("ipad", "iPad用")):
        fn = os.path.join(OUT, f"{course.TITLE}_{i:02d}_{re.sub(r'[ 　/]', '', name)}_{label}.pdf")
        if os.path.exists(fn) and os.path.getmtime(fn) > max(os.path.getmtime(x) for x in srcs):
            continue
        subprocess.run(["python3", "render_ab.py", fn], env=dict(env, ONLY=m, SIZE=size), check=True, cwd=HERE, capture_output=True)
        print("pdf:", fn)
