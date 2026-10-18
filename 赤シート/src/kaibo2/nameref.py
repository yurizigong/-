"""「No.@id の①」型の参照を、その問題の答えの名称に置き換える（解剖生理学Ⅱ用）
build_info(amod) → {id: (番号, [答え...])}
resolve(text, info) … ①〜つきの参照を名称に。置けないものは「No.12の①」のまま
fix_<m>.json … {"12": [["置換前","置換後"], ...], "n12": [...]}  12＝問題番号、n12＝その解説。名称にしたあとの文に当てる
"""
import json, os, re

CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
REF = re.compile(r"No\.@([A-Za-z]+)(?:の図の|の)?([①-⑳](?:[①-⑳]|[と・、〜](?=[①-⑳]))*)")
BARE = re.compile(r"No\.@([A-Za-z]+)")
RUBY = re.compile(r"([^|{}《》<>、。・（）()\s]+)\|([ぁ-んァ-ヶー・]+)")


def build_info(amod):
    info, n = {}, 0
    for _, items in amod.SECTIONS:
        for it in items:
            if it[0] == "FIG":
                continue
            n += 1
            if len(it) > 4:
                info[it[4]] = (n, it[2])
    return info


def name_of(ans):
    """答えを文の中に入れる形に。ルビ（語|よみ）は黒字ルビ《語|よみ》にする（すでに《》の所はそのまま）"""
    a = ans.strip()
    keep = []
    a = re.sub(r"《[^《》]*》", lambda m: keep.append(m.group(0)) or f"\0{len(keep) - 1}\0", a)
    a = RUBY.sub(lambda m: f"《{m.group(1)}|{m.group(2)}》", a)
    return re.sub(r"\0(\d+)\0", lambda m: keep[int(m.group(1))], a)


def resolve(text, info):
    def rep(m):
        i, run = m.group(1), m.group(2)
        n, answers = info[i]
        cs = re.findall("[①-⑳]", run)
        if any(CIRC.index(c) >= len(answers) for c in cs):
            return f"No.{n}の{run}"                     # 図のラベルなど、答えの数を超える番号は置けない
        s, prev = "", ""
        for c in run:
            if c in CIRC and prev and prev in CIRC:
                s += "・"
            s += c
            prev = c
        s = re.sub(r"([①-⑳])〜([①-⑳])", lambda mm: "・".join(CIRC[CIRC.index(mm.group(1)):CIRC.index(mm.group(2)) + 1]), s)
        return re.sub(r"[①-⑳]", lambda mm: name_of(answers[CIRC.index(mm.group(0))]), s)
    return REF.sub(rep, text)


def to_number(text, info):
    """残った No.@id（名称にしなかった参照）は番号に"""
    return BARE.sub(lambda m: f"No.{info[m.group(1)][0]}", text)


def load_fixes(m):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"fix_{m}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def apply_fixes(text, key, fixes, where=""):
    for old, new in fixes.get(key, []):
        if text.count(old) != 1:
            raise SystemExit(f"fix_{where}: {key}: 「{old}」が文中に{text.count(old)}回（1回でなければならない）: {text[:60]}")
        text = text.replace(old, new)
    return text


def full(text, n, info, fixes, key_prefix="", where=""):
    t = to_number(resolve(text, info), info)
    return apply_fixes(t, f"{key_prefix}{n}", fixes, where)
