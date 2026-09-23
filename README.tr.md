# MetinKap

Kopyalanamayan belgelerden, resimlerden, video karelerinden metni **tek kısayolla** alıp
panoya koyar. Windows'un kendi OCR motorunu (`Windows.Media.Ocr`) kullanır: kurulum yok,
internet yok, bir satır metin için **~15 ms**.

[![lisans: MIT](https://img.shields.io/badge/lisans-MIT-blue.svg)](LICENSE)
![platform: Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4)
![python: 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab)

*English: [README.md](README.md)*

![Ekranda alan seçme](docs/secim.png)

Ekran donuyor, istediğin yeri sürüklüyorsun, metin panoda.

Ne kadar sürdüğü ne kadar seçtiğine bağlı; işine gelen ucu değil aralığın tamamını
yazıyorum (bu makinede ölçüldü, 25 tekrarın medyanı):

| Seçim | Okuma süresi |
|---|---|
| Tek satır (400×40) | ~15 ms |
| Bir paragraf (800×300) | ~85–115 ms |
| Ekran dolusu (1600×900) | ~210–280 ms |

Ekranın donması bunun üstüne ~70 ms daha ekliyor, çünkü 2560×1600'lük sanal ekranın
tamamı tek karede yakalanıyor. `Ctrl+Shift+R` bu kısmı tümden atlıyor.

## Kurulum

**Sadece kullanmak istiyorsan:** [son sürümden](../../releases/latest) `MetinKap.exe`
dosyasını indir ve çalıştır. Başka hiçbir şey gerekmiyor — Python yok, kurulum yok. Saat
yanında tepsi ikonu çıkar ve `Ctrl+Shift+Space` çalışmaya başlar.

Exe ücretli bir kod imzalama sertifikasıyla imzalanmadı, o yüzden Windows direnir. Ne
kadar direneceği makinene bağlı:

- **SmartScreen** *"Windows bilgisayarınızı korudu"* ekranını gösterir. **Ek bilgi → Yine
  de çalıştır** de.
- **Smart App Control** açıksa düpedüz reddeder: *"kuruluşunuzun Device Guard ilkesi
  tarafından engellendi"*, "yine de çalıştır" seçeneği yok. Exe'nin içinde bunu aşacak bir
  şey yok — imzasız her programı engelliyor. Bu durumda kaynaktan çalıştır (aşağıda); o yol
  etkilenmiyor. Bunun için Smart App Control'ü **kapatma**: Windows onu yeniden kurulum
  olmadan geri açamıyor.

  Hangisinde olduğunu görmek için: Windows Güvenliği → Uygulama ve tarayıcı denetimi →
  Smart App Control.

Tanımadığın birinin ürettiği bir çalıştırılabilir dosyaya güvenmek istemiyorsan kendin
derle — aşağıda, tek betik.

İndirdiğin dosyanın makinende gerçekten çalıştığını görmek için:

```
MetinKap.exe --selftest
```

OCR motorunu, üretilen bir görüntüden metin okumayı ve panoyu hiç pencere açmadan
doğruluyor. Çalıştırdığın konsola bağlanıp sonucu yazar; ayrıca her şey yolundaysa `0`,
değilse `1` koduyla çıkar.

### Kaynaktan çalıştırma

```
kurulum.bat
```

Sanal ortamı `%USERPROFILE%\venvs\metinkap` altında kurar (OneDrive dışında, senkron sorunu
olmaz). Sonra `baslat.bat` ile çalıştır — saat yanında tepsi ikonu çıkar.

### Exe'yi kendin derlemek

```
exe-olustur.bat
```

PyInstaller'ı aynı sanal ortama kurar, `dist\MetinKap.exe` üretir ve sonucu `--selftest`
ile sınar — derleme bozuksa "tamam" demeyi reddeder. Yaklaşık 20 saniye sürüyor, ~22 MB
tek dosya çıkıyor.

Smart App Control açıksa doğrulama adımı hiç çalışamaz. Betik bunu fark edip derlemenin
**sınanmadığını** söyler, "bozuk" demez — ikisi farklı şeyler ve karıştırmamakta fayda var.

| Dosya | Ne yapar |
|---|---|
| `baslat.bat` | Sessizce çalıştırır |
| `konsol-ile-baslat.bat` | Konsol açık çalıştırır (sorun ararken) |
| `testleri-calistir.bat` | Test takımlarını çalıştırır |
| `exe-olustur.bat` | `dist\MetinKap.exe` üretir ve doğrular |
| `otomatik-baslat.bat` | Windows açılışına ekler / çıkarır — Ayarlar'dan da yapılabilir |

## Kullanım

| Kısayol | Ne yapar |
|---|---|
| `Ctrl+Shift+Space` | Alan seç → metin doğrudan panoya |
| `Ctrl+Shift+D` | Alan seç → düzeltme penceresinde göster → `Ctrl+Enter` ile kopyala |
| `Ctrl+Shift+R` | **Son alanı** tekrar seçmeden yakala |
| `Ctrl+Shift+A` | **Biriktirme modu** aç/kapa — aşağıya bak |

Seçim ekranında: **sürükle** (canlı boyut göstergesi), **Shift'e basılı tutup bırak** →
önce düzelt, **Enter** → son alanı kullan, **Esc** veya **sağ tık** → iptal. Sonra `Ctrl+V`.

Asıl akılda tutulacak olan `Ctrl+Shift+R`: bir belgeyi sayfa sayfa çevirirken metin hep aynı
yerde duruyorsa kutuyu bir daha hiç çizmen gerekmiyor.

### Biriktirme modu

`Ctrl+Shift+A`'ya bas, yakaladıkların artık panoya gitmez — toplanır. Sayfa sayfa yakala,
sonra tekrar `Ctrl+Shift+A`: hepsi tek blok halinde panoya gelir. On iki sayfalık bir belge,
on iki yakalama + **bir** yapıştırma olur. Parçalar arasındaki ayırıcı config'deki
`biriktir_ayirici` (varsayılan boş satır).

### Kısayolu değiştirmek

Ayarlar → Kısayollar → **Değiştir** → istediğin kombinasyona bas. Tuş Win32'den okunuyor, o
yüzden Türkçe klavyede de doğru harfi alıyor. Kombinasyon doluysa hiçbir şey kaydedilmez,
eski kısayol geri gelir.

> **Ctrl+Alt kullanma.** Türkçe klavyede `Ctrl+Alt` zaten `AltGr`. `Ctrl+Alt+T` kısayolu
> koyarsan `₺` yazamaz hale gelirsin. İlk sürümün varsayılanı bu yüzden değiştirildi; eski
> ayar dosyaları açılışta yeni varsayılana taşınıyor.

## Arayüz

Tepsi ikonuna çift tıkla. Beş sekme:

![Ayarlar penceresi](docs/ayarlar.png)


- **Yakala** — yakala butonu, son yakalanan metin, tekrar kopyala
- **Diller** — kurulu diller (tıkla seç) ve indirilebilirler (tıkla kur)
- **Ayarlar** — arayüz dili, kısayollar, metin biçimi, tanıma seçenekleri, otomatik başlatma
- **Geçmiş** — son 25 yakalama, **düzenlenebilir**: OCR bir şeyi yanlış okuduysa düzeltip
  geri kopyala
- **Hakkında** — doğruluk tablosu, dosya yolları

Arayüz varsayılan olarak İngilizce, Ayarlar'dan Türkçeye geçiyor; tepsi menüsü de çeviriliyor.

### Metin biçimi modları

Satırları korumanın/birleştirmenin ötesinde, iki mod yapıyı **kelimelerin ekrandaki
konumundan** geri kurar:

- **Girintiyi koru (kod)** — Windows OCR baştaki boşlukları atıyor, yapıştırılan kod şeklini
  kaybediyordu. Bu mod her satırın x konumunu girinti seviyesine geri çeviriyor. Çizilmiş bir
  fonksiyon üzerinde ölçüldü: seviyeler `0, 4, 8, 4, 0` olarak, aslıyla birebir çıktı.
- **Tablo (Markdown)** — kelime konumlarından sütun sınırlarını bulup Markdown tablosu yazar,
  böylece satır ve sütunlar yapıştırmada korunur:

  ```
  | Urun   | Adet | Fiyat  |
  |--------|------|--------|
  | Kalem  | 12   | 45.90  |
  ```

Tablo ve kod, eskiden ekran görüntüsü atmaktan kaçamadığın iki durumdu.

### Geldiğin pencereye geri yapıştır

Varsayılan kapalı. Açıkken, yakalamadan önce önde olan pencereyi geri getirip `Ctrl+V`
gönderir. Önce kısayol tuşlarını bırakmanı bekler (yoksa `Ctrl+V` gitmesi gerekirken
`Ctrl+Shift+V` gider) ve odak tam olarak o pencereye dönmediyse hiçbir şey yapmaz — yanlış
yere yazmaz.

### Geçmiş

![Geçmiş sekmesi](docs/gecmis.png)

Yakalamalar kapanışlar arasında kalıyor (`gecmis.json`). Bir kayda tıkla, sağda düzenle,
sonra **Kaydet** / **Kopyala** / **Sil** / **Hepsini temizle**. `Ctrl+S` kaydeder,
`Ctrl+Enter` kopyalar. Başka kayda geçersen düzenlemen otomatik kaydedilir, kaybolmaz.

## Diller

![Diller sekmesi](docs/diller.png)

35 dil listeleniyor. **İndir** yönetici izni ister ve paketi Windows Update üzerinden çeker
(birkaç dakika sürebilir). Kurulunca kurulu listeye geçer ve seçilebilir olur.

**Otomatik** kurulu dilleri sırayla deneyip en çok metin çıkaranı alır — karışık dilli
belgelerde işe yarar, karşılığında biraz daha yavaştır.

> Windows yeni kurulan bir OCR dilini yalnızca **yeni başlatılan** bir sürece gösteriyor.
> Böyle bir durumda uygulama bunu söyleyip **Şimdi yeniden başlat** düğmesi sunuyor; ayarları
> ve geçmişi koruyarak kendini yeniden başlatıyor.

Komut satırından kurmak istersen (yönetici PowerShell):

```powershell
Add-WindowsCapability -Online -Name "Language.OCR~~~fr-FR~0.0.1.0"
```

## Doğruluk

Ölçülen sonuçlar (Segoe UI, Türkçe metin, karakter benzerliği):

6 font × 6 punto, sayı ve noktalama içeren metinle:

| Ölçek | Doğruluk |
|---|---|
| ×1 | %80.15 |
| ×2 | %91.03 |
| **×2.5** | **%90.18** (kullanılan) |
| ×3 | %89.35 |

Ölçümlerin sonucu:

- **Büyütme en önemli etken.** Küçük seçimler büyütülmeden çoğu zaman *hiç* okunmuyor.
- **×3 değil ×2.5.** ×3 temiz düz metinde öne geçiyor ama sayıları bozuyor — `KDV %18`
  çıktıda `KDV 9618` oldu. ×2.5 düz metinde onun kadar iyi, sayılarda daha güvenli.
- **Adaptif ölçek değmiyor.** İlk geçişi yapıp satır yüksekliğini ölçen ve doğru ölçekle
  yeniden okuyan sürüm %89.88 verdi — sabit ×2.5'ten iyi değil, iki katı iş.
- **Kontrast artırma ve gri dönüşümü zarar veriyor** (11pt'de %99.6 → %95.0), ikisi de
  uygulanmıyor.
- **Çoklu ölçek deneyip otomatik seçmek işe yaramıyor.** 4 ölçek + otomatik skorlama, 5 font ×
  5 punto üzerinde: sabit ×3 %98.20, en iyi skorlama %98.06, teorik tavan %98.89. 3–4 kat
  maliyetin karşılığı yok.
- **Koyu tema sorun değil** (%99.3), ters çevirmeye gerek yok.
- **Başka bir OCR motoru eklemeye değmiyor.** RapidOCR (PP-OCRv5 latin) bu makinede Windows
  motoruyla karşılaştırıldı: 15 ms'ye karşı 750 ms, üstelik Türkçede *daha* hatalı — ortak
  latin modeli noktasız `ı`yı `i` yapıyor ve PaddleOCR'ın Türkçe modeli yok. PaddleOCR ve
  Surya Python 3.14'e zaten kurulamıyor; EasyOCR ve docTR ~2.5 GB torch getiriyor. Bulut OCR
  ise her kırpmayı ~30 kat gecikmeyle bir sunucuya gönderirdi.

Bilinen sınırlar:

- **Koddaki alt çizgiler güvenilir değil.** Windows motoru `_` karakterini sık sık düşürüyor;
  monospace fontlarda tanımlayıcının tamamını kaybedebiliyor: testte
  `self._gecmis_kirli = False` satırı `self = False` olarak okundu. Alt çizgiyi piksel
  verisinden geri kazanmak oransal fontlarda işe yarıyor (Segoe UI'da eksiksiz döndü) ama
  monospace'te yaramıyor, çünkü motor kelimeyi hiç raporlamıyor — onarılacak veri yok. Kod
  yakalıyorsan sonucu kontrol et; `Ctrl+Shift+D` metni panoya gitmeden önce düzenlemeye açar.
- Anlamsız büyük harf dizilerinde ve satır başındaki `İ` harfinde motor bazen büyük/küçük
  harfi karıştırıyor. Sözlük destekli çalıştığı için normal düz metinde görülmüyor.

Metin çıkmazsa: daha geniş bir alan seç (tek kelime yerine satırın tamamı) veya dili değiştir.

## Performans notları

Yakalama yolunda ölçüme dayanan tercihler:

- Kırpım OCR motoruna **PNG değil BMP** olarak veriliyor. Aynı yolun PNG'li ikiziyle
  ölçüldü: PNG küçük seçimde +6 ms, paragrafta +35 ms, ekran dolusunda +41 ms getiriyor ve
  tanınan metin birebir aynı. Hemen atılacak bir görüntüyü sıkıştırmanın karşılığı yok.
- `Ctrl+Shift+R` **yalnızca kendi bölgesini** GDI `BitBlt` ile alıyor — satır boyu bölgede
  ~3–4 ms, büyük bölgede ~20 ms. Tüm 2560×1600 sanal ekranı yakalayıp kırpmak ise bölge ne
  olursa olsun ~60–80 ms. Sonuç piksel piksel aynı; GDI çağrısı başarısız olursa PIL yoluna
  düşüyor.
- Seçim ekranının karartması `Image.blend` yerine LUT tabanlı `point()` geçişi — aynı sonuç,
  üçte bir süre.
- Her yakalama kırpımı `son_kirpim.png` olarak da diske yazıyor; okuma tuhaf çıktığında
  motora gerçekte ne verildiğine bakabilesin diye. Bu yazma yukarıdaki sürelerin **içinde** —
  yani o sayılar gerçek maliyet, hata ayıklama yardımcısı çıkarılmış hali değil.

## Dosyalar

Kod:

| Dosya | İçerik |
|---|---|
| `metinkap.py` | OCR, pano, global kısayollar, seçim katmanı, tepsi ikonu |
| `arayuz.py` | Ayar penceresi |
| `diller.py` | Dil tablosu, yönetici izniyle paket kurulumu, otomatik başlatma |
| `ceviri.py` | Arayüz metinleri (en / tr) |
| `tests/` | Test takımları — `python tests/calistir.py` |

Kullanıcı verisi `%APPDATA%\MetinKap\` altında:

- `config.json` — ayarlar; arayüzden düzenlenir ama elle de düzenlenebilir. Geçersiz değerler
  uygulamayı çökertmek yerine yüklenirken onarılıyor, yazma işlemi atomik.
- `gecmis.json` — geçmiş, kapanışlar arasında kalıyor
- `gecmis.txt` — zaman damgalı, sadece eklenen kayıt
- `son_kirpim.png` — en son seçilen alan, yanlış okuma olursa bakmak için
- `hata.log` — hatalar

## Testler

```
testleri-calistir.bat              # hepsi
testleri-calistir.bat --hizli      # yalnızca pencere açmayanlar
```

Testlerin paketlere ihtiyacı var, yani sanal ortamdaki yorumlayıcıyla çalışmaları
gerekiyor — yukarıdaki `.bat` bunu hallediyor. Elle yazacak olsan:

```
"%USERPROFILE%\venvs\metinkap\Scripts\python.exe" tests\calistir.py --hizli
```

Altı takım, 100+ kontrol: ayar ve geçmiş saklama (eşzamanlı yazım dahil), metin
biçimi modları, biriktirme, geri yapıştırmanın güvenlik kontrolleri, ayar
penceresinin iki dilde çizilmesi ve dil kurulum akışı. İkisi gerçek pencere açıp
ekran yakaladığı için çalışırken bilgisayarı kullanma — `--hizli` onları atlar.

Bir şey **doğrulanmadı** ve takımda öyle işaretli: `panoya_yaz` içindeki "pano
meşgul" yolu. Bu makinede başka bir süreç panoyu tutarken bile `OpenClipboard`
başarılı dönüyor, o yüzden hata dalı tetiklenemedi.

## Katkı

Issue ve pull request'ler açık. Baştan bilinmesi gereken bir şey var: **koddaki
tanımlayıcılar ve yorumlar Türkçe**, arayüz ve dokümantasyon İngilizce. Bu bilinçli
bir tercih — yama gönderirsen çevredeki üslubu koru, yeniden adlandırma.

## Nasıl çalışıyor

1. Kısayol `RegisterHotKey` ile sistem genelinde yakalanır (kendi thread'i + mesaj döngüsü)
2. Tüm sanal ekran tek karede yakalanır, kararmış hali tam ekran katman olarak gösterilir;
   seçilen bölge parlak kalır
3. Kırpım ölçeklenir, BMP olarak belleğe yazılır, `Windows.Media.Ocr` ile okunur
4. Aynı yatay banttaki parçalar tek satıra toplanır, satır modu uygulanır, `CF_UNICODETEXT`
   ile panoya yazılır

Çok ekran ve DPI ölçekleme destekli (`PER_MONITOR_AWARE_V2`, pencere oluşturulmadan
ayarlanır). Ayar penceresi DPI'ı ölçüp piksel sabitlerini buna göre ölçekler.
