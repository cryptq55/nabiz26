"""data/articles içindeki haberlerden statik siteyi public/ klasörüne üretir.

Ortam değişkenleri:
  SITE_URL   sitenin tam adresi (ör. https://nabiz26.com); canonical, sitemap ve RSS için
  LINK_EXT   iç bağlantıların uzantısı. Yerel önizlemede ".html", yayında "" (temiz adresler)
  DATA_DIR   haber klasörü (deneme ve önizleme için)
"""

import hashlib
import json
import math
import os
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageDraw

from newsbot import CATEGORIES, DISTRICTS, slugify
from servis import WEATHER
from social import brand, build_social, cover_image, font

ROOT = Path(__file__).parent
OUT = ROOT / "public"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data" / "articles"))
IMAGES_DIR = DATA_DIR.parent / "images"
EXT = os.environ.get("LINK_EXT", ".html")
REQUIRE_IMAGE = os.environ.get("REQUIRE_IMAGE", "1") != "0"
SITE = {
    "name": os.environ.get("SITE_NAME", "Nabız 26"),
    "url": os.environ.get("SITE_URL", "").rstrip("/"),
    "tagline": "Eskişehir'in nabzı, 7/24",
    "email": os.environ.get("SITE_EMAIL", "iletisim@nabiz26.com"),
    "description": ("Eskişehir son dakika haberleri: Odunpazarı, Tepebaşı ve ilçelerden gündem, belediye, "
                    "eğitim, spor, ekonomi ve asayiş haberleri, hava durumu ve namaz vakitleri Nabız 26'da."),
}
# IndexNow anahtarı: Bing ve Yandex'e yeni sayfaları anında bildirmek için (gizli değildir)
# Instagram açıklamalarına kategoriye göre ek etiketler (keşfedilebilirlik)
CATEGORY_TAGS = {
    "Spor": ["#Eskişehirspor", "#Spor"], "Eğitim": ["#Eğitim", "#Öğrenci"], "Ekonomi": ["#Ekonomi", "#Piyasa"],
    "Asayiş": ["#Asayiş", "#SonDakika"], "Siyaset": ["#Siyaset", "#Gündem"], "Gündem": ["#Gündem", "#SonDakika"],
    "Türkiye": ["#Türkiye", "#Gündem"], "Kültür-Sanat": ["#Kültür", "#Sanat", "#Etkinlik"],
    "Belediye": ["#Belediye", "#YerelYönetim"], "Ulaşım": ["#Ulaşım", "#Trafik"], "Sağlık": ["#Sağlık"],
    "Hava Durumu": ["#HavaDurumu"], "Tarım": ["#Tarım", "#Çiftçi"],
}
# Başlık/etiketlerde geçen sözcüğe göre ek etiketler
KEYWORD_TAGS = [
    ("togg", ["#Togg", "#YerliOtomobil"]), ("elektrik kesinti", ["#ElektrikKesintisi"]),
    ("su kesinti", ["#SuKesintisi"]), ("eskişehirspor", ["#Eskişehirspor"]),
    ("cumhuriyet bayram", ["#CumhuriyetBayramı", "#29Ekim"]), ("anadolu üniversitesi", ["#AnadoluÜniversitesi"]),
    ("deprem", ["#Deprem"]), ("hava durumu", ["#HavaDurumu"]), ("tramvay", ["#EskişehirTramvay"]),
    ("dolar", ["#Dolar", "#Döviz"]), ("enflasyon", ["#Enflasyon"]),
    ("yağış", ["#HavaDurumu", "#Yağış"]), ("kar yağ", ["#KarYağışı", "#HavaDurumu"]),
    ("trafik", ["#Trafik"]), ("yangın", ["#Yangın"]), ("festival", ["#Festival", "#Etkinlik"]),
    ("konser", ["#Konser", "#Etkinlik"]), ("sergi", ["#Sergi", "#Sanat"]), ("seçim", ["#Seçim"]),
    ("asgari ücret", ["#AsgariÜcret"]), ("emekli", ["#Emekli"]), ("öğretmen", ["#Öğretmenler"]),
    ("anadolu efes", ["#AnadoluEfes"]), ("osmangazi üniversitesi", ["#ESOGÜ"]),
    ("29 ekim", ["#CumhuriyetBayramı", "#29Ekim"]), ("cumhuriyetin 103", ["#Cumhuriyet103", "#29Ekim"]),
    ("atatürk", ["#Atatürk"]), ("10 kasım", ["#Atatürk", "#10Kasım"]), ("nöbetçi eczane", ["#NöbetçiEczane"]),
    ("kabine", ["#Kabine"]), ("bal kabağı", ["#Kızılinler", "#Eskişehir"]),
    ("ring sefer", ["#EskişehirUlaşım", "#ÜcretsizUlaşım"]), ("kentsel dönüşüm", ["#KentselDönüşüm"]),
    ("organize sanayi", ["#OSB", "#Sanayi"]), ("teknik üniversite", ["#ESTÜ"]),
    ("çiftçi", ["#Çiftçi", "#Tarım"]), ("kış lastiği", ["#KışLastiği", "#Trafik"]),
    ("hastane", ["#Sağlık", "#Hastane"]), ("bayram", ["#Bayram"]),
    ("solotürk", ["#SoloTürk", "#Gösteri"]), ("maden", ["#Maden", "#Çevre"]),
    ("mahkeme", ["#Mahkeme", "#Hukuk"]),
    ("gram altın", ["#Altın", "#AltınFiyatları"]), ("meteoroloji", ["#HavaDurumu", "#Meteoroloji"]),
    ("afad", ["#AFAD"]), ("kızılay", ["#Kızılay"]), ("kültür bakanlığı", ["#Kültür", "#Sanat"]), ("bisiklet", ["#Bisiklet", "#EskişehirYaşam"]),
]
INDEXNOW_KEY =hashlib.sha1(b"nabiz26-indexnow").hexdigest()
# Her kategorinin kendi rengi: kartlarda, rozetlerde ve kapak görsellerinde kullanılır
CATEGORY_COLORS = {
    "Gündem": "#e11d48", "Asayiş": "#475569", "Belediye": "#0891b2", "Ekonomi": "#059669",
    "Eğitim": "#7c3aed", "Sağlık": "#0d9488", "Spor": "#ea580c", "Kültür-Sanat": "#c026d3",
    "Tarım": "#65a30d", "Ulaşım": "#2563eb", "Hava Durumu": "#0284c7",
    "Siyaset": "#b91c1c", "Türkiye": "#1d4ed8",
}
# Kategori ve ilçe sayfalarının arama sonuçlarındaki açıklamaları
CATEGORY_DESC = {
    "Gündem": "Eskişehir gündem haberleri: kentte bugün öne çıkan gelişmeler, son dakika olaylar ve duyurular.",
    "Asayiş": "Eskişehir asayiş haberleri: trafik kazaları, yangınlar, emniyet ve jandarma çalışmaları.",
    "Belediye": "Eskişehir belediye haberleri: Büyükşehir, Odunpazarı ve Tepebaşı belediyelerinden projeler ve duyurular.",
    "Ekonomi": "Eskişehir ekonomi haberleri: OSB, sanayi, ihracat, esnaf, akaryakıt ve piyasa gelişmeleri.",
    "Eğitim": "Eskişehir eğitim haberleri: Anadolu, Osmangazi ve Teknik üniversiteleri, okullar ve öğrenci duyuruları.",
    "Sağlık": "Eskişehir sağlık haberleri: hastaneler, sağlık hizmetleri, farkındalık etkinlikleri ve araştırmalar.",
    "Spor": "Eskişehir spor haberleri: Eskişehirspor, amatör lig, basketbol ve kentteki spor etkinlikleri.",
    "Kültür-Sanat": "Eskişehir kültür sanat haberleri: konserler, sergiler, tiyatro, festivaller ve etkinlikler.",
    "Tarım": "Eskişehir tarım haberleri: hasat, sulama, çiftçi destekleri ve ilçelerden tarımsal gelişmeler.",
    "Ulaşım": "Eskişehir ulaşım haberleri: tramvay, otobüs seferleri, yol çalışmaları ve trafik düzenlemeleri.",
    "Hava Durumu": "Eskişehir hava durumu haberleri: meteoroloji uyarıları, sıcaklık, yağış ve kar tahminleri.",
    "Siyaset": "Siyaset haberleri: Cumhurbaşkanı, iktidar ve ana muhalefetten açıklamalar, Meclis ve gündem.",
    "Türkiye": "Türkiye haberleri: bakanlıklardan kararlar, açıklamalar ve vatandaşı ilgilendiren gelişmeler.",
}
TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
TR_TZ = timezone(timedelta(hours=3))
# Google'ın büyük önizleme için istediği oranlar (en az 1200 px genişlik)
GOOGLE_RATIOS = {"16x9": (1200, 675), "4x3": (1200, 900), "1x1": (1200, 1200)}
GOOGLE_IMAGE_LIMIT = 200  # her derlemede yalnızca son haberler için üretilir


