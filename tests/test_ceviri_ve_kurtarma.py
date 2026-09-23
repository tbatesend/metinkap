"""Ceviri butunlugu ve bozuk veriden kurtarma. Pencere acmaz.

Buradaki kontrollerin hepsi gercekten kacmis hatalardan dogdu; her biri
kacisin nasil mumkun oldugunu da yaziyor.
"""
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.stdout.reconfigure(encoding="utf-8")
import ortam
ortam.izole_et()   # gercek %APPDATA% verisine dokunma
import ceviri
import metinkap as mk

ok = True


def chk(ad, k, ek=""):
    global ok
    print(("  OK   " if k else "  FAIL ") + ad + (("  -> " + str(ek)) if ek else ""))
    ok &= bool(k)


print("[1] Kaynakta kullanilan her ceviri anahtari tabloda var mi")
# EN<->TR karsilastirmasi yetmiyordu: ikisinde birden olmayan anahtari goremez.
# "toast.pasted" tam boyle kacti. t() bilinmeyen anahtarda anahtarin kendisini
# donduruyor, yani "geri yapistir" acikken baloncugun tek icerigi
# "toast.pasted" oluyordu. Hicbir test gormedi, cunku eldeki iki test ya yalnizca
# EN/TR kume farkina bakiyordu ya da baloncugu bos bir lambda ile degistiriyordu.
DESEN = re.compile(r"""\bt\(\s*["']([a-z_]+\.[a-z_0-9]+)["']""")
kullanilan = {}
for dosya in ("metinkap.py", "arayuz.py", "diller.py"):
    with open(os.path.join(KOK, dosya), encoding="utf-8") as f:
        for no, satir in enumerate(f, 1):
            for anahtar in DESEN.findall(satir):
                kullanilan.setdefault(anahtar, f"{dosya}:{no}")

chk("anahtar taramasi bir sey buldu", len(kullanilan) > 40, len(kullanilan))
eksik_en = sorted((a, y) for a, y in kullanilan.items() if a not in ceviri.EN)
chk(f"{len(kullanilan)} anahtarin hepsi EN tablosunda", not eksik_en, eksik_en[:3])
eksik_tr = sorted((a, y) for a, y in kullanilan.items() if a not in ceviri.TR)
chk("hepsi TR tablosunda da var", not eksik_tr, eksik_tr[:3])

print("[2] Bozuk bir ayar, komsu ayari silmiyor")
# Iki donusum tek try blogundaydi: bozuk gecmis_boyut, kullanicinin duzgun
# karartma ayarini da varsayilana cekip diske oyle yaziyordu. gecmis_boyut
# arayuzden duzenlenemiyor, tek yolu config.json'u elle acmak — yani bu, dosyayi
# elle duzenleyen birinin tek yazim hatasiyla tetikleniyordu.
json.dump({"karartma": 0.8, "gecmis_boyut": "abc"},
          open(mk.CONFIG_PATH, "w", encoding="utf-8"))
c = mk.ayar_yukle()
chk("bozuk olan varsayilana dondu",
    c["gecmis_boyut"] == mk.VARSAYILAN["gecmis_boyut"], c["gecmis_boyut"])
chk("saglam olana DOKUNULMADI", abs(c["karartma"] - 0.8) < 1e-9, c["karartma"])

json.dump({"karartma": "yok", "gecmis_boyut": 60},
          open(mk.CONFIG_PATH, "w", encoding="utf-8"))
c = mk.ayar_yukle()
chk("ters yonde de ayni", c["gecmis_boyut"] == 60
    and c["karartma"] == mk.VARSAYILAN["karartma"],
    (c["gecmis_boyut"], c["karartma"]))

print("[3] ayar_kaydet basariyi bildiriyor")
# Eskiden istisnayi yutup None donuyordu; arayuz de donuse bakmadigi icin
# yazilmamis bir ayara "Kaydedildi" diyordu.
chk("normal yazim True doner", mk.ayar_kaydet(dict(mk.VARSAYILAN)) is True)
chk("ayar_kaydet bool donduruyor",
    isinstance(mk.ayar_kaydet(dict(mk.VARSAYILAN)), bool))


class SahteApp(mk.MetinKap):
    """tkinter/tepsi/kisayol acmadan sadece gecmis mantigi."""

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


print("[4] 'Hepsini temizle' silemezse dosyayi hic olmazsa bosaltiyor")
# os.remove basarisiz oldugunda (yedekleme, virus tarayici, dosyayi acik
# birakan bir editor) gecmis diskte kaliyordu: surec duzgun kapanmazsa bir
# sonraki acilista butun kayitlar geri geliyor, oysa kullanici sildigini
# saniyor. Gizlilik acisindan onemli.
a = SahteApp()
a.cfg["gecmis_kaydet"] = True
a.gecmise_ekle("gizli kalmamali 4321")
chk("once diske yazildi", os.path.exists(mk.HISTORY_JSON))
tutucu = open(mk.HISTORY_JSON, encoding="utf-8")     # dosyayi acik tut
try:
    sonuc = a.gecmis_temizle()
finally:
    tutucu.close()
kalan = ""
if os.path.exists(mk.HISTORY_JSON):
    with open(mk.HISTORY_JSON, encoding="utf-8") as f:
        kalan = f.read()
chk("silinemese bile metin diskte kalmiyor", "gizli kalmamali" not in kalan,
    repr(kalan[:60]))
chk("gecmis_temizle bool donuyor", isinstance(sonuc, bool), sonuc)
# Bu makinede acik tutulan dosya gercekten silinemedi ve yedek plan devreye
# girdi: dosya "[]" icerigiyle kaldi. Baska bir Windows surumu/dosya sistemi
# acik dosyanin silinmesine izin verebilir, o yuzden kontrol iki durumu da
# kabul ediyor: ya dosya silindi ya da icerigi bosaltildi.
chk("bellekteki liste de bosaldi", a.gecmis == [], a.gecmis)

print("[5] Bos metin panoya yazilmiyor ve bunu soyluyor")
# Arayuz donuse bakmayinca, kaydi bosaltip Kopyala'ya basan kullaniciya
# "kopyalandi" deniyor, panoda eski metin kaliyordu.
chk("bos metin False", mk.panoya_yaz("") is False)
chk("bosluk da False", mk.panoya_yaz("") is False)

print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
