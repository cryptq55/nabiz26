"""Instagram Reels (1080x1920 MP4) üretir: haber fotoğrafı yavaşça kayar, başlık ve altyazılar akar, sonda kapanış kartı.

Seslendirme isteğe bağlıdır: ELEVENLABS_API_KEY tanımlıysa haber metni ElevenLabs ile okunur ve altyazılar
sesin kelime zamanlarına oturtulur; tanımlı değilse video sessiz üretilir, altyazılar okuma hızına göre akar.

Kullanım (deneme):  python reels.py <haber-slug-parçası> [çıktı.mp4]
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from social import MUTED, NIGHT, PAPER, RED, _cover, beat_line, brand, font, hex_rgb, pill, wrap

W, H, FPS = 1080, 1920, 30
M = 64                       # kenar boşluğu
CARD = (40, 250, 1040, 1000)  # fotoğraf kartı (Instagram'ın üst çubuğunun altında)
END = 2.6                    # kapanış kartı süresi (sn)
CHARS_PER_SEC = 17           # sessiz videoda altyazı hızı
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")
VOICE_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def script(a, voiced=True):
    """Okunacak metin: başlık ekranda yazdığı için spot ve (sesliyse) sığdığı kadar ilk paragraf; cümle bölünmez."""
    text = a["spot"]
    if voiced:
        for sent in re.split(r"(?<=[.!?])\s+", a["body"].split("\n\n")[0]):
            if sent and sent[:40] not in text and len(text) + len(sent) + 1 <= 380:
                text += " " + sent
    return text


def synthesize(text, out_mp3):
    """ElevenLabs ile seslendirir; mp3'ü yazar ve karakter zamanlarını döndürür. Anahtar yoksa None."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key or not VOICE_ID:
        return None
    body = json.dumps({"text": text, "model_id": VOICE_MODEL, "language_code": "tr",
                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2}}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    import base64
    Path(out_mp3).write_bytes(base64.b64decode(res["audio_base64"]))
    al = res["alignment"]
    return list(zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]))


def phrases(text, alignment=None, total=None):
    """Altyazı parçaları: 4-6 kelimelik öbekler ve her birinin başlangıç/bitiş saniyesi."""
    words = list(re.finditer(r"\S+", text))
    chunks, cur = [], []
    for m in words:
        cur.append(m)
        if len(cur) >= 6 or (len(cur) >= 3 and m.group()[-1] in ".,;:!?"):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        a, b = c[0].start(), c[-1].end()
        if alignment:
            t0, t1 = alignment[min(a, len(alignment) - 1)][1], alignment[min(b, len(alignment)) - 1][2]
        else:
            t0, t1 = a / CHARS_PER_SEC, b / CHARS_PER_SEC
        out.append((" ".join(m.group() for m in c), t0, t1))
    return out


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m


def layers(a, image_path):
    """Kare kare değişmeyen katmanlar önceden hazırlanır; her karede yalnızca kırpma ve yapıştırma yapılır."""
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    color = hex_rgb(a.get("color", "#e11d48"))
    if image_path and Path(image_path).exists():
        src = Image.open(image_path).convert("RGB")
        bg = _cover(src, W, H).filter(ImageFilter.GaussianBlur(50))
        bg = Image.blend(bg, Image.new("RGB", (W, H), NIGHT), 0.62)
        big = _cover(src, int(cw * 1.16), int(ch * 1.16))  # kaydırma payı
    else:
        bg = Image.new("RGB", (W, H), NIGHT)
        big = Image.new("RGB", (int(cw * 1.16), int(ch * 1.16)), color)
    # Başlık bloğu (kategori + başlık), saydam katman
    head = Image.new("RGBA", (W, 640), (0, 0, 0, 0))
    d = ImageDraw.Draw(head)
    x = pill(d, M, 0, a["category"].upper(), color, 32)
    place = a["district"] if a["district"] != "Merkez" else "Eskişehir"
    d.text((x + 20, 10), place, font=font("Inter.ttf", 32, 600), fill=MUTED)
    size = 76
    for size in (76, 70, 64, 58):
        f = font("Bricolage.ttf", size, 800)
        lines = wrap(d, a["title"], f, W - 2 * M, 4)
        if len(lines) <= 3 or size == 58:
            break
    lh = int(size * 1.08)
    for i, line in enumerate(lines):
        d.text((M, 86 + i * lh), line, font=f, fill="white")
    head_h = 86 + lh * len(lines) + 10
    # Logo (fotoğraf kartının sol üst köşesinde, koyu zemin üstünde)
    logo = Image.new("RGBA", (420, 130), (0, 0, 0, 0))
    brand(ImageDraw.Draw(logo), 26, 22, 56, backing=True)
    return {"bg": bg, "big": big, "mask": rounded_mask(cw, ch, 34), "head": head, "head_h": head_h, "logo": logo}


