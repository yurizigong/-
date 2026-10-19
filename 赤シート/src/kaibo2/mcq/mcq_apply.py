"""mcqv_<m>.json の直しを mcq_<m>.json に反映する。usage: python3 mcq_apply.py（元は mcq_<m>.json.orig に残す）"""
import json, os, shutil
mods = "shoka1 shoka2 naibunpi1 naibunpi2 shinkei1 shinkei2 shinkei3 kankaku1 kankaku2 seishoku1 seishoku2 hinyo hifu".split()
nfix = ndrop = nok = 0
for m in mods:
    p = f"mcq_{m}.json"
    if not os.path.exists(p + ".orig"):
        shutil.copy(p, p + ".orig")
    d = json.load(open(p + ".orig", encoding="utf-8"))
    v = {x["src"]: x for x in json.load(open(f"mcqv_{m}.json", encoding="utf-8"))}
    missing = [q["src"] for q in d if q["src"] not in v]
    assert not missing, (m, "検査がない", missing)
    out = []
    for q in d:
        x = v[q["src"]]
        if x.get("ok"):
            nok += 1; out.append(q); continue
        if x.get("drop"):
            ndrop += 1; print("drop", m, q["src"], x.get("issue")); continue
        fx = x.get("fix") or {}
        q = dict(q); q.update({k: fx[k] for k in ("stem", "answer", "distractors", "explain") if k in fx})
        nfix += 1; out.append(q)
        print("fix", m, q["src"], "|", x.get("issue", "")[:60])
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", nok, "fix", nfix, "drop", ndrop)
