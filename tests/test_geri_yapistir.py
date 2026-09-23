import os
import ctypes, sys, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import ortam
ortam.izole_et()   # gercek %APPDATA% verisine dokunma
import metinkap as mk
u32 = ctypes.windll.user32
ok = True
def chk(a,k,e=""):
    global ok; print(("  OK   " if k else "  FAIL ")+a+(("  -> "+str(e)) if e else "")); ok &= bool(k)

print("[1] Guvenlik kontrolleri — yanlis yere yazmamali")
chk("hwnd None ise hicbir sey yapmaz", mk.pencereye_yapistir(None) is False)
chk("gecersiz hwnd ise hicbir sey yapmaz", mk.pencereye_yapistir(999999999) is False)

print("[2] Modifier basiliyken beklemeli, sonra vazgecmeli")
# Ctrl'yi bastir (sanal), yapistirma denemesi tuslari gondermeden vazgecmeli
u32.keybd_event(0x11, 0, 0, 0)          # Ctrl down
try:
    chk("modifier basiliyken _modifierlar_birakildi_mi False",
        mk._modifierlar_birakildi_mi() is False)
    t0 = time.perf_counter()
    r = mk.pencereye_yapistir(u32.GetForegroundWindow(), bekleme=0.4)
    gecen = (time.perf_counter()-t0)*1000
    chk("modifier birakilmadiysa yapistirmiyor", r is False, r)
    chk("belirtilen sure kadar bekledi", 350 < gecen < 900, f"{gecen:.0f} ms")
finally:
    u32.keybd_event(0x11, 0, 2, 0)      # Ctrl up
chk("birakilinca True", mk._modifierlar_birakildi_mi() is True)

print("[3] Varsayilan KAPALI (otomatik tus gondermek riskli)")
chk("varsayilan false", mk.VARSAYILAN["geri_yapistir"] is False)
c = mk.ayar_yukle()
chk("config'de alan var", "geri_yapistir" in c)

print("[4] Kapaliyken akis hic dokunmuyor")
cagrildi = []
gercek = mk.pencereye_yapistir
mk.pencereye_yapistir = lambda *a, **k: cagrildi.append(1) or True
mk.baloncuk = lambda *a, **k: None
class Sahte(mk.MetinKap):
    def __init__(self):
        self.cfg = dict(mk.VARSAYILAN); self.cfg["gecmis_kaydet"]=False
        self.gecmis=[]; self.son_metin=""; self._gecmis_sayac=0
        self.biriktiriyor=False; self.tampon=[]; self.onceki_pencere=12345
        self.pencere=None; self.tray=None; self.root=None
    def _menu_tazele(self): pass
    def _gecmis_degisti(self): pass
a = Sahte()
a._kopyala_ve_bildir("deneme")
chk("kapaliyken cagrilmadi", not cagrildi)
a.cfg["geri_yapistir"] = True
a._kopyala_ve_bildir("deneme2")
chk("acikken cagrildi", len(cagrildi) == 1, cagrildi)
# biriktirme sirasinda yapistirmamali
a.biriktiriyor = True
a._kopyala_ve_bildir("parca")
chk("biriktirirken yapistirmiyor", len(cagrildi) == 1, cagrildi)
a.biriktirmeyi_bitir()
chk("biriktirme bitince yapistiriyor", len(cagrildi) == 2, cagrildi)
mk.pencereye_yapistir = gercek

print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
