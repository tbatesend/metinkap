import ctypes
import json
import os
import sys
import time
import tkinter as tk

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.stdout.reconfigure(encoding="utf-8")

import ceviri
import ortam
ortam.izole_et()   # gercek %APPDATA% verisine dokunma
import metinkap as mk
import arayuz
import diller as dl

ok = True
u32 = ctypes.windll.user32


def chk(ad, k, ek=""):
    global ok
    print(("  OK   " if k else "  FAIL ") + ad + (("  -> " + str(ek)) if ek else ""))
    ok &= bool(k)


print("[1] ceviri butunlugu")
eksik = [k for k in ceviri.EN if k not in ceviri.TR]
fazla = [k for k in ceviri.TR if k not in ceviri.EN]
chk("TR'de eksik anahtar yok", not eksik, eksik)
chk("TR'de fazla anahtar yok", not fazla, fazla)
ceviri.dili_ayarla("en")
chk("varsayilan EN", ceviri.t("tab.capture") == "Capture", ceviri.t("tab.capture"))
ceviri.dili_ayarla("tr")
chk("TR'ye geciyor", ceviri.t("tab.capture") == "Yakala", ceviri.t("tab.capture"))
ceviri.dili_ayarla("xx")
chk("bilinmeyen dil EN'e duser", ceviri.t("tab.capture") == "Capture")
chk("bilinmeyen anahtar cokmeden doner", ceviri.t("yok.boyle.bir.sey") == "yok.boyle.bir.sey")
chk("eksik alan cokmeden doner", isinstance(ceviri.t("toast.ready"), str))
# format alanlari iki dilde de ayni mi
import re
for k in ceviri.EN:
    a = set(re.findall(r"\{(\w+)\}", ceviri.EN[k]))
    b = set(re.findall(r"\{(\w+)\}", ceviri.TR.get(k, "")))
    if a != b:
        chk(f"alanlar eslesiyor: {k}", False, f"EN={a} TR={b}")
print("  OK   tum anahtarlarda format alanlari eslesiyor")

print("[2] bozuk config kurtariliyor")
# ortam.izole_et() yollari gecici klasore aldi; elle yedeklemeye gerek yok.
open(mk.CONFIG_PATH, "w", encoding="utf-8").write("{ bu gecerli json degil ")
c = mk.ayar_yukle()
chk("bozuk json varsayilana donuyor", c["kisayol"] == mk.VARSAYILAN["kisayol"])
json.dump({"kisayol": "bu+gecersiz+tus", "satir_modu": "sacma",
           "karartma": 99, "gecmis_boyut": -5}, open(mk.CONFIG_PATH, "w", encoding="utf-8"))
c = mk.ayar_yukle()
chk("gecersiz kisayol duzeltildi", c["kisayol"] == mk.VARSAYILAN["kisayol"], c["kisayol"])
chk("gecersiz satir modu duzeltildi", c["satir_modu"] == "satir", c["satir_modu"])
chk("karartma sinirlandi", 0 <= c["karartma"] <= 0.9, c["karartma"])
chk("gecmis boyutu sinirlandi", c["gecmis_boyut"] >= 1, c["gecmis_boyut"])
json.dump({"kisayol": "ctrl+alt+t", "kisayol_duzelt": "ctrl+alt+shift+t"},
          open(mk.CONFIG_PATH, "w", encoding="utf-8"))
c = mk.ayar_yukle()
chk("eski AltGr kisayolu goc etti", c["kisayol"] == "ctrl+shift+space", c["kisayol"])

print("[3] gecmis dosyasi")
mk.HISTORY_JSON_YEDEK = None
if os.path.exists(mk.HISTORY_JSON):
    mk.HISTORY_JSON_YEDEK = open(mk.HISTORY_JSON, encoding="utf-8").read()
json.dump(["eski bicim metin", {"metin": "yeni bicim", "zaman": "2026-01-01"},
           {"bozuk": True}, 42],
          open(mk.HISTORY_JSON, "w", encoding="utf-8"), ensure_ascii=False)
g = mk.gecmis_yukle(25)
chk("karisik/bozuk gecmis ayiklandi", len(g) == 2, g)
chk("eski bicim donusturuldu", g[0]["metin"] == "eski bicim metin"
    and g[0]["zaman"] == "" and g[0].get("id"), g[0])
open(mk.HISTORY_JSON, "w", encoding="utf-8").write("bozuk")
chk("bozuk gecmis bos doner", mk.gecmis_yukle(25) == [])
os.remove(mk.HISTORY_JSON)
chk("dosya yoksa bos doner", mk.gecmis_yukle(25) == [])

print("[4] uygulama acilisi")
app = mk.MetinKap()
app.root.update()
time.sleep(0.4)
app.root.update()
if ortam.baska_ornek_calisiyor():
    # Kisayollar isletim sistemi genelinde tekil; acik olan kopya onlari tutuyor.
    # Bunu FAIL saymak yanlis yonlendiriyordu (bir kez tam bu yuzden "hata var"
    # dedi, oysa kodda sorun yoktu). Kapatip tekrar calistirmak gerekir.
    print("  NOT   MetinKap acik -> kisayol kaydi DOGRULANMADI "
          "(kapatip tekrar calistirin)")
else:
    chk("4 kisayol da kayitli", app.dinleyici.hatalar == [], app.dinleyici.hatalar)
for combo in (app.cfg["kisayol"], app.cfg["kisayol_duzelt"],
              app.cfg["kisayol_tekrar"], app.cfg["kisayol_biriktir"]):
    m, v = mk.kisayol_coz(combo)
    r = u32.RegisterHotKey(None, 81, m, v)
    if r:
        u32.UnregisterHotKey(None, 81)
    chk(f"{combo} gercekten tutuluyor", not r)

