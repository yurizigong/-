"""四択問題の元にする候補（最頻出・重要）の一覧。usage: python3 mcqcand.py  → mcqcand/<m>.txt"""
import importlib, re, os, nameref
mods = "shoka1 shoka2 naibunpi1 naibunpi2 shinkei1 shinkei2 shinkei3 kankaku1 kankaku2 seishoku1 seishoku2 hinyo hifu".split()
os.makedirs("mcqcand", exist_ok=True)
for m in mods:
    a = importlib.import_module("a_" + m)
    ns = {}; exec(open(f"freq_{m}.py.up1143", encoding="utf-8").read(), ns); U = ns["FREQ"]      # 見直し後の出やすさ（★★★＝2）
    info = nameref.build_info(a); fx = nameref.load_fixes(m)
    out, n = [], 0
    for sec, items in a.SECTIONS:
        out.append(f"\n## {sec}")
        for it in items:
            if it[0] == "FIG": continue
            n += 1
            if not (it[0] or U.get(it[1], 0) >= 2): continue
            s = nameref.full(it[1], n, info, fx, "", m)
            s = re.sub(r"［(\d+)］", lambda mm: "【" + re.sub(r"\|[ぁ-んァ-ヶー・]+", "", it[2][int(mm.group(1)) - 1]) + "】", s)
            s = re.sub(r"[《》]", "", re.sub(r"\|[ぁ-んァ-ヶー・]+", "", s))
            note = nameref.full(it[3], n, info, fx, "n", m)
            note = re.sub(r"\[\[fig\|[^\]]*\]\]", "", note); note = re.sub(r"[{}《》]", "", note); note = re.sub(r"\|[ぁ-んァ-ヶー・]+", "", note)
            out.append(f"No.{n} [{'重要' if it[0] else ''}{'★★★' if U.get(it[1],0)>=2 else '★★'}] {s}\n    解説: {note[:160]}")
    open(f"mcqcand/{m}.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print(m, sum(1 for l in out if l.startswith("No.")))