def caption_img(text):
    f = font("Inter.ttf", 46, 700)
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines = wrap(d, text, f, W - 2 * M - 60, 2)
    tw = max(d.textlength(l, font=f) for l in lines)
    im = Image.new("RGBA", (int(tw) + 60, 34 + 58 * len(lines)), (0, 0, 0, 0))
    di = ImageDraw.Draw(im)
    di.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 22, fill=(255, 255, 255, 240))
    for i, l in enumerate(lines):
        di.text((30, 14 + i * 58), l, font=f, fill=NIGHT)
    return im


def end_card(site="nabiz26.com"):
    im = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(im)
    right, _ = brand(ImageDraw.Draw(Image.new("RGB", (W, 300))), 0, 0, 150)  # genişliği ölç
    brand(d, (W - right) / 2, 640, 150)
    beat_line(d, 960, W, width=8)
    cf = font("Bricolage.ttf", 58, 800)
    t = f"Haberin tamamı → {site}"
    cw = d.textlength(t, font=cf)
    d.rounded_rectangle(((W - cw) / 2 - 46, 1120, (W + cw) / 2 + 46, 1230), radius=55, fill="white")
    d.text((W / 2, 1175), t, font=cf, fill=NIGHT, anchor="mm")
    d.text((W / 2, 1300), "Bağlantı profilde: @nabiz26haber", font=font("Inter.ttf", 36, 500), fill=MUTED, anchor="mm")
    return im


def render(a, image_path, out, audio=None, alignment=None):
    text = script(a, voiced=bool(alignment))
    caps = phrases(text, alignment)
    speech = caps[-1][2] if caps else 8
    body_t = max(9.0, speech + 0.8)
    total = body_t + END
    L = layers(a, image_path)
    cap_cache = {}
    endc = end_card()
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    bw, bh = L["big"].size

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    cmd += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-t", f"{total:.2f}",
            "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(int(total * FPS)):
        t = n / FPS
        frame = L["bg"].copy()
        # Fotoğraf: zamanla soldan sağa ve hafif aşağı kayar
        p = t / body_t
        x0, y0 = int((bw - cw) * p), int((bh - ch) * (0.3 + 0.4 * p))
        frame.paste(L["big"].crop((x0, y0, x0 + cw, y0 + ch)), CARD[:2], L["mask"])
        frame.paste(L["logo"], (CARD[0] + 4, CARD[1] + 4), L["logo"])
        # Başlık: aşağıdan kayarak gelir
        k = ease((t - 0.2) / 0.6)
        if k > 0:
            head = L["head"]
            if k < 1:
                head = head.copy()
                head.putalpha(head.getchannel("A").point(lambda v: int(v * k)))
            frame.paste(head, (0, CARD[3] + 40 + int(60 * (1 - k))), head)
        # Altyazı: o an okunan öbek
        cur = next((c for c in caps if c[1] <= t < c[2] + 0.15), None)
        if cur:
            img = cap_cache.get(cur[0]) or cap_cache.setdefault(cur[0], caption_img(cur[0]))
            frame.paste(img, ((W - img.width) // 2, 1560 - img.height), img)
        # Kapanış kartı: yumuşak geçiş
        if t > body_t - 0.4:
            frame = Image.blend(frame, endc, ease((t - body_t + 0.4) / 0.5))
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg reels videosunu üretemedi")
    return total


def make_reel(a, image_path, out):
    """Seslendirmeyi (varsa) yapıp videoyu üretir; sesli olup olmadığını döndürür."""
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "ses.mp3"
        alignment = None
        try:
            alignment = synthesize(script(a, voiced=True), mp3)
        except Exception as e:  # ses gelmezse video sessiz üretilir
            print("[uyarı] seslendirme yapılamadı:", str(e)[:200])
        render(a, image_path, out, audio=mp3 if alignment else None, alignment=alignment)
        return bool(alignment)


if __name__ == "__main__":
    import build
    arts = build.load_articles()
    a = next(x for x in arts if sys.argv[1] in x["slug"])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else f"{a['slug'][:40]}.mp4")
    img = build.DATA_DIR.parent / a["image"]["file"] if a.get("image") else None
    voiced = make_reel(a, img, out)
    print(out, "sesli" if voiced else "sessiz")
