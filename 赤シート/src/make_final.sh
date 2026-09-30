set -e
OUT="$1"
python3 combine.py "$OUT" > /tmp/comb1.txt
PP=$(python3 - "$OUT" <<'PY'
import pymupdf,sys,json,re
d=pymupdf.open(sys.argv[1]); res={}
names=[l.split('\t')[0] for l in open('/tmp/comb1.txt') if '\t' in l]
for pi in range(1,d.page_count):
    top=d[pi].get_text()[:120]
    for nm in names:
        i=nm.split('.')[0]
        if i not in res and re.search(r'(^|\n)'+re.escape(nm)+r'\s*\n', top): res[i]=pi+1
print(json.dumps(res))
PY
)
echo "$PP"
PARTPAGES="$PP" python3 combine.py "$OUT"
