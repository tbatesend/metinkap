"""
MetinKap - grab text from anywhere on screen.

Press the shortcut -> screen freezes -> drag over an area -> text is on the
clipboard. OCR uses the engine built into Windows (Windows.Media.Ocr): no
install, no internet, ~15-50 ms.

Default shortcuts (changeable in the settings window):
    ctrl+shift+space    capture and copy
    ctrl+shift+d        capture, review/edit, copy
    ctrl+shift+r        re-grab the last area without selecting again

On the selection overlay:
    drag                select an area
    release with Shift  open the edit window
    Enter               reuse the last area
    Esc / right click   cancel

Ctrl+Alt is deliberately avoided: on a Turkish keyboard it is the same as
AltGr, so a Ctrl+Alt hotkey breaks typing characters like the lira sign.

Modules: arayuz.py = settings window, diller.py = language packs,
ceviri.py = interface strings.
"""

import asyncio
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import queue
import sys
import threading
import time
import traceback

from PIL import Image, ImageDraw, ImageGrab, ImageTk

# --------------------------------------------------------------------------
# DPI farkindaligi: pencere olusturulmadan ONCE ayarlanmali, yoksa olcekli
# ekranlarda secim koordinatlari kayar.
# --------------------------------------------------------------------------
def _dpi_aware():
    u32 = ctypes.windll.user32
    try:
        u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))   # PER_MONITOR_V2
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        u32.SetProcessDPIAware()
    except Exception:
        pass


_dpi_aware()

import tkinter as tk  # noqa: E402  (DPI ayarindan sonra import edilmeli)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ceviri  # noqa: E402
from ceviri import t  # noqa: E402

# --------------------------------------------------------------------------
# Yollar ve ayarlar
# --------------------------------------------------------------------------
APP_NAME = "MetinKap"
__version__ = "1.0.0"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
HISTORY_JSON = os.path.join(DATA_DIR, "gecmis.json")
HISTORY_TXT = os.path.join(DATA_DIR, "gecmis.txt")
LAST_CROP_PATH = os.path.join(DATA_DIR, "son_kirpim.png")
LOG_PATH = os.path.join(DATA_DIR, "hata.log")
SHOW_FLAG = os.path.join(DATA_DIR, ".goster")

VARSAYILAN = {
    "arayuz_dil": "en",
    "kisayol": "ctrl+shift+space",
    "kisayol_duzelt": "ctrl+shift+d",
    "kisayol_tekrar": "ctrl+shift+r",
    "kisayol_biriktir": "ctrl+shift+a",
    "biriktir_ayirici": "\n\n",
    "dil": "tr",
    "satir_modu": "satir",           # satir | akilli | paragraf
    "buyutme": True,                 # kucuk secimleri OCR oncesi buyut
    "bant_birlestir": True,          # ayni satirda olup bolunmus parcalari birlestir
    "karartma": 0.45,                # secim ekraninda arka plan karartmasi (0-1)
    "bildirim": True,                # kopyalandi baloncugu
    "geri_yapistir": False,          # kopyaladiktan sonra onceki pencereye Ctrl+V
    "gecmis_kaydet": True,           # gecmis diske yazilsin mi
    "gecmis_boyut": 25,
}

# Ilk surumde varsayilan Ctrl+Alt+T idi; Turkce klavyede AltGr ile ayni oldugu
# icin degistirildi. Kullanici elle secmediyse yeni varsayilana tasinir.
ESKI_VARSAYILANLAR = {"kisayol": "ctrl+alt+t", "kisayol_duzelt": "ctrl+alt+shift+t"}

SATIR_MODLARI = ("satir", "akilli", "paragraf", "girinti", "tablo")
SATIR_MODU_ANAHTARI = {"satir": "set.mode_lines", "akilli": "set.mode_smart",
                       "paragraf": "set.mode_para", "girinti": "set.mode_indent",
                       "tablo": "set.mode_table"}
# Tablo ve girinti, sutun yapisini x koordinatlarindan cikardigi icin bant
# birlestirmenin KAPALI olmasini ister: birlestirme bir tablo satirindaki
# hucreleri tek parcaya yapistirip sutunlari yok ediyor.
KUTU_MODLARI = ("girinti", "tablo")


LOG_SINIR = 256 * 1024


def _log(msg):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        # Sinirsiz buyumesin: dolunca bir onceki dosyanin uzerine devret.
        if os.path.getsize(LOG_PATH) > LOG_SINIR:
            os.replace(LOG_PATH, LOG_PATH + ".1")
    except OSError:
        pass
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def ayar_yukle():
    cfg = dict(VARSAYILAN)
    yeni_kurulum = False
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            veri = json.load(f)
        if isinstance(veri, dict):
            cfg.update({k: v for k, v in veri.items() if k in VARSAYILAN})
    except FileNotFoundError:
        yeni_kurulum = True
    except Exception as e:
        _log(f"config okunamadi, varsayilanlara donuldu: {e}")

    degisti = yeni_kurulum
    for anahtar, eski in ESKI_VARSAYILANLAR.items():
        if cfg.get(anahtar) == eski:
            cfg[anahtar] = VARSAYILAN[anahtar]
            degisti = True

    # bozuk degerleri sessizce duzelt, yoksa uygulama acilmaz
    if cfg["satir_modu"] not in SATIR_MODLARI:
        cfg["satir_modu"] = VARSAYILAN["satir_modu"]
        degisti = True
    for anahtar in ("kisayol", "kisayol_duzelt", "kisayol_tekrar",
                    "kisayol_biriktir"):
        try:
            kisayol_coz(cfg[anahtar])
        except Exception:
            cfg[anahtar] = VARSAYILAN[anahtar]
            degisti = True
    # Ayri try'lar: ikisi tek blokta oldugunda bozuk bir gecmis_boyut,
    # kullanicinin duzgun karartma ayarini da varsayilana ceker ve diske oyle
    # yazardi. gecmis_boyut arayuzden duzenlenemiyor, yani elle config duzenleyen
    # birinin tek yazim hatasi baska bir ayarini siliyordu.
    try:
        cfg["karartma"] = max(0.0, min(0.9, float(cfg["karartma"])))
    except (TypeError, ValueError):
        cfg["karartma"] = VARSAYILAN["karartma"]
        degisti = True
    try:
        cfg["gecmis_boyut"] = max(1, min(200, int(cfg["gecmis_boyut"])))
    except (TypeError, ValueError):
        cfg["gecmis_boyut"] = VARSAYILAN["gecmis_boyut"]
        degisti = True

    if degisti:
        ayar_kaydet(cfg)
    return cfg


# Ayarlar hem ana thread'ten hem tepsi thread'inden yazilabiliyor. Ayni gecici
# dosya adini paylasan iki yazim Windows'ta birbirini ezip ayari sessizce
# dusuruyor, hatta bozuk JSON birakabiliyordu; kilit + surece ozgu gecici ad.
_yazma_kilidi = threading.Lock()


def _atomik_json_yaz(yol, veri, girinti=2, deneme=6):
    """Once gecici dosyaya yazip yerine tasir: yarida kesilirse eski dosya kalir.

    os.replace, hedefi o anda baska biri (okuyan bir thread, yedekleme yazilimi,
    virus tarayici) acik tutuyorsa Windows'ta PermissionError/WinError 5 verir.
    Bu genellikle birkac on milisaniyede gecen bir durum, o yuzden kisa araliklarla
    tekrar deniyoruz — yoksa kullanicinin ayari sessizce kayboluyor."""
    gecici = f"{yol}.{os.getpid()}.{threading.get_ident()}.tmp"
    with _yazma_kilidi:
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=girinti)
            for i in range(deneme):
                try:
                    os.replace(gecici, yol)
                    return
                except PermissionError:
                    if i == deneme - 1:
                        raise
                    time.sleep(0.03 * (i + 1))
        except Exception:
            try:
                os.remove(gecici)
            except OSError:
                pass
            raise


def ayar_kaydet(cfg):
    """Basarili olursa True. Cagiran tarafin buna bakmasi gerekiyor: bir ara
    hata sadece loglaniyordu ve arayuz yazilmamis bir ayara "Kaydedildi" diyordu.
    Kullanici uygulamayi kapatip acana kadar ayarinin durdugunu saniyordu."""
    try:
        _atomik_json_yaz(CONFIG_PATH, cfg)
        return True
    except Exception as e:
        _log(f"config yazilamadi: {e}")
        return False


# --------------------------------------------------------------------------
# Pano (Win32 - uygulama kapansa bile pano icerigi kalir)
# --------------------------------------------------------------------------
_u32 = ctypes.windll.user32
_k32 = ctypes.windll.kernel32
_k32.GlobalAlloc.restype = ctypes.c_void_p
_k32.GlobalLock.restype = ctypes.c_void_p
_k32.GlobalLock.argtypes = [ctypes.c_void_p]
_k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
_k32.GlobalFree.restype = ctypes.c_void_p
_k32.GlobalFree.argtypes = [ctypes.c_void_p]
_u32.SetClipboardData.restype = ctypes.c_void_p
_u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
# 64-bit'te varsayilan restype c_int: handle'in ust yarisi kesiliyor ve
# GlobalLock cope bakip NULL donuyor.
_u32.GetClipboardData.restype = ctypes.c_void_p
_u32.GetClipboardData.argtypes = [ctypes.c_uint]

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def panodan_metin_oku():
    """Panodaki metni doner; metin yoksa veya okunamazsa "".

    Yalnizca --selftest icin var: sinama panoya yaziyor ve kullanicinin orada
    ne varsa siliyordu. Once bunu okuyup sonra geri koyuyoruz. Resim/dosya gibi
    metin disi icerik bu yolla geri konulamaz, cagiran taraf bunu soyluyor."""
    if not _u32.OpenClipboard(None):
        return ""
    try:
        h = _u32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        p = _k32.GlobalLock(ctypes.c_void_p(h))
        if not p:
            return ""
        try:
            return ctypes.c_wchar_p(p).value or ""
        finally:
            _k32.GlobalUnlock(ctypes.c_void_p(h))
    except Exception:
        return ""
    finally:
        _u32.CloseClipboard()


