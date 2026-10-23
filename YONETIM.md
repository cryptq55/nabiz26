# Nabız 26 yönetim notları

## 23.10.2026 21:45 TSİ
**Denetim:** /, /hava-durumu, /namaz-vakitleri 200. Son 24 saatte 125 haber (Siyaset 26, Eğitim 17, Gündem 16, Türkiye 14, Ekonomi 12, Asayiş 10; Sağlık, Tarım, Hava Durumu 1'er). İlçe: Türkiye 62, Merkez 42, Tepebaşı 11, Odunpazarı 7, Beylikova/Sarıcakaya/Sivrihisar 1'er; diğer ilçeler boş. Fotoğrafsız haber 0, aynı başlık tekrarı 0. Instagram: son 24 saatte 16 paylaşım (DAILY_CAP=16 doldu), 2 Reels; son haberlerde `reel`/`video` işaretli haber yok (175 haberin yalnız 4'ü reel).
**Hata (düzeltildi):** `social.framed` içinde `im` değişkeni ezilmişti (ef1d043); `build.py` çöküyor, 18:09'dan beri yayın derlenmiyordu (18:31 ve 18:34 haberleri 404 veriyordu). bdcc6de ile düzeltildi, yerelde derleme geçti (172 haber).
**Kaynaklar (bulut IP'si):** Valilik, Büyükşehir, Anadolu Ünv., OGÜ açılmadı (yurt dışı IP engeli, bilinen); Günyüzü sayfasında bağlantı bulunamadı. Google Haberler/konu kaynakları çalışıyor (477 aday).
**İyileştirme:** bu turda yalnız derleme düzeltmesi.
**Sıradaki 3 fikir:** (1) haber akışı derlemesi bozulursa saglik.yml'in uyarması için `python build.py` denemesi eklemek; (2) editörün `reel` işaretini daha sık vermesi (önem 4+ için); (3) boş ilçeler için (Günyüzü, Mihalıççık, Seyitgazi...) kaynak ekleme.
SAHİBİNE: Cloudflare derleme hatası bildirimi yok; build çökerse haber sessizce yayına girmiyor. Cloudflare'de "build failed" e-posta bildirimi açmanız önerilir.
