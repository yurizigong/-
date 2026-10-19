"""mcq_<m>.json の形式チェック。usage: python3 mcqcheck.py"""
import importlib, json, re, sys
want = {"shoka1": 8, "shoka2": 7, "naibunpi1": 8, "naibunpi2": 8, "shinkei1": 5, "shinkei2": 7, "shinkei3": 9, "kankaku1": 7, "kankaku2": 8, "seishoku1": 8, "seishoku2": 8, "hinyo": 9, "hifu": 8}
bad = tot = 0
for m, k in want.items():
    try: d = json.load(open(f"mcq_{m}.json", encoding="utf-8"))
    except Exception as e: print(m, "未/読めない", e); bad += 1; continue
    a = importlib.import_module("a_" + m); ns = {}; exec(open(f"freq_{m}.py.up1143", encoding="utf-8").read(), ns); U = ns["FREQ"]
    qs = [it for _, items in a.SECTIONS for it in items if it[0] != "FIG"]
    srcs = [q["src"] for q in d]
    errs = []
    if len(d) != k: errs.append(f"問数 {len(d)}≠{k}")
    if len(set(srcs)) != len(srcs): errs.append("元の問題が重複")
    for q in d:
        s = q["src"]
        if not (1 <= s <= len(qs)): errs.append(f"src {s} 範囲外"); continue
        it = qs[s - 1]
        if not (it[0] or U.get(it[1], 0) >= 2): errs.append(f"src {s} は最頻出・重要ではない")
        ch = [q["answer"]] + q["distractors"]
        if len(q["distractors"]) != 3 or len(set(ch)) != 4: errs.append(f"src {s} 選択肢が4つ別でない")
        if re.search(r"No\.|［\d|図の|前の問題", q["stem"]): errs.append(f"src {s} stemが他を指す")
        if q["answer"] in q["stem"] and len(q["answer"]) >= 3: errs.append(f"src {s} 答えがstemに出ている?")
    tot += len(d)
    print(m, len(d), "OK" if not errs else errs)
    bad += bool(errs)
print("合計", tot, "NG" if bad else "OK")