def panoyu_bosalt():
    if not _u32.OpenClipboard(None):
        return False
    try:
        return bool(_u32.EmptyClipboard())
    finally:
        _u32.CloseClipboard()


def panoya_yaz(text):
    """Basarisizlikta False doner. Her adim kontrol ediliyor: EmptyClipboard
    zaten calistigi icin yarida kalan bir yazim kullanicinin eski pano icerigini
    de siler, o yuzden arayan tarafa 'kopyalandi' demek yanlis olur."""
    if not text:
        return False
    for _ in range(10):                    # pano baska uygulamadaysa kisa sure dene
        if _u32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return False
    h = None
    try:
        _u32.EmptyClipboard()
        buf = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(buf)
        h = _k32.GlobalAlloc(GMEM_MOVEABLE, size)
        if not h:
            return False
        p = _k32.GlobalLock(h)
        if not p:                          # NULL'a memmove sert cokme demek
            return False
        try:
            ctypes.memmove(p, buf, size)
        finally:
            _k32.GlobalUnlock(h)
        if not _u32.SetClipboardData(CF_UNICODETEXT, h):
            return False                   # handle bizde kaldi, finally serbest birakir
        h = None                           # sahiplik panoya gecti, artik bizim degil
        return True
    finally:
        _u32.CloseClipboard()
        if h:
            _k32.GlobalFree(h)


# --------------------------------------------------------------------------
# OCR (Windows.Media.Ocr)
# --------------------------------------------------------------------------
class Ocr:
    def __init__(self):
        self._engines = {}
        self._lock = threading.Lock()
        self._ready = False
        self._import_error = None
        try:
            from winrt.windows.globalization import Language
            from winrt.windows.graphics.imaging import BitmapDecoder
            from winrt.windows.media.ocr import OcrEngine
            from winrt.windows.storage.streams import (
                DataWriter,
                InMemoryRandomAccessStream,
            )

            self._Language = Language
            self._BitmapDecoder = BitmapDecoder
            self._OcrEngine = OcrEngine
            self._DataWriter = DataWriter
            self._Stream = InMemoryRandomAccessStream
            self._ready = True
        except Exception as e:  # pragma: no cover
            self._import_error = e
            _log(f"winrt import hatasi: {e}")

    @property
    def hazir(self):
        return self._ready

    def diller(self):
        if not self._ready:
            return []
        try:
            return [l.language_tag
                    for l in self._OcrEngine.available_recognizer_languages]
        except Exception as e:
            _log(f"dil listesi: {e}")
            return []

    def _engine(self, tag):
        with self._lock:
            if tag not in self._engines:
                self._engines[tag] = self._OcrEngine.try_create_from_language(
                    self._Language(tag))
            return self._engines[tag]

    async def _tani(self, data, tag):
        eng = self._engine(tag)
        if eng is None:
            raise RuntimeError(f"no OCR engine for '{tag}'")
        akis = self._Stream()
        yazici = self._DataWriter(akis)
        yazici.write_bytes(data)
        await yazici.store_async()
        await yazici.flush_async()
        yazici.detach_stream()
        akis.seek(0)
        dec = await self._BitmapDecoder.create_async(akis)
        bmp = await dec.get_software_bitmap_async()
        res = await eng.recognize_async(bmp)

        parcalar = []
        for satir in res.lines:
            kelimeler = list(satir.words)
            if not kelimeler:
                continue
            kutular = [k.bounding_rect for k in kelimeler]
            kutu = (min(b.x for b in kutular), min(b.y for b in kutular),
                    max(b.x + b.width for b in kutular),
                    max(b.y + b.height for b in kutular))
            parcalar.append((" ".join(k.text for k in kelimeler), kutu))
        return parcalar

    def parcalar(self, img, tag, bant_birlestir=True):
        """PIL goruntusunden [(metin, (x0,y0,x1,y1))] dondurur.

        Kutular tablo ve girinti modlari icin gerekli; sutun yapisi yalnizca
        x koordinatlarindan cikarilabiliyor."""
        buf = io.BytesIO()
        # convert() zaten RGB olan goruntuyu de kopyaliyor: 1600x900'de olculen
        # bedel 2.1 ms, kucuk secimde 0.00. Kirpim bu yola hep RGB geliyor,
        # yani normalde bu satir bos yere calisiyordu.
        (img if img.mode == "RGB" else img.convert("RGB")).save(buf, "BMP")
        # BMP, PNG degil: olculdu, PNG orta boyda +35 ms, buyukte +41 ms
        # getiriyor ve taninan metin birebir ayni. Hemen atilacak bir goruntuye
        # sikistirma yapmanin karsiligi yok.
        ham = asyncio.run(self._tani(buf.getvalue(), tag))
        return bantlari_birlestir(ham) if bant_birlestir else ham

    def satirlar(self, img, tag, bant_birlestir=True):
        """Yalnizca metin isteyen cagiranlar icin kisayol."""
        return [p[0] for p in self.parcalar(img, tag, bant_birlestir)]

    def isin(self):
        """Ilk cagriyi onceden yaparak soguk baslangici gizler."""
        try:
            diller = self.diller()
            if diller:
                self.satirlar(Image.new("RGB", (64, 32), "white"), diller[0])
        except Exception:
            pass

    def unut(self):
        """Yeni bir dil paketi kurulduktan sonra motor onbellegini bosaltir."""
        with self._lock:
            self._engines.clear()

    def dil_var_mi(self, tag):
        """available_recognizer_languages surec omru boyunca onbelleklenebiliyor;
        yeni kurulan bir dil orada gorunmese de motoru olusturulabiliyor olabilir.
        Bu yuzden liste yerine dogrudan motor olusturmayi deniyoruz."""
        if not self._ready:
            return False
        try:
            return self._engine(tag) is not None
        except Exception:
            return False


def bantlari_birlestir(parcalar, ortusme=0.55, bosluk_kati=3.0):
    """Windows OCR bazen tek bir gorsel satiri, icindeki genis bosluklardan
    bolup birden fazla 'line' olarak dondurur. Ayni yatay bantta duran ve
    aralarindaki bosluk makul olan parcalari tek satira geri birlestirir.
    Bosluk esigi, iki sutunlu metinlerin yanlislikla birlesmesini onler."""
    # Dikkat: bu fonksiyon (metin, kutu) ciftleri dondurur. Erken donus de ayni
    # tipte olmali; bir ara sadece metin donuyordu ve cagiran taraf p[0] alinca
    # metnin ILK HARFINI aliyordu — tek satirlik her yakalama tek harfe dusuyordu.
    if len(parcalar) < 2:
        return list(parcalar)

    gruplar = []
    for metin, r in sorted(parcalar, key=lambda p: (p[1][1], p[1][0])):
        h = r[3] - r[1]
        for g in gruplar:
            gy0 = min(x[1][1] for x in g)
            gy1 = max(x[1][3] for x in g)
            ortak = min(gy1, r[3]) - max(gy0, r[1])
            ref = min(gy1 - gy0, h)
            if ref <= 0 or ortak / ref < ortusme:
                continue
            gx0 = min(x[1][0] for x in g)
            gx1 = max(x[1][2] for x in g)
            if max(r[0] - gx1, gx0 - r[2]) < bosluk_kati * ref:
                g.append((metin, r))
                break
        else:
            gruplar.append([(metin, r)])

    gruplar.sort(key=lambda g: min(x[1][1] for x in g))
    birlesik = []
    for g in gruplar:
        g.sort(key=lambda x: x[1][0])
        kutu = (min(x[1][0] for x in g), min(x[1][1] for x in g),
                max(x[1][2] for x in g), max(x[1][3] for x in g))
        birlesik.append((" ".join(x[0] for x in g), kutu))
    return birlesik


def satirlara_grupla(parcalar, ortusme=0.5):
    """Parcalari gorsel satirlara boler: [[(metin, kutu), ...], ...]

    Tablo modunda bant birlestirme kapali kaldigi icin bir tablo satirindaki
    hucreler ayri parcalar olarak gelir; burada y ortusmesine gore toplanir."""
    satirlar = []
    for metin, r in sorted(parcalar, key=lambda p: (p[1][1], p[1][0])):
        h = r[3] - r[1]
        for s in satirlar:
            sy0 = min(x[1][1] for x in s)
            sy1 = max(x[1][3] for x in s)
            ortak = min(sy1, r[3]) - max(sy0, r[1])
            ref = min(sy1 - sy0, h)
            if ref > 0 and ortak / ref >= ortusme:
                s.append((metin, r))
                break
        else:
            satirlar.append([(metin, r)])
    for s in satirlar:
        s.sort(key=lambda x: x[1][0])
    satirlar.sort(key=lambda s: min(x[1][1] for x in s))
    return satirlar


