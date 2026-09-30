"""PDF -> テキスト（色・太字マーク付き）
  [赤:…] [青:…] [紫:…] [色#xxxxxx:…]  **…** = 太字"""
import sys, pymupdf, re, collections
NAMES={0xff2600:'赤',0xff0000:'赤',0x0433ff:'青',0x0000ff:'青',0x9437ff:'紫'}
def cname(c):
    if c in NAMES: return NAMES[c]
    r,g,b=c>>16,(c>>8)&255,c&255
    if max(r,g,b)<90: return None          # 黒〜濃いグレー＝通常文字
    return f'#{c:06x}'
def isbold(s):
    f=s['font'].lower()
    return bool(s['flags']&16) or any(k in f for k in ('bold','w6','w7','w8','w9','heavy','black','demi','semibold'))
doc=pymupdf.open(sys.argv[1])
fonts=collections.Counter()
out=[]
def hlines(p):
    L=[]
    for d in p.get_drawings():
        for it in d['items']:
            if it[0]=='l':
                a,b=it[1],it[2]
                if abs(a.y-b.y)<1.2 and abs(a.x-b.x)>4: L.append((min(a.x,b.x),max(a.x,b.x),(a.y+b.y)/2))
            elif it[0]=='re':
                r=it[1]
                if r.height<2.2 and r.width>4: L.append((r.x0,r.x1,(r.y0+r.y1)/2))
    return L
def underlined(bb,L):
    x0,y0,x1,y1=bb; w=max(x1-x0,1)
    for lx0,lx1,ly in L:
        if y0+0.65*(y1-y0)<=ly<=y1+3.5 and (min(x1,lx1)-max(x0,lx0))>0.6*w: return True
    return False
for pi,p in enumerate(doc,1):
    out.append(f'\n===== PDF p{pi} =====')
    HL=hlines(p)
    for b in p.get_text('dict',sort=True)['blocks']:
        for l in b.get('lines',[]):
            line=''
            for s in l['spans']:
                t=s['text']
                if not t.strip(): line+=t; continue
                fonts[s['font']]+=len(t)
                c=cname(s['color']); bd=isbold(s)
                if bd: t=f'**{t}**'
                if underlined(s['bbox'],HL): t=f'<u>{t}</u>'
                if c: t=f'[{c}:{t}]'
                line+=t
            if line.strip(): out.append(line)
txt='\n'.join(out)
txt=re.sub(r'\]\[(赤|青|紫|#[0-9a-f]{6}):', lambda m:'', txt) if False else txt
open(sys.argv[2],'w').write(txt)
print('fonts:',fonts.most_common(12))
print('chars',len(txt))
