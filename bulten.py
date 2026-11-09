"""Günlük video bültenleri (Instagram/Facebook Reels): sabah "Günaydın Eskişehir" ve akşam "Eskişehir'de bugün".

Sabah: hava durumu + namaz vakitleri + günün öne çıkan 3 haberi. Akşam: son 24 saatin en önemli 5 haberi.
Tek seslendirme metni sahnelere bölünür; her sahne, sesin o sahnenin cümlelerine geldiği anda başlar.

Kullanım:  python bulten.py sabah|aksam|hafta [çıktı.mp4]   (yayın: python bulten.py sabah --yayinla)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import reels
from reels import CARD, FPS, H, M, W, caption_img, ease, end_card, ffmpeg_bin, layers, phrases
from social import MUTED, NIGHT, PAPER, RED, beat_line, brand, font, pill

ROOT = Path(__file__).parent
TR = timezone(timedelta(hours=3))
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def anma_gunu(now):
    """10 Kasım: bültenler Atatürk'ü anma kancasıyla açılır."""
    return now.month == 11 and now.day == 10


def first_sentence(text, limit=170):
    s = re.split(r"(?<=[.!?])\s+", text.strip())[0]
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "."


def pick(articles, kind, now):
    """Bültene girecek haberler: fotoğraflı, Eskişehir'le ilgili (ulusal değil), önem ve yeniliğe göre."""
    hours = {"sabah": 14, "hafta": 168}.get(kind, 24)
    pool = [a for a in articles if a.get("image") and a.get("district") != "Türkiye"
            and now - datetime.fromisoformat(a["published_at"]) <= timedelta(hours=hours)]
    pool.sort(key=lambda a: (int(a.get("importance") or 3), a["published_at"]), reverse=True)
    return pool[:3 if kind == "sabah" else 5]


