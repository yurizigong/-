"""スライドPDFから図（スライド画像）を切り出し、図中の文字を赤字に塗り替えてJPEGにする
- 赤字にしたラベルは赤シートで隠れる（答えが図から見えないように）
- 参照の書き方（データ中）: "fig:<module>:<スライド番号>" または "fig:<module>:<スライド番号>:x0,y0,x1,y1"
  （x0..y1 はスライド内の相対位置 0〜1。省略時はスライド全体）
usage (確認用): python3 figtool.py <module> [スライド番号 ...]  → figs/ にJPEGを書き出して一覧表示
"""
import os, re, sys, math, unicodedata, pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
RED = (1, 0.2, 0)
OUTDIR = os.path.join(HERE, "figs")
os.makedirs(OUTDIR, exist_ok=True)
_cache = {}


def _fix_radicals(t):
    """康熙部首などの互換文字（⾨⼩⾎…）はフォントにないので、ふつうの漢字（門小血…）に直す"""
    t = t.translate(_RAD2)
    return "".join(unicodedata.normalize("NFKC", c) if 0x2F00 <= ord(c) <= 0x2FDF else c for c in t)


_RAD2 = str.maketrans("⻝⻑⻘⻄⻩⻲⻭⻯⻨⻫⺠⺟⻤⻣⻒⺫", "食長青西黄亀歯竜麦斉民母鬼骨長目")


def slide_map(module):
    """スライド番号 -> (ページ番号0始まり, スライド枠Rect)。枠はページ左側の大きい四角形。番号はノート欄の数字から取る"""
    if module in _cache:
        return _cache[module]
    doc = pymupdf.open(os.path.join(HERE, "pdf", module + ".pdf"))
    res = {}
    if module.startswith("eiyo"):                  # 栄養代謝学：1ページ＝1スライド（プリントも1ページ＝1枚）
        res = {pi + 1: (pi, pymupdf.Rect(p.rect)) for pi, p in enumerate(doc)}
        _cache[module] = (doc.name, res)
        return _cache[module]
    for pi, p in enumerate(doc):
        frames = []
        for dr in p.get_drawings():
            r = dr["rect"]
            if r.width > 200 and r.height > 140 and r.x0 < 120 and all(abs(r.y0 - f.y0) > 20 for f in frames):
                frames.append(r)
        frames.sort(key=lambda r: r.y0)
        # スライド番号：枠の右上すぐ外にある数字
        words = p.get_text("words")
        for fr in frames:
            num = None
            for w in words:
                x0, y0, x1, y1, t = w[:5]
                if re.fullmatch(r"\d{1,3}", t) and fr.x1 - 2 <= x0 <= fr.x1 + 40 and fr.y0 - 12 <= y0 <= fr.y0 + 25:
                    num = int(t)
                    break
            if num is not None and num not in res:
                res[num] = (pi, pymupdf.Rect(fr))
    _cache[module] = (doc.name, res)
    return _cache[module]


def auto_rel(module, n):
    """スライド内の図（画像＋近くのラベル文字）を囲む範囲を 0〜1 の相対座標で返す。タイトル帯は除く"""
    path, smap = slide_map(module)
    pi, fr = smap[n]
    page = pymupdf.open(path)[pi]
    title_y = fr.y0 + 0.17 * fr.height
    box = None
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"]) & fr
        if r.is_empty or r.width < 12 or r.height < 12:
            continue
        if r.width * r.height > 0.9 * fr.width * fr.height:      # 背景画像
            continue
        r.y0 = max(r.y0, title_y)
        box = r if box is None else box | r
    if box is None:
        return [0, 0.17, 1, 1]
    for _ in range(2):                                            # 近くのラベルを取り込む
        for b in page.get_text("dict", clip=fr)["blocks"]:
            for l in b.get("lines", []):
                lr = pymupdf.Rect(l["bbox"])
                if lr.y0 < title_y:
                    continue
                if (lr + (-8, -8, 8, 8)).intersects(box):
                    box |= lr
    box = (box + (-3, -3, 3, 3)) & fr
    return [(box.x0 - fr.x0) / fr.width, (box.y0 - fr.y0) / fr.height,
            (box.x1 - fr.x0) / fr.width, (box.y1 - fr.y0) / fr.height]


