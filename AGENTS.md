# Nabız 26: Codex için devir notu

Bu depo nabiz26.com (Eskişehir yerel haber sitesi). Haberleri yapay zekâ yazar, site statik üretilir ve her
`main` push'unda Cloudflare tarafından yayınlanır. 05.11.2026'dan itibaren haber masası sensin (önceki: Claude).
Sahibi Türkçe konuşur; yanıtlar Türkçe, kısa ve adım adım.

## Çalışma yeri (05.11.2026)
Sahibi tüm düzenli işlerin bulutta çalışmasını istedi. Yerel Codex zamanlaması kapalıdır.
Haber yazımı GitHub Actions `masa.yml` üzerinden Gemini ile yürür; `GEMINI_API_KEY` depo secret'ıdır.
Ücretli faturalandırma açılmadan ayrı NABIZ26 Google projesi kullanılır. Anahtarı yazdırma.
Yerel bilgisayara bağlı yeni bir düzenli görev kurma. Aşağıdaki oturum adımları elle müdahale içindir.
Yayın `haber.yml` içinde doğrudan Cloudflare'a yapılır (`CLOUDFLARE_API_TOKEN` depo secret'ı).
Bu adım yalnızca `nabiz26` Worker'ının eski derlemelerini iptal eder; başka Worker'lara dokunma.
Gemini yoğunluk hataları sınırlı sayıda yeniden denenir; işlenmeyen kaynaklar görüldü sayılmaz.
Arşiv sorgusu genel konu adı olamaz ve özel ad haberde birebir geçmelidir (`media.subject_queries`).
CLIProxy desteği: `NEWS_API_BASE` ayarlanırsa haberler `NEWS_API_KEY` secret'ı ve
`NEWS_API_MODEL` ile özel sunucuda yazılır; otomatik Gemini geri dönüşü yapılmaz.
Özel ağa GitHub OIDC kimliği ve Tailscale `tag:nabiz26-ci` ile bağlanılır.
Bağlantı `proxy-kontrol.yml` ile yayın yapmadan doğrulanmadan `NEWS_API_BASE` etkinleştirilmez.

## Önce oku
1. `CLAUDE.md`: mimari, kurallar, hesaplar, açık işler (hepsi senin için de geçerli).
2. `OTURUM.md`: haber turu talimatı (asıl görevin).
3. `python newsbot.py --rules`: editör kuralları ve karar şeması.

## Haber turu (sahibi "tur at" dediğinde ya da zamanlanmış çalıştığında)
1. `git pull --rebase origin main` ve `pip install -r requirements.txt`
2. `python newsbot.py --collect kuyruk.json --max 16`
3. Kuyruktaki HER kaynağı ayrı oku, kurallara göre karar ver; kararları şemaya uygun `kararlar.json`'a yaz
   (`image_query` dahil). Bütün kuyruğu tek gerekçeyle geçme; `--save` bunu reddeder.
4. `python newsbot.py --save kuyruk.json kararlar.json`
5. `git add data SON_HABERLER.md && git commit -m "Haber turu" && git push origin main`
   (reddedilirse `git pull --rebase origin main`, bir kez daha dene). Haber doğrudan `main`'e gitmeli; PR açılırsa
   birleştirilene kadar yayına girmez.
6. Sahibine kısa özet: kaç haber yazıldı, kaçı fotoğraf bekliyor, hangileri neden geçildi.

İnternet erişimi gerekir (kaynak siteleri, Google Haberler, GitHub push).

## Kesin kurallar
- Fotoğraf yalnızca resmî kurum sitesinden (gov.tr, bel.tr, edu.tr) ya da `image_query` ile Wikimedia Commons'tan
  birebir eşleşen serbest lisanslı fotoğraf. Gazete/ajans fotoğrafı, yapay zekâ görseli, yazılı kapak yok.
  Haberlere elle fotoğraf ekleme.
- `image_query`: fotoğrafta görünecek kişi/ürün/belirli yerin tam adı (["Eskişehirspor"], ["Ayşe Ünlüce"]);
  belirli konu yoksa boş liste. Fotoğrafı `foto.yml` (GitHub Actions) bulup haberi yayına alır.
- Kaynakta olmayan bilgi yok. Asayişte masumiyet karinesi, tam isim yok. Siyasette tarafsız.
- Yayınlanmış haberi değiştirme. Yalnızca `data/` ve `SON_HABERLER.md` değişir; kod, iş akışı ve ayar dosyalarını
  sahibine sormadan değiştirme. `data/instagram.json`'a dokunma. Token/şifre yazma.

## Kendiliğinden çalışanlar (GitHub Actions; karışma)
`foto.yml` (fotoğraf), `haber.yml` (Instagram + IndexNow), `altin.yml` (09.00 altın haberi), `saglik.yml`,
`servis.yml` (hava/namaz), `bulten.yml`, `masa.yml` (2 saatte bir otomatik haber turu, Gemini). Claude'un bulut haber masası ve yönetici rutinleri kapalı.
