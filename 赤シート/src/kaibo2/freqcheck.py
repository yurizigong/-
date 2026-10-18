"""freq_<m>.py（出やすさ 0/1/2）の機械チェック  usage: python3 freqcheck.py <m> ..."""
import importlib, sys, collections
for m in sys.argv[1:]:
    a = importlib.import_module("a_" + m); F = importlib.import_module("freq_" + m).FREQ
    qs = [x for _, it in a.SECTIONS for x in it if x[0] != "FIG"]
    s = [x[1] for x in qs]
    miss = [i + 1 for i, x in enumerate(s) if x not in F]; extra = [k[:30] for k in F if k not in s]
    bad = [k[:30] for k, v in F.items() if v not in (0, 1, 2)]
    imp0 = [i + 1 for i, x in enumerate(qs) if x[0] == 1 and F.get(x[1]) == 0]
    c = collections.Counter(F.get(x, None) for x in s)
    print(f"== {m}: {len(s)}問 {'OK' if not (miss or extra or bad) else 'NG'}  2:{c[2]} 1:{c[1]} 0:{c[0]}  "
          f"({round(100*c[2]/len(s))}%/{round(100*c[1]/len(s))}%/{round(100*c[0]/len(s))}%)")
    if miss: print("  - ない問題 No.", miss)
    if extra: print("  - 余分なキー", extra)
    if bad: print("  - 値が0/1/2でない", bad)
    if imp0: print("  - [要確認] 重要(star=1)なのに 0: No.", imp0)
