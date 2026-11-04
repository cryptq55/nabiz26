"""Yeni haberleri Instagram'a paylaşır (Instagram Graph API, içerik yayınlama).

Görseller sitede yayınlandıktan sonra çalışır: nabiz26.com/social/feed.json okunur ve haberler editörün verdiği
önem puanına göre dağıtılır: her yeni haber story; önemi 3 ve üzeri fotoğraflı haberler gönderi; editörün "önemli ve
izlenecek" diye işaretlediği haberler (reel) sesli Reels olur (reels.py, video Cloudflare R2'de; akışta da görünür,
o haber ayrıca fotoğraf gönderisi olmaz). R2 ayarı yoksa Reels atlanır.
Paylaşılanlar data/instagram.json dosyasında tutulur.

Yöntem: "Instagram girişi ile Instagram API" (graph.instagram.com). Facebook sayfası, işletme
portföyü veya sistem kullanıcısı gerekmez; token doğrudan @nabiz26haber'den alınır ve 60 gün geçerlidir.
`python instagram.py --refresh` token'ı yeniler (ig-token.yml iş akışı haftada bir çalıştırır).

Ortam değişkenleri: IG_ACCESS_TOKEN (zorunlu), IG_USER_ID (isteğe bağlı; yoksa token'dan bulunur),
isteğe bağlı GRAPH_VERSION. Eski Facebook-girişli token kullanılacaksa IG_API=facebook.
"""

import difflib
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
MAX_STORIES = 2   # tur başına
DAILY_CAP = 16    # 24 saatte en fazla paylaşım: Instagram bu hesapta fiilen ~25 izin veriyor (API 50 dese de);
                  # günlük iki video bülten ve yedek için hak boş kalır
MAX_POSTS = 2     # tur başına; yalnızca Reels'e dönüştürülemeyen haberler için (R2 yoksa)
MAX_REELS = 2     # tur başına (Reels ortalama 517 erişim, fotoğraf gönderisi 6: BUYUME.md, 04.11.2026)
REELS_PER_DAY = 12  # 24 saatte en fazla Reels (videolu haber > editörün "izlenecek" dedikleri > önemli yerel haberler)
POST_MIN = 4      # fotoğraf gönderisi için en düşük önem puanı (erişimi çok düşük, kotayı Reels'e bırak)
DUP_RATIO = 0.7   # iki başlık bu oranda benziyorsa aynı olay sayılır, ikinci kez paylaşılmaz


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


def title_of(f):
    """Haber başlığı: feed.json'da ayrı alan yok, açıklamanın ilk satırıdır."""
    return (f.get("caption") or "").split("\n", 1)[0].strip()


def _key(t):
    return " ".join("".join(c if c.isalnum() else " " for c in t.lower()).split())


def is_dup(f, done):
    """Aynı olayı anlatan başka bir haber zaten paylaşıldıysa True (farklı kaynaktan gelen, benzer başlıklı haber).
    Günlük altın haberleri başlıkları benzese de farklı gündür: kontrol dışı."""
    t = _key(title_of(f))
    if not t or t.startswith("altın fiyatları"):
        return False
    return any(difflib.SequenceMatcher(None, t, d).ratio() >= DUP_RATIO
               for slug, d in done.items() if slug != f["slug"])  # aynı haberin gönderisi ve story'si birbirini engellemez


