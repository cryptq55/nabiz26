# Nabız 26: proje notları (Claude için)

Eskişehir yerel haber sitesi **nabiz26.com**. Haberleri yapay zekâ yazar, site statik üretilir.
Sahibi Türkçe konuşur; yanıtlar Türkçe, kısa ve adım adım olmalı.

## Nasıl çalışıyor
- **Haber masası:** "Nabız 26 haber masası" adlı Claude bulut oturumu, zamanlanmış görevle 2 saatte bir
  uyanır ve `OTURUM.md` talimatını uygular: `newsbot.py --collect` → haberleri yazar → `--save` → `main`'e push.
  Editör kuralları: `python newsbot.py --rules`. Kaynaklar: `sources.yaml`.
- **Yayın:** Cloudflare Workers (GitHub bağlantısı), her push'ta derler. Derleme komutu:
  `pip install -r requirements.txt && SITE_URL=https://nabiz26.com LINK_EXT= python build.py`, ayar `wrangler.jsonc`.
  Alan adları nabiz26.com ve www.nabiz26.com bağlı; `worker.js` www ve http isteklerini 301 ile https://nabiz26.com'a
  yönlendirir (Search Console tekrar eden URL uyarısı, 24.10.2026).
- **GitHub Actions** (`.github/workflows/haber.yml`): yeni haberde IndexNow (Bing/Yandex) bildirimi ve
  Instagram paylaşımı (`instagram.py`; `IG_ACCESS_TOKEN` gizli değişkeni yoksa atlar).
  `ig-token.yml` haftada bir 60 günlük Instagram token'ını yeniler (`GH_SECRETS_TOKEN` gerekir).
- **Sosyal medya dağıtımı:** editör her habere 1-5 `importance` ve `reel` (önemli ve izlenecek mi) verir. Instagram:
  her haber story, önem 3+ gönderi, `reel: true` olanlar sesli Reels (`reels.py`; video R2 `nabiz26-media` →
  media.nabiz26.com; ses ücretsiz edge-tts, `EDGE_TTS_VOICE`=tr-TR-EmelNeural repo değişkeni). Kota sırası Reels >
  gönderi > story. Elle Reels: "Bildir ve paylaş" iş akışı `reel` girdisi. Facebook (`facebook.py`): önem 3+ bağlantılı
  gönderi + Reels; FB_PAGE_ID/FB_PAGE_TOKEN henüz yok (atlanıyor). Resmî kaynağın haber sayfasında kendi mp4 videosu
  varsa (`newsbot.find_video`, şu an Valilik) haber kaydına `video` eklenir ve o haber önce, videolu Reels olur
  (`reels.render_video`). YouTube gömmeleri kullanılmaz. Story yalnızca gerçek fotoğraflı haberlerden.
  Günde en fazla 22 paylaşım (`instagram.DAILY_CAP`). Günlük bülten: `bulten.py` + `bulten.yml` (08:00 ve 20:00).
- **Instagram görselleri:** `social.py` her haber için 1080x1350 gönderi ve 1080x1920 story üretir,
  `nabiz26.com/social/feed.json` açıklamalarla birlikte. Profil bağlantısı sayfası `nabiz26.com/instagram`.
- **Sabah altın haberi:** `gold.py`, Harem Altın canlı fiyatlarından (socket.io) haber + fiyat tablosu görseli yazar;
  `.github/workflows/altin.yml` her gün 06:00 UTC (09:00 TSİ) çalıştırır, sonra "Bildir ve paylaş"ı başlatır.
- **Konu kaynakları (Eskişehir şartı yok):** `sources.yaml`'da `topic` alanıyla: `togg`, `siyaset` (Cumhurbaşkanı, CHP),
  `bakanlik`. Google Haberler kaynaklarına `image_query` ile Commons arşiv fotoğrafı konur; İletişim Başkanlığı, Aile,
  MEB ve Enerji bakanlıkları resmî fotoğraflı. Kategoriler "Siyaset" ve "Türkiye", ilçe yerine "Türkiye".
  Her turda önce yerel kaynaklar, sonra konu kaynakları kuyruğa girer.
- **SEO:** canonical, Open Graph, JSON-LD (NewsArticle, BreadcrumbList, WebSite, NewsMediaOrganization),
  `sitemap.xml`, `news-sitemap.xml`, `robots.txt`, RSS. Search Console'a iki site haritası gönderildi.
  Her haber için 1200 px 16:9/4:3/1:1 görseller (`public/images/g/`, Google Discover/Haberler), tarihler +03:00,
  boş kategori/ilçe sayfaları noindex, Google Fonts sayfa çizimini bekletmeden yüklenir.

## Kendi kendine çalışma (sahibine muhtaç olmadan)
- **Yönetici rutini SİLİNDİ, müdür rutini KAPALI (05.11.2026, token tasarrufu; sahibi istedi).** Eski yönetici rutini
  ("Nabız 26 yönetici", 09:30 ve 21:30 TSİ): siteyi, haber akışını,
  Instagram kayıtlarını ve kaynakları denetler, düzeltir, her çalışmada bir büyüme iyileştirmesi yapar ve `YONETIM.md`'ye
  yazar. Sahibine ait kararlar `SAHİBİNE:` satırlarıyla orada. Instagram fiili sınırı ~25/24 saat (`DAILY_CAP`=16 + 2 bülten).
