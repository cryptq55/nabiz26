# Nabız 26 yönetim notları

## 24.10.2026 21:45 TSİ
**Denetim:** /, /hava-durumu, /namaz-vakitleri ve son 3 haber 200. Derleme geçti (131 haber). Son haber 20:32 TSİ. Son 24 saatte 29 haber (önceki turda 87; akış belirgin yavaşladı): Spor 7, Gündem 6, Eğitim 5, Ulaşım 3, Ekonomi/Belediye/Türkiye 2'şer, Asayiş/Siyaset 1'er. İlçe: Merkez 18, Türkiye 5, Tepebaşı 4, Odunpazarı 2. Tekrar başlık 0, fotoğrafsız 0. Önem: 3→16, 2→11, 1→2 (yine 4+ yok); `reel: true` 0. Instagram: log 16 (DAILY_CAP dolu), reel_log 7, toplam 12 Reels kaydı.
**Kaynaklar (bulut IP'si):** Büyükşehir (ReadTimeout), Anadolu Ünv., Gençlik ve Spor İl Müdürlüğü açılmadı (yurt dışı engeli); Günyüzü bağlantı yok; MSB bir haber bağlantısı 404. 367 yeni aday.
**İyileştirme:** `newsbot.py` editör kurallarına önem kalibrasyonu: gerçekten 4-5 olan haberi 3'e düşürmemesi, günde en az 2-3 haberin 4+ (Reels adayı) olması.
**Sıradaki 3 fikir:** (1) 4+ önem sonrası Reels sayısını izlemek, yine 0 ise koddan Spor "maç sonucu" kuralı; (2) boş ilçeler için kaynak/arama; (3) nöbetçi eczane sayfası.
SAHİBİNE: yok.

## 24.10.2026 09:45 TSİ
**Denetim:** /, /hava-durumu, /namaz-vakitleri ve son 2 haber 200. Derleme geçti (114 haber). Son haber 04:32 TSİ (gece, normal). Son 24 saatte 87 haber (Eğitim 15, Gündem 14, Siyaset 11, Spor 9, Ekonomi 8, Asayiş 6, Türkiye 6, Kültür-Sanat 6, Belediye 5, Ulaşım 5; Sağlık, Tarım, Hava 1'er). İlçe: Merkez 39, Türkiye 28, Tepebaşı 13, Odunpazarı 5, Sivrihisar 1, Sarıcakaya 1; diğer ilçeler boş. Tekrar başlık 0. 44 haberin kapağı gizli (`image: null`, birebir fotoğraf yok kuralı). `reel: true` 0, önem dağılımı 1:5, 2:50, 3:32 (editör hiç 4+ vermemiş). Instagram: son 24 saatte 11 paylaşım (cap 16 altında), 5 Reels.
**Kaynaklar (bulut IP'si):** Valilik, Büyükşehir, Anadolu Ünv., Alpu açılmadı (yurt dışı engeli, bilinen); Günyüzü bağlantı yok. Google Haberler kaynakları 352 aday verdi.
**Not:** ortamda sistem pip/Pillow bozuk; derleme için venv kullanıldı.
**İyileştirme:** `build.py` Instagram açıklamalarına kategoriye göre ek hashtag (Spor→#Eskişehirspor, Asayiş→#SonDakika vb.).
**Sıradaki 3 fikir:** (1) editöre önem 4+ ve `reel` işaretini ağırlıklı vermesini hatırlatmak (OTURUM.md); (2) boş ilçeler için kaynak/arama; (3) nöbetçi eczane sayfası (açık veri kaynağı araştırılacak).
SAHİBİNE: yok (yeni).

## 23.10.2026 21:45 TSİ
**Denetim:** /, /hava-durumu, /namaz-vakitleri 200. Son 24 saatte 125 haber (Siyaset 26, Eğitim 17, Gündem 16, Türkiye 14, Ekonomi 12, Asayiş 10; Sağlık, Tarım, Hava Durumu 1'er). İlçe: Türkiye 62, Merkez 42, Tepebaşı 11, Odunpazarı 7, Beylikova/Sarıcakaya/Sivrihisar 1'er; diğer ilçeler boş. Fotoğrafsız haber 0, aynı başlık tekrarı 0. Instagram: son 24 saatte 16 paylaşım (DAILY_CAP=16 doldu), 2 Reels; son haberlerde `reel`/`video` işaretli haber yok (175 haberin yalnız 4'ü reel).
**Hata (düzeltildi):** `social.framed` içinde `im` değişkeni ezilmişti (ef1d043); `build.py` çöküyor, 18:09'dan beri yayın derlenmiyordu (18:31 ve 18:34 haberleri 404 veriyordu). bdcc6de ile düzeltildi, yerelde derleme geçti (172 haber).
**Kaynaklar (bulut IP'si):** Valilik, Büyükşehir, Anadolu Ünv., OGÜ açılmadı (yurt dışı IP engeli, bilinen); Günyüzü sayfasında bağlantı bulunamadı. Google Haberler/konu kaynakları çalışıyor (477 aday).
**İyileştirme:** bu turda yalnız derleme düzeltmesi.
**Sıradaki 3 fikir:** (1) haber akışı derlemesi bozulursa saglik.yml'in uyarması için `python build.py` denemesi eklemek; (2) editörün `reel` işaretini daha sık vermesi (önem 4+ için); (3) boş ilçeler için (Günyüzü, Mihalıççık, Seyitgazi...) kaynak ekleme.
SAHİBİNE: Cloudflare derleme hatası bildirimi yok; build çökerse haber sessizce yayına girmiyor. Cloudflare'de "build failed" e-posta bildirimi açmanız önerilir.