def district_desc(d):
    if d == "Türkiye":
        return "Türkiye haberleri: Cumhurbaşkanlığı, bakanlıklar ve siyasetten Eskişehirlileri ilgilendiren gelişmeler."
    if d == "Merkez":
        return "Eskişehir merkez haberleri: kent genelini ilgilendiren son dakika gelişmeler ve duyurular."
    return f"{d} haberleri: Eskişehir {d} ilçesinden son dakika gelişmeler, belediye duyuruları ve yerel haberler."


def to_tr_time(iso):
    # Türkiye saati (UTC+3, yaz saati uygulaması yok)
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return datetime.fromtimestamp(dt.timestamp() + 3 * 3600, timezone.utc)


def iso_tr(iso):
    """Arama motorları için sade tarih: Türkiye saati, saniye hassasiyeti (2026-10-21T21:35:08+03:00)."""
    return datetime.fromisoformat(iso).astimezone(TR_TZ).replace(microsecond=0).isoformat()


def google_images(a, out_dir):
    """Google Haberler/Discover için haber fotoğrafının 1200 px genişlikte 16:9, 4:3 ve 1:1 sürümleri."""
    src = DATA_DIR.parent / a["image"]["file"]
    out = []
    for name, (w, h) in GOOGLE_RATIOS.items():
        path = out_dir / f"{a['slug']}-{name}.jpg"
        cover_image(src, w, h, a["color"]).save(path, "JPEG", quality=82, optimize=True, progressive=True)
        out.append({"url": f"{SITE['url']}/images/g/{path.name}", "w": w, "h": h})
    return out


