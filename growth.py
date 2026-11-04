"""Instagram büyüme ölçümü (@nabiz26haber): takipçi sayısını ve son paylaşımların performansını kaydeder.

Yalnızca okur; IG_ACCESS_TOKEN (instagram.py ile aynı) gerekir. Çıktılar:
  data/growth.json  günlük takipçi/paylaşım sayısı + son paylaşımların erişim, beğeni, kaydetme değerleri
  BUYUME.md         insan okuyabilir özet: takipçi eğrisi, türe göre ortalama erişim, en iyi paylaşımlar
İzin ya da metrik yoksa (Insights için instagram_business_manage_insights gerekir) o kısım atlanır ve nedeni
growth.json içindeki "notlar" alanına yazılır; takipçi sayısı yine kaydedilir.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "growth.json"
REPORT = ROOT / "BUYUME.md"
GRAPH = f"https://graph.instagram.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
TR = timezone(timedelta(hours=3))
MEDIA_METRICS = ["reach", "saved", "shares", "total_interactions", "views"]


def get(path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:300]) from None


def media_insights(mid):
    """Bir paylaşımın metrikleri; türe göre desteklenmeyenler atlanır."""
    out = {}
    for m in MEDIA_METRICS:
        try:
            d = get(f"{mid}/insights", metric=m)["data"]
            if d:
                out[m] = d[0]["values"][0]["value"]
        except Exception:
            continue
    return out


def main():
    if not os.environ.get("IG_ACCESS_TOKEN"):
        print("IG_ACCESS_TOKEN tanımlı değil; ölçüm atlandı.")
        return
    state = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"gunluk": [], "paylasimlar": {}, "notlar": []}
    notes = []
    me = get("me", fields="username,followers_count,follows_count,media_count")
    today = datetime.now(TR).strftime("%Y-%m-%d")
    row = {"gun": today, "takipci": me.get("followers_count"), "takip": me.get("follows_count"), "paylasim": me.get("media_count")}
    # Aynı gün birden çok çalışırsa son değer kalır
    state["gunluk"] = [r for r in state["gunluk"] if r["gun"] != today] + [row]
    state["gunluk"] = state["gunluk"][-400:]
    print(f"@{me.get('username')}: {row['takipci']} takipçi, {row['paylasim']} paylaşım")

    # Hesap erişimi (son 7 gün): Insights izni yoksa atlanır
    try:
        since = int(time.time()) - 7 * 86400
        d = get("me/insights", metric="reach", period="day", since=since, until=int(time.time()))["data"]
        row["erisim_7g"] = sum(v["value"] for v in d[0]["values"])
    except Exception as e:
        notes.append(f"hesap erişimi okunamadı: {str(e)[:160]}")

    # Son paylaşımlar ve performansları
    try:
        items = get("me/media", fields="id,media_type,media_product_type,permalink,timestamp,like_count,comments_count,caption", limit=30)["data"]
    except Exception as e:
        items = []
        notes.append(f"paylaşım listesi okunamadı: {str(e)[:160]}")
    for it in items:
        rec = state["paylasimlar"].get(it["id"], {})
        rec.update({"tur": it.get("media_product_type") or it.get("media_type"), "zaman": it["timestamp"],
                    "link": it["permalink"], "baslik": (it.get("caption") or "").split("\n")[0][:90],
                    "begeni": it.get("like_count"), "yorum": it.get("comments_count")})
        age = time.time() - datetime.fromisoformat(it["timestamp"].replace("Z", "+00:00")).timestamp()
        if age > 3600:  # ilk saatte metrikler henüz oturmamıştır
            rec.update(media_insights(it["id"]))
        state["paylasimlar"][it["id"]] = rec
    # Eski kayıtları sınırla
    keep = sorted(state["paylasimlar"].items(), key=lambda kv: kv[1]["zaman"], reverse=True)[:300]
    state["paylasimlar"] = dict(keep)
    state["notlar"] = notes
    DATA.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(state)


def write_report(state):
    days = state["gunluk"]
    lines = ["# Instagram büyüme raporu (@nabiz26haber)", "",
             f"Güncelleme: {datetime.now(TR):%d.%m.%Y %H:%M} TSİ. Otomatik üretilir (`growth.py`, `growth.yml`).", ""]
    if days:
        last = days[-1]
        lines.append(f"**Takipçi: {last['takipci']}** · takip edilen {last['takip']} · paylaşım {last['paylasim']}")
        for label, n in (("Son 1 gün", 1), ("Son 7 gün", 7), ("Son 30 gün", 30)):
            old = next((r for r in reversed(days) if r["gun"] <= (datetime.now(TR) - timedelta(days=n)).strftime("%Y-%m-%d")), None)
            if old and old.get("takipci") is not None and last.get("takipci") is not None:
                diff = last["takipci"] - old["takipci"]
                lines.append(f"- {label}: {diff:+d} takipçi")
        lines += ["", "| Gün | Takipçi | Paylaşım | 7 gün erişim |", "|---|---|---|---|"]
        for r in days[-14:][::-1]:
            lines.append(f"| {r['gun']} | {r.get('takipci')} | {r.get('paylasim')} | {r.get('erisim_7g', '-')} |")
    posts = list(state["paylasimlar"].values())
    by = {}
    for p in posts:
        by.setdefault(p["tur"], []).append(p)
    if any("reach" in p for p in posts):
        lines += ["", "## Türe göre ortalama (son paylaşımlar)", "", "| Tür | Adet | Erişim | Beğeni | Kaydetme | Paylaşma |", "|---|---|---|---|---|---|"]
        avg = lambda L, k: round(sum(x.get(k) or 0 for x in L) / max(1, len(L)), 1)
        for t, L in sorted(by.items(), key=lambda kv: -avg(kv[1], "reach")):
            L2 = [x for x in L if "reach" in x]
            if L2:
                lines.append(f"| {t} | {len(L2)} | {avg(L2, 'reach')} | {avg(L2, 'begeni')} | {avg(L2, 'saved')} | {avg(L2, 'shares')} |")
        top = sorted([p for p in posts if "reach" in p], key=lambda p: p["reach"], reverse=True)[:8]
        lines += ["", "## En çok erişen paylaşımlar", ""]
        for p in top:
            lines.append(f"- {p['reach']} erişim · {p.get('begeni')} beğeni · {p.get('saved', 0)} kayıt · {p['tur']} · [{p['baslik']}]({p['link']})")
    if state.get("notlar"):
        lines += ["", "## Notlar", ""] + [f"- {n}" for n in state["notlar"]]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("büyüme ölçümü başarısız:", str(e)[:300], file=sys.stderr)
        sys.exit(1)
