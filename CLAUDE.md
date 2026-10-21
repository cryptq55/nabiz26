# Nabız 26: proje notları (Claude için)

Eskişehir yerel haber sitesi **nabiz26.com**. Haberleri yapay zekâ yazar, site statik üretilir.
Sahibi Türkçe konuşur; yanıtlar Türkçe, kısa ve adım adım olmalı.

## Nasıl çalışıyor
- **Haber masası:** "Nabız 26 haber masası" adlı Claude bulut oturumu, zamanlanmış görevle 2 saatte bir
  uyanır ve `OTURUM.md` talimatını uygular: `newsbot.py --collect` → haberleri yazar → `--save` → `main`'e push.
  Editör kuralları: `python newsbot.py --rules`. Kaynaklar: `sources.yaml`.
- **Yayın:** Cloudflare Workers (GitHub bağlantısı), her push'ta derler. Derleme komutu:
  `pip install -r requirements.txt && SITE_URL=https://nabiz26.com LINK_EXT= python build.py`, ayar `wrangler.jsonc`.
  Alan adları nabiz26.com ve www.nabiz26.com bağlı.
- **GitHub Actions** (`.github/workflows/haber.yml`): yeni haberde IndexNow (Bing/Yandex) bildirimi ve
  Instagram paylaşımı (`instagram.py`; `IG_ACCESS_TOKEN` gizli değişkeni yoksa atlar).
  `ig-token.yml` haftada bir 60 günlük Instagram token'ını yeniler (`GH_SECRETS_TOKEN` gerekir).
- **Instagram görselleri:** `social.py` her haber için 1080x1350 gönderi ve 1080x1920 story üretir,
  `nabiz26.com/social/feed.json` açıklamalarla birlikte. Profil bağlantısı sayfası `nabiz26.com/instagram`.
- **SEO:** canonical, Open Graph, JSON-LD (NewsArticle, BreadcrumbList, WebSite, NewsMediaOrganization),
  `sitemap.xml`, `news-sitemap.xml`, `robots.txt`, RSS. Search Console'a iki site haritası gönderildi.

## Kurallar
- Fotoğraflar yalnızca resmî kurum sitelerinden (gov.tr, bel.tr, edu.tr). Gazete ve ajans fotoğrafı yok.
- Yayınlanmış haber sonradan elle değiştirilmez (düzeltme gerekirse sahibine sor).
- Haberlerde kaynakta olmayan bilgi yok. Asayişte masumiyet karinesi, tam isim yok.
- Gizli bilgiler (token, şifre) sohbete yazılmaz; GitHub Secrets'a eklenir.

## Hesaplar
- E-posta: iletisim@, haber@, reklam@nabiz26.com → Cloudflare Email Routing ile sahibinin Gmail'ine.
- Instagram: @nabiz26haber (işletme hesabı).
- Google Search Console: doğrulandı. Bing ve Yandex Webmaster: eklendi (Yandex DNS doğrulaması var).

## Açık işler (sırayla)
1. E-posta yönlendirme testi: başka bir adresten iletisim@nabiz26.com'a posta gönderilip Gmail'e düştüğü görülecek.
2. Instagram'a logo ve web sitesi bağlantısı (`https://nabiz26.com/instagram`, yalnızca mobil uygulamadan),
   Facebook sayfasına logo. Otomatik paylaşım çalışıyor (21.10.2026): Instagram girişli API, uygulama
   "Nabız 26 Paylaşım" (ID 1055728357426949), secrets `IG_ACCESS_TOKEN` + `GH_SECRETS_TOKEN`, `ig-token.yml` test edildi.
3. Künye: imtiyaz sahibi Intertrade Danışmanlık İç ve Dış Ticaret Ltd. Şti., yer sağlayıcı Cloudflare. Sahibi sorumlu
   müdür ve adres satırlarını istemedi (22.10.2026); Google Haberler başvurusunda sorulursa tekrar konuşulacak.
4. Google Haberler Yayıncı Merkezi başvurusu (künye dolduktan ve birkaç gün haber biriktikten sonra).
5. Valilik (bağlantı reddediyor) ve Anadolu Üniversitesi (haber bağlantısı bulunamıyor) kaynakları düzeltilecek.