def abs_url(path):
    """Site içi yolu tam adrese çevirir; yayında uzantısız (temiz) adres döner."""
    if path.endswith(".html"):
        path = path[: -len(".html")] + EXT
    if path in ("index" + EXT, "index.html"):
        path = ""
    return f"{SITE['url']}/{path}"


def load_articles():
    articles = []
    for f in DATA_DIR.glob("*.json"):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("status") != "published":
            continue
        if REQUIRE_IMAGE and not a.get("image"):
            continue  # fotoğrafsız haber sitede gösterilmez
        a["published_at"] = iso_tr(a["published_at"])
        if a.get("updated_at"):
            a["updated_at"] = iso_tr(a["updated_at"])
        d = to_tr_time(a["published_at"])
        a["paragraphs"] = [p.strip() for p in a["body"].split("\n\n") if p.strip()]
        a["date_tr"] = f"{d.day} {TR_MONTHS[d.month - 1]} {d.year}, {d:%H:%M}"
        a["time_tr"] = f"{d:%H:%M}"
        a["rfc822"] = format_datetime(datetime.fromisoformat(a["published_at"]))
        a["read_min"] = max(1, math.ceil(len(a["body"].split()) / 200))
        a["color"] = CATEGORY_COLORS.get(a["category"], "#e11d48")
        a["url"] = abs_url(f"haber/{a['slug']}.html")
        img = a.get("image")
        if img and img.get("file"):
            path = DATA_DIR.parent / img["file"]
            if path.exists():
                with Image.open(path) as im:
                    img["w"], img["h"] = im.size
                img["abs"] = f"{SITE['url']}/{img['file']}"
            else:
                a.pop("image")
        elif img:
            a.pop("image")  # eski biçim (uzak adres) kullanılmaz
        if REQUIRE_IMAGE and not a.get("image"):
            continue
        articles.append(a)
    return sorted(articles, key=lambda a: a["published_at"], reverse=True)


