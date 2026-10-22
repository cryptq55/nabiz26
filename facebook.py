"""Yeni haberleri "Nabız 26" Facebook sayfasında paylaşır (Graph API, sayfa token'ı).

instagram.py'den sonra çalışır ve aynı önem puanı dağılımını izler: önemi 3 ve üzeri fotoğraflı haberler
haber bağlantısıyla birlikte fotoğraf gönderisi olur; Instagram için üretilmiş Reels videosu (R2'de) varsa
sayfada Reels olarak da paylaşılır. Paylaşılanlar data/facebook.json dosyasında tutulur.

Ortam değişkenleri: FB_PAGE_ID ve FB_PAGE_TOKEN (süresiz sayfa token'ı); yoksa paylaşım atlanır.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
STATE = ROOT / "data" / "facebook.json"
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
MAX_POSTS, MAX_REELS = 2, 1  # tur başına
POST_MIN, REEL_MIN = 3, 4


def call(path, url=None, headers=None, **params):
    params["access_token"] = os.environ["FB_PAGE_TOKEN"]
    req = urllib.request.Request(url or f"{GRAPH}/{path}", data=urllib.parse.urlencode(params).encode(),
                                 headers=headers or {}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:500]) from None


def message(f):
    """Facebook'ta bağlantı tıklanabilir: Instagram açıklamasındaki "profildeki bağlantı" yerine haberin adresi."""
    text = f["caption"].replace("📲 Haberin tamamı profildeki bağlantıda: nabiz26.com", f"📲 Haberin tamamı: {f['url']}")
    return text


def post_reel(page, f, video_url):
    start = call(f"{page}/video_reels", upload_phase="start")
    vid = start["video_id"]
    req = urllib.request.Request(start.get("upload_url") or f"https://rupload.facebook.com/video-upload/v23.0/{vid}",
                                 method="POST", headers={"Authorization": f"OAuth {os.environ['FB_PAGE_TOKEN']}",
                                                         "file_url": video_url})
    with urllib.request.urlopen(req, timeout=120) as r:
        json.load(r)
    call(f"{page}/video_reels", upload_phase="finish", video_id=vid, video_state="PUBLISHED", description=message(f))
    return vid


def main():
    page = os.environ.get("FB_PAGE_ID")
    if not page or not os.environ.get("FB_PAGE_TOKEN"):
        print("Facebook sayfa bilgileri (FB_PAGE_ID, FB_PAGE_TOKEN) tanımlı değil; paylaşım atlandı.")
        return
    feed = json.loads((ROOT / "public" / "social" / "feed.json").read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if not state:
        # İlk çalıştırmada geriye dönük paylaşma: yalnızca bundan sonraki haberler
        state = {"posts": [f["slug"] for f in feed[2:]], "reels": [f["slug"] for f in feed[3:]]}
    imp = lambda f: int(f.get("importance") or 3)
    ig = json.loads((ROOT / "data" / "instagram.json").read_text(encoding="utf-8")) if (ROOT / "data" / "instagram.json").exists() else {}
    public = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    # Reels: Instagram için üretilmiş video R2'de hazır
    for f in [f for f in feed if imp(f) >= REEL_MIN and f["slug"] in ig.get("reels", [])
              and f["slug"] not in state["reels"]][:MAX_REELS]:
        if public:
            try:
                print("facebook reels:", f["slug"], post_reel(page, f, f"{public}/reels/{f['slug'][:80]}.mp4"))
            except Exception as e:
                print("facebook reels hatası:", f["slug"], str(e)[:300], file=sys.stderr)
        state["reels"].append(f["slug"])
    cands = [f for f in feed[:12] if f["has_photo"] and imp(f) >= POST_MIN and f["slug"] not in state["posts"]]
    for f in sorted(cands, key=imp, reverse=True)[:MAX_POSTS]:
        try:
            res = call(f"{page}/photos", url=f["post"], message=message(f))
            print("facebook gönderi:", f["slug"], res.get("post_id") or res.get("id"))
            state["posts"].append(f["slug"])
        except RuntimeError as e:
            print("facebook gönderi hatası:", f["slug"], e, file=sys.stderr)
    for k in ("posts", "reels"):
        state[k] = state[k][-500:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
