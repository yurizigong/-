"""解剖：各問題の答えの語が、スライド（colorU_<m>.txt）で赤字・青字・太字・下線になっているかを自動で調べて emph_<m>.py に書く
usage: python3 emph.py <m> ...   → EMPH = {問題文: ["赤字", "青字", "太字", "下線"]}（当てはまるものだけ）"""
import importlib, re, sys, unicodedata

TAGS = ["赤字", "青字", "太字", "下線"]


def norm(s):
    s = re.sub(r"\|[ぁ-んァ-ヶー・]+", "", s).replace("《", "").replace("》", "")
    s = re.sub(r"<[^>]+>", "", s)
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


def styled(text):
    """各スタイルについて、その書式の文字だけを残し、ほかを区切り「｜」にした文字列を返す"""
    out = {t: [] for t in TAGS}
    color = []          # 色の入れ子（赤/青/その他）
    bold = ul = False
    i = 0
    while i < len(text):
        m = re.match(r"\[(赤|青|#[0-9a-fA-F]{6}|紫):", text[i:])
        if m:
            color.append(m.group(1)); i += m.end(); continue
        if text[i] == "]" and color:
            color.pop(); i += 1; continue
        if text.startswith("**", i):
            bold = not bold; i += 2; continue
        if text.startswith("<u>", i):
            ul = True; i += 3; continue
        if text.startswith("</u>", i):
            ul = False; i += 4; continue
        c = text[i]; i += 1
        if c in "\n 　":
            continue                     # 行の折り返しでは区切らない
        c = unicodedata.normalize("NFKC", c)
        cur = color[-1] if color else None
        flags = {"赤字": cur == "赤", "青字": cur == "青", "太字": bold, "下線": ul}
        for t in TAGS:
            out[t].append(c if flags[t] else "｜")
    return {t: "".join(v) for t, v in out.items()}


def atoms(ans):
    a = norm(ans)
    parts = [p for p in re.split(r"[・／/、,，（）()「」：:；;→⇒〜~]|または|および", a) if p]
    return a, parts


def main(m):
    st = styled(open(f"colorU_{m}.txt", encoding="utf-8").read())
    a = importlib.import_module("a_" + m)
    res, cnt = {}, {t: 0 for t in TAGS}
    for _, items in a.SECTIONS:
        for it in items:
            if it[0] == "FIG":
                continue
            tags = []
            for t in TAGS:
                s = st[t]
                hit = False
                for ans in it[2]:
                    whole, parts = atoms(ans)
                    cands = [whole] + parts
                    for p in cands:
                        if len(p) >= 2 and p in s:
                            hit = True; break
                        if len(p) == 1 and f"｜{p}｜" in f"｜{s}｜":   # 1文字の答えは、その字だけが強調されているとき
                            hit = True; break
                    if hit:
                        break
                if hit:
                    tags.append(t); cnt[t] += 1
            res[it[1]] = tags
    with open(f"emph_{m}.py", "w", encoding="utf-8") as f:
        f.write("# 自動生成（emph.py）：答えの語がスライドで赤字・青字・太字・下線になっている問題\nEMPH = {\n")
        for k, v in res.items():
            f.write(f"{k!r}: {v!r},\n")
        f.write("}\n")
    any_ = sum(1 for v in res.values() if v)
    print(f"{m}: {len(res)}問  印あり {any_}  " + " ".join(f"{t}{c}" for t, c in cnt.items()))


for m in sys.argv[1:]:
    main(m)
