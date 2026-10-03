"""形式A・Bが元の問題データ（<m>.py）の隠れた答えを漏れなくカバーしているか機械チェック
usage: python3 check_ab.py <module> [<module> ...]
- 元データの {…}（隠れた答え）を「・／、→（）」などで語に分解し、
  A: 答え欄＋解説の赤字 / B: 本文の赤字 に含まれているかを調べる
- A: 問題数・★の一致、文中に［n］と答えの数が合っているか、問題文に自分の答えが見えていないか
- B: 赤字でない（黒字の）部分に、そのブロックの答え語がそのまま出ていないか
"""
import importlib, re, sys, unicodedata

SPLIT = re.compile(r"[・／/、,，→＋+（）()「」『』：:；;\s]|<br>|\bor\b|または|および|と")


def norm(s):
    s = re.sub(r"\|[ぁ-んァ-ヶー・]+", "", s)          # ルビ（語|よみ）のよみを除く
    s = s.replace("《", "").replace("》", "")
    s = re.sub(r"\[\[[^\]]*\]\]", "", s)               # 図の指定を除く
    s = re.sub(r"<[^>]+>", "", s)                      # HTMLタグを先に除く（＜＞がNFKCで<>になるため）
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


def atoms(hidden):
    out = []
    for h in hidden:
        for a in SPLIT.split(norm(h)):
            a = a.strip("①②③④⑤⑥⑦⑧⑨⑩ ")
            if len(a) >= 2 and not re.fullmatch(r"[0-9.%〜~\-ー]+", a):
                out.append(a)
    return out


def covered(at, hidden_text):
    """短い語は完全一致、長い語句（9字以上）は3文字単位の6割以上が隠れていればOK"""
    if at in hidden_text:
        return True
    if len(at) <= 8:
        return False
    grams = [at[i:i + 3] for i in range(len(at) - 2)]
    return sum(g in hidden_text for g in grams) / len(grams) >= 0.6


def hidden_of(text):
    return re.findall(r"\{([^{}]*)\}", text)


def main(m):
    q = importlib.import_module(m)
    probs = []
    qitems = [(sec, it) for sec, items in q.SECTIONS for it in items]
    # ---- A（元の問題はすべて含め、テストに出そうな問題を追加してよい。上限88問）
    try:
        a = importlib.import_module("a_" + m)
        aitems = [(sec, it) for sec, items in a.SECTIONS for it in items if it[0] != "FIG"]
        LIM = max(getattr(q, "LIMIT", 88), 130)   # 見直しで空欄の多い問題を分けたので上限を130に
        if len(aitems) > LIM:
            probs.append(f"A: 問題数 {len(aitems)} が上限{LIM}を超えている")
        if len(aitems) < len(qitems):
            probs.append(f"A: [要確認] 問題数 {len(aitems)} が元の {len(qitems)} より少ない（まとめた問題があるなら可）")
        all_hidden = []
        noexp = 0
        for n, (_, ai) in enumerate(aitems, 1):
            star, sent, answers, note = ai[:4]
            if star not in (0, 1):
                probs.append(f"A{n}: ★の値が0/1でない")
            nums = sorted(set(int(x) for x in re.findall(r"［(\d+)］", sent)))
            if nums != list(range(1, len(answers) + 1)):
                probs.append(f"A{n}: 空欄番号{nums}と答えの数{len(answers)}が合わない")
            if len(answers) >= 6:
                probs.append(f"A{n}: 空欄が{len(answers)}個で多すぎる（4個までに分ける。同じ種類の語を並べる一覧でも5個まで）")
            elif len(answers) == 5:
                probs.append(f"A{n}: [要確認] 空欄が5個（同じ種類の語を並べる一覧なら可。それ以外は分ける）")
            all_hidden += list(answers) + hidden_of(re.sub(r"\[\[[^\]]*\]\]", "", note))
            if not re.sub(r"\[\[[^\]]*\]\]", "", note).strip():
                noexp += 1
            vis = norm(re.sub(r"［\d+］", "", sent) + re.sub(r"\{[^{}]*\}", "", note))
            for ans in answers:
                for at in atoms([ans]):
                    if len(at) >= 3 and at in vis:
                        probs.append(f"A{n}: [要確認] 答え「{at}」が見える文字（問題文/解説）に出ている（二択の選択肢などなら可）")
        atext = norm("／".join(all_hidden))
        for k, (_, qi) in enumerate(qitems, 1):
            for at in atoms(hidden_of(qi[2])):
                if not covered(at, atext):
                    probs.append(f"A: 元の問題{k}の答え「{at}」がどこにも隠れた答えとして入っていない")
        for r in getattr(q, "RED", []):
            miss = [at for at in atoms([r]) if not covered(at, atext)]
            if miss:
                probs.append(f"A: [要確認] スライドの赤字「{r}」の「{'・'.join(miss)}」が隠れた答えに入っていない（出ない理由があれば可）")
        figs = sum(len(re.findall(r"\[\[fig\|", it[3])) for _, it in aitems)
        print(f"   (A: {len(aitems)}問 / 元{len(qitems)}問, 図{figs}枚, 解説なし{noexp}問, ★{sum(it[0] for _, it in aitems)})")
    except ModuleNotFoundError:
        probs.append("A: a_%s.py がない" % m)
    # ---- B
    try:
        b = importlib.import_module("b_" + m)
        red_all = norm("／".join("／".join(hidden_of(re.sub(r"\[\[[^\]]*\]\]", "", h))) for _, _, h in b.BLOCKS))
        vis_all = []
        if [t for t, _, _ in b.BLOCKS] != [s for s, _ in q.SECTIONS]:
            probs.append("B: ブロック見出しが元のセクション名・順番と違う")
        n = 0
        for (sec, items), (bt, rng, html) in zip(q.SECTIONS, b.BLOCKS):
            first, last = n + 1, n + len(items)
            n = last
            exp = f"{first}〜{last}" if first != last else f"{first}"
            if rng != exp:
                probs.append(f"B[{bt}]: 問題No.「{rng}」は「{exp}」のはず")
            vis = norm(re.sub(r"\{[^{}]*\}", "", re.sub(r"<div class='ct'>.*?</div>", "", re.sub(r"\[\[[^\]]*\]\]", "", html))))
            for k, it in enumerate(items, first):
                for at in atoms(hidden_of(it[2])):
                    if not covered(at, red_all):
                        probs.append(f"B: 問題{k}の答え「{at}」が赤字になっていない")
                    elif len(at) >= 3 and at in vis:
                        probs.append(f"B[{bt}]: [要確認] 答え「{at}」が黒字の部分にも出ている（出てくるたびに赤字にする）")
    except ModuleNotFoundError:
        pass
    print(f"== {m}: {'OK' if not probs else str(len(probs)) + ' 件'}")
    for p in probs:
        print("  -", p)


for m in sys.argv[1:]:
    main(m)
