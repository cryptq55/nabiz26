"""Yeni haberleri Instagram'a paylaşır (Instagram Graph API, içerik yayınlama).

Görseller sitede yayınlandıktan sonra çalışır: nabiz26.com/social/feed.json okunur ve haberler editörün verdiği
önem puanına göre dağıtılır: her yeni haber story; önemi 3 ve üzeri fotoğraflı haberler sesli Reels (reels.py ile
üretilir, Cloudflare R2'ye yüklenir, akışta da görünür). R2 ayarı yoksa bu haberler fotoğraf gönderisi olur.
Paylaşılanlar data/instagram.json dosyasında tutulur.

Yöntem: "Instagram girişi ile Instagram API" (graph.instagram.com). Facebook sayfası, işletme
portföyü veya sistem kullanıcısı gerekmez; token doğrudan @nabiz26haber'den alınır ve 60 gün geçerlidir.
`python instagram.py --refresh` token'ı yeniler (ig-token.yml iş akışı haftada bir çalıştırır).

Ortam değişkenleri: IG_ACCESS_TOKEN (zorunlu), IG_USER_ID (isteğe bağlı; yoksa token'dan bulunur),
isteğe bağlı GRAPH_VERSION. Eski Facebook-girişli token kullanılacaksa IG_API=facebook.
"""

import json
import os
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://nabiz26.com"
STATE = Path(__file__).parent / "data" / "instagram.json"
HOST = "graph.facebook.com" if os.environ.get("IG_API") == "facebook" else "graph.instagram.com"
GRAPH = f"https://{HOST}/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
MAX_STORIES = 4   # tur başına
MAX_POSTS = 2     # tur başına; yalnızca Reels'e dönüştürülemeyen haberler için (R2 yoksa)
MAX_REELS = 2     # tur başına; akış video ağırlıklı: önemli haberler fotoğraf yerine Reels olur
POST_MIN, REEL_MIN = 3, 3  # gönderi ve Reels için en düşük önem puanı


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    req = urllib.request.Request(url if method == "POST" else f"{url}?{data.decode()}",
                                 data=data if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:500]) from None


LIMITED = False  # Instagram "çok fazla işlem" dedi: bu turda başka paylaşım denenmez


def publish(user, tries=20, **media):
    global LIMITED
    if LIMITED:
        raise RuntimeError("bu turda Instagram işlem sınırına ulaşıldı, sonraki tura kaldı")
    time.sleep(8)  # art arda paylaşımlar Instagram'ın saatlik sınırına takılmasın
    try:
        container = call("POST", f"{user}/media", **media)["id"]
    except RuntimeError as e:
        if "2207042" in str(e) or '"code":9' in str(e):
            LIMITED = True
        raise
    for _ in range(tries):  # Instagram görseli/videoyu işleyene kadar bekle
        status = call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram görseli işleyemedi")
        time.sleep(3)
    try:
        return call("POST", f"{user}/media_publish", creation_id=container)["id"]
    except RuntimeError as e:
        if "2207042" in str(e) or '"code":9' in str(e):
            LIMITED = True
        raise


def quota_left(user):
    """Instagram'ın 24 saatlik paylaşım kotasından kalan hak (Reels, gönderi ve story hepsi sayılır)."""
    try:
        d = call("GET", f"{user}/content_publishing_limit", fields="quota_usage,config")["data"][0]
        return int(d["config"]["quota_total"]) - int(d["quota_usage"])
    except Exception as e:  # kota okunamazsa temkinli davran
        print("[uyarı] kota okunamadı:", str(e)[:200], file=sys.stderr)
        return 6


def upload_r2(path, key):
    """Videoyu Cloudflare R2'ye yükler ve herkese açık adresini döndürür (Instagram videoyu adresten çeker)."""
    import boto3
    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    s3.upload_file(str(path), os.environ["R2_BUCKET"], key, ExtraArgs={"ContentType": "video/mp4"})
    return f"{os.environ['R2_PUBLIC_URL'].rstrip('/')}/{key}"


def make_reel_video(slug):
    """Haberin Reels videosunu üretir ve R2'ye yükler; video adresini döndürür."""
    import build
    import reels
    a = next(x for x in build.load_articles() if x["slug"] == slug)
    img = build.DATA_DIR.parent / a["image"]["file"] if a.get("image") else None
    out = Path(tempfile.gettempdir()) / f"{slug[:60]}.mp4"
    voiced = reels.make_reel(a, img, out)
    print("reels videosu:", slug, "sesli" if voiced else "sessiz")
    return upload_r2(out, f"reels/{slug[:80]}.mp4")


