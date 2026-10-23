"""Haberin konusuyla birebir ilgili, serbest lisanslı gerçek fotoğrafı Wikimedia Commons'tan bulur.

Gazete ve ajans fotoğrafları telifli olduğu için kullanılmaz. Editör her habere `image_query` yazar: fotoğrafta
görünmesi gereken kişinin, yerin ya da ürünün tam adı (ör. "Kemal Kılıçdaroğlu", "Togg T10X", "Odunpazarı Evleri").
Yalnızca dosya adında bu adın bütün kelimeleri geçen, en az 1000 px genişliğinde, CC BY / CC BY-SA / CC0 /
kamu malı lisanslı fotoğraflar seçilir. Uygun fotoğraf yoksa None döner ve haber yayınlanmaz.
"""

import re
import time
import unicodedata
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "Nabiz26Bot/1.0 (https://nabiz26.com; iletisim@nabiz26.com)"}
OK_LICENSE = re.compile(r"^(cc[ -]by(-sa)?[ -]\d|cc0|public domain|pd\b|pd-)", re.I)
BAD_WORDS = ("logo", "map", "flag", "harita", "bayrak", "signature", "imza", "icon", "diagram", "chart", "poster",
             "afis", "coat of arms", "seal", "svg", "letter", "mektup", "document", "belge", "handwrit", "el yazisi",
             "stamp", "pul", "banknote", "coin", "screenshot", "ekran goruntusu", "graffiti", "caricature", "karikatur",
             "tebrik", "mesaj", "message", "card", "kart", "book", "kitap", "newspaper", "gazete", "cover", "kapak",
             "billboard", "pano", "mural", "banner", "pankart", "sticker")


# Bir kişinin adını taşıyan yerler (stadyum, havalimanı, cadde...) o kişinin fotoğrafı değildir;
# bu kelimeler aranan adın içinde geçmiyorsa dosya elenir
PLACE_WORDS = ("stadium", "stadyum", "stadi", "arena", "airport", "havalimani", "havaalani", "cami", "mosque",
               "caddesi", "cadde", "bulvari", "boulevard", "street", "avenue", "sokak", "school", "okulu", "lisesi",
               "hospital", "hastanesi", "bridge", "koprusu", "tunnel", "tuneli", "parki", "kulliye", "statue", "heykel",
               "bust", "bust", "tomb", "turbe", "station", "istasyon", "ship", "gemi")


def _norm(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _get(params, tries=4):
    for i in range(tries):
        r = requests.get(API, params={**params, "format": "json"}, headers=HEADERS, timeout=30)
        if r.status_code == 429:  # Commons kısa sürede çok istek yapılınca bekletir
            time.sleep(8 * (i + 1))
            continue
        r.raise_for_status()
        return r.json()
    return {}


def candidates(query, limit=15):
    data = _get(dict(action="query", generator="search", gsrnamespace=6, gsrsearch=query, gsrlimit=limit,
                     prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=1600))
    words = [w for w in _norm(query).split() if len(w) > 1]
    out = []
    for p in (data.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        title = _norm(p["title"].removeprefix("File:"))
        lic = re.sub("<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", ""))
        if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1000:
            continue
        if not all(w in title for w in words):  # birebir ilgili: adın bütün kelimeleri dosya adında olmalı
            continue
        if any(b in title for b in BAD_WORDS) or not OK_LICENSE.match(lic):
            continue
        qn = _norm(query)
        if any(w in title.split() and w not in qn for w in PLACE_WORDS):
            continue
        artist = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()[:60]
        out.append({"index": p.get("index", 99), "title": p["title"], "url": ii.get("thumburl") or ii["url"],
                    "page": ii.get("descriptionurl"), "license": lic, "artist": artist or "Bilinmiyor"})
    return sorted(out, key=lambda c: c["index"])


def _wikidata(name, params):
    r = requests.get("https://www.wikidata.org/w/api.php", params={**params, "format": "json"}, headers=HEADERS,
                     timeout=30)
    return r.json() if r.ok else {}


def wikidata_image(query):
    """Kişi/yer/ürünün Wikidata kaydındaki ana görsel (P18): topluluğun seçtiği temsil edici fotoğraf."""
    found = _wikidata(query, dict(action="wbsearchentities", search=query, language="tr", uselang="tr", limit=3))
    words = [w for w in _norm(query).split() if len(w) > 1]
    for ent in found.get("search", []):
        if not all(w in _norm(ent.get("label", "")) for w in words):  # adı birebir tutmalı
            continue
        claims = _wikidata(query, dict(action="wbgetclaims", entity=ent["id"], property="P18")).get("claims", {})
        for cl in claims.get("P18", []):
            fname = cl.get("mainsnak", {}).get("datavalue", {}).get("value")
            if not fname or not fname.lower().endswith((".jpg", ".jpeg")):
                continue
            data = _get(dict(action="query", titles=f"File:{fname}", prop="imageinfo",
                             iiprop="url|extmetadata|size|mime", iiurlwidth=1600))
            for p in (data.get("query", {}).get("pages", {}) or {}).values():
                ii = (p.get("imageinfo") or [{}])[0]
                meta = ii.get("extmetadata", {})
                lic = re.sub("<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", ""))
                if ii.get("width", 0) >= 600 and OK_LICENSE.match(lic):
                    artist = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()[:60]
                    return {"title": p["title"], "url": ii.get("thumburl") or ii["url"], "page": ii.get("descriptionurl"),
                            "license": lic, "artist": artist or "Bilinmiyor"}
    return None


