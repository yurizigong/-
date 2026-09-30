"""ウィキメディア・コモンズ（自由ライセンスの画像）から画像を取得する
- 参照の書き方（データ中）: "web:File:ファイル名.jpg"
- 取得時にライセンスと作者を記録し、キャプションに出典を自動で付ける
- 使えるライセンス: パブリックドメイン / CC0 / CC BY / CC BY-SA のみ
usage: python3 webimg.py search "キーワード"      （候補一覧：タイトル・ライセンス・サイズ）
       python3 webimg.py get "File:xxx.jpg"        （取得して figs/web_… に保存、情報を表示）
"""
import json, os, re, sys, time, urllib.parse, urllib.request, html

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs")
os.makedirs(OUT, exist_ok=True)
UA = "RedSheetStudyBuilder/1.0 (personal nursing study materials; non-commercial)"
API = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"(public domain|pd|cc0|cc[- ]by(-sa)?)", re.I)


def _get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(8 * (k + 1))


def api(**params):
    params["format"] = "json"
    time.sleep(1.0)
    return json.loads(_get(API + "?" + urllib.parse.urlencode(params)))


def info(title):
    d = api(action="query", titles=title, prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=960)
    page = next(iter(d["query"]["pages"].values()))
    ii = page["imageinfo"][0]
    md = ii.get("extmetadata", {})
    strip = lambda k: re.sub(r"<[^>]+>", "", html.unescape(md.get(k, {}).get("value", ""))).strip()
    return {"title": title, "url": ii.get("thumburl") or ii["url"], "orig": ii["url"],
            "license": strip("LicenseShortName"), "artist": strip("Artist")[:80],
            "desc": strip("ImageDescription")[:200], "w": ii.get("width"), "h": ii.get("height")}


def path_for(title):
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", title.replace("File:", ""))[:90]
    return os.path.join(OUT, "web_" + os.path.splitext(safe)[0] + ".jpg")


def fetch(title):
    """取得してJPEGで保存。(パス, 出典文字列) を返す。ライセンスが自由でなければ例外"""
    p = path_for(title)
    meta = p + ".json"
    if os.path.exists(p) and os.path.exists(meta):
        m = json.load(open(meta))
    else:
        m = info(title)
        if not OK_LIC.search(m["license"] or ""):
            raise ValueError(f"{title}: 使えないライセンス「{m['license']}」")
        data = _get(m["url"])
        tmp = p + ".src"
        open(tmp, "wb").write(data)
        import pymupdf
        pix = pymupdf.Pixmap(tmp)
        if pix.alpha:
            pix = pymupdf.Pixmap(pix, 0)
        if pix.n > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        pix.save(p, jpg_quality=82)
        os.remove(tmp)
        json.dump(m, open(meta, "w"), ensure_ascii=False)
    credit = f"出典：Wikimedia Commons（{m['artist'] or '作者不明'}／{m['license']}）"
    return p, credit


def search(q, n=12):
    d = api(action="query", list="search", srsearch=q, srnamespace=6, srlimit=n)
    rows = []
    for s in d["query"]["search"]:
        try:
            m = info(s["title"])
            rows.append((s["title"], m["license"], f"{m['w']}x{m['h']}", m["desc"][:80]))
        except Exception as e:
            rows.append((s["title"], "?", "?", str(e)[:60]))
    return rows


if __name__ == "__main__":
    if sys.argv[1] == "search":
        for r in search(" ".join(sys.argv[2:])):
            print(" | ".join(str(x) for x in r))
    elif sys.argv[1] == "get":
        print(fetch(sys.argv[2]))
