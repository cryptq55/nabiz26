"""Instagram görselleri: her haber için marka tasarımında gönderi (1080x1350) ve story (1080x1920) üretir.

build.py tarafından çağrılır; çıktılar public/social/<slug>-post.jpg ve <slug>-story.jpg olur.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
FONTS = ROOT / "static" / "fonts"
RED = (229, 16, 46)
NIGHT = (12, 11, 16)
PAPER = (244, 241, 236)
MUTED = (175, 170, 182)


def font(name, size, weight):
    f = ImageFont.truetype(str(FONTS / name), size)
    axes = [a["name"] for a in f.get_variation_axes()]
    values = []
    for a in axes:
        if a == b"Weight":
            values.append(weight)
        elif a == b"Optical size":
            values.append(min(96, max(12, size)) if name.startswith("Bricolage") else min(32, max(14, size)))
        else:
            values.append(100)  # genişlik
    f.set_variation_by_axes(values)
    return f


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap(draw, text, fnt, width, max_lines):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=fnt) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=fnt) > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
        lines[-1] += "…"
    return lines


def fit_headline(draw, text, width, max_lines, sizes):
    """Başlığı sığdığı en büyük punto ile satırlara böler."""
    for size in sizes:
        f = font("Bricolage.ttf", size, 800)
        lines = wrap(draw, text, f, width, max_lines + 1)
        if len(lines) <= max_lines:
            return f, lines, size
    f = font("Bricolage.ttf", sizes[-1], 800)
    return f, wrap(draw, text, f, width, max_lines), sizes[-1]


def _cover(im, w, h):
    scale = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 3
    return im.crop((left, top, left + w, top + h))


def cover_image(path, w, h, color, whole=False):
    """Haber fotoğrafını alana yerleştirir; fotoğraf yoksa kategori renginde nabız desenli zemin çizer.

    Oranı alana yakın fotoğraflar kırpılarak doldurulur. Uzak olanlar (afiş, bilgi grafiği) kesilmesin
    diye bütün olarak, kendi bulanık ve koyulaştırılmış kopyasının üstüne ortalanır.
    """
    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        ratio = (im.width / im.height) / (w / h)
        if 0.8 <= ratio <= 1.3 and not whole:
            return _cover(im, w, h)
        bg = _cover(im, w, h).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", (w, h), NIGHT), 0.45)
        scale = min(w / im.width, h / im.height)
        fg = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
        return bg
    c = hex_rgb(color)
    bg = Image.new("RGB", (w, h), c)
    d = ImageDraw.Draw(bg)
    dark = tuple(int(v * .45) for v in c)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(c[i] * (1 - t) + dark[i] * t) for i in range(3)))
    beat = [(0, .55), (.34, .55), (.4, .35), (.48, .78), (.56, .2), (.63, .62), (.67, .5), (1, .5)]
    for k, alpha in ((0, 230), (1, 50), (2, 50)):
        off = [0, -.28, .28][k]
        pts = [(x * w, (y + off) * h) for x, y in beat]
        layer = Image.new("RGBA", (w, h))
        ImageDraw.Draw(layer).line(pts, fill=(255, 255, 255, alpha), width=12 if k == 0 else 6, joint="curve")
        bg.paste(layer, (0, 0), layer)
    return bg


def shade(im, start, strength=245):
    """Fotoğrafın altını yazı okunsun diye koyulaştırır."""
    w, h = im.size
    grad = Image.new("L", (1, h))
    for y in range(h):
        t = max(0.0, (y / h - start) / (1 - start))
        grad.putpixel((0, y), int(min(1, t * 1.25) ** 1.2 * strength))
    grad = grad.resize((w, h))
    black = Image.new("RGB", (w, h), NIGHT)
    return Image.composite(black, im, grad)


def brand(draw, x, y, size, backing=False):
    """Logo: "nabız" ve yanında kırmızı "26" rozeti. Rozet küçük harf boyunda ve yazının satır çizgisinde durur.

    (x, y) logonun sol üst köşesidir (küçük harflerin "b" sapı dahil üst sınırı).
    """
    f = font("Bricolage.ttf", size, 800)
    asc = -f.getbbox("b", anchor="ls")[1]   # "b" sapının yüksekliği
    xh = -f.getbbox("n", anchor="ls")[1]    # küçük harf yüksekliği
    base = y + asc
    tw = draw.textlength("nabız", font=f)
    fs = font("Bricolage.ttf", int(xh * .78), 800)
    bh = xh
    bw = draw.textlength("26", font=fs) + bh * .62
    bx = x + tw + size * .1
    if backing:
        # Açık renkli fotoğraflarda logo kaybolmasın diye koyu zemin
        pad = size * .26
        draw.rounded_rectangle((x - pad, y - pad, bx + bw + pad, base + pad * 1.1), radius=int(size * .24), fill=NIGHT)
    draw.text((x, base), "nabız", font=f, fill=PAPER, anchor="ls")
    draw.rounded_rectangle((bx, base - bh, bx + bw, base), radius=int(bh * .26), fill=RED)
    # Rakamları gözle ortala: yazı tipi kutusuna değil, rakamların kendi sınırlarına göre
    l, t, r, _ = fs.getbbox("26", anchor="ls")
    draw.text((bx + (bw - (r - l)) / 2 - l, base - (bh + t) / 2), "26", font=fs, fill="white", anchor="ls")
    return bx + bw, base


def pill(draw, x, y, text, color, size=34):
    f = font("Inter.ttf", size, 800)
    tw = draw.textlength(text, font=f)
    draw.rounded_rectangle((x, y, x + tw + size * 1.1, y + size * 1.75), radius=int(size * .9), fill=color)
    draw.text((x + size * .55, y + size * .3), text, font=f, fill="white")
    return x + tw + size * 1.1


def beat_line(draw, y, w, color=RED, width=5):
    draw.line([(0, y), (w * .38, y), (w * .42, y - 34), (w * .47, y + 40), (w * .52, y - 52),
               (w * .56, y + 22), (w * .58, y), (w, y)], fill=color, width=width, joint="curve")


def top_shade(im, height, strength=170):
    """Logonun açık renkli fotoğraflarda da görünmesi için üst kenarı koyulaştırır."""
    w, h = im.size
    grad = Image.new("L", (1, h))
    for y in range(h):
        grad.putpixel((0, y), int(max(0.0, 1 - y / height) ** 1.6 * strength) if y < height else 0)
    return Image.composite(Image.new("RGB", (w, h), NIGHT), im, grad.resize((w, h)))


def framed(a, image_path, W, H, photo_h):
    """Üstte fotoğraf, altta koyu zemin: fotoğrafta yazı olsa da başlık okunur kalır."""
    im = Image.new("RGB", (W, H), NIGHT)
    # Kendi ürettiğimiz kapaklar (Togg, altın, konu haberleri) üstünde yazı taşır: kırpılmadan bütün sığdırılır
    card = (a.get("image") or {}).get("credit", "").startswith("Nabız 26")
    photo = cover_image(image_path, W, photo_h, a["color"], whole=card)
    if not card:
        photo = top_shade(photo, 240)
    im.paste(photo, (0, 0))
    d = ImageDraw.Draw(im)
    im = a.get("image") or {}
    if im.get("archive"):
        ai_tag(d, W - 24, photo_h - 22, text="Arşiv fotoğrafı")
    elif im.get("ai") or im.get("representative"):
        ai_tag(d, W - 24, photo_h - 22, text="Temsilî fotoğraf" if im.get("representative") else None)
    # Fotoğrafla zemin arasında kategori renginde ince şerit
    d.rectangle((0, photo_h, W, photo_h + 10), fill=hex_rgb(a["color"]))
    return im, d


def ai_tag(d, right, bottom, size=24, text=None):
    """Temsilî görsellerin (Commons fotoğrafı ya da yapay zekâ) köşesine konan açıklama etiketi."""
    f = font("Inter.ttf", size, 700)
    t = text or "Temsilî görsel · yapay zekâ"
    w = d.textlength(t, font=f)
    d.rounded_rectangle((right - w - 28, bottom - size - 18, right, bottom), radius=12, fill=(12, 11, 16))
    d.text((right - 14, bottom - 9), t, font=f, fill=(230, 226, 235), anchor="rs")


def make_post(a, image_path, out, site="nabiz26.com"):
    W, H, PH = 1080, 1350, 700
    im, d = framed(a, image_path, W, H, PH)
    M = 64
    _, base = brand(d, M, PH + 52, 62)
    cat = a["category"].upper()
    pw = d.textlength(cat, font=font("Inter.ttf", 28, 800)) + 28 * 1.1
    pill(d, W - M - pw, base - 46, cat, hex_rgb(a["color"]), 28)
    place = a["district"] if a["district"] != "Merkez" else "Eskişehir"
    d.text((W - M - pw - 18, base - 22), place, font=font("Inter.ttf", 28, 600), fill=MUTED, anchor="rm")
    f, lines, size = fit_headline(d, a["title"], W - 2 * M, 3, [80, 74, 68, 62, 56])
    lh = int(size * 1.08)
    if (a.get("image") or {}).get("credit") == "Nabız 26":
        lines = []  # başlık zaten kapağın üstünde yazıyor; iki kez görünmesin
        sf = font("Inter.ttf", 40, 500)
        for i, line in enumerate(wrap(d, a["spot"], sf, W - 2 * M, 4)):
            d.text((M, base + 50 + i * 56), line, font=sf, fill=(205, 200, 212))
    for i, line in enumerate(lines):
        d.text((M, base + 50 + i * lh), line, font=f, fill="white")
    beat_line(d, H - 118, W)
    d.text((64, H - 82), site, font=font("Inter.ttf", 34, 700), fill=PAPER)
    t = "Haberin tamamı sitede"
    ft = font("Inter.ttf", 30, 500)
    d.text((W - 64 - d.textlength(t, font=ft), H - 80), t, font=ft, fill=MUTED)
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)


def make_story(a, image_path, out, site="nabiz26.com"):
    # Instagram story'de üstteki ~180 px ilerleme çubuğu ve hesap adının altında kalır (yalnızca
    # fotoğraf görünür); logo, başlık ve çağrı fotoğrafın altındaki koyu alana yerleşir.
    W, H, PH, M = 1080, 1920, 860, 72
    im, d = framed(a, image_path, W, H, PH)
    y = PH + 64
    _, base = brand(d, M, y, 74)
    x = W - M
    cat = a["category"].upper()
    cf = font("Inter.ttf", 30, 800)
    pw = d.textlength(cat, font=cf) + 30 * 1.1
    pill(d, x - pw, base - 50, cat, hex_rgb(a["color"]), 30)
    place = a["district"] if a["district"] != "Merkez" else "Eskişehir"
    pf = font("Inter.ttf", 30, 600)
    d.text((x - pw - 20, base - 24), place, font=pf, fill=MUTED, anchor="rm")

    cta_top = H - 330
    f, lines, size = fit_headline(d, a["title"], W - 2 * M, 4, [96, 90, 84, 78, 72, 66])
    lh = int(size * 1.08)
    y = base + 70
    for i, line in enumerate(lines):
        d.text((M, y + i * lh), line, font=f, fill="white")
    spot_f = font("Inter.ttf", 38, 500)
    y2 = y + lh * len(lines) + 30
    room = (cta_top - 120 - y2) // 54
    if room >= 1:
        for i, line in enumerate(wrap(d, a["spot"], spot_f, W - 2 * M, min(3, room))):
            d.text((M, y2 + i * 54), line, font=spot_f, fill=(205, 200, 212))

    beat_line(d, cta_top - 60, W, width=6)
    cta_f = font("Bricolage.ttf", 50, 800)
    cta = f"Haberin tamamı → {site}"
    cw = d.textlength(cta, font=cta_f)
    d.rounded_rectangle(((W - cw) / 2 - 44, cta_top, (W + cw) / 2 + 44, cta_top + 96), radius=48, fill="white")
    d.text((W / 2, cta_top + 48), cta, font=cta_f, fill=NIGHT, anchor="mm")
    hint = "Bağlantı profilde: @nabiz26haber"
    hf = font("Inter.ttf", 32, 500)
    d.text((W / 2, cta_top + 140), hint, font=hf, fill=MUTED, anchor="mm")
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)


def build_social(articles, data_root, out_dir, limit=40):
    out_dir.mkdir(parents=True, exist_ok=True)
    for a in articles[:limit]:
        img = data_root / a["image"]["file"] if a.get("image") else None
        make_post(a, img, out_dir / f"{a['slug']}-post.jpg")
        make_story(a, img, out_dir / f"{a['slug']}-story.jpg")
        a["social"] = {"post": f"social/{a['slug']}-post.jpg", "story": f"social/{a['slug']}-story.jpg"}


def topic_card(out, title, label, color="#e11d48", rows=None, note=None):
    """Fotoğrafı olmayan konu haberleri (Togg, altın) için kendi tasarımımız olan 1200x800 kapak görseli.

    rows verilirse (ör. altın fiyatları) başlık yerine tablo çizilir: [(ad, alış, satış, değişim%), ...]
    """
    W, H = 1200, 800
    c = hex_rgb(color)
    im = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(im)
    # Kategori renginde hafif ışıma ve nabız deseni
    glow = Image.new("RGB", (W, H), c)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((W * .45, -H * .6, W * 1.5, H * .7), fill=120)
    im.paste(glow, (0, 0), mask.filter(ImageFilter.GaussianBlur(160)))
    d = ImageDraw.Draw(im)
    big = font("Bricolage.ttf", 300, 800)
    lw = d.textlength(label, font=big)
    layer = Image.new("RGBA", (W, H))
    ImageDraw.Draw(layer).text((W - lw - 30, -40), label, font=big, fill=(255, 255, 255, 26))
    im.paste(layer, (0, 0), layer)
    brand(d, 56, 44, 64, backing=False)
    pill(d, 60, 150, label.upper(), c, 30)
    if rows:
        hf = font("Inter.ttf", 26, 700)
        nf = font("Inter.ttf", 34, 600)
        vf = font("Bricolage.ttf", 40, 800)
        cols = [60, 520, 760, 1000]
        for x, t in zip(cols, ["", "ALIŞ", "SATIŞ", "DEĞİŞİM"]):
            d.text((x, 236), t, font=hf, fill=MUTED)
        y = 282
        for name, buy, sell, chg in rows:
            d.line([(60, y - 12), (W - 60, y - 12)], fill=(42, 39, 49), width=2)
            d.text((cols[0], y), name, font=nf, fill=PAPER)
            d.text((cols[1], y - 4), buy, font=vf, fill="white")
            d.text((cols[2], y - 4), sell, font=vf, fill="white")
            up = chg.startswith("+")
            d.text((cols[3], y), chg, font=nf, fill=(34, 197, 94) if up else (RED if chg.startswith("-") else MUTED))
            y += 62
    else:
        f, lines, size = fit_headline(d, title, W - 120, 4, [76, 70, 64, 58, 52])
        lh = int(size * 1.08)
        y = 250 + (4 - len(lines)) * lh // 2
        for i, line in enumerate(lines):
            d.text((60, y + i * lh), line, font=f, fill="white")
    beat_line(d, H - 92, W)
    d.text((60, H - 62), "nabiz26.com", font=font("Inter.ttf", 30, 700), fill=PAPER)
    if note:
        nf2 = font("Inter.ttf", 24, 500)
        d.text((W - 60 - d.textlength(note, font=nf2), H - 58), note, font=nf2, fill=MUTED)
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)
