# Pixel Museum

Her sabah Met Museum'dan public-domain bir tablo seçer, pixel art'a çevirir, altın çerçeveye koyar
ve GitHub Pages'te yayınlar. Bilgisayarındaki küçük bir script de bunu Discord profilinde
**"Playing Pixel Museum"** kartı olarak gösterir.

```
pixel_art_of_the_day.py        # tabloyu seç + pixel art'a çevir -> docs/
.github/workflows/daily.yml    # her gün 07:07'de çalıştırır, commit'ler
docs/index.html                # günün tablosunu gösteren sayfa (GitHub Pages)
rpc/pixel_museum_rpc.py        # Discord Rich Presence (senin bilgisayarında çalışır)
```

## 1. GitHub tarafı (bir kez)

1. GitHub'da **`pixel-museum`** adında **public** bir repo aç ve bu klasördeki her şeyi push'la.
   Repo adını değiştirirsen RPC script'indeki `BASE` linkini de değiştir.
2. **Settings → Pages → Build and deployment**: Source = *Deploy from a branch*,
   Branch = `main`, klasör = `/docs` → Save.
3. **Actions** sekmesi → *pixel-museum-daily* → **Run workflow**. İlk tablo hemen oluşur.
4. 1-2 dakika sonra `https://arif-aygun.github.io/pixel-museum/` adresini aç, tabloyu görmelisin.

Sonrasında workflow her sabah kendiliğinden çalışır.

## 2. Discord tarafı (Rich Presence)

1. Developer Portal → Pixel Museum → **General Information**: İsim ve ikon kartta görünür,
   ikona bir pixel art koyabilirsin.
2. Bilgisayarında:
   ```
   pip install pypresence requests
   ```
3. Discord masaüstü uygulaması açıkken çalıştır:
   ```
   python rpc/pixel_museum_rpc.py
   ```
   Konsolda `Gösteriliyor: ...` yazısı çıkınca profiline bak.
4. Discord → User Settings → **Activity Privacy** → "Share your detected activities with others" açık olmalı.

### Windows açılışında otomatik başlatma
`Win + R` → `shell:startup` → açılan klasöre yeni bir **kısayol** oluştur, hedefi:
```
pythonw "C:\Users\arif\Documents\GitHub\pixel-museum\rpc\pixel_museum_rpc.py"
```
`pythonw` konsol penceresi açmadan arka planda çalışır.

## 3. Discord widget (şimdilik kapalı)

Discord yeni uygulamalarda widget oluşturmayı kapattı. Resmi özellik geldiğinde
`daily.yml`'deki **Update Discord widget** adımı hazır: Secrets'ı ekle ve `if: false` satırını sil.

## Notlar
- Eserler Met Museum Open Access'ten, sadece public-domain olanlar seçiliyor.
- Dosya adları tarihli (`docs/art/2026-11-26.png`), böylece Discord eski görseli cache'ten göstermez.
- Rich Presence token kullanmaz, sadece Application ID'ye ihtiyaç duyar.
