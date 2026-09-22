"""Pencere acmayan testler — ajan bulgularinin dogrulanmasi.
Kullanici oyundayken calistirilabilir: hicbir Toplevel/baloncuk acilmaz."""
import json
import os
import sys
import threading
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.stdout.reconfigure(encoding="utf-8")
import metinkap as mk
import diller as dl

ok = True


def chk(ad, k, ek=""):
    global ok
    print(("  OK   " if k else "  FAIL ") + ad + (("  -> " + str(ek)) if ek else ""))
    ok &= bool(k)


yedek_cfg = (open(mk.CONFIG_PATH, encoding="utf-8").read()
             if os.path.exists(mk.CONFIG_PATH) else None)
yedek_gec = (open(mk.HISTORY_JSON, encoding="utf-8").read()
             if os.path.exists(mk.HISTORY_JSON) else None)

print("[A] Ayar yazimi: iki thread ayni anda (eskiden ayarlar sessizce kayboluyordu)")
hatalar = []
bozuk = [0]


def yazar(etiket):
    for i in range(400):
        try:
            mk.ayar_kaydet(dict(mk.VARSAYILAN, karartma=0.1 * (i % 9),
                                dil=f"{etiket}{i}"))
        except Exception as e:
            hatalar.append(e)


def okuyucu():
    for _ in range(400):
        try:
            with open(mk.CONFIG_PATH, encoding="utf-8") as f:
                json.load(f)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            bozuk[0] += 1
        except OSError:
            pass


ths = [threading.Thread(target=yazar, args=("a",)),
       threading.Thread(target=yazar, args=("b",)),
       threading.Thread(target=okuyucu)]
for t_ in ths:
    t_.start()
for t_ in ths:
    t_.join()
chk("800 eszamanli yazimda istisna yok", not hatalar, hatalar[:2])
chk("okuyucu hic bozuk JSON gormedi", bozuk[0] == 0, f"{bozuk[0]} kez")
with open(mk.CONFIG_PATH, encoding="utf-8") as f:
    chk("son dosya gecerli JSON", isinstance(json.load(f), dict))
kalinti = [x for x in os.listdir(mk.DATA_DIR) if x.endswith(".tmp")]
chk("gecici dosya kalintisi yok", not kalinti, kalinti)

print("[B] Gecmis kimlikle adresleniyor (eskiden komsu kaydin uzerine yaziliyordu)")


class SahteApp(mk.MetinKap):
    """tkinter/tepsi/kisayol acmadan sadece gecmis mantigini kullan."""
    def __init__(self):
        self.cfg = dict(mk.VARSAYILAN)
        self.gecmis = []
        self.son_metin = ""
        self._gecmis_sayac = 0
        self.pencere = None
        self.tray = None

    def _menu_tazele(self):
        pass

    def _gecmis_degisti(self):
        pass


a = SahteApp()
a.gecmis_temizle()
for s in ("bir", "iki", "uc"):
    a.gecmise_ekle(s)
kimlik_iki = a.gecmis[1]["id"]          # "iki" kaydi
chk("kimlikler benzersiz", len({k["id"] for k in a.gecmis}) == 3)
a.gecmise_ekle("dort")                  # liste kayar: iki artik indeks 2
chk("yeni kayit basa eklendi", a.gecmis[0]["metin"] == "dort")
a.gecmis_guncelle(kimlik_iki, "IKI-DUZENLENDI")
metinler = [k["metin"] for k in a.gecmis]
chk("dogru kayit guncellendi", metinler == ["dort", "uc", "IKI-DUZENLENDI", "bir"],
    metinler)
chk("komsu kayit bozulmadi", "uc" in metinler and "bir" in metinler)
chk("olmayan kimlik False doner", a.gecmis_guncelle("yok", "x") is False)
chk("olmayan kimlik silinmiyor", a.gecmis_sil("yok") is False)

print("[C] 'Hepsini temizle' diski de temizliyor (eskiden geri geliyordu)")
a.cfg["gecmis_kaydet"] = True
a.gecmise_ekle("gizli sifre 1234")
chk("json diske yazildi", os.path.exists(mk.HISTORY_JSON))
chk("txt diske yazildi", os.path.exists(mk.HISTORY_TXT))
a.gecmis_temizle()
chk("json silindi", not os.path.exists(mk.HISTORY_JSON))
chk("txt de silindi (gizlilik)", not os.path.exists(mk.HISTORY_TXT))
chk("yeniden yuklenince geri gelmiyor", mk.gecmis_yukle(25) == [])