def _kumeleri_bul(degerler, tolerans):
    """Yakin sayilari gruplar, her grubun temsilcisini (en kucuk) dondurur."""
    kume = []
    for d in sorted(degerler):
        if kume and d - kume[-1][-1] <= tolerans:
            kume[-1].append(d)
        else:
            kume.append([d])
    return [k[0] for k in kume]


def girintili_metin(parcalar):
    """Satir basi x koordinatlarindan girinti seviyesini geri uretir.

    Windows OCR bastaki bosluklari yutuyor; kod yapistirirken girinti
    kaybolmasin diye x degerleri kumelenip seviyeye cevriliyor."""
    satirlar = satirlara_grupla(parcalar)
    if not satirlar:
        return ""
    yukseklik = statistics_medyan([max(x[1][3] for x in s) - min(x[1][1] for x in s)
                                   for s in satirlar]) or 10
    basluklar = [min(x[1][0] for x in s) for s in satirlar]
    seviyeler = _kumeleri_bul(basluklar, yukseklik * 0.6)
    out = []
    for s in satirlar:
        x0 = min(x[1][0] for x in s)
        # bu satirin hangi kumeye dustugu = girinti seviyesi
        seviye = max((i for i, v in enumerate(seviyeler) if x0 >= v - yukseklik * 0.6),
                     default=0)
        out.append("    " * seviye + " ".join(x[0] for x in s))
    return "\n".join(out)


def tablo_metni(parcalar, markdown=True):
    """Sutunlari x koordinatlarindan cikarip tablo olarak bicimler.

    Bosluklarla hizalanmis bir tabloyu duz metin olarak yapistirmak sutunlari
    karistiriyor; Markdown/TSV olarak vermek yapiyi koruyor."""
    satirlar = satirlara_grupla(parcalar)
    if not satirlar:
        return ""
    yukseklik = statistics_medyan([max(x[1][3] for x in s) - min(x[1][1] for x in s)
                                   for s in satirlar]) or 10
    baslangiclar = [x[1][0] for s in satirlar for x in s]
    sutunlar = _kumeleri_bul(baslangiclar, yukseklik * 1.2)
    if len(sutunlar) < 2:
        return "\n".join(" ".join(x[0] for x in s) for s in satirlar)

    izgara = []
    for s in satirlar:
        hucreler = [""] * len(sutunlar)
        for metin, r in s:
            i = max((j for j, v in enumerate(sutunlar) if r[0] >= v - yukseklik * 1.2),
                    default=0)
            hucreler[i] = (hucreler[i] + " " + metin).strip()
        izgara.append(hucreler)

    if not markdown:
        return "\n".join("\t".join(h) for h in izgara)
    genislik = [max(len(satir[i]) for satir in izgara) for i in range(len(sutunlar))]
    cizgi = lambda h: "| " + " | ".join(
        v.ljust(genislik[i]) for i, v in enumerate(h)) + " |"
    out = [cizgi(izgara[0]),
           "|" + "|".join("-" * (g + 2) for g in genislik) + "|"]
    out += [cizgi(h) for h in izgara[1:]]
    return "\n".join(out)


def statistics_medyan(degerler):
    d = sorted(v for v in degerler if v)
    if not d:
        return 0
    n = len(d)
    return d[n // 2] if n % 2 else (d[n // 2 - 1] + d[n // 2]) / 2


# --------------------------------------------------------------------------
# Metin birlestirme
# --------------------------------------------------------------------------
_CUMLE_SONU = ".!?:;•—…"
_MADDE_BASI = "-•*·—>"


def bicimlendir(parcalar, mod):
    """OCR parcalarini secilen metin bicimine cevirir."""
    if mod == "tablo":
        return tablo_metni(parcalar)
    if mod == "girinti":
        return girintili_metin(parcalar)
    return satirlari_birlestir([p[0] for p in parcalar], mod)


def satirlari_birlestir(satirlar, mod):
    satirlar = [s.strip() for s in satirlar]
    if mod == "paragraf":
        return " ".join(s for s in satirlar if s)
    if mod != "akilli":
        return "\n".join(satirlar)

    out = []
    for ln in satirlar:
        if not ln:
            out.append("")
            continue
        if out and out[-1]:
            prev = out[-1].rstrip()
            if prev.endswith("-"):                       # hece bolunmesi
                out[-1] = prev[:-1] + ln
                continue
            bitti = prev[-1] in _CUMLE_SONU
            yeni = ln[0].isupper() or ln[0].isdigit() or ln[0] in _MADDE_BASI
            if not bitti and not yeni:
                out[-1] = prev + " " + ln
                continue
        out.append(ln)
    return "\n".join(out)


# --------------------------------------------------------------------------
# Global kisayol (RegisterHotKey + kendi mesaj dongusu)
# --------------------------------------------------------------------------
MOD = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002, "shift": 0x0004,
       "win": 0x0008, "super": 0x0008}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_OZEL_TUS = {
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B,
    "escape": 0x1B, "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27,
    "down": 0x28, "printscreen": 0x2C, "oem3": 0xC0,
}
for _i in range(1, 25):
    _OZEL_TUS[f"f{_i}"] = 0x6F + _i


def kisayol_coz(s):
    """'ctrl+shift+space' -> (mods, vk)"""
    if not isinstance(s, str):
        raise ValueError("shortcut must be a string")
    parcalar = [p.strip().lower() for p in s.split("+") if p.strip()]
    mods = 0
    vk = None
    for p in parcalar:
        if p in MOD:
            mods |= MOD[p]
        elif p in _OZEL_TUS:
            vk = _OZEL_TUS[p]
        elif len(p) == 1 and (p.isalpha() or p.isdigit()):
            vk = ord(p.upper())
        else:
            raise ValueError(f"unknown key: {p}")
    if vk is None:
        raise ValueError(f"no key in: {s}")
    return mods | MOD_NOREPEAT, vk


class KisayolDinleyici(threading.Thread):
    """Kendi thread'inde RegisterHotKey yapar, olaylari kuyruga koyar."""

    def __init__(self, bindings, kuyruk):
        super().__init__(daemon=True, name="hotkey")
        self.bindings = bindings              # {id: "ctrl+shift+space"}
        self.kuyruk = kuyruk
        self.tid = None
        self.hatalar = []
        self._kuruldu = threading.Event()

    def run(self):
        u32 = ctypes.windll.user32
        self.tid = _k32.GetCurrentThreadId()
        for hid, combo in self.bindings.items():
            try:
                mods, vk = kisayol_coz(combo)
            except ValueError:
                self.hatalar.append((hid, combo))
                continue
            # Birkac kez deniyoruz: yeniden baslatmada eski kopya kisayollari
            # birakana kadar birkac yuz ms gecebiliyor.
            for deneme in range(6):
                if u32.RegisterHotKey(None, hid, mods, vk):
                    break
                time.sleep(0.2)
            else:
                self.hatalar.append((hid, combo))
        self._kuruldu.set()

        msg = wt.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                self.kuyruk.put(("hotkey", int(msg.wParam)))
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))

        for hid in self.bindings:
            u32.UnregisterHotKey(None, hid)

    def bekle(self, sn=8.0):
        self._kuruldu.wait(sn)
        return self.hatalar

    def durdur(self):
        if self.tid:
            _u32.PostThreadMessageW(self.tid, WM_QUIT, 0, 0)


# --------------------------------------------------------------------------
# Sanal ekran
# --------------------------------------------------------------------------
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79


def sanal_ekran():
    g = _u32.GetSystemMetrics
    return (g(SM_XVIRTUALSCREEN), g(SM_YVIRTUALSCREEN),
            g(SM_CXVIRTUALSCREEN), g(SM_CYVIRTUALSCREEN))


def imlec_konumu():
    pt = wt.POINT()
    _u32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


# --------------------------------------------------------------------------
# Onceki pencereye geri yapistirma
# --------------------------------------------------------------------------
VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN, VK_V = (
    0x11, 0x10, 0x12, 0x5B, 0x5C, 0x56)
KEYEVENTF_KEYUP = 0x0002


def _modifierlar_birakildi_mi():
    gak = _u32.GetAsyncKeyState
    return not any(gak(v) & 0x8000
                   for v in (VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN))


def pencereye_yapistir(hwnd, bekleme=1.5):
    """Verilen pencereyi one getirip Ctrl+V gonderir.

    Kullanici kisayolu hala basili tutuyor olabilir; oyle bir anda Ctrl+V
    gondermek Ctrl+Shift+V gibi bambaska bir kisayola donusur, o yuzden once
    tum yardimci tuslarin birakilmasi bekleniyor."""
    if not hwnd or not _u32.IsWindow(hwnd):
        return False
    son = time.time() + bekleme
    while not _modifierlar_birakildi_mi():
        if time.time() > son:
            return False                      # kullanici tuslari birakmadi
        time.sleep(0.02)
    if not _u32.SetForegroundWindow(hwnd):
        return False
    time.sleep(0.06)                          # odak gercekten gecsin
    if _u32.GetForegroundWindow() != hwnd:
        return False                          # baska pencereye yazmayalim
    for vk, bayrak in ((VK_CONTROL, 0), (VK_V, 0),
                       (VK_V, KEYEVENTF_KEYUP), (VK_CONTROL, KEYEVENTF_KEYUP)):
        _u32.keybd_event(vk, 0, bayrak, 0)
        time.sleep(0.01)
    return True