def make_brand_images(static_dir):
    """Paylaşım görseli (1200x630) ve yayıncı logosu (512x512) üretir."""
    red, night = (229, 16, 46), (12, 11, 16)
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), night)
    d = ImageDraw.Draw(im)
    d.line([(0, 420), (430, 420), (480, 330), (540, 520), (610, 270), (670, 460), (700, 400), (W, 400)],
           fill=red, width=10, joint="curve")
    brand(d, 80, 110, 190)
    d.text((84, 530), "Eskişehir'in nabzı · 14 ilçe, 7/24 haber", font=font("Inter.ttf", 40, 500), fill=(156, 151, 164))
    im.save(static_dir / "og.png", "PNG", optimize=True)

    logo = Image.new("RGB", (512, 512), red)
    d = ImageDraw.Draw(logo)
    d.line([(40, 290), (170, 290), (205, 200), (255, 380), (310, 140), (350, 320), (372, 280), (472, 280)],
           fill="white", width=26, joint="curve")
    logo.save(static_dir / "logo.png", "PNG", optimize=True)


def main():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())
    env.filters["slug"] = slugify
    articles = load_articles()
    now = datetime.now(timezone.utc)
    now_tr = to_tr_time(now.isoformat())
    common = {
        "site": SITE, "categories": CATEGORIES, "districts": DISTRICTS, "colors": CATEGORY_COLORS,
        "year": now_tr.year, "ext": EXT,
        "today": f"{now_tr.day} {TR_MONTHS[now_tr.month - 1]} {now_tr.year}, {TR_DAYS[now_tr.weekday()]}",
        "ticker": articles[:8], "og_default": f"{SITE['url']}/static/og.png",
        # Stil ve betik değişince tarayıcı önbelleği eski dosyayı kullanmasın
        "asset_v": hashlib.sha1(b"".join((ROOT / "static" / f).read_bytes() for f in ("style.css", "app.js"))).hexdigest()[:8],
    }

    # Ana sayfadaki "Bugün Eskişehir" kutusu için anlık hava ve günün namaz vakitleri
    svc_file = DATA_DIR.parent / "servis.json"
    if svc_file.exists():
        esk = json.loads(svc_file.read_text(encoding="utf-8"))["places"].get("Eskişehir", {})
        common["svc_now"] = {"w": esk.get("weather"), "wx": WEATHER.get((esk.get("weather") or {}).get("code"), ("", "")),
                             "p": next((d for d in esk.get("prayer") or [] if d["date"] == f"{now_tr:%d-%m-%Y}"), None)}

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")
    if IMAGES_DIR.exists():
        shutil.copytree(IMAGES_DIR, OUT / "images")
    make_brand_images(OUT / "static")
    # Instagram gönderi/story görselleri; haber sayfalarındaki "Story'de paylaş" düğmesi de bunları kullanır
    build_social(articles, DATA_DIR.parent, OUT / "social", limit=30)

    org = {"@type": "NewsMediaOrganization", "@id": f"{SITE['url']}/#org", "name": SITE["name"],
           "url": f"{SITE['url']}/", "logo": {"@type": "ImageObject", "url": f"{SITE['url']}/static/logo.png",
                                               "width": 512, "height": 512},
           "email": SITE["email"], "areaServed": {"@type": "City", "name": "Eskişehir"},
           "sameAs": ["https://www.instagram.com/nabiz26haber/"],
           "publishingPrinciples": abs_url("kunye.html") + "#ilkeler"}

    def crumbs(*items):
        return {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}

    def render(template, path, seo, **ctx):
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        # Göreli bağlantılar: site alt dizinde veya yerelde de çalışsın
        base = "../" * path.count("/")
        if path == "404.html" and not EXT:
            base = "/"  # 404 sayfası her adreste gösterilir; göreli yollar bozulmasın
        home = (base or "./") if not EXT else base + "index.html"
        seo.setdefault("canonical", abs_url(path))
        seo.setdefault("image", common["og_default"])
        seo.setdefault("type", "website")
        html = env.get_template(template).render(**common, base=base, home=home, path=path, seo=seo, **ctx)
        target.write_text(html, encoding="utf-8")

    by_cat = {c: [a for a in articles if a["category"] == c] for c in CATEGORIES}
    # "Kentin nabzı" paneli: son 24 saat ve son 7 günün dağılımı
    def within(a, hours):
        return now - datetime.fromisoformat(a["published_at"]) <= timedelta(hours=hours)
    day = [a for a in articles if within(a, 24)]
    week = [a for a in articles if within(a, 24 * 7)]
    cat_counts = sorted(((c, sum(a["category"] == c for a in day)) for c in CATEGORIES), key=lambda x: -x[1])
    dist_counts = {d: sum(a["district"] == d for a in week) for d in DISTRICTS}
    common["pulse"] = {"day": len(day), "week": len(week), "cats": [c for c in cat_counts if c[1]][:5],
                       "districts": dist_counts, "max_dist": max(dist_counts.values() or [0]) or 1}

    # Manşete son 6 haber içinden fotoğraflı olan çıksın
    # Manşet: son fotoğraflı 5 haber sırayla kayar; yanında sonraki 2 haber
    slides = [a for a in articles[:12] if a.get("image")][:5] or articles[:1]
    lead = slides[0] if slides else None
    side = [a for a in articles[:10] if all(a is not x for x in slides)][:2]
    strip = [a for a in articles if all(a is not x for x in slides + side)][:4]  # manşet altı 4'lü sıra
    rest = [a for a in articles if all(a is not x for x in slides + side + strip)][:12]
    home_ld = [org, {"@type": "WebSite", "@id": f"{SITE['url']}/#site", "name": SITE["name"], "url": f"{SITE['url']}/",
                     "inLanguage": "tr-TR", "publisher": {"@id": org["@id"]},
                     "potentialAction": {"@type": "SearchAction", "target": abs_url("ara.html") + "?q={search_term_string}",
                                         "query-input": "required name=search_term_string"}}]
    render("index.html", "index.html",
           {"title": f"{SITE['name']} | Eskişehir Son Dakika Haberleri", "description": SITE["description"],
            "image": lead["image"]["abs"] if lead and lead.get("image") else common["og_default"], "ld": home_ld},
           articles=articles, by_cat=by_cat, title=None, lead=lead, slides=slides, side=side, strip=strip, rest=rest)

    for cat, items in by_cat.items():
        p = f"kategori/{slugify(cat)}.html"
        render("list.html", p, {"title": f"Eskişehir {cat} Haberleri | {SITE['name']}", "description": CATEGORY_DESC[cat],
                                "ld": [crumbs(("Ana Sayfa", f"{SITE['url']}/"), (cat, abs_url(p)))],
                                # Henüz haberi olmayan kategori sayfaları boş sayfa olarak dizinlenmesin
                                "noindex": not items},
               articles=items, title=cat, kind="Kategori", color=CATEGORY_COLORS[cat], intro=CATEGORY_DESC[cat])
    for dist in DISTRICTS:
        items = [a for a in articles if a["district"] == dist]
        p = f"ilce/{slugify(dist)}.html"
        name = "Eskişehir Merkez" if dist == "Merkez" else dist
        render("list.html", p, {"title": f"{name} Haberleri | {SITE['name']}", "description": district_desc(dist),
                                "ld": [crumbs(("Ana Sayfa", f"{SITE['url']}/"), (name, abs_url(p)))],
                                # Henüz haberi olmayan ilçe sayfaları arama motorunda boş sayfa olarak görünmesin
                                "noindex": not items},
               articles=items, title=dist, kind="İlçe", color=None, intro=district_desc(dist))

    gdir = OUT / "images" / "g"
    gdir.mkdir(parents=True, exist_ok=True)
    for i, a in enumerate(articles):
        related = [r for r in by_cat[a["category"]] if r["slug"] != a["slug"]][:4]
        gimgs = google_images(a, gdir) if a.get("image") and i < GOOGLE_IMAGE_LIMIT else []
        if gimgs:
            images, og = [g["url"] for g in gimgs], gimgs[0]
        elif a.get("image"):
            images, og = [a["image"]["abs"]], {"url": a["image"]["abs"], "w": a["image"]["w"], "h": a["image"]["h"]}
        else:
            images, og = [common["og_default"]], {"url": common["og_default"], "w": 1200, "h": 630}
        latest = [r for r in articles if r["slug"] != a["slug"]][:6]
        cat_url = abs_url(f"kategori/{slugify(a['category'])}.html")
        ld = [{"@type": "NewsArticle", "headline": a["title"][:110], "description": a["spot"],
               "datePublished": a["published_at"], "dateModified": a.get("updated_at", a["published_at"]),
               "articleSection": a["category"], "keywords": ", ".join(a.get("tags", [])), "inLanguage": "tr-TR",
               "mainEntityOfPage": a["url"], "url": a["url"], "isAccessibleForFree": True,
               "author": {"@type": "Organization", "name": f"{SITE['name']} Haber Merkezi", "url": f"{SITE['url']}/"},
               "publisher": {"@id": org["@id"]},
               "contentLocation": {"@type": "Place", "name": f"{a['district']}, Eskişehir" if a["district"] not in ("Merkez", "Türkiye") else ("Türkiye" if a["district"] == "Türkiye" else "Eskişehir")},
               "image": images,
               "isBasedOn": a["source"]["url"]},
              crumbs(("Ana Sayfa", f"{SITE['url']}/"), (a["category"], cat_url), (a["title"], a["url"])), org]
        render("article.html", f"haber/{a['slug']}.html",
               {"title": f"{a['title']} | {SITE['name']}", "description": a["spot"], "type": "article",
                "image": og["url"], "image_w": og["w"], "image_h": og["h"], "image_alt": a["title"], "ld": ld,
                "published": a["published_at"], "modified": a.get("updated_at", a["published_at"]),
                "section": a["category"], "tags": a.get("tags", [])},
               a=a, related=related, latest=latest, title=a["title"])

    # Kent servisleri: hava durumu ve namaz vakitleri (Eskişehir + ilçeler), veri servis.yml ile 3 saatte bir yenilenir
    servis_pages = []
    svc_path = DATA_DIR.parent / "servis.json"
    if svc_path.exists():
        svc = json.loads(svc_path.read_text(encoding="utf-8"))
        upd = to_tr_time(svc["updated"])
        today_dmy = f"{now_tr:%d-%m-%Y}"

        def dayname(d):
            y, m, dd = (d.split("-") if len(d.split("-")[0]) == 4 else d.split("-")[::-1])
            dt = datetime(int(y), int(m), int(dd))
            return f"{dt.day} {TR_MONTHS[dt.month - 1]} {TR_DAYS[dt.weekday()]}"

        helpers = {"wx": lambda c: WEATHER.get(c, ("", "")), "dayname": dayname, "places": list(svc["places"]),
                   "all_places": svc["places"], "updated_tr": f"{upd.day} {TR_MONTHS[upd.month - 1]} {upd:%H:%M}",
                   "today_tr": common["today"]}
        for name, place in svc["places"].items():
            slug = "" if name == "Eskişehir" else "/" + slugify(name)
            w = place.get("weather")
            if w:
                p = f"hava-durumu{slug}.html"
                d0 = w["days"][0]
                render("servis.html", p, {
                    "title": f"{name} Hava Durumu: Saatlik ve 7 Günlük Tahmin | {SITE['name']}",
                    "description": (f"{name} hava durumu: şu an {w['temp']}°C, {WEATHER.get(w['code'], ('',))[0].lower()}. "
                                    f"Bugün en düşük {d0['min']}°, en yüksek {d0['max']}°. Saatlik ve 7 günlük tahmin."),
                    "ld": [crumbs(("Ana Sayfa", f"{SITE['url']}/"), ("Hava Durumu", abs_url("hava-durumu.html")),
                                  *([(name, abs_url(p))] if slug else []))]},
                    kind="hava", place=place, name=name, heading=f"{name} hava durumu", root="hava-durumu",
                    other_root="namaz-vakitleri", title=f"{name} Hava Durumu", **helpers)
                servis_pages.append(abs_url(p))
            days = place.get("prayer") or []
            today = next((d for d in days if d["date"] == today_dmy), None)
            if today:
                p = f"namaz-vakitleri{slug}.html"
                i = days.index(today)
                tt = today["times"]
                render("servis.html", p, {
                    "title": f"{name} Namaz Vakitleri ({now_tr.day} {TR_MONTHS[now_tr.month - 1]}): İmsak {tt['İmsak']}, Akşam {tt['Akşam']} | {SITE['name']}",
                    "description": (f"{name} namaz vakitleri bugün: İmsak {tt['İmsak']}, Güneş {tt['Güneş']}, Öğle {tt['Öğle']}, "
                                    f"İkindi {tt['İkindi']}, Akşam {tt['Akşam']}, Yatsı {tt['Yatsı']}. Aylık imsakiye."),
                    "ld": [crumbs(("Ana Sayfa", f"{SITE['url']}/"), ("Namaz Vakitleri", abs_url("namaz-vakitleri.html")),
                                  *([(name, abs_url(p))] if slug else []))]},
                    kind="namaz", place=place, name=name, heading=f"{name} namaz vakitleri", root="namaz-vakitleri",
                    other_root="hava-durumu", today_prayer=today, month=days[i:i + 30],
                    title=f"{name} Namaz Vakitleri", **helpers)
                servis_pages.append(abs_url(p))

    render("kunye.html", "kunye.html", {"title": f"Künye ve Yayın İlkeleri | {SITE['name']}",
                                        "description": f"{SITE['name']} künye bilgileri, yayın ilkeleri ve iletişim."},
           title="Künye ve Yayın İlkeleri")
    render("ara.html", "ara.html", {"title": f"Haber Ara | {SITE['name']}", "description": "Nabız 26 haber arşivinde ara.",
                                    "noindex": True}, title="Haber Ara")
    render("404.html", "404.html", {"title": f"Sayfa bulunamadı | {SITE['name']}", "description": SITE["description"],
                                    "noindex": True, "canonical": f"{SITE['url']}/"}, title="Sayfa bulunamadı")

    # Arama motoru dosyaları
    feed_ctx = {"site": SITE, "now_rfc": format_datetime(now)}
    (OUT / "rss.xml").write_text(env.get_template("rss.xml").render(**feed_ctx, articles=articles[:50]), encoding="utf-8")
    listing = ([(abs_url(f"kategori/{slugify(c)}.html"), by_cat[c][0]["published_at"]) for c in CATEGORIES if by_cat[c]] +
               [(abs_url(f"ilce/{slugify(d)}.html"), next(a["published_at"] for a in articles if a["district"] == d))
                for d in DISTRICTS if dist_counts.get(d) or any(a["district"] == d for a in articles)])
    (OUT / "sitemap.xml").write_text(env.get_template("sitemap.xml").render(
        site=SITE, articles=articles, listing=listing + [(u, now.astimezone(TR_TZ).replace(microsecond=0).isoformat()) for u in servis_pages], home_mod=articles[0]["published_at"] if articles else now.isoformat(),
        kunye=abs_url("kunye.html")), encoding="utf-8")
    # Google Haberler site haritası: yalnızca son 48 saatin haberleri
    fresh = [a for a in articles if within(a, 48)][:1000]
    (OUT / "news-sitemap.xml").write_text(env.get_template("news-sitemap.xml").render(site=SITE, articles=fresh),
                                          encoding="utf-8")
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /ara\n\n"
        f"Sitemap: {SITE['url']}/sitemap.xml\nSitemap: {SITE['url']}/news-sitemap.xml\n", encoding="utf-8")
    (OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    # Cloudflare Pages önbellek ayarları: görseller ve statik dosyalar uzun süre, sayfalar kısa süre
    (OUT / "_headers").write_text(
        "/images/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/static/*\n  Cache-Control: public, max-age=604800\n"
        "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n",
        encoding="utf-8")
    # IndexNow ile bildirilecek adresler (yayın iş akışı kullanır)
    (ROOT / "indexnow-urls.txt").write_text("\n".join([f"{SITE['url']}/"] + [a["url"] for a in fresh]), encoding="utf-8")

    # Instagram: açıklama metinleri ve profil bağlantısı sayfası (görseller yukarıda üretildi)
    feed = []
    for a in articles[:30]:
        tags = ["#Eskişehir", "#nabız26", "#EskişehirHaber"]
        if a["district"] == "Türkiye":  # ulusal haber: yerel etiketler yanlış kitleyi çeker
            tags = ["#nabız26", "#SonDakika", "#Haber"]
        elif a["district"] not in ("Merkez",):
            tags.append("#" + a["district"].replace(" ", ""))
        tags.append("#" + a["category"].replace("-", "").replace(" ", ""))
        for t in CATEGORY_TAGS.get(a["category"], []):
            if t not in tags:
                tags.append(t)
        if "altın" in a["title"].lower():  # günlük altın haberi: aranan etiketler
            tags += [t for t in ("#Altın", "#AltınFiyatları") if t not in tags]
        text = (a["title"] + " " + " ".join(a.get("tags") or [])).lower()
        for kw, kt in KEYWORD_TAGS:  # konuya özgü, aranan etiketler
            if kw in text:
                tags += [t for t in kt if t not in tags]
        tags = tags[:15]  # Instagram en çok 30 etiket izin verir; konuya özgü olanlar sonda, kesilmesin diye 15
        caption = (f"{a['title']}\n\n{a['spot']}\n\n"
                   f"📲 Haberin tamamı profildeki bağlantıda: nabiz26.com\n\n" + " ".join(tags))
        feed.append({"slug": a["slug"], "url": a["url"], "has_photo": bool(a.get("image")),
                     "importance": int(a.get("importance") or 3),
                     "reel": bool(a.get("reel", int(a.get("importance") or 3) >= 4)),
                     "local": a.get("district") != "Türkiye",
                     "video": bool(a.get("video")),  # kaynağın kendi videosu var: Reels öncelikli
                     # Kendi ürettiğimiz başlıklı kapak (gerçek fotoğraf değil): story'ye konmaz
                     "own_cover": (a.get("image") or {}).get("credit") == "Nabız 26",
                     "post": f"{SITE['url']}/{a['social']['post']}", "story": f"{SITE['url']}/{a['social']['story']}",
                     "caption": caption, "published_at": a["published_at"]})
    (OUT / "social" / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    render("instagram.html", "instagram.html",
           {"title": f"{SITE['name']} · Instagram", "description": "Instagram'da paylaştığımız haberlerin tamamı.",
            "noindex": True}, articles=articles[:24], title="Instagram")

    # İstemci tarafı arama için hafif dizin
    index = [{"t": a["title"], "s": a["spot"], "c": a["category"], "d": a["district"],
              "u": f"haber/{a['slug']}{EXT}", "p": a["published_at"]} for a in articles[:1000]]
    (OUT / "search.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"Site üretildi: {len(articles)} haber -> {OUT}")


if __name__ == "__main__":
    main()
