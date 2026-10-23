"""Resmî fotoğrafı olmayan haberler için Wikimedia Commons'tan habere uygun, serbest lisanslı fotoğraf seçer.

Commons'taki her dosya serbest lisanslıdır (CC BY, CC BY-SA, CC0, kamu malı); fotoğrafçı ve lisans haberin altında
yazılır. Gazete/ajans fotoğrafı kullanılmaz (telif). Sıra: başlıktaki yer/kurum adları -> ilçe + konu -> konu -> ilçe ->
Eskişehir. Aynı fotoğraf 14 gün içinde tekrar kullanılmaz (data/commons_used.json).
"""

import json
import random
import re
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).parent
USED = ROOT / "data" / "commons_used.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "Nabiz26Bot/1.0 (https://nabiz26.com; iletisim@nabiz26.com)"}

# Başlıkta geçerse doğrudan aranacak yer ve kurumlar (anahtar küçük harfle aranır)
ENTITIES = {
    "togg": "Togg", "eskişehirspor": "Eskişehirspor", "es-es": "Eskişehirspor",
    "anadolu üniversitesi": "Anadolu Üniversitesi", "osmangazi üniversitesi": "Eskişehir Osmangazi Üniversitesi",
    "esogü": "Eskişehir Osmangazi Üniversitesi", "teknik üniversite": "Eskişehir Teknik Üniversitesi",
    "estü": "Eskişehir Teknik Üniversitesi", "şehir hastanesi": "Eskişehir Şehir Hastanesi",
    "tramvay": "Eskişehir tramvay", "porsuk": "Porsuk River Eskişehir", "sazova": "Sazova Park Eskişehir",
    "kent park": "Kentpark Eskişehir", "odunpazarı modern": "Odunpazarı Modern Müze", "omm": "Odunpazarı Modern Müze",
    "haller": "Haller Gençlik Merkezi", "yunus emre": "Yunus Emre Eskişehir", "nasreddin": "Nasreddin Hoca Sivrihisar",
    "kurşunlu": "Kurşunlu Külliyesi", "lületaşı": "Lületaşı", "midas": "Midas Monument", "frig": "Phrygian Valley",
    "tren garı": "Eskişehir railway station", "yht": "YHT Eskişehir", "hava üssü": "Eskişehir Air Base",
    "meclis": "Building of the Grand National Assembly of Turkey", "tbmm": "Building of the Grand National Assembly of Turkey",
    "cumhurbaşkanlığı": "Presidential Complex Ankara", "külliye": "Presidential Complex Ankara",
    "kızılay": "Kızılay Square Ankara", "anıtkabir": "Anıtkabir", "çarşı": "Eskişehir çarşı",
    "sakarya ılıca": "Sakarı Ilıca", "şeker fabrikası": "Eskişehir Şeker Fabrikası", "tülomsaş": "TÜLOMSAŞ",
    "tusaş": "TUSAŞ Engine", "organize sanayi": "Eskişehir Organize Sanayi Bölgesi",
    # Konu kelimeleri
    "yangın": "Turkish fire truck", "itfaiye": "Turkish fire truck", "kaza": "traffic accident Turkey",
    "deprem": "earthquake Turkey", "elektrik kesintisi": "power lines Turkey", "su kesintisi": "water pipe repair",
    "kar ": "Eskişehir snow", "sel ": "flood Turkey", "konser": "concert crowd stage", "festival": "Eskişehir festival",
    "tiyatro": "theatre stage Turkey", "sergi": "art exhibition gallery", "kütüphane": "library Turkey",
    "altın": "gold jewelry Grand Bazaar", "akaryakıt": "fuel station Turkey", "benzin": "fuel station Turkey",
    "otobüs": "Eskişehir bus", "yol çalışması": "road works Turkey", "asfalt": "road works Turkey",
    "hastane": "Eskişehir Şehir Hastanesi", "aşı": "vaccination Turkey", "orman": "forest Eskişehir",
}
# Ulusal (Türkiye) haberlerinde Eskişehir fotoğrafı kullanılmaz
NATIONAL = {
    "Eğitim": ["Ministry of National Education Turkey", "school classroom Turkey"], "Sağlık": ["Ministry of Health Turkey", "hospital Turkey"],
    "Ekonomi": ["Turkish lira", "Borsa Istanbul"], "Asayiş": ["Turkish police car", "Jandarma Turkey"],
    "Spor": ["football stadium Turkey"], "Ulaşım": ["Turkish State Railways", "highway Turkey"],
    "Tarım": ["wheat field Turkey"], "Kültür-Sanat": ["Ankara State Opera", "museum Turkey"],
}
CATEGORY = {
    "Asayiş": ["Turkish police car", "Jandarma Turkey", "Polis Eskişehir"], "Ekonomi": ["Eskişehir çarşı", "Turkish lira", "Eskişehir sanayi"],
    "Siyaset": ["Building of the Grand National Assembly of Turkey", "Ankara Kızılay"], "Türkiye": ["Ankara city", "Türkiye"],
    "Eğitim": ["Anadolu Üniversitesi", "Eskişehir Osmangazi Üniversitesi", "school Turkey classroom"],
    "Sağlık": ["Eskişehir Şehir Hastanesi", "hospital Turkey"], "Spor": ["Eskişehir Atatürk Stadyumu", "Eskişehirspor", "Eskişehir sports hall"],
    "Kültür-Sanat": ["Odunpazarı Modern Müze", "Odunpazarı evleri", "Eskişehir opera"], "Tarım": ["Eskişehir tarla", "wheat field Turkey"],
    "Ulaşım": ["Eskişehir tramvay", "Eskişehir railway station", "Eskişehir road"], "Hava Durumu": ["Eskişehir panorama", "Porsuk River Eskişehir"],
    "Belediye": ["Eskişehir Büyükşehir Belediyesi", "Eskişehir city"], "Gündem": ["Eskişehir city", "Eskişehir"],
}
SKIP = re.compile(r"map|harita|logo|flag|bayrak|coat|arma|seal|mühür|diagram|chart|plan|signature|imza|svg|icon|"
                  r"locator|location|konum|graph|poster|afiş|badge|rozet", re.I)


def _artist(meta):
    raw = (meta.get("Artist") or {}).get("value", "") or "bilinmiyor"
    return re.sub(r"<[^>]+>", "", raw).strip()[:80] or "bilinmiyor"


def search(query, n=20):
    r = requests.get(API, params={"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                  "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": n, "prop": "imageinfo",
                                  "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1280}, headers=UA, timeout=30)
    out = []
    for p in ((r.json().get("query") or {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png") or ii.get("width", 0) < 900 or SKIP.search(p["title"]):
            continue
        meta = ii.get("extmetadata") or {}
        out.append({"title": p["title"], "thumb": ii.get("thumburl") or ii["url"], "page": ii.get("descriptionurl"),
                    "landscape": ii["width"] / max(1, ii["height"]) >= 1.2, "artist": _artist(meta),
                    "license": (meta.get("LicenseShortName") or {}).get("value", "serbest lisans")})
    return out


def queries(a):
    title = a.get("title", "").lower()
    qs = [q for k, q in ENTITIES.items() if k in title]
    dist, cat = a.get("district", ""), a.get("category", "")
    local = dist not in ("Merkez", "Türkiye", "")
    cats = NATIONAL.get(cat, ["Building of the Grand National Assembly of Turkey", "Ankara city"]) if dist == "Türkiye" \
        else CATEGORY.get(cat, [])
    if local and cat in ("Belediye", "Gündem", "Kültür-Sanat", "Tarım", "Hava Durumu"):
        qs.append(f"{dist} Eskişehir")
    qs += cats[:2]
    if local:
        qs.append(f"{dist} Eskişehir")
    if dist != "Türkiye":
        qs.append("Eskişehir")
    return list(dict.fromkeys(qs))


def pick(a):
    used = json.loads(USED.read_text(encoding="utf-8")) if USED.exists() else {}
    now = time.time()
    used = {k: v for k, v in used.items() if now - v < 14 * 86400}
    for q in queries(a):
        try:
            res = search(q)
        except Exception:
            continue
        fresh = [r for r in res if r["title"] not in used]
        pool = [r for r in fresh if r["landscape"]] or fresh
        if pool:
            choice = random.choice(pool[:6])
            used[choice["title"]] = now
            USED.write_text(json.dumps(used, ensure_ascii=False), encoding="utf-8")
            return choice
    return None


def fetch(a, out_path):
    """Habere uygun Commons fotoğrafını indirir, 1280 px'e küçültüp kaydeder; görsel kaydını döndürür."""
    c = pick(a)
    if not c:
        return None
    r = requests.get(c["thumb"], headers=UA, timeout=60)
    r.raise_for_status()
    im = Image.open(BytesIO(r.content)).convert("RGB")
    im.thumbnail((1280, 1280))
    im.save(out_path, "JPEG", quality=84, optimize=True, progressive=True)
    return {"file": f"images/{Path(out_path).name}", "source_url": c["page"], "representative": True,
            "credit": f"{c['artist']} / Wikimedia Commons ({c['license']})"}