def ekrani_yakala():
    """Tum sanal ekran. Goruntunun (0,0) noktasi sanal ekranin sol ust kosesi.

    PIL'de bbox goruntu koordinatlarinda yorumlandigi icin bbox verilmiyor."""
    return ImageGrab.grab(all_screens=True).convert("RGB")


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


SRCCOPY = 0x00CC0020


def bolge_yakala(kutu):
    """Sanal ekran goruntu koordinatlarindaki tek bir dikdortgeni yakalar.

    Tum ekrani alip kirpmak 2560x1600'de ~60-80 ms (iki bagimsiz turun medyani
    62 ve 74; once buraya ~55 yazilmisti, o minimuma yakin bir degerdi).
    Tek bolgeyi BitBlt ile almak satir boyunda ~3-4 ms, 1600x900'de ~20 ms.
    Sonuc piksel piksel ayni: statik bir bolgede 10/10 esitlendi. (Degisen bir
    bolgede karsilastirma anlamsiz — arka arkaya iki BitBlt de tutmuyor.)
    'Son alani tekrar yakala' her seferinde bunu cagirdigi icin fark
    hissediliyor."""
    gdi = ctypes.windll.gdi32
    u32 = ctypes.windll.user32
    vx, vy, _, _ = sanal_ekran()
    x, y = int(kutu[0]) + vx, int(kutu[1]) + vy
    w, h = int(kutu[2] - kutu[0]), int(kutu[3] - kutu[1])
    if w <= 0 or h <= 0:
        raise ValueError("empty region")

    ekran_dc = mem_dc = bmp = None
    try:
        ekran_dc = u32.GetDC(None)
        mem_dc = gdi.CreateCompatibleDC(ekran_dc)
        bmp = gdi.CreateCompatibleBitmap(ekran_dc, w, h)
        gdi.SelectObject(mem_dc, bmp)
        if not gdi.BitBlt(mem_dc, 0, 0, w, h, ekran_dc, x, y, SRCCOPY):
            raise OSError("BitBlt failed")
        bi = _BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bi.biWidth, bi.biHeight = w, -h        # negatif = yukaridan asagi
        bi.biPlanes, bi.biBitCount, bi.biCompression = 1, 32, 0
        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(bi), 0):
            raise OSError("GetDIBits failed")
        return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
    finally:
        if bmp:
            gdi.DeleteObject(bmp)
        if mem_dc:
            gdi.DeleteDC(mem_dc)
        if ekran_dc:
            u32.ReleaseDC(None, ekran_dc)


def karart(img, oran):
    """Image.blend ile ayni sonuc, ucte bir surede (LUT tek gecis)."""
    k = max(0.0, min(0.9, oran))
    return img.point([int(i * (1 - k)) for i in range(256)] * 3)


# --------------------------------------------------------------------------
# Secim katmani
# --------------------------------------------------------------------------
class SecimKatmani:
    """Tum ekranlari kaplayan donmus goruntu uzerinde dikdortgen secimi."""

    def __init__(self, root, karartma, on_done, son_kutu=None):
        self.root = root
        self.on_done = on_done
        self.son_kutu = son_kutu

        vx, vy, vw, vh = sanal_ekran()
        self.parlak = ekrani_yakala()
        vw, vh = self.parlak.size
        self.karanlik = karart(self.parlak, karartma)

        self.win = tk.Toplevel(root)
        try:
            self._kur(vx, vy, vw, vh, son_kutu)
        except Exception:
            # Yarida kalan kurulum, ekrani kaplayan basliksiz ve her zaman ustte
            # duran bir pencere birakir; Esc bile henuz baglanmamis olabilir.
            try:
                self.win.destroy()
            except Exception:
                pass
            raise

    def _kur(self, vx, vy, vw, vh, son_kutu):
        self.win.overrideredirect(True)
        self.win.geometry(f"{vw}x{vh}+{vx}+{vy}")
        self.win.attributes("-topmost", True)
        self.win.configure(cursor="crosshair", bg="black")

        self.canvas = tk.Canvas(self.win, width=vw, height=vh, highlightthickness=0,
                                bd=0, bg="black", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self._bg = ImageTk.PhotoImage(self.karanlik)
        self.canvas.create_image(0, 0, anchor="nw", image=self._bg)

        self._sel_img = None
        self._sel_id = None
        self._cerceve = self.canvas.create_rectangle(0, 0, 0, 0, outline="#4ea1ff",
                                                     width=2, state="hidden")
        self._etiket_bg = self.canvas.create_rectangle(0, 0, 0, 0, fill="#101418",
                                                       outline="#4ea1ff",
                                                       state="hidden")
        self._etiket = self.canvas.create_text(0, 0, text="", fill="#e8f1ff",
                                               anchor="nw", state="hidden",
                                               font=("Segoe UI", 10, "bold"))
        ipucu = t("sel.hint")
        if not son_kutu:
            ipucu = ipucu.replace("   ·   Enter: last area", "") \
                         .replace("   ·   Enter: son alan", "")
        self.canvas.create_text(vw // 2, 28, text=ipucu, fill="#cfe3ff",
                                font=("Segoe UI", 12), tags="ipucu")
        self._crossh = self.canvas.create_line(0, 0, 0, 0, fill="#4ea1ff", dash=(3, 3))
        self._crossv = self.canvas.create_line(0, 0, 0, 0, fill="#4ea1ff", dash=(3, 3))

        self.baslangic = None
        self._render_bekliyor = False
        self._son_render_kutu = None

        self.canvas.bind("<Button-1>", self._bas)
        self.canvas.bind("<B1-Motion>", self._surukle)
        self.canvas.bind("<ButtonRelease-1>", self._birak)
        self.canvas.bind("<Motion>", self._hareket)
        self.win.bind("<Escape>", lambda e: self._kapat(None))
        self.win.bind("<Button-3>", lambda e: self._kapat(None))
        self.win.bind("<Return>", self._son_alani_kullan)

        self.win.focus_force()
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

    def _hareket(self, e):
        if self.baslangic:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.coords(self._crossh, 0, e.y, w, e.y)
        self.canvas.coords(self._crossv, e.x, 0, e.x, h)

    def _bas(self, e):
        self.baslangic = (e.x, e.y)
        self.canvas.itemconfigure(self._crossh, state="hidden")
        self.canvas.itemconfigure(self._crossv, state="hidden")
        self.canvas.itemconfigure("ipucu", state="hidden")

    def _kutu(self, e):
        x0, y0 = self.baslangic
        return (min(x0, e.x), min(y0, e.y), max(x0, e.x), max(y0, e.y))

    def _surukle(self, e):
        if not self.baslangic:
            return
        self._son_render_kutu = self._kutu(e)
        if not self._render_bekliyor:
            self._render_bekliyor = True
            self.canvas.after(8, self._ciz)

    def _ciz(self):
        self._render_bekliyor = False
        kutu = self._son_render_kutu
        if not kutu:
            return
        x0, y0, x1, y1 = kutu
        w, h = x1 - x0, y1 - y0
        if w < 2 or h < 2:
            return

        self._sel_img = ImageTk.PhotoImage(self.parlak.crop((x0, y0, x1, y1)))
        if self._sel_id is None:
            self._sel_id = self.canvas.create_image(x0, y0, anchor="nw",
                                                    image=self._sel_img)
        else:
            self.canvas.itemconfigure(self._sel_id, image=self._sel_img)
            self.canvas.coords(self._sel_id, x0, y0)
        self.canvas.tag_raise(self._sel_id)

        self.canvas.coords(self._cerceve, x0, y0, x1, y1)
        self.canvas.itemconfigure(self._cerceve, state="normal")
        self.canvas.tag_raise(self._cerceve)

        ex, ey = x0, y0 - 24
        if ey < 2:
            ey = y1 + 6
        self.canvas.coords(self._etiket, ex + 6, ey + 3)
        self.canvas.itemconfigure(self._etiket, text=f"{w} × {h}", state="normal")
        bx = self.canvas.bbox(self._etiket)
        if bx:
            self.canvas.coords(self._etiket_bg, bx[0] - 6, bx[1] - 3,
                               bx[2] + 6, bx[3] + 3)
            self.canvas.itemconfigure(self._etiket_bg, state="normal")
            self.canvas.tag_raise(self._etiket_bg)
            self.canvas.tag_raise(self._etiket)

    def _son_alani_kullan(self, _e=None):
        if not self.son_kutu:
            return
        kutu = self._kirp_sinira(self.son_kutu)
        if kutu:
            self._kapat((self.parlak.crop(kutu), False, kutu))

    def _kirp_sinira(self, kutu):
        w, h = self.parlak.size
        x0 = max(0, min(int(kutu[0]), w - 1))
        y0 = max(0, min(int(kutu[1]), h - 1))
        x1 = max(x0 + 1, min(int(kutu[2]), w))
        y1 = max(y0 + 1, min(int(kutu[3]), h))
        return (x0, y0, x1, y1) if (x1 - x0) > 4 and (y1 - y0) > 4 else None

    def _birak(self, e):
        if not self.baslangic:
            return self._kapat(None)
        kutu = self._kutu(e)
        if (kutu[2] - kutu[0]) < 5 or (kutu[3] - kutu[1]) < 5:
            return self._kapat(None)
        shift = bool(e.state & 0x0001)
        self._kapat((self.parlak.crop(kutu), shift, kutu))

    def _kapat(self, sonuc):
        try:
            self.win.grab_release()
        except Exception:
            pass
        self.win.destroy()
        self.on_done(sonuc)


# --------------------------------------------------------------------------
# Kopyalandi baloncugu (ayni anda tek tane)
# --------------------------------------------------------------------------
_aktif_baloncuk = None


def baloncuk(root, metin, hata=False, sure=1400):
    global _aktif_baloncuk
    try:
        if _aktif_baloncuk is not None:
            try:
                _aktif_baloncuk.destroy()
            except Exception:
                pass
            _aktif_baloncuk = None

        w = tk.Toplevel(root)
        _aktif_baloncuk = w
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha", 0.0)
        renk = "#7a1f28" if hata else "#16321f"
        kenar = "#ff7b8a" if hata else "#4ade80"
        f = tk.Frame(w, bg=renk, highlightbackground=kenar, highlightthickness=1)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=metin, bg=renk, fg="#eaf6ee", font=("Segoe UI", 11),
                 padx=14, pady=9, justify="left").pack()
        w.update_idletasks()

        cx, cy = imlec_konumu()
        vx, vy, vw, vh = sanal_ekran()
        ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
        x = min(max(cx + 16, vx + 4), vx + vw - ww - 4)
        y = min(max(cy + 22, vy + 4), vy + vh - wh - 4)
        w.geometry(f"+{x}+{y}")

        def bit():
            global _aktif_baloncuk
            if _aktif_baloncuk is w:
                _aktif_baloncuk = None
            try:
                w.destroy()
            except Exception:
                pass

        def ac(a=0.0):
            if not w.winfo_exists():
                return
            a += 0.18
            w.attributes("-alpha", min(a, 0.96))
            if a < 0.96:
                w.after(16, ac, a)
            else:
                w.after(sure, kapat, 0.96)

        def kapat(a):
            if not w.winfo_exists():
                return
            a -= 0.12
            if a <= 0:
                return bit()
            w.attributes("-alpha", a)
            w.after(20, kapat, a)

        ac()
    except Exception as e:
        _log(f"baloncuk: {e}")


