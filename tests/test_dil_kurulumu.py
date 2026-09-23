"""Dil kurulumu sonrası akış + yeniden başlatma."""
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.stdout.reconfigure(encoding="utf-8")
import ceviri
import ortam
ortam.izole_et()   # gercek %APPDATA% verisine dokunma
import metinkap as mk
import diller as dl

ok = True


def chk(ad, k, ek=""):
    global ok
    print(("  OK   " if k else "  FAIL ") + ad + (("  -> " + str(ek)) if ek else ""))
    ok &= bool(k)


print("[1] dil_var_mi — listeye güvenmeden doğrudan motor sorgusu")
o = mk.Ocr()
liste = o.diller()
print("     listelenen:", liste)
chk("kurulu dil icin True", o.dil_var_mi("tr"))
chk("kullanicinin indirdigi en-GB icin True", o.dil_var_mi("en-GB"))
chk("kurulu olmayan fr-FR icin False", o.dil_var_mi("fr-FR") is False)
chk("sacma etiket icin False, cokmuyor", o.dil_var_mi("zz-ZZ") is False)

print("[2] dilleri_tazele(ekstra=...)")
app = mk.MetinKap()
app.root.update()
time.sleep(0.3)
app.root.update()
d = app.dilleri_tazele()
chk("en-GB artik listede", "en-GB" in d, d)
# listede olmayan ama kurulu bir dil 'ekstra' ile eklenebiliyor mu
app.diller = [x for x in d if x != "en-GB"]
app.ocr.unut()
d2 = app.dilleri_tazele(ekstra="en-GB")
chk("ekstra ile geri eklendi", "en-GB" in d2, d2)
d3 = app.dilleri_tazele(ekstra="fr-FR")
chk("kurulu olmayan ekstra eklenmiyor", "fr-FR" not in d3)

print("[3] kurulum sonrasi arayuz akisi (dil_kur taklit ediliyor)")
app.arayuzu_ac()
app.root.update()
p = app.pencere
p.sekme_goster("diller")
app.root.update()

# senaryo A: kurulum basarili ve dil gorunur
dl_gercek = dl.dil_kur
dl.dil_kur = lambda etiket: (True, "State: Installed")
p._dil_indir("en-GB", "İngilizce (BK)")
for _ in range(60):
    app._kuyruk_isle_bir_kez()
    app.root.update()
    time.sleep(0.05)
    if not p.mesgul and p.bildirim.winfo_ismapped():
        break
app._kuyruk_isle_bir_kez()
app.root.update()
chk("A: gorunur dilde yeniden baslat ISTENMIYOR",
    p.bildirim.winfo_children() == [], len(p.bildirim.winfo_children()))
chk("A: basarili mesaji", "kuruldu" in p.bildirim.cget("text").lower()
    or "installed" in p.bildirim.cget("text").lower(), p.bildirim.cget("text")[:60])

# senaryo B: kurulum basarili ama dil listede gorunmuyor (Windows onbellegi)
p._bildirimi_gizle()
app.root.update()
dl.dil_kur = lambda etiket: (True, "State: Installed")
gercek_dil_var_mi = app.ocr.dil_var_mi
app.ocr.dil_var_mi = lambda tag: False          # yeni dil hic gorunmuyor
p._dil_indir("fr-FR", "Fransızca")
for _ in range(60):
    app._kuyruk_isle_bir_kez()
    app.root.update()
    time.sleep(0.05)
    if not p.mesgul and p.bildirim.winfo_ismapped():
        break
app._kuyruk_isle_bir_kez()
app.root.update()
cocuk = p.bildirim.winfo_children()
chk("B: yeniden baslat dugmesi cikti", len(cocuk) == 1, len(cocuk))
if cocuk:
    dugmeler = [w.cget("text") for w in cocuk[0].winfo_children()]
    chk("B: dugme etiketi dogru", any("başlat" in x or "Restart" in x
                                      for x in dugmeler), dugmeler)
chk("B: mesaj yeniden baslatmayi anlatiyor",
    "yeniden" in p.bildirim.cget("text").lower()
    or "restart" in p.bildirim.cget("text").lower(), p.bildirim.cget("text")[:70])

# senaryo C: kurulum basarisiz
p._bildirimi_gizle()
app.root.update()
dl.dil_kur = lambda etiket: (False, "0x800f0954 test hatasi")
p._dil_indir("fr-FR", "Fransızca")
for _ in range(60):
    app._kuyruk_isle_bir_kez()
    app.root.update()
    time.sleep(0.05)
    if not p.mesgul and p.bildirim.winfo_ismapped():
        break
app._kuyruk_isle_bir_kez()
app.root.update()
chk("C: hata mesaji sebebi iceriyor", "0x800f0954" in p.bildirim.cget("text"),
    p.bildirim.cget("text")[:70])
chk("C: yeniden baslat dugmesi YOK", p.bildirim.winfo_children() == [])

dl.dil_kur = dl_gercek
app.ocr.dil_var_mi = gercek_dil_var_mi

print("[4] kisayol kaydi yeniden deniyor mu (yeniden baslatma icin sart)")
import ctypes
u32 = ctypes.windll.user32
# app'in kisayolunu disaridan kapip biraz sonra birakalim
import threading
m, v = mk.kisayol_coz("ctrl+shift+f8")
tutuldu = threading.Event()

def tutucu():
    # RegisterHotKey/UnregisterHotKey thread'e bagli: ayni thread birakmali
    if u32.RegisterHotKey(None, 77, m, v):
        tutuldu.set()
        time.sleep(0.6)
        u32.UnregisterHotKey(None, 77)

th = threading.Thread(target=tutucu, daemon=True)
th.start()
tutuldu.wait(2)
chk("test kisayolu baskasi tarafindan tutuluyor", tutuldu.is_set())
q = __import__("queue").Queue()
d = mk.KisayolDinleyici({9: "ctrl+shift+f8"}, q)
t0 = time.perf_counter()
d.start()
hatalar = d.bekle()
sure = (time.perf_counter() - t0) * 1000
chk("mesgul kisayol icin tekrar denedi ve aldi", hatalar == [],
    f"{hatalar} ({sure:.0f} ms)")
th.join(timeout=2)
d.durdur()
d.join(timeout=2)

app.cikis()
print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
