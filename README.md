# Nabız 26: Eskişehir’in 7/24 yapay zekâ destekli haber portalı

Sistem **saatte bir** şunları yapar:

1. **Tarama:** `sources.yaml` içindeki haber akışlarını (RSS) okur ve yeni haberleri bulur.
2. **Editör ajanı (Claude):** Her haber için karar verir: Eskişehir'le ilgili mi, haber değeri var mı, daha önce yayınlandı mı? Uygun olanı özgün cümlelerle yeniden yazar, kategori ve ilçe atar.
3. **Yayın:** Yeni haber varsa site üretilir ve Cloudflare Pages'te ücretsiz yayınlanır.

Sunucu kiralamanız gerekmez. Tek maliyet Claude API kullanımıdır.

## Kurulum

### 1. Claude API anahtarı
[console.anthropic.com](https://console.anthropic.com) üzerinden anahtar alın ve aylık harcama limiti koyun.

### 2. Cloudflare (ücretsiz)
1. [dash.cloudflare.com](https://dash.cloudflare.com) adresinde hesap açın.
2. **Workers & Pages → Create → Pages → Direct Upload** yolunu izleyin. Proje adı: `nabiz26`. Boş bir klasör yükleyip oluşturmanız yeterli.
3. **Account ID:** Workers & Pages sayfasının sağ tarafında yazar.
4. **API Token:** Sağ üstteki profil → **API Tokens → Create Token → "Edit Cloudflare Workers"** şablonu, ya da özel token ile *Account → Cloudflare Pages → Edit* izni.

### 3. GitHub gizli değişkenleri
Depoda **Settings → Secrets and variables → Actions → New repository secret** yolunu izleyin:

| Secret | Değer |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API anahtarı |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare hesap kimliği |

### 4. Önce deneyin (yayınsız)
Deneme için sadece `ANTHROPIC_API_KEY` yeterli. Cloudflare gerekmez.

**Actions → Deneme (yayınsız) → Run workflow.** Kaç kaynak işleneceğini ve modeli seçebilirsiniz.

- Çalışma bitince sayfasında, ajanın her kaynak için verdiği kararlar ve yazdığı haberlerin tam metni görünür.
- Aynı sayfanın altından **site-onizleme** dosyasını indirip `index.html`'i açarak siteyi kendi bilgisayarınızda görebilirsiniz.
- Hiçbir şey yayınlanmaz ve depoya kaydedilmez.

### 5. Yayına alın
Denemelerden memnun kalınca **Settings → Secrets and variables → Actions → Variables** altına `YAYIN_AKTIF` = `true` ekleyin. Ajan saatte bir çalışmaya ve siteyi güncellemeye başlar. Durdurmak için değeri `false` yapın.

### 6. Alan adı
Cloudflare'de **Pages → nabiz26 → Custom domains** bölümünden `nabiz26.com` adresini bağlayın. Alan adını Cloudflare'den alırsanız ayar otomatik yapılır.

İsteğe bağlı ayarlar (**Settings → Secrets and variables → Actions → Variables**):

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `SITE_NAME` | Nabız 26 | Site adı |
| `SITE_URL` | `https://nabiz26.com` | RSS, sitemap ve paylaşım bağlantıları için |
| `PUBLISH_MODE` | `auto` | `review` yaparsanız haberler taslak olarak kaydedilir |
| `MAX_PER_RUN` | `6` | Her turda modele en fazla kaç kaynak gönderilsin (maliyet sınırı) |
| `NEWS_MODEL` | `claude-opus-5-5` | Daha ucuz seçenek için `claude-haiku-5-5` |

## Maliyet (yaklaşık)

Haber başına yaklaşık 4 bin girdi ve 1,5 bin çıktı token'ı harcanır.

| Model | Haber başı | Günde 40 haber, aylık |
|---|---|---|
| `claude-opus-5-5` (varsayılan, en kaliteli) | ~$0,05 | ~$50–60 |
| `claude-haiku-5-5` (ekonomik) | ~$0,002 | ~$2–3 |

Modele gönderilen her kaynak, yayınlanmasa bile bir çağrı harcar. Üst sınır: günde 24 tur × `MAX_PER_RUN` (varsayılan 6) = 144 çağrı. Bu da Opus ile en kötü durumda günde ~$7, Haiku ile ~$0,30 eder. Gerçek kullanım genellikle bunun altında kalır. Anthropic Console'dan aylık harcama limiti koymayı unutmayın.

## Kaynak ekleme

`sources.yaml` dosyasına RSS adresi eklemeniz yeterli. En değerli kaynaklar resmî kurum duyurularıdır:
Valilik, Büyükşehir, Odunpazarı ve Tepebaşı belediyeleri, üniversiteler, Emniyet ve AFAD.

## Taslak / onay modu

`PUBLISH_MODE=review` olduğunda haberler `data/articles/*.json` içine `"status": "draft"` olarak kaydedilir.
Onaylamak için ilgili dosyada `draft` değerini `published` yapın. GitHub web arayüzünden de düzenleyebilirsiniz.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python newsbot.py --dry-run   # sadece adayları listeler, API harcamaz
python newsbot.py --max 3     # 3 haber yazar
python build.py               # siteyi public/ klasörüne üretir
```

## Hukuki hatırlatmalar

- İnternet haber siteleri süreli yayın sayılır. Cumhuriyet Başsavcılığı'na beyanname verilmesi ve bir **sorumlu müdür** atanması gerekir. Yayınlanan içerikten yapay zekâ değil, sorumlu müdür sorumludur.
- `templates/kunye.html` içindeki köşeli parantezli alanları doldurun.
- Başkalarının haberlerini birebir kopyalamak telif ihlalidir. Sistem özgün metin yazar ve kaynak gösterir, ancak resmî kurum duyurularına ağırlık vermek en güvenli yoldur.
- Asayiş ve adliye haberleri en riskli alandır. Başlangıçta `review` moduyla çalışıp çıktıları birkaç gün kontrol etmeniz önerilir.