def render(ref, dpi=220):
    """ref = "fig:<module>:<n>[:x0,y0,x1,y1]"（手動範囲）または "figA:<module>:<n>"（自動トリミング） -> JPEGのパス"""
    parts = ref.split(":")
    module, n = parts[1], int(parts[2])
    if parts[0] == "figA":
        rel = auto_rel(module, n)
    else:
        rel = [float(v) for v in parts[3].split(",")] if len(parts) > 3 else [0, 0, 1, 1]
    # 画像の中の文字（ラスター）を赤くして隠す範囲: ":R=x0,y0,x1,y1/x0,y0,x1,y1…"（スライド内の相対位置）
    masks = []
    if len(parts) > 4 and parts[4].startswith("R="):
        masks = [[float(v) for v in m.split(",")] for m in parts[4][2:].split("/") if m]
    key = f"{module}_{n}_" + "_".join(f"{v:.3f}" for v in rel)
    if masks:
        import hashlib
        key += "_R" + hashlib.md5(parts[4].encode()).hexdigest()[:8]
    out = os.path.join(OUTDIR, key + ".jpg")
    if os.path.exists(out):
        return out
    path, smap = slide_map(module)
    if n not in smap:
        raise KeyError(f"{module}: スライド{n}が見つからない（あるのは {sorted(smap)}）")
    pi, fr = smap[n]
    clip = pymupdf.Rect(fr.x0 + rel[0] * fr.width, fr.y0 + rel[1] * fr.height,
                        fr.x0 + rel[2] * fr.width, fr.y0 + rel[3] * fr.height)
    doc = pymupdf.open(path)
    page = doc[pi]
    spans = []
    for b in page.get_text("dict", clip=clip)["blocks"]:
        for l in b.get("lines", []):
            if l.get("wmode", 0) != 0:             # 縦書きはそのまま
                continue
            for s in l["spans"]:
                if s["text"].strip() and pymupdf.Rect(s["bbox"]).intersects(clip):
                    s["dir"] = tuple(l.get("dir", (1, 0)))
                    spans.append(s)
    for s in spans:
        page.add_redact_annot(pymupdf.Rect(s["bbox"]), fill=False)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=0)
    font = pymupdf.Font(fontfile=FONT)
    for s in spans:
        size = s["size"]
        text = _fix_radicals(s["text"])
        text = "".join(c if (c.isspace() or font.has_glyph(ord(c))) else "＊" for c in text)   # フォントにない記号（✴など）は＊に
        horiz = abs(s["dir"][0] - 1) < 1e-3 and abs(s["dir"][1]) < 1e-3
        if horiz:
            w = font.text_length(text, fontsize=size)
            bw = s["bbox"][2] - s["bbox"][0]
            if w > bw * 1.02 and w > 0:
                size = size * bw / w          # 元の幅に収まるように縮める
        try:
            if horiz:
                page.insert_text(s["origin"], text, fontsize=size, fontname="ipag", fontfile=FONT, color=RED)
            else:                             # 斜めの文字：同じ向きで赤字に書き直す
                ang = math.degrees(math.atan2(-s["dir"][1], s["dir"][0]))
                o = pymupdf.Point(s["origin"])
                page.insert_text(o, text, fontsize=size, fontname="ipag", fontfile=FONT, color=RED,
                                 morph=(o, pymupdf.Matrix(ang)))
        except Exception:
            pass
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    if masks:
        pix = _redden(pix, clip, fr, masks, dpi)
    pix.save(out, jpg_quality=90)
    return out


def _redden(pix, clip, fr, masks, dpi):
    """マスク範囲の中の濃い色の画素（画像に埋め込まれた文字）を赤（赤シートで消える色）に塗り替える"""
    import numpy as np
    if pix.alpha or pix.n != 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix, 0)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    sx, sy = pix.width / clip.width, pix.height / clip.height
    for mx0, my0, mx1, my1 in masks:
        X0 = int(max(0, (fr.x0 + mx0 * fr.width - clip.x0) * sx)); X1 = int(min(pix.width, (fr.x0 + mx1 * fr.width - clip.x0) * sx))
        Y0 = int(max(0, (fr.y0 + my0 * fr.height - clip.y0) * sy)); Y1 = int(min(pix.height, (fr.y0 + my1 * fr.height - clip.y0) * sy))
        if X1 <= X0 or Y1 <= Y0:
            continue
        sub = a[Y0:Y1, X0:X1].astype(np.float32)
        # 赤シートは赤(R)の成分しか通さないので、範囲内の画素を「R=255・濃さは赤の濃淡」に置き換える。
        # 白→白、黒い文字→赤(#ff3300)、薄い色の縁や色つきの文字→薄い赤。赤シートを重ねると範囲内は全部同じ明るさになり、文字の縁も消える
        t = (0.299 * sub[..., 0] + 0.587 * sub[..., 1] + 0.114 * sub[..., 2]) / 255.0
        t = np.clip((t - 0.15) / 0.8, 0, 1)            # 少しコントラストを上げて、赤字がはっきり見えるように
        out = np.stack([np.full_like(t, 255), 51 + 204 * t, 255 * t], axis=-1)
        a[Y0:Y1, X0:X1] = out.round().astype(np.uint8)
    return pymupdf.Pixmap(pymupdf.csRGB, pix.width, pix.height, a.tobytes(), 0)


if __name__ == "__main__":
    m = sys.argv[1]
    _, smap = slide_map(m)
    nums = [int(x) for x in sys.argv[2:]] or sorted(smap)
    print(m, "slides found:", sorted(smap))
    for n in nums:
        print(n, "auto", [round(v, 2) for v in auto_rel(m, n)], render(f"figA:{m}:{n}"))


def grid(module, n, dpi=130):
    """範囲を決めるための目盛り付き画像（0.1刻み）を figs/grid_<module>_<n>.png に書き出す"""
    path, smap = slide_map(module)
    pi, fr = smap[n]
    doc = pymupdf.open(path)
    page = doc[pi]
    for k in range(1, 10):
        x = fr.x0 + fr.width * k / 10
        y = fr.y0 + fr.height * k / 10
        page.draw_line((x, fr.y0), (x, fr.y1), color=(0, 0.6, 1), width=0.3)
        page.draw_line((fr.x0, y), (fr.x1, y), color=(0, 0.6, 1), width=0.3)
        page.insert_text((x + 0.5, fr.y0 + 5), f"{k/10:.1f}", fontsize=4, color=(0, 0.4, 1))
        page.insert_text((fr.x0 + 0.5, y - 0.5), f"{k/10:.1f}", fontsize=4, color=(0, 0.4, 1))
    out = os.path.join(OUTDIR, f"grid_{module}_{n}.png")
    page.get_pixmap(clip=fr, dpi=dpi).save(out)
    return out
