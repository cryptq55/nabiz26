"""Günlük altın haberi: Harem Altın canlı fiyatlarından sabah haberi ve fiyat tablosu görseli üretir.

GitHub Actions (altin.yml) her sabah 09:00'da (TSİ) çalıştırır. Aynı gün ikinci kez çalışırsa yeni haber yazmaz.
Fiyatlar haremaltin.com'un sayfasında kullandığı canlı fiyat bağlantısından (socket.io) okunur.
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import socketio

import newsbot
from social import topic_card

SOCKET = "https://hrmsocketonly.haremaltin.com"
SOURCE_URL = "https://www.haremaltin.com/altin-fiyatlari"
TR = timezone(timedelta(hours=3))
ITEMS = [  # (Harem kodu, haberdeki ad, ondalık)
    ("KULCEALTIN", "Gram altın", 2), ("CEYREK_YENI", "Çeyrek altın", 0), ("YARIM_YENI", "Yarım altın", 0),
    ("TEK_YENI", "Tam altın", 0), ("ATA_YENI", "Ata altın", 0), ("AYAR22", "22 ayar bilezik (gram)", 2),
    ("ALTIN", "Has altın (gram)", 2), ("ONS", "Ons (dolar)", 2), ("USDTRY", "Dolar/TL", 2),
]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
          "Kasım", "Aralık"]


def fetch_prices(timeout=25):
    need = {code for code, _, _ in ITEMS}
    for attempt in range(3):
        got = {}
        sio = socketio.Client(reconnection=False)
        sio.on("price_changed", lambda data: got.update((data or {}).get("data", {}) or {}))
        try:
            sio.connect(SOCKET, transports=["websocket"], wait_timeout=20,
                        headers={"User-Agent": "Mozilla/5.0", "Origin": "https://www.haremaltin.com"})
            start = time.time()
            while time.time() - start < timeout and not need <= set(got):
                time.sleep(0.5)
        except Exception as e:
            print(f"bağlantı hatası (deneme {attempt + 1}): {e}", file=sys.stderr)
        finally:
            try:
                sio.disconnect()
            except Exception:
                pass
        if need <= set(got):
            return got
        time.sleep(5)
    missing = need - set(got)
    if {"KULCEALTIN", "CEYREK_YENI"} & missing:
        sys.exit(f"Fiyatlar alınamadı, eksik: {sorted(missing)}")
    return got


def tr_num(x, dec):
    s = f"{float(x):,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(row):
    close, sell = float(row.get("kapanis") or 0), float(row["satis"])
    return (sell - close) / close * 100 if close else 0.0


def pct_text(p):
    return ("+" if p > 0.005 else "-" if p < -0.005 else "") + tr_num(abs(p), 2) + "%"


def main():
    now = datetime.now(TR)
    day = f"{now.day} {MONTHS[now.month - 1]} {now.year}"
    newsbot.ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    for f in newsbot.ARTICLES_DIR.glob("*.json"):
        a = json.loads(f.read_text(encoding="utf-8"))
        if "altin-gunluk" in a.get("tags", []) and a["published_at"][:10] == now.astimezone(timezone.utc).strftime("%Y-%m-%d"):
            print("Bugünün altın haberi zaten var:", a["title"])
            return

    p = fetch_prices()
    gram = p["KULCEALTIN"]
    g_chg = pct(gram)
    saat = f"{now:%H.%M}"
    move = "yükselişle" if g_chg > 0.05 else "düşüşle" if g_chg < -0.05 else "yatay seyirle"
    verb = "yükseldi" if g_chg > 0.05 else "geriledi" if g_chg < -0.05 else "yatay seyretti"

    def sell(code):
        return tr_num(p[code]["satis"], dict((c, d) for c, _, d in ITEMS)[code])

    def buy(code):
        return tr_num(p[code]["alis"], dict((c, d) for c, _, d in ITEMS)[code])

    title = f"Altın fiyatları {day}: Gram altın {sell('KULCEALTIN')} TL"
    spot = (f"Gram altın güne {move} başladı. Harem Altın verilerine göre gram altın {buy('KULCEALTIN')} TL'den alınıyor, "
            f"{sell('KULCEALTIN')} TL'den satılıyor.")
    paras = [
        f"Altın piyasasında güne {move} başlandı. Harem Altın'ın saat {saat} itibarıyla verilerine göre gram altının "
        f"satış fiyatı {sell('KULCEALTIN')} TL, alış fiyatı {buy('KULCEALTIN')} TL oldu. Gram altın, önceki kapanışa "
        f"göre yüzde {tr_num(abs(g_chg), 2)} {verb}.",
    ]
    coins = [(c, n) for c, n, _ in ITEMS if c in ("CEYREK_YENI", "YARIM_YENI", "TEK_YENI", "ATA_YENI") and c in p]
    if coins:
        paras.append("Ziynet altınlarda " + ", ".join(
            f"{n.lower()} {sell(c)} TL" for c, n in coins) + " seviyesinden satışa sunuluyor.")
    extra = []
    if "AYAR22" in p:
        extra.append(f"22 ayar bileziğin gram satış fiyatı {sell('AYAR22')} TL")
    if "ALTIN" in p:
        extra.append(f"has altının gram fiyatı {sell('ALTIN')} TL")
    if extra:
        text = ", ".join(extra)
        paras.append(text[0].upper() + text[1:] + " olarak belirlendi.")
    if "ONS" in p and "USDTRY" in p:
        paras.append(f"Uluslararası piyasalarda altının onsu {sell('ONS')} dolardan işlem görürken, dolar/TL "
                     f"{sell('USDTRY')} seviyesinde bulunuyor.")
    paras.append(f"Fiyatlar Harem Altın'ın saat {saat} itibarıyla paylaştığı verilere dayanmaktadır; kuyumcular "
                 "arasında farklılık gösterebilir. Bu haber yatırım tavsiyesi değildir.")

    rows = []
    for code, name, dec in ITEMS:
        if code in p and code not in ("ATA_YENI", "ALTIN"):
            rows.append((name.replace(" (gram)", "").replace(" (dolar)", " ($)"), tr_num(p[code]["alis"], dec),
                         tr_num(p[code]["satis"], dec), pct_text(pct(p[code]))))
    key = f"altin-{now:%Y%m%d}"
    newsbot.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    topic_card(newsbot.IMAGES_DIR / f"{key}.jpg", title, "Altın", "#b8860b", rows=rows[:7],
               note=f"Kaynak: Harem Altın · {now:%d.%m.%Y} {now:%H:%M}")
    article = {"title": title, "spot": spot, "body": "\n\n".join(paras), "category": "Ekonomi",
               "district": "Merkez", "tags": ["altın", "gram altın", "çeyrek altın", "altın fiyatları", "altin-gunluk"]}
    candidate = {"source_name": "Harem Altın", "title": "Harem Altın canlı fiyatlar", "link": SOURCE_URL}
    record = newsbot.save_article(article, candidate, {"file": f"images/{key}.jpg", "source_url": SOURCE_URL})
    record["image"]["credit"] = "Nabız 26 (veriler: Harem Altın)"
    (newsbot.ARTICLES_DIR / f"{record['slug']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                                                   encoding="utf-8")
    newsbot.write_digest()
    print("yazıldı:", title)


if __name__ == "__main__":
    main()