def intro_card(kind, now, svc):
    """İlk sahne: tarih, başlık; sabah bülteninde hava durumu ve namaz vakitleri."""
    im = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(im)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((-300, -200, W + 300, 900), fill=110)
    im.paste(Image.new("RGB", (W, H), RED), (0, 0), glow.filter(ImageFilter.GaussianBlur(220)))
    d = ImageDraw.Draw(im)
    brand(d, M, 250, 72)
    date = f"{now.day} {AYLAR[now.month - 1]} {GUNLER[now.weekday()]}"
    pill(d, M, 420, date.upper(), RED, 34)
    title = {"sabah": "Günaydın\nEskişehir", "hafta": "Eskişehir'de\nbu hafta"}.get(kind, "Eskişehir'de\nbugün")
    if anma_gunu(now):
        title = "Saygıyla\nanıyoruz"
    d.multiline_text((M, 520), title, font=font("Bricolage.ttf", 150, 800), fill="white", spacing=6)
    if kind == "sabah" and svc:
        w, p = svc.get("weather"), svc.get("prayer")
        y = 930
        if w:
            wx = reels_weather(w["code"])
            d.text((M, y), f"{w['temp']}°", font=font("Bricolage.ttf", 170, 800), fill="white")
            d.text((M + 330, y + 30), wx[0], font=font("Bricolage.ttf", 54, 800), fill=PAPER)
            d.text((M + 330, y + 100), f"En düşük {w['days'][0]['min']}° · En yüksek {w['days'][0]['max']}°",
                   font=font("Inter.ttf", 36, 600), fill=MUTED)
            y += 250
        if p:
            cols = list(p["times"].items())
            cw = (W - 2 * M) / 3
            for i, (k, v) in enumerate(cols):
                x, yy = M + (i % 3) * cw, y + (i // 3) * 140
                d.text((x, yy), k.upper(), font=font("Inter.ttf", 28, 700), fill=MUTED)
                d.text((x, yy + 36), v, font=font("Bricolage.ttf", 70, 800), fill="white")
    else:
        d.text((M, 900), "Haftanın öne çıkan haberleri" if kind == "hafta" else "Günün öne çıkan haberleri", font=font("Bricolage.ttf", 56, 800), fill=PAPER)
    beat_line(d, 1650, W, width=7)
    return im


def reels_weather(code):
    from servis import WEATHER
    return WEATHER.get(code, ("", ""))


def counter_badge(i, n):
    im = Image.new("RGBA", (240, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 230, 66), 33, fill=(12, 11, 16, 220))
    d.text((115, 33), f"{i} / {n}", font=font("Bricolage.ttf", 36, 800), fill="white", anchor="mm")
    return im


def build_script(kind, items, now, svc):
    """Okunacak metin ve her sahnenin metindeki başlangıç konumu."""
    date = f"{now.day} {AYLAR[now.month - 1]} {GUNLER[now.weekday()]}"
    parts = []
    if kind == "sabah":
        intro = f"Günaydın Eskişehir. Bugün {date}."
        if anma_gunu(now):
            intro = "Ulu Önder Mustafa Kemal Atatürk'ü saygı, minnet ve özlemle anıyoruz. Bugün 10 Kasım."
        w = (svc or {}).get("weather")
        if w:
            intro += f" Hava {reels_weather(w['code'])[0].lower()}, en yüksek sıcaklık {w['days'][0]['max']} derece."
        intro += " İşte günün öne çıkan haberleri."
    elif kind == "hafta":
        intro = "Eskişehir'de bu hafta. Haftanın en çok öne çıkan haberleri Nabız 26'da."
    else:
        intro = f"Eskişehir'de bugün. {date} gününün öne çıkan haberleri Nabız 26'da."
    parts.append(intro)
    for a in items:  # sıra numarası okunmaz; köşedeki sayaç yeterli
        parts.append(first_sentence(a["spot"]))
    parts.append("Haberlerin tamamı nabız yirmi altı nokta com'da.")
    text, starts = "", []
    for ptxt in parts:
        starts.append(len(text) + (1 if text else 0))
        text = f"{text} {ptxt}".strip()
    return text, starts


def render_bulletin(kind, items, out, now, svc=None):
    text, starts = build_script(kind, items, now, svc)
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "ses.mp3"
        alignment = None
        try:
            alignment = reels.synthesize(text, mp3)
        except Exception as e:
            print("[uyarı] seslendirme yapılamadı:", str(e)[:200])
        caps = phrases(text, alignment, breaks=set(starts))
        if alignment:
            tstart = [alignment[min(s, len(alignment) - 1)][1] for s in starts]
            total = alignment[-1][2] + 0.6
        else:
            tstart = [s / reels.CHARS_PER_SEC for s in starts]
            total = len(text) / reels.CHARS_PER_SEC + 1
        total = max(total, tstart[-1] + 2.4)
        scenes = [("intro", None)] + [("haber", a) for a in items] + [("son", None)]
        intro = intro_card(kind, now, svc)
        endc = end_card()
        L = {}
        for a in items:
            img = ROOT / "data" / a["image"]["file"]
            L[a["slug"]] = layers(a, img)
        cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-"]
        cmd += ["-i", str(mp3)] if alignment else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        cache = {}
        n_items = len(items)
        for f in range(int(total * FPS)):
            t = f / FPS
            si = max(i for i, s in enumerate(tstart) if s <= t + 1e-6) if t >= tstart[0] else 0
            kind_s, a = scenes[si]
            local = t - tstart[si]
            nxt = tstart[si + 1] if si + 1 < len(tstart) else total
            if kind_s == "intro":
                frame = intro.copy()
            elif kind_s == "son":
                frame = endc.copy()
            else:
                Ls = L[a["slug"]]
                frame = Ls["bg"].copy()
                p = min(1, local / max(1, nxt - tstart[si]))
                bw, bh = Ls["big"].size
                x0, y0 = int((bw - cw) * p), int((bh - ch) * (0.3 + 0.4 * p))
                frame.paste(Ls["big"].crop((x0, y0, x0 + cw, y0 + ch)), CARD[:2], Ls["mask"])
                frame.paste(Ls["logo"], (CARD[0] + 4, CARD[1] + 4), Ls["logo"])
                badge = counter_badge(si, n_items)
                frame.paste(badge, (CARD[2] - 250, CARD[1] + 20), badge)
                k = ease((local - 0.1) / 0.5)
                head = Ls["head"]
                if k < 1:
                    head = head.copy()
                    head.putalpha(head.getchannel("A").point(lambda v: int(v * k)))
                frame.paste(head, (0, CARD[3] + 40 + int(50 * (1 - k))), head)
                cur = next((c for c in caps if c[1] <= t < c[2] + 0.15), None)
                if cur:
                    img = cache.get(cur[0]) or cache.setdefault(cur[0], caption_img(cur[0]))
                    frame.paste(img, ((W - img.width) // 2, 1560 - img.height), img)
            proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg bülten videosunu üretemedi")
    return text


def caption(kind, items, now):
    date = f"{now.day} {AYLAR[now.month - 1]} {GUNLER[now.weekday()]}"
    head = {"sabah": f"☀️ Günaydın Eskişehir · {date}",
            "hafta": f"📅 Eskişehir'de bu hafta · {date}"}.get(kind, f"🌙 Eskişehir'de bugün · {date}")
    if anma_gunu(now):
        head = f"🇹🇷 Ulu Önder Atatürk'ü saygıyla anıyoruz · {date}"
    lines = [head, ""] + [f"{i + 1}. {a['title']}" for i, a in enumerate(items)]
    lines += ["", "📲 Haberlerin tamamı profildeki bağlantıda: nabiz26.com", "",
              "#Eskişehir #EskişehirHaber #nabız26 #Odunpazarı #Tepebaşı #EskişehirGündem"
              + (" #10Kasım #Atatürk #Anma" if anma_gunu(now) else "")]
    return "\n".join(lines)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "aksam"
    publish = "--yayinla" in sys.argv
    out = Path(next((x for x in sys.argv[2:] if x.endswith(".mp4")), f"bulten-{kind}.mp4"))
    import build
    now = datetime.now(TR)
    items = pick(build.load_articles(), kind, now)
    if len(items) < 2:
        print("Bülten için yeterli haber yok; atlandı.")
        return
    svc = None
    sp = ROOT / "data" / "servis.json"
    if sp.exists():
        e = json.loads(sp.read_text(encoding="utf-8"))["places"].get("Eskişehir", {})
        svc = {"weather": e.get("weather"),
               "prayer": next((d for d in e.get("prayer") or [] if d["date"] == f"{now:%d-%m-%Y}"), None)}
    render_bulletin(kind, items, out, now, svc)
    cap = caption(kind, items, now)
    print("bülten videosu:", out, len(items), "haber")
    if publish:
        import instagram
        key = f"bulten/{now:%Y%m%d}-{kind}.mp4"
        url = instagram.upload_r2(out, key)
        user = os.environ.get("IG_USER_ID") or instagram.call("GET", "me", fields="user_id")["user_id"]
        if instagram.quota_left(user) <= 0:
            print("Instagram günlük paylaşım hakkı dolu; bülten atlandı.")
            return
        try:
            mid = instagram.publish(user, tries=60, media_type="REELS", video_url=url, caption=cap, share_to_feed="true")
            print("instagram bülten:", mid)
        except RuntimeError as e:
            if not instagram.LIMITED:
                raise
            print("Instagram paylaşım sınırına takıldı; bülten atlandı:", str(e)[:200])
        if os.environ.get("FB_PAGE_ID") and os.environ.get("FB_PAGE_TOKEN"):
            import facebook
            fb = {"caption": cap, "url": "https://nabiz26.com/"}
            print("facebook bülten:", facebook.post_reel(os.environ["FB_PAGE_ID"], fb, url))


if __name__ == "__main__":
    main()
