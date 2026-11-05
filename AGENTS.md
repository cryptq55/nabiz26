# Nabız 26: Codex için devir notu

Bu depo nabiz26.com (Eskişehir yerel haber sitesi). Haberleri yapay zekâ yazar, site statik üretilir ve her
`main` push'unda Cloudflare tarafından yayınlanır. 05.11.2026'dan itibaren haber masası sensin (önceki: Claude).
Sahibi Türkçe konuşur; yanıtlar Türkçe, kısa ve adım adım.

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
