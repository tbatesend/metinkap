"""Tablo ve girinti modlari — pencere acmaz, sentetik goruntu uzerinde calisir."""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.stdout.reconfigure(encoding="utf-8")
import metinkap as mk
from PIL import Image, ImageDraw, ImageFont

ok = True


def chk(ad, k, ek=""):
    global ok
    print(("  OK   " if k else "  FAIL ") + ad + (("  -> " + str(ek)) if ek else ""))
    ok &= bool(k)


ocr = mk.Ocr()


def ciz(satirlar, font="consola.ttf", pt=20, genislik=900):
    """satirlar: [(x, metin), ...] veya [[(x, metin), ...], ...] (tablo satiri)"""
    f = ImageFont.truetype("C:/Windows/Fonts/" + font, pt)
    yuk = 20 + len(satirlar) * int(pt * 1.8)
    im = Image.new("RGB", (genislik, yuk), "white")
    d = ImageDraw.Draw(im)
    for i, satir in enumerate(satirlar):
        y = 10 + i * int(pt * 1.8)
        hucreler = satir if isinstance(satir, list) else [satir]
        for x, metin in hucreler:
            d.text((x, y), metin, font=f, fill="black")
    return im


def oku(im, bant=False):
    return ocr.parcalar(im.resize((im.width * 2, im.height * 2), Image.LANCZOS),
                        "en-US", bant)


print("[1] Girinti modu — kod yapistirirken girinti korunuyor mu")
kod = [(20, "def topla(a, b):"), (70, "if a > b:"), (120, "return a"),
       (70, "return b"), (20, "print(topla(3, 5))")]
metin = mk.bicimlendir(oku(ciz(kod)), "girinti")
print("--- cikti ---")
print(metin)
print("-------------")
satirlar = metin.splitlines()
chk("5 satir", len(satirlar) == 5, len(satirlar))
if len(satirlar) == 5:
    girintiler = [len(s) - len(s.lstrip()) for s in satirlar]
    chk("girinti seviyeleri artiyor/azaliyor", girintiler[0] == 0
        and girintiler[1] > girintiler[0] and girintiler[2] > girintiler[1]
        and girintiler[3] == girintiler[1] and girintiler[4] == 0, girintiler)
    chk("metin bozulmadi", "def topla" in satirlar[0] and "return a" in satirlar[2])

print("\n[2] Girinti modu duz metni bozmuyor")
duz = [(20, "Birinci satir burada"), (20, "Ikinci satir burada"),
       (20, "Ucuncu satir burada")]
m2 = mk.bicimlendir(oku(ciz(duz)), "girinti")
chk("hicbir satirda girinti yok", all(not s.startswith(" ")
                                      for s in m2.splitlines() if s), repr(m2[:60]))

print("\n[3] Tablo modu — sutunlar korunuyor mu")
tablo = [
    [(20, "Urun"), (300, "Adet"), (500, "Fiyat")],
    [(20, "Kalem"), (300, "12"), (500, "45.90")],
    [(20, "Defter"), (300, "3"), (500, "120.50")],
    [(20, "Silgi"), (300, "25"), (500, "8.75")],
]
m3 = mk.bicimlendir(oku(ciz(tablo)), "tablo")
print("--- cikti ---")
print(m3)
print("-------------")
chk("Markdown tablo bicimi", m3.startswith("|") and "---" in m3)
sat = [s for s in m3.splitlines() if s.startswith("|") and "---" not in s]
chk("4 veri satiri", len(sat) == 4, len(sat))
if sat:
    sutun_sayilari = [s.count("|") for s in sat]
    chk("her satirda ayni sutun sayisi", len(set(sutun_sayilari)) == 1,
        sutun_sayilari)
    chk("3 sutun", sutun_sayilari[0] == 4, sutun_sayilari[0])
chk("basliklar dogru", "Urun" in m3 and "Adet" in m3 and "Fiyat" in m3)
chk("degerler dogru sutunda",
    any("Kalem" in s and "12" in s and "45" in s for s in sat), sat[:2])

print("\n[4] Tablo modu tek sutunda duz metne duser")
m4 = mk.bicimlendir(oku(ciz(duz)), "tablo")
chk("tek sutunlu icerik tabloya zorlanmiyor", not m4.startswith("|"), repr(m4[:40]))

print("\n[5] Bant birlestirme tablo modunda kapali olmali")
# Genis sutunlu tabloda bant birlestirme zaten dokunmuyor (bosluk esigi):
p_genis_b = oku(ciz(tablo), bant=True)
p_genis_s = oku(ciz(tablo), bant=False)
chk("genis sutunlu tabloyu bant birlestirme BOZMUYOR",
    len(p_genis_b) == len(p_genis_s), f"{len(p_genis_b)} vs {len(p_genis_s)}")
# Dar sutunlu tabloda ise birlestiriyor -> tablo modu bunu kapatmali
dar = [[(20, "Ad"), (150, "Yas"), (260, "Sehir")],
       [(20, "Ali"), (150, "34"), (260, "Bursa")],
       [(20, "Veli"), (150, "28"), (260, "Izmir")]]
d_b = oku(ciz(dar, genislik=500), bant=True)
d_s = oku(ciz(dar, genislik=500), bant=False)
chk("dar sutunlu tabloyu da bozmuyor (bosluk esigi calisiyor)",
    len(d_b) == len(d_s), f"{len(d_b)} vs {len(d_s)}")
m_dar = mk.bicimlendir(d_s, "tablo")
print("--- dar sutunlu tablo (bant kapali) ---")
print(m_dar)
chk("dar tablo da sutunlara ayrildi", m_dar.startswith("|") and "Sehir" in m_dar)
chk("tablo modu KUTU_MODLARI icinde", "tablo" in mk.KUTU_MODLARI)
chk("girinti modu KUTU_MODLARI icinde", "girinti" in mk.KUTU_MODLARI)

print("\n[6] Kenar durumlari cokmuyor")
for mod in mk.SATIR_MODLARI:
    for veri in ([], [("tek", (0, 0, 10, 10))]):
        try:
            r = mk.bicimlendir(veri, mod)
            assert isinstance(r, str)
        except Exception as e:
            chk(f"{mod} / {len(veri)} parca", False, e)
print("  OK   bos ve tek parcali girdi tum modlarda guvenli")

print("\n[7] Eski API bozulmadi")
im = ciz(duz)
chk("Ocr.satirlar hala string listesi",
    all(isinstance(x, str) for x in ocr.satirlar(im, "en-US")))
chk("satirlari_birlestir calisiyor",
    mk.satirlari_birlestir(["a", "b"], "paragraf") == "a b")

print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
