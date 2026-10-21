"""data/articles içindeki haberlerden statik siteyi public/ klasörüne üretir."""

import json
import math
import os
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsbot import CATEGORIES, DISTRICTS, slugify

ROOT = Path(__file__).parent
OUT = ROOT / "public"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data" / "articles"))
SITE = {
    "name": os.environ.get("SITE_NAME", "Nabız 26"),
    "url": os.environ.get("SITE_URL", "").rstrip("/"),
    "tagline": "Eskişehir'in nabzı, 7/24",
    "email": os.environ.get("SITE_EMAIL", "iletisim@nabiz26.com"),
}
# Her kategorinin kendi rengi: kartlarda, rozetlerde ve kapak görsellerinde kullanılır
CATEGORY_COLORS = {
    "Gündem": "#e11d48", "Asayiş": "#475569", "Belediye": "#0891b2", "Ekonomi": "#059669",
    "Eğitim": "#7c3aed", "Sağlık": "#0d9488", "Spor": "#ea580c", "Kültür-Sanat": "#c026d3",
    "Tarım": "#65a30d", "Ulaşım": "#2563eb", "Hava Durumu": "#0284c7",
}
TR_MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
             "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def to_tr_time(iso):
    # Türkiye saati (UTC+3, yaz saati uygulaması yok)
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc)
    return datetime.fromtimestamp(dt.timestamp() + 3 * 3600, timezone.utc)


def load_articles():
    articles = []
    for f in DATA_DIR.glob("*.json"):
        a = json.loads(f.read_text(encoding="utf-8"))
        if a.get("status") != "published":
            continue
        d = to_tr_time(a["published_at"])
        a["paragraphs"] = [p.strip() for p in a["body"].split("\n\n") if p.strip()]
        a["date_tr"] = f"{d.day} {TR_MONTHS[d.month - 1]} {d.year}, {d:%H:%M}"
        a["time_tr"] = f"{d:%H:%M}"
        a["rfc822"] = format_datetime(datetime.fromisoformat(a["published_at"]))
        a["read_min"] = max(1, math.ceil(len(a["body"].split()) / 200))
        a["color"] = CATEGORY_COLORS.get(a["category"], "#e11d48")
        articles.append(a)
    return sorted(articles, key=lambda a: a["published_at"], reverse=True)


def main():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape())
    env.filters["slug"] = slugify
    articles = load_articles()
    now = to_tr_time(datetime.now(timezone.utc).isoformat())
    common = {
        "site": SITE, "categories": CATEGORIES, "districts": DISTRICTS, "colors": CATEGORY_COLORS,
        "year": now.year, "today": f"{now.day} {TR_MONTHS[now.month - 1]} {now.year}, {TR_DAYS[now.weekday()]}",
        "ticker": articles[:8],
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")
    images = DATA_DIR.parent / "images"
    if images.exists():
        shutil.copytree(images, OUT / "images")

    def render(template, path, **ctx):
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        # Göreli bağlantılar: site alt dizinde (ör. GitHub Pages) de çalışsın
        base = "../" * path.count("/")
        target.write_text(env.get_template(template).render(**common, base=base, path=path, **ctx), encoding="utf-8")

    by_cat = {c: [a for a in articles if a["category"] == c] for c in CATEGORIES}
    # Manşete son 6 haber içinden fotoğraflı olan çıksın
    lead = next((a for a in articles[:6] if a.get("image")), articles[0] if articles else None)
    side = [a for a in articles[:5] if a is not lead][:4]
    render("index.html", "index.html", articles=articles, by_cat=by_cat, title=None, lead=lead, side=side)
    for cat, items in by_cat.items():
        render("list.html", f"kategori/{slugify(cat)}.html", articles=items, title=cat,
               kind="Kategori", color=CATEGORY_COLORS[cat])
    for dist in DISTRICTS:
        items = [a for a in articles if a["district"] == dist]
        render("list.html", f"ilce/{slugify(dist)}.html", articles=items, title=dist, kind="İlçe", color=None)
    for a in articles:
        related = [r for r in by_cat[a["category"]] if r["slug"] != a["slug"]][:4]
        latest = [r for r in articles if r["slug"] != a["slug"]][:6]
        render("article.html", f"haber/{a['slug']}.html", a=a, related=related, latest=latest, title=a["title"])
    render("kunye.html", "kunye.html", title="Künye ve Yayın İlkeleri")
    render("ara.html", "ara.html", title="Haber Ara")
    render("rss.xml", "rss.xml", articles=articles[:50])
    render("sitemap.xml", "sitemap.xml", articles=articles)
    # İstemci tarafı arama için hafif dizin
    index = [{"t": a["title"], "s": a["spot"], "c": a["category"], "d": a["district"],
              "u": f"haber/{a['slug']}.html", "p": a["published_at"]} for a in articles[:1000]]
    (OUT / "search.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"Site üretildi: {len(articles)} haber -> {OUT}")


if __name__ == "__main__":
    main()