# --------------------------------------------------------------------------
# Duzeltme penceresi
# --------------------------------------------------------------------------
class DuzeltPenceresi:
    def __init__(self, root, metin, on_copy):
        self.on_copy = on_copy
        w = tk.Toplevel(root)
        self.win = w
        w.title(t("edit.title"))
        w.attributes("-topmost", True)
        w.configure(bg="#11151a")

        ust = tk.Frame(w, bg="#11151a")
        ust.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(ust, text=t("edit.hint"), bg="#11151a", fg="#8fa3b8",
                 font=("Segoe UI", 9)).pack(side="left")
        self.sayac = tk.Label(ust, text="", bg="#11151a", fg="#8fa3b8",
                              font=("Segoe UI", 9))
        self.sayac.pack(side="right")

        self.text = tk.Text(w, wrap="word", width=78, height=18, undo=True,
                            bg="#0d1117", fg="#e6edf3", insertbackground="#e6edf3",
                            relief="flat", padx=12, pady=10, font=("Consolas", 11))
        self.text.pack(fill="both", expand=True, padx=12)
        self.text.insert("1.0", metin)
        self.text.bind("<<Modified>>", self._degisti)

        alt = tk.Frame(w, bg="#11151a")
        alt.pack(fill="x", padx=12, pady=12)
        tk.Button(alt, text=t("btn.copy"), command=self._kopyala, relief="flat",
                  bg="#2563eb", fg="white", activebackground="#1d4ed8",
                  activeforeground="white", font=("Segoe UI", 10, "bold"),
                  padx=18, pady=6, cursor="hand2").pack(side="right")
        tk.Button(alt, text=t("btn.close"), command=w.destroy, relief="flat",
                  bg="#1f2630", fg="#c9d4e0", activebackground="#2a323d",
                  activeforeground="white", font=("Segoe UI", 10),
                  padx=14, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

        w.bind("<Control-Return>", lambda e: self._kopyala())
        w.bind("<Escape>", lambda e: w.destroy())

        w.update_idletasks()
        cx, cy = imlec_konumu()
        vx, vy, vw, vh = sanal_ekran()
        ww, wh = w.winfo_width(), w.winfo_height()
        w.geometry(f"+{min(max(cx - ww // 2, vx + 20), vx + vw - ww - 20)}"
                   f"+{min(max(cy - 80, vy + 20), vy + vh - wh - 20)}")
        w.focus_force()
        self.text.focus_set()
        self._guncelle_sayac()

    def _degisti(self, _e):
        self.text.edit_modified(False)
        self._guncelle_sayac()

    def _guncelle_sayac(self):
        self.sayac.configure(
            text=t("common.chars", n=len(self.text.get("1.0", "end-1c"))))

    def _kopyala(self):
        self.on_copy(self.text.get("1.0", "end-1c"))
        self.win.destroy()


# --------------------------------------------------------------------------
# Tepsi ikonu
# --------------------------------------------------------------------------
_ikon_onbellek = {}


def ikon_ciz(boyut=64):
    """Secim koseleri + ortada bir T. Olculer 64 piksel tabanina gore yazilip
    istenen boyuta olceklendi; .ico uretimi 256'ya kadar cikabilsin diye."""
    if boyut not in _ikon_onbellek:
        k = boyut / 64.0
        img = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        o = lambda v: v * k
        kalin = max(1, round(3 * k))
        d.rounded_rectangle((o(3), o(3), o(60), o(60)), radius=round(13 * k),
                            fill=(37, 99, 235, 255))
        for (x, y, dx, dy) in ((14, 14, 1, 1), (49, 14, -1, 1),
                               (14, 49, 1, -1), (49, 49, -1, -1)):
            d.line((o(x), o(y), o(x + 9 * dx), o(y)),
                   fill=(255, 255, 255, 235), width=kalin)
            d.line((o(x), o(y), o(x), o(y + 9 * dy)),
                   fill=(255, 255, 255, 235), width=kalin)
        govde = max(1, round(5 * k))
        d.line((o(22), o(27), o(42), o(27)), fill="white", width=govde)   # T
        d.line((o(32), o(27), o(32), o(46)), fill="white", width=govde)
        _ikon_onbellek[boyut] = img
    return _ikon_onbellek[boyut]


# --------------------------------------------------------------------------
# Uygulama
# --------------------------------------------------------------------------
HK_NORMAL, HK_DUZELT, HK_TEKRAR, HK_BIRIKTIR = 1, 2, 3, 4
HK_ANAHTAR = {HK_NORMAL: "kisayol", HK_DUZELT: "kisayol_duzelt",
              HK_TEKRAR: "kisayol_tekrar", HK_BIRIKTIR: "kisayol_biriktir"}
_MUTEX = None


class MetinKap:
    def __init__(self):
        # ayar_yukle() dosya yoksa varsayilanlari YAZIYOR, yani kendisinden
        # sonra CONFIG_PATH her zaman var. Ilk acilis kontrolu asagida, yukleme
        # sonrasinda yapiliyordu ve hep False cikiyordu: ilk kurulumda ayar
        # penceresi hic acilmiyor, kullanici tepsi ikonunu kendi bulmak zorunda
        # kaliyordu. Bu yuzden dosyaya yuklemeden ONCE bakiyoruz.
        ilk_acilis = not os.path.exists(CONFIG_PATH)
        self.cfg = ayar_yukle()
        ceviri.dili_ayarla(self.cfg["arayuz_dil"])
        self.ocr = Ocr()
        self.kuyruk = queue.Queue()
        self.gecmis = gecmis_yukle(self.cfg["gecmis_boyut"])
        self.son_metin = self.gecmis[0]["metin"] if self.gecmis else ""
        self.son_kutu = None
        self.biriktiriyor = False
        self.tampon = []
        self.onceki_pencere = None
        self._gecmis_sayac = 0
        self.mesgul = False
        self.tray = None
        self.pencere = None
        self.dinleyici = None
        self._tik = 0

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)

        self.dilleri_tazele()
        hatalar = self.kisayollari_yenile()

        threading.Thread(target=self.ocr.isin, daemon=True).start()
        threading.Thread(target=self._tepsi_baslat, daemon=True).start()
        self.root.after(40, self._kuyruk_isle)

        if not self.ocr.hazir:
            self.root.after(500, lambda: baloncuk(
                self.root, t("toast.no_winrt"), hata=True, sure=6000))
        elif ilk_acilis:
            self.root.after(300, self.arayuzu_ac)
        elif hatalar:
            self.root.after(500, lambda: baloncuk(
                self.root, t("toast.hk_failed", h="\n".join(hatalar.values())),
                hata=True, sure=7000))
        else:
            self.root.after(400, lambda: baloncuk(
                self.root, t("toast.ready", k=self.cfg["kisayol"],
                             d=self.cfg["dil"]), sure=2200))

    # -- arayuzun kullandigi yardimcilar ----------------------------------
    def ayar_yaz(self):
        ok = ayar_kaydet(self.cfg)
        self._menu_tazele()
        return ok

    def panoya(self, metin):
        return panoya_yaz(metin)

    def dilleri_tazele(self, ekstra=None):
        """ekstra: az once kurulan dil etiketi. Windows'un listesi bu surecte
        eskimis olabilir, o yuzden ayrica dogrudan sorulur."""
        self.diller = self.ocr.diller()
        if ekstra and ekstra not in self.diller and self.ocr.dil_var_mi(ekstra):
            self.diller.append(ekstra)
        if (self.cfg["dil"] != "oto" and self.cfg["dil"] not in self.diller
                and self.diller):
            self.cfg["dil"] = self.diller[0]
            ayar_kaydet(self.cfg)          # yoksa her acilista yeniden duzeltilir
        self._menu_tazele()
        return self.diller

    def yeniden_baslat(self):
        """Ayarlari yazip yeni bir kopya baslatir ve bu kopyayi kapatir.

        Windows OCR dil listesi surec basinda okundugu icin yeni kurulan bir dil
        ancak yeniden baslatinca gorunuyor."""
        ayar_kaydet(self.cfg)
        self._gecmis_yaz()
        global _MUTEX
        if _MUTEX:                       # yeni kopya tek-ornek kontrolune takilmasin
            k32 = ctypes.windll.kernel32
            k32.ReleaseMutex(ctypes.c_void_p(_MUTEX))
            k32.CloseHandle(ctypes.c_void_p(_MUTEX))
            _MUTEX = None
        try:
            import subprocess
            subprocess.Popen([self.pythonw_yolu(), self.betik_yolu()],
                             close_fds=True,
                             creationflags=0x00000008 | 0x08000000)  # DETACHED
        except Exception:
            _log("yeniden baslatma: " + traceback.format_exc())
        self.cikis()

    def arayuz_dilini_ayarla(self, kod):
        ceviri.dili_ayarla(kod)
        self.cfg["arayuz_dil"] = kod
        ayar_kaydet(self.cfg)
        self._menu_tazele()

    def kisayollari_yenile(self):
        """Dinleyiciyi durdurup yeni kisayollarla yeniden kurar.
        Bos liste donerse her sey yolunda demektir."""
        if self.dinleyici:
            self.dinleyici.durdur()
            self.dinleyici.join(timeout=2.0)
        self.dinleyici = KisayolDinleyici({
            HK_NORMAL: self.cfg["kisayol"],
            HK_DUZELT: self.cfg["kisayol_duzelt"],
            HK_TEKRAR: self.cfg["kisayol_tekrar"],
            HK_BIRIKTIR: self.cfg["kisayol_biriktir"]}, self.kuyruk)
        self.dinleyici.start()
        # {config_anahtari: kisayol} - hangi islevin kaydedilemedigi onemli:
        # tek bir cakisma yuzunden digerlerini degistirmek engellenmemeli.
        return {HK_ANAHTAR[hid]: combo for hid, combo in self.dinleyici.bekle()}

    def veri_klasoru(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        return DATA_DIR

    def betik_yolu(self):
        return os.path.abspath(__file__)

    def pythonw_yolu(self):
        w = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        return w if os.path.exists(w) else sys.executable

    def yollar(self):
        return [("about.f_settings", CONFIG_PATH), ("about.f_history", HISTORY_JSON),
                ("about.f_crop", LAST_CROP_PATH), ("about.f_log", LOG_PATH),
                ("about.f_source", self.betik_yolu())]

    def tk_ikon(self):
        return ImageTk.PhotoImage(ikon_ciz())

    def arayuzu_ac(self):
        try:
            if self.pencere is None or not self.pencere.win.winfo_exists():
                import arayuz
                self.pencere = arayuz.AyarPenceresi(self)
            else:
                self.pencere.goster()
        except Exception:
            _log("arayuz: " + traceback.format_exc())
            baloncuk(self.root, t("toast.ui_failed"), hata=True, sure=5000)

    def _arayuz_sekme(self, sekme):
        self.arayuzu_ac()
        if self.pencere:
            self.pencere.sekme_goster(sekme)

    # -- olay dongusu -----------------------------------------------------
    def _kuyruk_isle_bir_kez(self):
        """Kuyrugu bir kez bosaltir. Dongunun govdesi; testler de bunu cagirir."""
        try:
            while True:
                tip, veri = self.kuyruk.get_nowait()
                if tip == "hotkey":
                    if veri == HK_TEKRAR:
                        self.son_alani_yakala()
                    elif veri == HK_BIRIKTIR:
                        self.biriktirmeyi_degistir()
                    else:
                        self.yakala(duzelt=(veri == HK_DUZELT))
                elif tip == "cagir":
                    veri()
        except queue.Empty:
            pass
        except Exception as e:
            _log("kuyruk: " + traceback.format_exc())
            baloncuk(self.root, str(e), hata=True, sure=4000)

    def _kuyruk_isle(self):
        self._kuyruk_isle_bir_kez()

        # ikinci kez baslatilmaya calisilirsa bayrak birakilir; arayuzu ac
        self._tik += 1
        if self._tik % 12 == 0 and os.path.exists(SHOW_FLAG):
            try:
                os.remove(SHOW_FLAG)
            except OSError:
                pass
            self.arayuzu_ac()

        self.root.after(40, self._kuyruk_isle)

    def _tk_de_calistir(self, fn):
        """Tepsi thread'inden tkinter thread'ine is aktarir."""
        self.kuyruk.put(("cagir", fn))

    # -- yakalama ---------------------------------------------------------
    def yakala(self, duzelt=False):
        if self.mesgul:
            return
        if not self.ocr.hazir:
            return baloncuk(self.root, t("toast.no_ocr"), hata=True)
        self.mesgul = True
        self.onceki_pencere = _u32.GetForegroundWindow()
        try:
            SecimKatmani(self.root, self.cfg["karartma"],
                         lambda r: self._secim_bitti(r, duzelt), self.son_kutu)
        except Exception:
            self.mesgul = False
            _log("secim: " + traceback.format_exc())
            baloncuk(self.root, t("toast.no_grab"), hata=True)

    def son_alani_yakala(self, duzelt=False):
        """Secim ekrani acmadan, en son secilen bolgeyi yeniden okur."""
        if self.mesgul:
            return
        if not self.son_kutu:
            return baloncuk(self.root, t("toast.no_last_area"), hata=True,
                            sure=2500)
        if not self.ocr.hazir:
            return baloncuk(self.root, t("toast.no_ocr"), hata=True)
        self.mesgul = True
        self.onceki_pencere = _u32.GetForegroundWindow()
        try:
            _, _, vw, vh = sanal_ekran()
            x0, y0, x1, y1 = self.son_kutu
            kutu = (max(0, min(x0, vw - 1)), max(0, min(y0, vh - 1)),
                    min(x1, vw), min(y1, vh))
            if kutu[2] - kutu[0] < 5 or kutu[3] - kutu[1] < 5:
                self.mesgul = False
                return baloncuk(self.root, t("toast.no_last_area"), hata=True)
            try:
                kirpim = bolge_yakala(kutu)
            except Exception as e:                # GDI yolu tutmazsa PIL'e don
                _log(f"bolge yakalama basarisiz, tam ekrana donuldu: {e}")
                kirpim = ekrani_yakala().crop(kutu)
        except Exception:
            self.mesgul = False
            _log("son alan: " + traceback.format_exc())
            return baloncuk(self.root, t("toast.no_grab"), hata=True)
        self.mesgul = False
        self._isle(kirpim, duzelt)

    def _secim_bitti(self, sonuc, duzelt):
        self.mesgul = False
        if sonuc is None:
            return
        kirpim, shift, kutu = sonuc
        ilk_kutu = self.son_kutu is None
        self.son_kutu = kutu
        if ilk_kutu:
            self._menu_tazele()            # menu ogesi artik etkin olmali
        self.root.after(1, lambda: self._isle(kirpim, duzelt or shift))

    def _olcekle(self, img):
        """Olcek en etkili dogruluk kazanci; kontrast/gri donusumu zarar veriyor.

        6 font x 6 punto, sayi ve noktalama iceren metinle olculdu:
        x2.5 %90.18, x3 %89.35, x1 %80.15. x3 buyuk puntoda geri gidiyor ve
        sayilari bozuyor ("%18" -> "9618"), o yuzden x2.5. Ilk gecisten satir
        yuksekligini olcup yeniden okuyan adaptif surum de denendi (%89.88):
        ek karmasiklik kazanc getirmedi."""
        if not self.cfg["buyutme"]:
            return img
        h = img.height
        s = 2.5 if h < 500 else 1.5 if h < 1200 else 1.0
        if max(img.width, img.height) * s > 5000:
            s = 5000 / max(img.width, img.height)
        if s <= 1.05:
            return img
        return img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)

    def _isle(self, kirpim, duzelt):
        t0 = time.perf_counter()
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            kirpim.save(LAST_CROP_PATH)
        except Exception:
            pass

        img = self._olcekle(kirpim)
        dil = self.cfg["dil"]
        mod = self.cfg["satir_modu"]
        bant = self.cfg["bant_birlestir"] and mod not in KUTU_MODLARI
        try:
            if dil == "oto":
                en_iyi, en_skor = [], -1
                for tag in self.diller:
                    try:
                        p = self.ocr.parcalar(img, tag, bant)
                    except Exception:
                        continue
                    skor = sum(len(x[0]) for x in p)
                    if skor > en_skor:
                        en_iyi, en_skor = p, skor
                parcalar = en_iyi
            else:
                parcalar = self.ocr.parcalar(img, dil, bant)
        except Exception as e:
            _log("ocr: " + traceback.format_exc())
            return baloncuk(self.root, t("toast.ocr_fail", e=e), hata=True,
                            sure=4000)

        metin = bicimlendir(parcalar, mod)
        ms = (time.perf_counter() - t0) * 1000

        if not metin.strip():
            return baloncuk(self.root, t("toast.no_text"), hata=True, sure=3500)

        if duzelt:
            DuzeltPenceresi(self.root, metin, self._kopyala_ve_bildir)
        else:
            self._kopyala_ve_bildir(metin, ms)

    # -- biriktirme modu --------------------------------------------------
    def biriktirmeyi_degistir(self):
        """Acikken her yakalama panoya degil tampona gider; kapatilinca hepsi
        tek seferde panoya yazilir. Cok sayfali bir belgeyi tek yapistirmada
        aktarmak icin."""
        if self.biriktiriyor:
            return self.biriktirmeyi_bitir()
        self.biriktiriyor = True
        self.tampon = []
        self._menu_tazele()
        baloncuk(self.root, t("toast.stack_on", k=self.cfg["kisayol_biriktir"]),
                 sure=2600)

    def biriktirmeyi_bitir(self):
        self.biriktiriyor = False
        parcalar = self.tampon
        self.tampon = []
        self._menu_tazele()
        if not parcalar:
            return baloncuk(self.root, t("toast.stack_empty"), sure=2000)
        metin = self.cfg["biriktir_ayirici"].join(parcalar)
        self.son_metin = metin
        self.gecmise_ekle(metin)
        if not panoya_yaz(metin):
            return baloncuk(self.root, t("toast.no_clipboard"), hata=True)
        if self.cfg["geri_yapistir"]:
            try:
                pencereye_yapistir(self.onceki_pencere)
            except Exception as e:
                _log(f"geri yapistirma: {e}")
        baloncuk(self.root, t("toast.stack_done", n=len(parcalar),
                              c=len(metin)), sure=3000)

    def _kopyala_ve_bildir(self, metin, ms=None):
        if not metin:
            return
        if self.biriktiriyor:
            self.tampon.append(metin)
            self._menu_tazele()
            return baloncuk(self.root, t("toast.stack_added", n=len(self.tampon),
                                         k=self.cfg["kisayol_biriktir"]),
                            sure=1800)
        ok = panoya_yaz(metin)
        self.son_metin = metin
        self.gecmise_ekle(metin)
        if not ok:
            return baloncuk(self.root, t("toast.no_clipboard"), hata=True)
        yapistirildi = False
        if self.cfg["geri_yapistir"]:
            try:
                yapistirildi = pencereye_yapistir(self.onceki_pencere)
            except Exception as e:
                _log(f"geri yapistirma: {e}")
        if self.cfg["bildirim"]:
            n, l = len(metin), metin.count("\n") + 1
            bilgi = (t("toast.info_ms", n=n, l=l, ms=f"{ms:.0f}") if ms is not None
                     else t("toast.info", n=n, l=l))
            onizleme = " ".join(metin.split())
            if len(onizleme) > 60:
                onizleme = onizleme[:57] + "…"
            baloncuk(self.root, t("toast.pasted" if yapistirildi else "toast.copied",
                                  bilgi=bilgi, onizleme=onizleme))

    # -- gecmis -----------------------------------------------------------
    # Kayitlar indeksle degil kimlikle adreslenir: yeni yakalama listenin basina
    # eklendigi icin indeksler kayiyor ve acik pencerede duzenlenen kayit yanlis
    # satirin uzerine yaziliyordu.
    def _yeni_kimlik(self):
        self._gecmis_sayac += 1
        return f"{int(time.time() * 1000):x}-{self._gecmis_sayac}"

    def gecmis_bul(self, kimlik):
        for i, kayit in enumerate(self.gecmis):
            if kayit.get("id") == kimlik:
                return i
        return -1

    def gecmise_ekle(self, metin):
        self.gecmis.insert(0, {"metin": metin, "id": self._yeni_kimlik(),
                               "zaman": time.strftime("%Y-%m-%d %H:%M:%S")})
        del self.gecmis[self.cfg["gecmis_boyut"]:]
        self._gecmis_yaz()
        if self.cfg["gecmis_kaydet"]:
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(HISTORY_TXT, "a", encoding="utf-8") as f:
                    f.write(f"\n===== {self.gecmis[0]['zaman']} =====\n{metin}\n")
            except Exception as e:
                _log(f"gecmis.txt: {e}")
        self._gecmis_degisti()

    def gecmis_guncelle(self, kimlik, metin):
        i = self.gecmis_bul(kimlik)
        if i < 0:
            return False
        self.gecmis[i]["metin"] = metin
        if i == 0:
            self.son_metin = metin
        self._gecmis_yaz()
        self._menu_tazele()
        return True

    def gecmis_sil(self, kimlik):
        i = self.gecmis_bul(kimlik)
        if i < 0:
            return False
        del self.gecmis[i]
        self.son_metin = self.gecmis[0]["metin"] if self.gecmis else ""
        self._gecmis_yaz()
        self._menu_tazele()
        return True

    def gecmis_temizle(self):
        """Diski de temizler. Temizlenemezse False doner — arayuz 'temizlendi'
        demeden once buna bakmali, cunku kullanici sildigini saniyor."""
        self.gecmis = []
        self.son_metin = ""
        ok = self._gecmis_dosyalarini_sil()
        self._menu_tazele()
        return ok

    def _gecmis_dosyalarini_sil(self):
        """Silinemeyen dosyanin uzerine bos liste yazmayi dener.

        Baska bir surec (yedekleme, virus tarayici, dosyayi acik birakan bir
        editor) dosyayi tutuyorsa os.remove WinError 32 veriyordu ve gecmis
        diskte kaliyordu: surec duzgun kapanmazsa bir sonraki acilista butun
        kayitlar geri geliyor. Kullanici acisindan bu, silinmedigi soylenmemis
        bir veri; icerigi bosaltmak en azindan metni birakmiyor."""
        tamam = True
        for yol in (HISTORY_JSON, HISTORY_TXT):
            try:
                os.remove(yol)
            except FileNotFoundError:
                pass
            except OSError as e:
                _log(f"gecmis silinemedi ({yol}): {e}")
                try:
                    with open(yol, "w", encoding="utf-8") as f:
                        f.write("[]" if yol == HISTORY_JSON else "")
                except OSError as e2:
                    _log(f"gecmis bosaltilamadi da ({yol}): {e2}")
                    tamam = False
        return tamam

    def _gecmis_yaz(self):
        if not self.cfg["gecmis_kaydet"]:
            # Kapatildiysa diskte kalmis kayitlar sessizce geri yuklenmesin
            self._gecmis_dosyalarini_sil()
            return
        try:
            _atomik_json_yaz(HISTORY_JSON, self.gecmis, girinti=1)
        except Exception as e:
            _log(f"gecmis.json: {e}")

    def _gecmis_degisti(self):
        if self.pencere is not None:
            try:
                if self.pencere.win.winfo_exists():
                    if self.pencere.win.winfo_viewable():
                        self.pencere.sekme_goster(self.pencere.aktif)
                    else:
                        # Simge durumunda/gizliyken cizmeye gerek yok, ama geri
                        # acildiginda tazelensin diye isaretliyoruz.
                        self.pencere._bayat = True
            except Exception:
                pass
        self._menu_tazele()

    # -- tepsi ------------------------------------------------------------
    def _menu_olustur(self):
        """pystray menu nesnesi sabittir; oge listesi degisince (dil kuruldu,
        gecmise kayit eklendi) menu yeniden olusturulup atanmali."""
        from pystray import Menu, MenuItem as MI
        import diller as dl

        def dil_sec(tag):
            def f(icon, item):
                self.cfg["dil"] = tag
                self.ayar_yaz()
            return f

        def mod_sec(mod):
            def f(icon, item):
                self.cfg["satir_modu"] = mod
                self.ayar_yaz()
            return f

        def ayar_degistir(anahtar):
            def f(icon, item):
                self.cfg[anahtar] = not self.cfg[anahtar]
                self.ayar_yaz()
            return f

        def gecmis_menu():
            if not self.gecmis:
                return Menu(MI(t("common.empty"), None, enabled=False))
            ogeler = []
            for i, kayit in enumerate(self.gecmis[:12]):
                et = " ".join(kayit["metin"].split())
                et = (et[:45] + "…") if len(et) > 45 else et
                ogeler.append(MI(f"{i + 1}. {et}",
                                 (lambda m: lambda i_, it_: panoya_yaz(m))(
                                     kayit["metin"])))
            return Menu(*ogeler)

        dil_ogeleri = [MI(t("lang.auto"), dil_sec("oto"),
                          checked=lambda it: self.cfg["dil"] == "oto", radio=True),
                       Menu.SEPARATOR]
        for tag in self.diller:
            dil_ogeleri.append(
                MI(f"{dl.gorunen_ad(tag)}  ({tag})", dil_sec(tag),
                   checked=(lambda x: lambda it: self.cfg["dil"] == x)(tag),
                   radio=True))
        dil_ogeleri += [Menu.SEPARATOR,
                        MI(t("tray.download_lang"),
                           lambda i, it: self._tk_de_calistir(
                               lambda: self._arayuz_sekme("diller")))]

        return Menu(
            MI(t("tray.settings"),
               lambda i, it: self._tk_de_calistir(self.arayuzu_ac), default=True),
            Menu.SEPARATOR,
            MI(t("tray.capture", k=self.cfg["kisayol"]),
               lambda i, it: self._tk_de_calistir(lambda: self.yakala(False))),
            MI(t("tray.capture_edit", k=self.cfg["kisayol_duzelt"]),
               lambda i, it: self._tk_de_calistir(lambda: self.yakala(True))),
            MI(t("tray.repeat", k=self.cfg["kisayol_tekrar"]),
               lambda i, it: self._tk_de_calistir(self.son_alani_yakala),
               enabled=bool(self.son_kutu)),
            MI(t("tray.stack_finish", n=len(self.tampon))
               if self.biriktiriyor
               else t("tray.stack_start", k=self.cfg["kisayol_biriktir"]),
               lambda i, it: self._tk_de_calistir(self.biriktirmeyi_degistir)),
            Menu.SEPARATOR,
            MI(t("tray.language"), Menu(*dil_ogeleri)),
            MI(t("tray.line_mode"), Menu(*[
                MI(t(SATIR_MODU_ANAHTARI[m]), mod_sec(m),
                   checked=(lambda x: lambda it: self.cfg["satir_modu"] == x)(m),
                   radio=True) for m in SATIR_MODLARI])),
            MI(t("set.upscale"), ayar_degistir("buyutme"),
               checked=lambda it: self.cfg["buyutme"]),
            MI(t("set.bandmerge"), ayar_degistir("bant_birlestir"),
               checked=lambda it: self.cfg["bant_birlestir"]),
            MI(t("set.toast"), ayar_degistir("bildirim"),
               checked=lambda it: self.cfg["bildirim"]),
            Menu.SEPARATOR,
            MI(t("tray.copy_last"),
               lambda i, it: panoya_yaz(self.son_metin),
               enabled=bool(self.son_metin)),
            MI(t("tray.history"), gecmis_menu()),
            Menu.SEPARATOR,
            MI(t("tray.quit"), lambda i, it: self._tk_de_calistir(self.cikis)),
        )

    def _menu_tazele(self):
        if not self.tray:
            return
        try:
            self.tray.title = f"{APP_NAME} — {self.cfg['kisayol']}"
            self.tray.menu = self._menu_olustur()
            self.tray.update_menu()
        except Exception as e:
            _log(f"menu tazeleme: {e}")

    def _tepsi_baslat(self):
        try:
            import pystray
            self.tray = pystray.Icon(
                APP_NAME, ikon_ciz(),
                f"{APP_NAME} — {self.cfg['kisayol']}", self._menu_olustur())
            self.tray.run()
        except Exception:
            _log("tepsi: " + traceback.format_exc())

    # -- yasam dongusu ----------------------------------------------------
    def cikis(self):
        ayar_kaydet(self.cfg)
        self._gecmis_yaz()
        try:
            os.remove(SHOW_FLAG)
        except OSError:
            pass
        try:
            if self.pencere and self.pencere.win.winfo_exists():
                self.pencere.win.destroy()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        if self.dinleyici:
            self.dinleyici.durdur()
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def calistir(self):
        self.root.mainloop()