- **Otomatik masa** (`masa.yml`, 05.11.2026): Claude masası kapalı; 08-24 TSİ 2 saatte bir `newsbot.py --auto` haberleri
  ücretsiz Gemini (`GEMINI_API_KEY` secret) ile yazar, sonra foto.yml ve haber.yml'yi başlatır. Codex için `AGENTS.md`.
- **Sağlık kontrolü** (`saglik.yml`, saatte bir): gündüz son haber 3 saatten eskiyse yedek masa (`newsbot.py --auto`)
  çalışır: önce Anthropic API, kredi yoksa ücretsiz Gemini (`GEMINI_API_KEY`). Site açılmazsa ya da 8 saat haber
  yoksa `saglik` etiketli GitHub kaydı açılır (sahibine e-posta), düzelince kapanır.
- **Aktarıcı** (`relay/`, Cloudflare Worker `nabiz26-relay`): yurt dışı/bot engelli kurum siteleri (Beylikova) Avrupa'ya
  sabitli Durable Object üzerinden okunur (`newsbot.RELAY_HOSTS`). Büyükşehir yalnızca Türkiye IP'sine açık; aktarıcı
  da aşamıyor, onun haberleri Google Haberler kayıtlarından (`topic: yerel`) Commons arşiv fotoğrafıyla gelir.
  Dikkat: `relay/` içinde `wrangler deploy --config ./wrangler.toml` kullanın; aksi halde kök ayarla site yayınlanır.
- **Kaynak kontrolü** (`kaynak-kontrol.yml`, elle): kaynakların yurt dışı sunucudan erişimini raporlar.
- **Kent rehberi** (`servis.py` + `servis.yml`, 3 saatte bir): /hava-durumu ve /namaz-vakitleri (+14 ilçe) sayfaları.
- Büyüme fikirleri sırada: nöbetçi eczane (Eczacı Odası sitesi bot engelli), planlı elektrik (OEDAŞ formla sorgu),
  su kesintisi (ESKİ), Eskişehirspor fikstür.

## Kurallar
- Fotoğraflar yalnızca resmî kurum sitelerinden (gov.tr, bel.tr, edu.tr). Gazete ve ajans fotoğrafı yok.
  Resmî fotoğraf yoksa editörün `image_query`'sine (kişi/ürün/yer tam adı) birebir uyan Wikimedia Commons
  fotoğrafı (`media.py`: dosya adında adın bütün kelimeleri, ≥1000 px, CC BY/BY-SA/CC0/kamu malı, logo/harita/afiş yok);
  sitede ve kartlarda "Arşiv fotoğrafı" etiketi, fotoğrafçı ve lisans. Bulunamazsa haber yayınlanmaz. Bulut oturumlarının IP'si
  Wikimedia'da engelli (429): masa haberi `photo_pending` ile yayın dışı kaydeder, `foto.yml` (20 dk'da bir, Actions)
  `newsbot.py --fill-photos` ile fotoğrafı bulup yayına alır ve "Bildir ve paylaş"ı başlatır; 3 denemede bulunamazsa
  `photo_failed`. Elle deneme: "Fotoğraf bul" iş akışı `dene` girdisi. `--save` bütün kuyruğu tek gerekçeyle geçen
  kararları reddeder (masa 25-31.10 arası böyle yapıp akışı durdurmuştu). Sahibi yapay zekâ
  görseli ve yazılı kapak istemedi (23.10.2026). Birebir fotoğrafı olmayan eski haberler gizlendi (`image: null`,
  eski görsel `image_hidden` alanında). Altın haberi tablo kapağıyla kalır. Tek kişi aranırken görüşme fotoğrafı,
  grafik/tablo, karanlık/bulanık fotoğraf elenir; aynı fotoğraf 10 günde en fazla 2 haberde (`data/media_used.json`);
  yalnızca şehir/ilçe adıyla aranmaz (24.10.2026, sahibi "saçma görsel kullanma" dedi).
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
4. Google Haberler: başvuru yok artık (Google 2024-25'te elle eklemeyi kaldırdı); politikalara uyan siteler otomatik
   değerlendiriliyor. Birkaç haftada bir news.google.com'da "nabiz26" aranıp çıkıp çıkmadığına bakılacak.
5. Kaynaklar (22.10.2026 düzeltildi): Valilik (/haberler, link_text ile), Büyükşehir (icerik-detay), Anadolu Ünv.
   (anahaber.anadolu.edu.tr) metin ve fotoğrafla geliyor. Valilik daha önce bulutta "bağlantı reddediyor" demişti;
   Türkiye IP'sinden açılıyor, bulut oturumunda yine reddederse sebep yurt dışı IP engelidir. ESOGÜ'de haberin kendi
   fotoğrafı bulunamıyor (sayfadaki /files/haber/ görseli her haberde aynı), o yüzden ESOGÜ haberleri fotoğrafsız kalıp atlanıyor.