print("[5] gecmis islemleri")
app.gecmis_temizle()
for s in ("birinci kayit", "ikinci kayit", "ucuncu kayit"):
    app.gecmise_ekle(s)
chk("3 kayit eklendi", len(app.gecmis) == 3)
chk("en yeni basta", app.gecmis[0]["metin"] == "ucuncu kayit")
chk("zaman damgasi var", len(app.gecmis[0]["zaman"]) > 10, app.gecmis[0]["zaman"])
app.gecmis_guncelle(app.gecmis[1]["id"], "DUZENLENDI")
chk("duzenleme uygulandi", app.gecmis[1]["metin"] == "DUZENLENDI")
chk("diske yazildi", json.load(open(mk.HISTORY_JSON, encoding="utf-8"))[1]["metin"] == "DUZENLENDI")
app.gecmis_guncelle(app.gecmis[0]["id"], "YENI BAS")
chk("0. duzenlenince son_metin de guncellendi", app.son_metin == "YENI BAS")
app.gecmis_sil(app.gecmis[0]["id"])
chk("silindi", len(app.gecmis) == 2 and app.gecmis[0]["metin"] == "DUZENLENDI")
chk("son_metin kaydi izledi", app.son_metin == "DUZENLENDI")
app.gecmis_guncelle("boyle-bir-kimlik-yok", "yok")
app.gecmis_sil("boyle-bir-kimlik-yok")
chk("gecersiz indeks cokertmedi", len(app.gecmis) == 2)
chk("yeniden yuklenince kaliyor",
    [k["metin"] for k in mk.gecmis_yukle(25)] == ["DUZENLENDI", "birinci kayit"],
    mk.gecmis_yukle(25))

print("[6] arayuz: tum sekmeler iki dilde")
app.arayuzu_ac()
app.root.update()
p = app.pencere
for kod in ("en", "tr"):
    app.arayuz_dilini_ayarla(kod)
    p._serit_ciz()
    for anahtar, _ in arayuz.SEKMELER:
        try:
            p.sekme_goster(anahtar)
            app.root.update()
            chk(f"[{kod}] sekme '{anahtar}'", len(p.icerik.winfo_children()) > 0)
        except Exception as e:
            import traceback
            traceback.print_exc()
            chk(f"[{kod}] sekme '{anahtar}'", False, e)

print("[7] gecmis sekmesi duzenleme akisi")
p.sekme_goster("gecmis")
app.root.update()
p._gecmis_goster(0)
p.gecmis_kutu.delete("1.0", "end")
p.gecmis_kutu.insert("1.0", "ARAYUZDEN DUZENLENDI")
app.root.update()
chk("kirli bayragi kalkti", p._gecmis_kirli)
p._gecmis_kaydet()
app.root.update()
chk("arayuzden kaydedildi", app.gecmis[0]["metin"] == "ARAYUZDEN DUZENLENDI",
    app.gecmis[0]["metin"])
# kart degistirince otomatik kaydetme
p._gecmis_goster(0)
p.gecmis_kutu.delete("1.0", "end")
p.gecmis_kutu.insert("1.0", "KAYDETMEDEN GECIS")
app.root.update()
p._gecmis_sec(1)
app.root.update()
chk("kart degisiminde otomatik kaydedildi",
    app.gecmis[0]["metin"] == "KAYDETMEDEN GECIS", app.gecmis[0]["metin"])
# kopyalama
p._gecmis_goster(0)
app.root.update()
p._gecmis_kopyala()
app.root.update()
chk("gecmisten kopyalandi", app.root.clipboard_get() == "KAYDETMEDEN GECIS")
# silme
onceki = len(app.gecmis)
p._gecmis_sil()
app.root.update()
chk("arayuzden silindi", len(app.gecmis) == onceki - 1)
p._gecmis_temizle()
app.root.update()
chk("hepsi temizlendi", len(app.gecmis) == 0)
chk("bos gecmis sekmesi cizilebiliyor", len(p.icerik.winfo_children()) > 0)

print("[8] son alan tekrar yakalama")
chk("alan yokken uyari veriyor, cokmuyor", app.son_alani_yakala() is None)
app.son_kutu = (100, 150, 700, 330)
app.son_alani_yakala()
app.root.update()
time.sleep(0.3)
app.root.update()
chk("son alan islendi (mesgul degil)", app.mesgul is False)
app.son_kutu = (99999, 99999, 100500, 100500)
app.son_alani_yakala()
app.root.update()
chk("ekran disi alan cokertmedi", app.mesgul is False)

print("[9] kisayol cakisma kontrolu")
p.sekme_goster("ayarlar")
app.root.update()
p._kisayol_degisti("kisayol", app.cfg["kisayol_tekrar"])
app.root.update()
chk("uc islev arasi cakisma engellendi",
    app.cfg["kisayol"] != app.cfg["kisayol_tekrar"])

print("[10] tepsi menusu")
time.sleep(1.5)
app.root.update()
if app.tray:
    app._menu_tazele()
    adlar = [i.text for i in app.tray.menu]
    chk("menu olustu", len(adlar) > 8, len(adlar))
    ceviri.dili_ayarla("en")
    app._menu_tazele()
    chk("menu EN'e gecti", any("Settings" in a for a in [i.text for i in app.tray.menu]))
else:
    chk("tepsi ikonu", False, "olusmadi")

app.cikis()
try:
    os.remove(mk.HISTORY_JSON)
except OSError:
    pass
print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