def save(state):
    """Durumu hemen yazar: tur ortasında bir hata olsa bile paylaşılan haber tekrar paylaşılmasın."""
    for k in ("stories", "posts", "reels"):
        state[k] = state[k][-500:]
    state["reel_log"] = [t for t in state.get("reel_log", []) if time.time() - t < 86400]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


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
    voiced = reels.make_video_reel(a, out) if a.get("video") else reels.make_reel(a, img, out)
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
    shared = set(state["stories"]) | set(state["posts"]) | set(state["reels"])
    done_titles = {f["slug"]: _key(title_of(f)) for f in feed if f["slug"] in shared}
    now = time.time()
    state["log"] = [t for t in state.get("log", []) if now - t < 86400]
    left = min(quota_left(user) - 1, DAILY_CAP - len(state["log"]))  # bir hak yedekte kalsın
    print("kalan paylaşım hakkı:", left)
    # 1) Reels: önemi yüksek, henüz Reels'i yapılmamış en yeni haber (R2 ayarlıysa)
    forced = os.environ.get("REEL_SLUG", "").strip()  # elle seçilen haber (iş akışı girdisi)
    failed = set()
    if os.environ.get("R2_BUCKET") and left > 0:
        # Kaynağın kendi videosu olan haberler her zaman Reels olur ve önce gelir; sonra editörün "izlenecek" dedikleri
        # Yedek olarak: kendi fotoğrafı olan önemli yerel haberler (gün boyu video akışı dursun diye, günde en fazla 8 Reels)
        reels_today = len([t for t in state.get("reel_log", []) if now - t < 86400])
        def score(f):
            if f.get("video"):
                return 3
            if f["has_photo"] and f.get("reel") and (f.get("local", True) or imp(f) >= 5):
                return 2
            if f["has_photo"] and not f.get("own_cover") and f.get("local", True) and imp(f) >= 3:
                return 1
            if f.get("own_cover") and f.get("local", True) and imp(f) >= 4:
                return 0.5  # kendi kapağımızla (kesinti, kaza gibi önemli yerel haberler)
            return 0
        cands = [f for f in feed[:15] if f["slug"] not in state["reels"] and score(f) and not is_dup(f, done_titles)]
        room = min(MAX_REELS, max(0, left), max(0, REELS_PER_DAY - reels_today))
        picks = ([f for f in feed if forced in f["slug"]][:1] if forced else
                 sorted(cands, key=lambda f: (score(f), imp(f)), reverse=True)[:room])
        for f in picks:
            try:
                url = make_reel_video(f["slug"])  # Instagram'a gitmeden önceki adım: hata olursa fotoğraf gönderisine dönülebilir
            except Exception as e:
                print("reels video hatası:", f["slug"], str(e)[:300], file=sys.stderr)
                failed.add(f["slug"])
                state["reels"].append(f["slug"])
                save(state)
                continue
            try:
                mid = publish(user, tries=60, media_type="REELS", video_url=url, caption=f["caption"], share_to_feed="true")
                print("reels:", f["slug"], mid)
                state["log"].append(time.time())
                state.setdefault("reel_log", []).append(time.time())
                done_titles[f["slug"]] = _key(title_of(f))
                left -= 1
            except Exception as e:
                # Instagram'a gönderim denendi: sonucu belirsiz olabilir (zaman aşımı), aynı haber fotoğraf olarak
                # da paylaşılırsa iki kez görünür. Bu yüzden fotoğraf yedeği yok.
                print("reels hatası:", f["slug"], str(e)[:300], file=sys.stderr)
                if LIMITED:
                    continue  # Instagram sınırı: Reels sonraki turda yeniden denensin
            state["reels"].append(f["slug"])
            save(state)
    # 2) Gönderi: önemi yeterli fotoğraflı haberler, en önemliler önce
    # Reels'i yapılan haber ayrıca fotoğraf gönderisi olmaz (Reels akışta da görünür)
    reeled = set(state["reels"]) - failed if os.environ.get("R2_BUCKET") else set()
    cands = [f for f in feed[:12] if f["has_photo"] and imp(f) >= POST_MIN
             and f["slug"] not in state["posts"] and f["slug"] not in reeled and not is_dup(f, done_titles)]
    for f in sorted(cands, key=imp, reverse=True)[:min(MAX_POSTS, max(0, left))]:
        try:
            mid = publish(user, image_url=f["post"], caption=f["caption"])
            print("gönderi:", f["slug"], mid)
            state["log"].append(time.time())
            state["posts"].append(f["slug"])
            done_titles[f["slug"]] = _key(title_of(f))
            save(state)
            left -= 1
        except RuntimeError as e:
            print("gönderi hatası:", f["slug"], e, file=sys.stderr)
    # 3) Story: kalan hakla, en yeniler (fazlası atlanır)
    # Story yalnızca haberin kendi gerçek fotoğrafıyla (kendi başlıklı kapağımız story'de başlığı iki kez gösterir)
    new = [f for f in reversed(feed) if f["slug"] not in state["stories"] and not f.get("own_cover")]
    for f in [f for f in new if is_dup(f, done_titles)]:
        state["stories"].append(f["slug"])  # aynı olay başka haberle zaten paylaşıldı
        new.remove(f)
    take = new[-min(MAX_STORIES, max(0, left)):] if left > 0 else []
    for f in take:
        try:
            mid = publish(user, image_url=f["story"], media_type="STORIES")
            print("story:", f["slug"], mid)
            state["log"].append(time.time())
            state["stories"].append(f["slug"])
            done_titles[f["slug"]] = _key(title_of(f))
            save(state)
        except RuntimeError as e:
            print("story hatası:", f["slug"], e, file=sys.stderr)
    # Atlananlar bir daha denenmesin
    for f in new:
        if f not in take:
            state["stories"].append(f["slug"])
    save(state)


if __name__ == "__main__":
    refresh() if "--refresh" in sys.argv else main()