# --------------------------------------------------------------------------
# Gecmis dosyasi
# --------------------------------------------------------------------------
def gecmis_yukle(limit):
    try:
        with open(HISTORY_JSON, encoding="utf-8") as f:
            veri = json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        _log(f"gecmis.json okunamadi: {e}")
        return []
    temiz = []
    for sira, kayit in enumerate(veri if isinstance(veri, list) else []):
        if isinstance(kayit, dict) and isinstance(kayit.get("metin"), str):
            temiz.append({"metin": kayit["metin"],
                          "zaman": str(kayit.get("zaman", "")),
                          "id": str(kayit.get("id") or f"eski-{sira}")})
        elif isinstance(kayit, str):                     # eski bicim
            temiz.append({"metin": kayit, "zaman": "", "id": f"eski-{sira}"})
    return temiz[:limit]


# --------------------------------------------------------------------------
# Tek ornek
# --------------------------------------------------------------------------
def tek_ornek():
    """Ikinci kopya acilmasin. Zaten calisan varsa ona 'arayuzu ac' de."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = ctypes.c_void_p
    k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    global _MUTEX
    _MUTEX = k32.CreateMutexW(None, True, f"Local\\{APP_NAME}_mutex")
    if ctypes.get_last_error() != 183:                   # ERROR_ALREADY_EXISTS
        return True
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        open(SHOW_FLAG, "w").close()                     # calisan ornek bunu goruyor
    except OSError:
        pass
    return False


def kendini_sina():
    """--selftest: pencere acmadan temel yetenekleri dogrular.

    Paketlenmis bir exe'nin gercekten calistigini anlamanin en hizli yolu:
    OCR motoru yuklendi mi, dil var mi, bir goruntuden metin okuyabiliyor mu,
    panoya yazabiliyor mu. CI de bunu kullanir."""
    print(f"{APP_NAME} {__version__} — kendini sinama")
    sorun = []

    ocr = Ocr()
    if not ocr.hazir:
        sorun.append(f"OCR modulleri yuklenemedi: {ocr._import_error}")
        print("  [X] OCR motoru")
    else:
        print("  [OK] OCR motoru yuklendi")
        diller = ocr.diller()
        if diller:
            print(f"  [OK] {len(diller)} OCR dili: {', '.join(diller)}")
        else:
            sorun.append("Hic OCR dili kurulu degil")
            print("  [X] OCR dili yok")

        if diller:
            # Sozluk destekli motor uydurma kelimelerde tokezliyor; sinama
            # metni sade ve rakam agirlikli, dil de mumkunse Ingilizce.
            dil = next((d for d in diller if d.lower().startswith("en")),
                       diller[0])
            BEKLENEN = "Test 12345 ABC"
            try:
                from PIL import ImageDraw, ImageFont
                img = Image.new("RGB", (460, 80), "white")
                d = ImageDraw.Draw(img)
                try:
                    f = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 32)
                except OSError:
                    f = ImageFont.load_default()
                d.text((14, 18), BEKLENEN, font=f, fill="black")
                buyuk = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
                okunan = " ".join(ocr.satirlar(buyuk, dil)).strip()
                if "12345" in okunan and "Test" in okunan:
                    print(f"  [OK] OCR okudu ({dil}): {okunan!r}")
                else:
                    sorun.append(f"OCR beklenen metni okumadi: {okunan!r}")
                    print(f"  [X] OCR ciktisi ({dil}): {okunan!r}")
            except Exception as e:
                sorun.append(f"OCR denemesi patladi: {e}")
                print(f"  [X] OCR denemesi: {e}")

    # Pano kullanicinin calisan hafizasi. Sinama onu ezip birakiyordu: panoda
    # ne varsa (sifre, link, yarim kalmis bir metin) gidiyordu. Once okuyup
    # sonra geri koyuyoruz. Metin disi bir icerik (resim, dosya) geri
    # konulamiyor; o durumu sessiz gecmek yerine yaziyoruz.
    try:
        onceki = panodan_metin_oku()
        if panoya_yaz(f"selftest-{time.time():.0f}"):
            print("  [OK] panoya yazildi")
        else:
            sorun.append("Panoya yazilamadi")
            print("  [X] panoya yazilamadi")
        if onceki:
            panoya_yaz(onceki)
            print("  [OK] panonun eski icerigi geri konuldu")
        else:
            panoyu_bosalt()
            print("  [!]  panoda metin yoktu; metin disi icerik geri konulamaz")
    except Exception as e:
        sorun.append(f"Pano: {e}")
        print(f"  [X] pano: {e}")

    try:
        ekran = sanal_ekran()
        print(f"  [OK] sanal ekran {ekran[2]}x{ekran[3]}")
    except Exception as e:
        sorun.append(f"Ekran olculemedi: {e}")
        print(f"  [X] ekran: {e}")

    print()
    if sorun:
        print("SONUC: SORUN VAR")
        for s in sorun:
            print("  -", s)
        return 1
    print("SONUC: her sey calisiyor")
    return 0


def konsola_baglan():
    """Paketlenmis exe --windowed derlendigi icin stdout hicbir yere gitmiyor.

    --selftest ve --version'in tum anlami ciktilarini okumak; cagiran komut
    isteminin konsoluna baglanmazsak kullanici sadece cikis kodunu goruyor.
    Konsol yoksa (cift tiklama) sessizce vazgeciyoruz.
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        if not ctypes.windll.kernel32.AttachConsole(-1):   # ATTACH_PARENT_PROCESS
            return
        for ad in ("stdout", "stderr"):
            try:
                setattr(sys, ad, open("CONOUT$", "w", encoding="utf-8",
                                      errors="replace", buffering=1))
            except OSError:
                pass
    except Exception:
        pass


def main():
    if "--selftest" in sys.argv:
        konsola_baglan()
        sys.exit(kendini_sina())
    if "--version" in sys.argv or "-V" in sys.argv:
        konsola_baglan()
        print(f"{APP_NAME} {__version__}")
        sys.exit(0)
    if not tek_ornek():
        ceviri.dili_ayarla(ayar_yukle()["arayuz_dil"])
        _u32.MessageBoxW(None, t("msg.running"), APP_NAME, 0x40)
        return
    try:
        MetinKap().calistir()
    except Exception:
        _log("main: " + traceback.format_exc())
        try:
            _u32.MessageBoxW(None, t("msg.start_failed", p=LOG_PATH), APP_NAME, 0x10)
        except Exception:
            pass


if __name__ == "__main__":
    main()
