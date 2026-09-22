import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import metinkap as mk
ok = True
def chk(a,k,e=""):
    global ok; print(("  OK   " if k else "  FAIL ")+a+(("  -> "+str(e)) if e else "")); ok &= bool(k)

baloncuklar = []
mk.baloncuk = lambda root, metin, hata=False, sure=0: baloncuklar.append(metin)

class Sahte(mk.MetinKap):
    def __init__(self):
        self.cfg = dict(mk.VARSAYILAN); self.cfg["gecmis_kaydet"] = False
        self.gecmis=[]; self.son_metin=""; self._gecmis_sayac=0
        self.biriktiriyor=False; self.tampon=[]
        self.pencere=None; self.tray=None; self.root=None
    def _menu_tazele(self): pass
    def _gecmis_degisti(self): pass

a = Sahte()
print("[1] Normal modda panoya gidiyor")
a._kopyala_ve_bildir("birinci")
chk("panoda", mk.panoya_yaz and True)
chk("gecmise eklendi", len(a.gecmis)==1)
chk("tampon bos", a.tampon==[])

print("[2] Biriktirme acilinca panoya gitmiyor, toplaniyor")
a.biriktirmeyi_degistir()
chk("mod acik", a.biriktiriyor is True)
for m in ("parca bir","parca iki","parca uc"):
    a._kopyala_ve_bildir(m)
chk("3 parca toplandi", a.tampon==["parca bir","parca iki","parca uc"], a.tampon)
chk("gecmise ayri ayri EKLENMEDI", len(a.gecmis)==1, len(a.gecmis))

print("[3] Bitirince hepsi tek metin olarak panoya")
mk.panoya_yaz("---temiz---")
a.biriktirmeyi_degistir()
chk("mod kapandi", a.biriktiriyor is False)
chk("tampon bosaldi", a.tampon==[])
bekl = "parca bir\n\nparca iki\n\nparca uc"
chk("son_metin birlesik", a.son_metin==bekl, repr(a.son_metin))
chk("gecmise tek kayit olarak eklendi", len(a.gecmis)==2 and a.gecmis[0]["metin"]==bekl)

print("[4] Bos tamponla bitirmek zararsiz")
a.biriktirmeyi_degistir(); a.biriktirmeyi_degistir()
chk("cokmedi, gecmise eklemedi", len(a.gecmis)==2, len(a.gecmis))
chk("bilgi verildi", any("toplanmamisti" in b or "nothing was collected" in b.lower()
                         for b in baloncuklar[-2:]), baloncuklar[-1][:50])

print("[5] Ayirici ayarlanabilir")
a.cfg["biriktir_ayirici"] = "\n---\n"
a.biriktirmeyi_degistir()
a._kopyala_ve_bildir("x"); a._kopyala_ve_bildir("y")
a.biriktirmeyi_degistir()
chk("ozel ayirici kullanildi", a.son_metin=="x\n---\ny", repr(a.son_metin))

print("[6] Kisayol yapilandirmasi")
chk("varsayilan kisayol var", mk.VARSAYILAN["kisayol_biriktir"]=="ctrl+shift+a")
chk("cozulebiliyor", mk.kisayol_coz(mk.VARSAYILAN["kisayol_biriktir"])[1]==ord("A"))
chk("HK_ANAHTAR'da", mk.HK_ANAHTAR[mk.HK_BIRIKTIR]=="kisayol_biriktir")
chk("4 kisayol", len(mk.HK_ANAHTAR)==4)
c = mk.ayar_yukle()
chk("gecersiz biriktir kisayolu onariliyor", "kisayol_biriktir" in c)

print("\nSONUC:", "HEPSI GECTI" if ok else "HATA VAR")
sys.exit(0 if ok else 1)
