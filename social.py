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


def cover_image(path, w, h, color):
    """Haber fotoğrafını kırparak doldurur; fotoğraf yoksa kategori renginde nabız desenli zemin çizer."""
    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        scale = max(w / im.width, h / im.height)
        im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1), Image.LANCZOS)
        left, top = (im.width - w) // 2, (im.height - h) // 3
        return im.crop((left, top, left + w, top + h))
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
    f = font("Bricolage.ttf", size, 800)
    if backing:
        # Beyaz/açık fotoğraflarda logo kaybolmasın diye koyu zemin
        w = draw.textlength("nabız", font=f) + size * 1.15
        draw.rounded_rectangle((x - size * .28, y - size * .06, x + w, y + size * 1.02), radius=int(size * .26), fill=NIGHT)
    draw.text((x, y), "nabız", font=f, fill=PAPER)
    tw = draw.textlength("nabız", font=f)
    fs = font("Bricolage.ttf", int(size * .42), 800)
    bw = draw.textlength("26", font=fs) + size * .3
    bx, by = x + tw + size * .14, y + size * .12
    draw.rounded_rectangle((bx, by, bx + bw, by + size * .55), radius=int(size * .14), fill=RED)
    draw.text((bx + size * .15, by + size * .02), "26", font=fs, fill="white")
    return bx + bw


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
    photo = top_shade(cover_image(image_path, W, photo_h, a["color"]), 240)
    im.paste(photo, (0, 0))
    d = ImageDraw.Draw(im)
    # Fotoğrafla zemin arasında kategori renginde ince şerit
    d.rectangle((0, photo_h, W, photo_h + 10), fill=hex_rgb(a["color"]))
    return im, d


def make_post(a, image_path, out, site="nabiz26.com"):
    W, H, PH = 1080, 1350, 700
    im, d = framed(a, image_path, W, H, PH)
    brand(d, 60, 44, 70, backing=True)
    x = pill(d, 64, PH + 50, a["category"].upper(), hex_rgb(a["color"]))
    d.text((x + 20, PH + 60), a["district"] if a["district"] != "Merkez" else "Eskişehir",
           font=font("Inter.ttf", 32, 600), fill=MUTED)
    f, lines, size = fit_headline(d, a["title"], W - 128, 4, [84, 78, 72, 66, 60])
    lh = int(size * 1.06)
    for i, line in enumerate(lines):
        d.text((64, PH + 140 + i * lh), line, font=f, fill="white")
    beat_line(d, H - 118, W)
    d.text((64, H - 82), site, font=font("Inter.ttf", 34, 700), fill=PAPER)
    t = "Haberin tamamı sitede"
    ft = font("Inter.ttf", 30, 500)
    d.text((W - 64 - d.textlength(t, font=ft), H - 80), t, font=ft, fill=MUTED)
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)


def make_story(a, image_path, out, site="nabiz26.com"):
    W, H, PH = 1080, 1920, 900
    im, d = framed(a, image_path, W, H, PH)
    brand(d, 72, 110, 84, backing=True)
    tf = font("Inter.ttf", 30, 800)
    sw = d.textlength("SON DAKİKA", font=tf)
    d.rounded_rectangle((W - 72 - sw - 26, 124, W - 46, 184), radius=30, fill=RED)
    d.text((W - 72 - sw, 136), "SON DAKİKA", font=tf, fill="white")
    x = pill(d, 72, PH + 64, a["category"].upper(), hex_rgb(a["color"]), 36)
    d.text((x + 22, PH + 74), a["district"] if a["district"] != "Merkez" else "Eskişehir",
           font=font("Inter.ttf", 34, 600), fill=MUTED)
    f, lines, size = fit_headline(d, a["title"], W - 144, 5, [92, 86, 80, 74, 68])
    lh = int(size * 1.06)
    y = PH + 170
    for i, line in enumerate(lines):
        d.text((72, y + i * lh), line, font=f, fill="white")
    spot_f = font("Inter.ttf", 38, 500)
    y2 = y + lh * len(lines) + 34
    for i, line in enumerate(wrap(d, a["spot"], spot_f, W - 144, max(1, min(3, (H - 400 - y2) // 54)))):
        d.text((72, y2 + i * 54), line, font=spot_f, fill=(205, 200, 212))
    # Çağrı: bağlantı çıkartması bu alanın üstüne eklenebilir
    beat_line(d, H - 330, W, width=6)
    cta_f = font("Bricolage.ttf", 52, 800)
    cta = f"Haberin tamamı → {site}"
    cw = d.textlength(cta, font=cta_f)
    d.rounded_rectangle(((W - cw) / 2 - 44, H - 262, (W + cw) / 2 + 44, H - 160), radius=51, fill="white")
    d.text(((W - cw) / 2, H - 249), cta, font=cta_f, fill=NIGHT)
    hint = "Profildeki bağlantıya dokun"
    hf = font("Inter.ttf", 32, 500)
    d.text(((W - d.textlength(hint, font=hf)) / 2, H - 126), hint, font=hf, fill=MUTED)
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)


def build_social(articles, data_root, out_dir, limit=40):
    out_dir.mkdir(parents=True, exist_ok=True)
    for a in articles[:limit]:
        img = data_root / a["image"]["file"] if a.get("image") else None
        make_post(a, img, out_dir / f"{a['slug']}-post.jpg")
        make_story(a, img, out_dir / f"{a['slug']}-story.jpg")
        a["social"] = {"post": f"social/{a['slug']}-post.jpg", "story": f"social/{a['slug']}-story.jpg"}