def wikipedia_image(query):
    """Türkçe Vikipedi maddesinin kapak görseli; yalnızca Commons'ta serbest lisanslıysa kullanılır."""
    for lang in ("tr", "en"):
        r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=HEADERS, timeout=30, params=dict(
            action="query", titles=query, redirects=1, prop="pageimages", piprop="name", format="json"))
        if not r.ok:
            continue
        for p in r.json().get("query", {}).get("pages", {}).values():
            words = [w for w in _norm(query).split() if len(w) > 1]
            name = p.get("pageimage")
            if not name or not all(w in _norm(p.get("title", "")) for w in words):
                continue
            data = _get(dict(action="query", titles=f"File:{name}", prop="imageinfo",
                             iiprop="url|extmetadata|size|mime", iiurlwidth=1600))
            for q in (data.get("query", {}).get("pages", {}) or {}).values():
                ii = (q.get("imageinfo") or [{}])[0]
                meta = ii.get("extmetadata", {})
                lic = re.sub("<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", ""))
                if ii.get("mime") == "image/jpeg" and ii.get("width", 0) >= 600 and OK_LICENSE.match(lic):
                    artist = re.sub(r"\s+", " ", re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", ""))).strip()[:60]
                    return {"title": q["title"], "url": ii.get("thumburl") or ii["url"], "page": ii.get("descriptionurl"),
                            "license": lic, "artist": artist or "Bilinmiyor"}
    return None


def _ordered(queries):
    """Aday sırası: her sorgu için önce olaya/konuya özel Commons sonucu, sonra Wikidata/Vikipedi ana görseli,
    sonra kırpılmış portre ("cropped"), en son genel Commons araması."""
    seen = set()
    for q in queries:
        for c in candidates(q)[:3] if len(q.split()) > 3 else []:  # uzun sorgu = olaya özel (ör. iki kişinin görüşmesi)
            yield c
        for c in (wikidata_image(q), wikipedia_image(q)):  # topluluğun seçtiği tek kişilik/temsil edici görsel
            if c:
                yield c
        for c in candidates(f"{q} cropped")[:3]:
            yield c
        for c in candidates(q)[:4]:
            yield c


def find_image(query, images_dir, key):
    """Bulunan ilk uygun fotoğrafı indirip images_dir/<key>.jpg olarak kaydeder.

    query bir metin ya da en özelden en genele sıralı metin listesi olabilir:
    ["Recep Tayyip Erdoğan Mark Carney", "Recep Tayyip Erdoğan"]."""
    queries = [q.strip() for q in ([query] if isinstance(query, str) else (query or [])) if q and q.strip()]
    if not queries:
        return None
    tried = set()
    for c in _ordered(queries):
        if c["title"] in tried:
            continue
        tried.add(c["title"])
        if len(tried) > 8:
            break
        try:
            r = requests.get(c["url"], headers=HEADERS, timeout=40)
            if not r.ok:
                continue
            im = Image.open(BytesIO(r.content)).convert("RGB")
            im.thumbnail((1280, 1280))
            Path(images_dir).mkdir(parents=True, exist_ok=True)
            im.save(Path(images_dir) / f"{key}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
            return {"file": f"images/{key}.jpg", "source_url": c["page"], "archive": True,
                    "credit": f"{c['artist']} / Wikimedia Commons ({c['license']})"}
        except Exception:
            continue
        finally:
            time.sleep(1)
    return None