def refresh():
    """60 günlük token'ı yeniler ve yeni token'ı yalnızca stdout'a yazar (iş akışı onu gizli değişkene kaydeder).
    Token en az 24 saatlik ve süresi dolmamış olmalı."""
    q = urllib.parse.urlencode({"grant_type": "ig_refresh_token",
                                "access_token": os.environ["IG_ACCESS_TOKEN"]})
    try:
        with urllib.request.urlopen(f"https://graph.instagram.com/refresh_access_token?{q}", timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Token yenilenemedi: {e.read().decode()[:300]}")
    print(f"Token yenilendi, {data['expires_in'] // 86400} gün geçerli.", file=sys.stderr)
    print(data["access_token"])


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        print("Instagram token'ı (IG_ACCESS_TOKEN) tanımlı değil; paylaşım atlandı.")
        return
    user = os.environ.get("IG_USER_ID") or call("GET", "me", fields="user_id")["user_id"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"stories": [], "posts": []}
    local = Path(__file__).parent / "public" / "social" / "feed.json"  # iş akışında build.py üretir
    if local.exists():
        feed = json.loads(local.read_text(encoding="utf-8"))
    else:
        req = urllib.request.Request(f"{SITE}/social/feed.json?t={int(time.time())}",
                                     headers={"User-Agent": "Mozilla/5.0 (compatible; nabiz26-bot)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            feed = json.load(r)
    state.setdefault("reels", [])
    if not state["stories"] and not state["posts"]:
        # İlk çalıştırmada eski haberlerin hepsini birden paylaşma: en yeni 2 haberle başla
        state["stories"] = [f["slug"] for f in feed[2:]]
        state["posts"] = [f["slug"] for f in feed[2:]]
    if not state["reels"]:
        state["reels"] = [f["slug"] for f in feed[3:]]  # Reels geriye dönük üretilmesin
    imp = lambda f: int(f.get("importance") or 3)
    left = quota_left(user) - 1  # bir hak yedekte kalsın
    print("kalan paylaşım hakkı:", left)
    # 1) Reels: önemi yüksek, henüz Reels'i yapılmamış en yeni haber (R2 ayarlıysa)
    forced = os.environ.get("REEL_SLUG", "").strip()  # elle seçilen haber (iş akışı girdisi)
    failed = set()
    if os.environ.get("R2_BUCKET") and left > 0:
        picks = ([f for f in feed if forced in f["slug"]][:1] if forced else
                 sorted([f for f in feed[:12] if f["has_photo"] and imp(f) >= REEL_MIN and f["slug"] not in state["reels"]],
                        key=imp, reverse=True)[:min(MAX_REELS, max(0, left))])
        for f in picks:
            try:
                url = make_reel_video(f["slug"])
                mid = publish(user, tries=60, media_type="REELS", video_url=url, caption=f["caption"], share_to_feed="true")
                print("reels:", f["slug"], mid)
                left -= 1
            except Exception as e:
                print("reels hatası:", f["slug"], str(e)[:300], file=sys.stderr)
                failed.add(f["slug"])  # Reels olmadıysa fotoğraf gönderisi olarak paylaşılabilsin
            state["reels"].append(f["slug"])  # hata verse de tekrar denenmesin
    # 2) Gönderi: önemi yeterli fotoğraflı haberler, en önemliler önce
    # Reels'i yapılan haber ayrıca fotoğraf gönderisi olmaz (Reels akışta da görünür)
    reeled = set(state["reels"]) - failed if os.environ.get("R2_BUCKET") else set()
    cands = [f for f in feed[:12] if f["has_photo"] and imp(f) >= POST_MIN
             and f["slug"] not in state["posts"] and f["slug"] not in reeled]
    for f in sorted(cands, key=imp, reverse=True)[:min(MAX_POSTS, max(0, left))]:
        try:
            mid = publish(user, image_url=f["post"], caption=f["caption"])
            print("gönderi:", f["slug"], mid)
            state["posts"].append(f["slug"])
            left -= 1
        except RuntimeError as e:
            print("gönderi hatası:", f["slug"], e, file=sys.stderr)
    # 3) Story: kalan hakla, en yeniler (fazlası atlanır)
    new = [f for f in reversed(feed) if f["slug"] not in state["stories"]]  # eskiden yeniye
    take = new[-min(MAX_STORIES, max(0, left)):] if left > 0 else []
    for f in take:
        try:
            mid = publish(user, image_url=f["story"], media_type="STORIES")
            print("story:", f["slug"], mid)
            state["stories"].append(f["slug"])
        except RuntimeError as e:
            print("story hatası:", f["slug"], e, file=sys.stderr)
    # Atlananlar bir daha denenmesin
    for f in new:
        if f not in take:
            state["stories"].append(f["slug"])
    for k in ("stories", "posts", "reels"):
        state[k] = state[k][-500:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    refresh() if "--refresh" in sys.argv else main()