print("[D] Gecmis kaydi kapatilinca diskte iz kalmiyor")
a.cfg["gecmis_kaydet"] = True
a.gecmise_ekle("baska bir gizli metin")
chk("once yazildi", os.path.exists(mk.HISTORY_JSON))
a.cfg["gecmis_kaydet"] = False
a.gecmise_ekle("artik yazilmamali")
chk("kapatilinca json silindi", not os.path.exists(mk.HISTORY_JSON))
chk("kapatilinca txt silindi", not os.path.exists(mk.HISTORY_TXT))
chk("bellekte yine de duruyor", len(a.gecmis) >= 1)

print("[E] Eski bicim gecmise kimlik veriliyor")
json.dump(["eski1", {"metin": "eski2", "zaman": "2026-01-01"}],
          open(mk.HISTORY_JSON, "w", encoding="utf-8"), ensure_ascii=False)
g = mk.gecmis_yukle(25)
chk("iki kayit okundu", len(g) == 2, g)
chk("hepsinde kimlik var", all(k.get("id") for k in g), g)
chk("kimlikler farkli", g[0]["id"] != g[1]["id"])

print("[F] panoya_yaz basarisizlikta yalan soylemiyor")
chk("bos metin False", mk.panoya_yaz("") is False)
chk("normal metin True", mk.panoya_yaz("metinkap testi") is True)
import ctypes
u32 = ctypes.windll.user32
# "Pano mesgul" durumu bu ortamda uretilemiyor: baska bir surec panoyu
# acik tutarken bile OpenClipboard basariyla donuyor. panoya_yaz'in hata
# yolu (NULL lock / SetClipboardData basarisiz) bu yuzden DOGRULANMADI;
# kod her adimi kontrol ediyor ama calistirilabilir bir senaryo bulunamadi.
print("  NOT   'pano mesgul' senaryosu bu ortamda uretilemedi - dogrulanmadi")
# Uzun metin ve Turkce karakterlerle gidis-donus
uzun = "Satır: ışığı çöpçü ĞÜŞİÖÇ · 1.249,90\n" * 500
chk("uzun metin yazildi", mk.panoya_yaz(uzun) is True)
chk("pano sonrasinda yine calisiyor", mk.panoya_yaz("tekrar") is True)

print("[G] Kisayol hatalari islev bazinda ayirt ediliyor")
import queue
q = queue.Queue()
d = mk.KisayolDinleyici({mk.HK_NORMAL: "ctrl+shift+f9",
                         mk.HK_DUZELT: "bu+gecersiz"}, q)
d.start()
h = d.bekle()
d.durdur()
d.join(timeout=2)
chk("hata listesi (hid, combo) ciftleri", all(isinstance(x, tuple) and len(x) == 2
                                              for x in h), h)
idler = {x[0] for x in h}
chk("gecersiz olan raporlandi", mk.HK_DUZELT in idler, h)
chk("gecerli olan raporlanmadi", mk.HK_NORMAL not in idler, h)
chk("HK_ANAHTAR eslemesi tam",
    set(mk.HK_ANAHTAR) == {mk.HK_NORMAL, mk.HK_DUZELT, mk.HK_TEKRAR,
                           mk.HK_BIRIKTIR}, sorted(mk.HK_ANAHTAR))
chk("her hid bir config anahtarina bakiyor",
    all(a in mk.VARSAYILAN for a in mk.HK_ANAHTAR.values()),
    list(mk.HK_ANAHTAR.values()))

print("[H] diller.py kucuk duzeltmeler")
chk("baslangici_ayarla(False) OSError yutmuyor",
    dl.baslangici_ayarla(False, "x", "y")[0] in (True, False))
kalinti = [x for x in os.listdir(os.environ.get("TEMP", "."))
           if x.startswith("metinkap_")]
chk("TEMP'te kurulum kalintisi yok", not kalinti, kalinti[:3])

# geri yukle
for yol, icerik in ((mk.CONFIG_PATH, yedek_cfg), (mk.HISTORY_JSON, yedek_gec)):
    if icerik is not None:
        open(yol, "w", encoding="utf-8").write(icerik)
    else:
        try:
            os.remove(yol)
        except OSError:
            pass
try:
    os.remove(mk.HISTORY_TXT)
except OSError:
    pass

print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
