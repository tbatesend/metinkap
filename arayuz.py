"""MetinKap ayar penceresi."""

import ctypes
import os
import threading
import tkinter as tk

import ceviri
import diller as dl
from ceviri import t

# --------------------------------------------------------------------------
# Tema
# --------------------------------------------------------------------------
BG = "#0d1117"
PANEL = "#161b22"
PANEL2 = "#1c2430"
KENAR = "#30363d"
METIN = "#e6edf3"
SOLUK = "#8b949e"
VURGU = "#2f81f7"
VURGU2 = "#1f6feb"
YESIL = "#3fb950"
KIRMIZI = "#f85149"
SARI = "#d29922"

F = "Segoe UI"

# Yuksek DPI: font boyutlari punto cinsinden verildigi icin Windows onlari
# kendisi buyutuyor, ama geometry/width/wraplength gibi piksel degerleri sabit
# kaliyor ve icerik tasiyor. Pencere acilirken gercek olcek olculup buraya
# yaziliyor; piksel sabitleri ol() ile carpiliyor.
_OLCEK = 1.0


def olcegi_belirle(pencere):
    global _OLCEK
    try:
        _OLCEK = max(1.0, min(2.5, pencere.winfo_fpixels("1i") / 96.0))
    except Exception:
        _OLCEK = 1.0
    return _OLCEK


def ol(n):
    return int(round(n * _OLCEK))


def dugme(ust, metin, komut, tur="normal"):
    renkler = {
        "normal": (VURGU, VURGU2, "white"),
        "sessiz": (PANEL2, KENAR, METIN),
        "tehlike": ("#3d1d1f", "#5a2a2d", "#ff9d96"),
    }[tur]
    return tk.Button(ust, text=metin, command=komut, relief="flat", bd=0,
                     bg=renkler[0], fg=renkler[2], activebackground=renkler[1],
                     activeforeground=renkler[2], font=(F, 10, "bold"),
                     cursor="hand2", padx=16, pady=7, highlightthickness=0,
                     disabledforeground=SOLUK)


def baslik(ust, metin, alt=None):
    c = tk.Frame(ust, bg=BG)
    tk.Label(c, text=metin, bg=BG, fg=METIN, font=(F, 17, "bold"),
             anchor="w").pack(fill="x")
    if alt:
        tk.Label(c, text=alt, bg=BG, fg=SOLUK, font=(F, 10), anchor="w",
                 justify="left", wraplength=ol(560)).pack(fill="x", pady=(3, 0))
    c.pack(fill="x", pady=(0, 16))
    return c


def bolum(ust, metin, ust_bosluk=0):
    tk.Label(ust, text=metin, bg=BG, fg=METIN, font=(F, 12, "bold"),
             anchor="w").pack(fill="x", pady=(ust_bosluk, 8))


def ayirici(ust):
    tk.Frame(ust, bg=KENAR, height=1).pack(fill="x", pady=12)


class Kaydirilabilir(tk.Frame):
    """Dikey kaydırma çubuğu olan çerçeve. İçerik .govde içine konur.

    Tekerlek olayını kendisi bağlamaz: bind_all her örnekte uygulama geneline
    bir binding daha eklerdi ve sekme değişince yok edilmiş widget'lara
    erişilirdi. Bağlamayı pencere tek elden yapıp buraya yönlendiriyor."""

    def __init__(self, ust, **kw):
        super().__init__(ust, bg=BG, **kw)
        self.tuval = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.cubuk = tk.Scrollbar(self, orient="vertical", command=self.tuval.yview,
                                  bg=PANEL, troughcolor=BG, bd=0,
                                  activebackground=KENAR, relief="flat",
                                  width=ol(11))
        self.govde = tk.Frame(self.tuval, bg=BG)
        self._pencere = self.tuval.create_window((0, 0), window=self.govde,
                                                 anchor="nw")
        self.tuval.configure(yscrollcommand=self.cubuk.set)
        self.tuval.pack(side="left", fill="both", expand=True)
        self.cubuk.pack(side="right", fill="y")
        self.govde.bind("<Configure>", self._icerik_degisti)
        self.tuval.bind("<Configure>", self._tuval_degisti)

    def _icerik_degisti(self, _e):
        self.tuval.configure(scrollregion=self.tuval.bbox("all"))

    def _tuval_degisti(self, e):
        self.tuval.itemconfigure(self._pencere, width=e.width)

    def kaydir(self, delta):
        try:
            self.tuval.yview_scroll(int(-delta / 120), "units")
        except tk.TclError:
            pass


# --------------------------------------------------------------------------
# Kısayol gösterimi / seçimi
# --------------------------------------------------------------------------
VK_ADI = {
    0x20: "space", 0x0D: "enter", 0x09: "tab", 0x2D: "insert", 0x2E: "delete",
    0x24: "home", 0x23: "end", 0x21: "pageup", 0x22: "pagedown",
    0x25: "left", 0x26: "up", 0x27: "right", 0x28: "down", 0x2C: "printscreen",
}
for _i in range(1, 25):
    VK_ADI[0x6F + _i] = f"f{_i}"

_SUSLU = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
_MODIFIER_VK = (0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)


def gosterim(kisayol):
    return " + ".join(_SUSLU.get(x, x.upper())
                      for x in kisayol.split("+") if x)


class KisayolSecici(tk.Frame):
    """Tıkla, tuşa bas, kaydet.

    Modifier durumu Win32'den okunur: tkinter'ın event.state'i Windows'ta Alt
    için güvenilir değil. event.keycode ise doğrudan sanal tuş kodudur, yani
    Türkçe klavyede de doğru harfi verir. Tuş dinlemesini pencere yapar, bu
    sınıf yalnızca sırası gelince çağrılır."""

    def __init__(self, ust, pencere, deger, on_change):
        super().__init__(ust, bg=BG)
        self.pencere = pencere
        self.deger = deger
        self.on_change = on_change
        self.dinliyor = False

        self.kutu = tk.Label(self, text=gosterim(deger), bg=PANEL2, fg=METIN,
                             font=("Consolas", 11, "bold"), padx=14, pady=8,
                             cursor="hand2", anchor="w", width=22,
                             highlightthickness=1, highlightbackground=KENAR)
        self.kutu.pack(side="left")
        self.kutu.bind("<Button-1>", lambda e: self.basla())
        self.dgm = dugme(self, t("btn.change"), self.basla, "sessiz")
        self.dgm.pack(side="left", padx=8)

    def basla(self):
        if self.dinliyor:
            return
        onceki = self.pencere.aktif_secici
        if onceki is not None and onceki is not self:
            onceki.bitir()
        self.dinliyor = True
        self.pencere.aktif_secici = self
        self.kutu.configure(text=t("set.press_keys"), fg=SARI,
                            highlightbackground=SARI)
        self.dgm.configure(state="disabled")
        self.pencere.win.focus_force()

    def bitir(self):
        self.dinliyor = False
        if self.pencere.aktif_secici is self:
            self.pencere.aktif_secici = None
        try:
            self.kutu.configure(text=gosterim(self.deger), fg=METIN,
                                highlightbackground=KENAR)
            self.dgm.configure(state="normal")
        except tk.TclError:
            pass

    def tus(self, e):
        """Pencerenin KeyPress yönlendirmesinden çağrılır."""
        vk = e.keycode
        if vk in _MODIFIER_VK:
            return "break"
        if vk == 0x1B:                                   # Esc = iptal
            self.bitir()
            return "break"

        gak = ctypes.windll.user32.GetAsyncKeyState
        mods = []
        if gak(0x11) & 0x8000:
            mods.append("ctrl")
        if gak(0x12) & 0x8000:
            mods.append("alt")
        if gak(0x10) & 0x8000:
            mods.append("shift")
        if (gak(0x5B) & 0x8000) or (gak(0x5C) & 0x8000):
            mods.append("win")

        if vk in VK_ADI:
            tus = VK_ADI[vk]
        elif 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
            tus = chr(vk).lower()
        elif 0x60 <= vk <= 0x69:                          # numpad rakamlari
            tus = chr(vk - 0x60 + 0x30)
        else:
            self.pencere.bilgi(t("set.key_unusable"), "kotu")
            return "break"

        if not mods and not tus.startswith("f"):
            self.pencere.bilgi(t("set.need_modifier"), "kotu")
            return "break"

        yeni = "+".join(mods + [tus])
        self.deger = yeni
        self.bitir()
        self.on_change(yeni)
        return "break"


# --------------------------------------------------------------------------
# Ayar penceresi
# --------------------------------------------------------------------------
SEKMELER = [("yakala", "tab.capture"), ("diller", "tab.languages"),
            ("ayarlar", "tab.settings"), ("gecmis", "tab.history"),
            ("hakkinda", "tab.about")]

ONERILEN_KISAYOLLAR = ("ctrl+shift+space", "ctrl+shift+d", "ctrl+shift+1", "f9")


class AyarPenceresi:
    def __init__(self, app):
        self.app = app
        self.cfg = app.cfg
        self.aktif = None
        self.aktif_secici = None
        self.kaydirilabilir = None
        self.dil_satirlari = {}
        self.mesgul = False
        self._karartma_is = None
        self._gecmis_id = None
        self._gecmis_kirli = False

        w = tk.Toplevel(app.root)
        self.win = w
        w.title("MetinKap")
        w.configure(bg=BG)
        olcegi_belirle(w)
        yuk = min(ol(660), int(w.winfo_screenheight() * 0.86))
        w.geometry(f"{ol(940)}x{yuk}")
        w.minsize(ol(760), ol(470))
        w.protocol("WM_DELETE_WINDOW", self.kapat)
        w.bind("<KeyPress>", self._tus_yakala)
        w.bind("<MouseWheel>", self._tekerlek)

        try:
            self._ikon = app.tk_ikon()
            w.iconphoto(False, self._ikon)
        except Exception:
            pass

        self.sol = tk.Frame(w, bg=PANEL, width=ol(178))
        self.sol.pack(side="left", fill="y")
        self.sol.pack_propagate(False)

        self.icerik = tk.Frame(w, bg=BG)
        self.icerik.pack(side="left", fill="both", expand=True)

        self.bildirim = tk.Label(w, text="", bg=PANEL2, fg=METIN, font=(F, 10),
                                 padx=14, pady=8, anchor="w", justify="left")

        self._serit_ciz()
        self.sekme_goster("yakala")
        w.update_idletasks()
        w.geometry("+%d+%d" % (
            max(0, (w.winfo_screenwidth() - w.winfo_width()) // 2),
            max(0, (w.winfo_screenheight() - w.winfo_height()) // 3)))

    # -- sol şerit --------------------------------------------------------
    def _serit_ciz(self):
        for c in self.sol.winfo_children():
            c.destroy()

        ust = tk.Frame(self.sol, bg=PANEL)
        ust.pack(fill="x", pady=(22, 18), padx=18)
        tk.Label(ust, text="MetinKap", bg=PANEL, fg=METIN, font=(F, 15, "bold"),
                 anchor="w").pack(fill="x")
        self.durum_etiketi = tk.Label(ust, text="", bg=PANEL, fg=SOLUK,
                                      font=(F, 8), anchor="w", justify="left",
                                      wraplength=ol(138))
        self.durum_etiketi.pack(fill="x", pady=(2, 0))

        self.sekme_dugmeleri = {}
        for anahtar, etiket in SEKMELER:
            b = tk.Label(self.sol, text="   " + t(etiket), bg=PANEL, fg=SOLUK,
                         font=(F, 11), anchor="w", padx=14, pady=10, cursor="hand2")
            b.pack(fill="x", padx=10, pady=1)
            b.bind("<Button-1>", lambda e, k=anahtar: self.sekme_goster(k))
            self.sekme_dugmeleri[anahtar] = b

        alt = tk.Frame(self.sol, bg=PANEL)
        alt.pack(side="bottom", fill="x", pady=16, padx=14)
        dugme(alt, t("btn.hide"), self.kapat, "sessiz").pack(fill="x")
        tk.Label(alt, text=t("side.keeps_running"), bg=PANEL, fg=SOLUK,
                 font=(F, 8), justify="center").pack(pady=(6, 0))
        self.durumu_tazele()

    # -- olay yönlendirme -------------------------------------------------
    def _tus_yakala(self, e):
        if self.aktif_secici is not None:
            return self.aktif_secici.tus(e)

    def _tekerlek(self, e):
        """Tek binding; olay metin kutusundan geliyorsa dokunma (kendi kaydırır)."""
        if self.kaydirilabilir is None:
            return
        try:
            alt = self.win.winfo_containing(e.x_root, e.y_root)
            if isinstance(alt, (tk.Text, tk.Listbox)):
                return
        except Exception:
            pass
        self.kaydirilabilir.kaydir(e.delta)

    # -- yardımcılar ------------------------------------------------------
    def kapat(self):
        self._gecmis_kaydet_sessiz()
        self.win.withdraw()

    def goster(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()
        self.sekme_goster(self.aktif or "yakala")

    def durumu_tazele(self):
        try:
            self.durum_etiketi.configure(
                text=t("side.status", k=gosterim(self.cfg["kisayol"]),
                       n=len(self.app.diller)))
        except tk.TclError:
            pass

    def bilgi(self, metin, tur="normal", sure=3500, eylem=None):
        """eylem: (etiket, fonksiyon) — şeride bir düğme koyar ve şerit, kullanıcı
        karar verene kadar kalır."""
        renk = {"normal": METIN, "iyi": YESIL, "kotu": KIRMIZI}[tur]
        for c in self.bildirim.winfo_children():
            c.destroy()
        self.bildirim.configure(text="  " + metin, fg=renk)
        self.bildirim.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        if eylem:
            kutu = tk.Frame(self.bildirim, bg=PANEL2)
            kutu.place(relx=1.0, rely=0.5, anchor="e", x=-ol(10))
            dugme(kutu, eylem[0], eylem[1]).pack(side="left")
            dugme(kutu, "✕", self._bildirimi_gizle, "sessiz").pack(side="left",
                                                                   padx=(6, 0))
        else:
            self.win.after(sure, self._bildirimi_gizle)

    def _bildirimi_gizle(self):
        try:
            for c in self.bildirim.winfo_children():
                c.destroy()
            self.bildirim.place_forget()
        except tk.TclError:
            pass

    def sekme_goster(self, anahtar):
        # "gecmis" harici demiyoruz: yeni bir yakalama geldiginde bu sekme
        # kendini yeniden ciziyor ve kaydedilmemis duzenleme sessizce ucuyordu.
        self._gecmis_kaydet_sessiz()
        self.aktif = anahtar
        for k, b in self.sekme_dugmeleri.items():
            secili = k == anahtar
            b.configure(bg=PANEL2 if secili else PANEL,
                        fg=METIN if secili else SOLUK,
                        font=(F, 11, "bold" if secili else "normal"))
        for c in self.icerik.winfo_children():
            c.destroy()
        self.kaydirilabilir = None
        self.aktif_secici = None
        getattr(self, "_sekme_" + anahtar)()
        self.durumu_tazele()

    def _sayfa(self, kaydir=True):
        """kaydir=False olan sekmeler (Yakala, Geçmiş) dikey alanı paylaştırır;
        canvas içinde expand çalışmadığı için doğrudan yerleştirilirler."""
        if not kaydir:
            ic = tk.Frame(self.icerik, bg=BG)
            ic.pack(fill="both", expand=True, padx=ol(28), pady=ol(22))
            return ic
        k = Kaydirilabilir(self.icerik)
        k.pack(fill="both", expand=True)
        self.kaydirilabilir = k
        ic = tk.Frame(k.govde, bg=BG)
        ic.pack(fill="both", expand=True, padx=ol(28), pady=ol(22))
        return ic

    # -- sekme: yakala ----------------------------------------------------
    def _sekme_yakala(self):
        s = self._sayfa(kaydir=False)
        baslik(s, t("capture.title"), t("capture.subtitle"))

        kart = tk.Frame(s, bg=PANEL, highlightthickness=1, highlightbackground=KENAR)
        kart.pack(fill="x")
        ic = tk.Frame(kart, bg=PANEL)
        ic.pack(fill="x", padx=22, pady=20)
        b = dugme(ic, t("capture.now"), self._yakala_tikla)
        b.configure(font=(F, 12, "bold"), pady=12)
        b.pack(side="left")
        tk.Label(ic, text=t("capture.or", k=gosterim(self.cfg["kisayol"])),
                 bg=PANEL, fg=SOLUK, font=(F, 11)).pack(side="left", padx=16)

        for anahtar, k in (("capture.edit_hint", self.cfg["kisayol_duzelt"]),
                           ("capture.repeat_hint", self.cfg["kisayol_tekrar"])):
            tk.Label(kart, text=t(anahtar, k=gosterim(k)), bg=PANEL, fg=SOLUK,
                     font=(F, 9), anchor="w", justify="left",
                     wraplength=ol(560)).pack(fill="x", padx=22, pady=(0, 6))
        tk.Frame(kart, bg=PANEL, height=8).pack()

        ayirici(s)
        bolum(s, t("capture.last"))

        metin = self.app.son_metin or ""
        kutu = tk.Text(s, height=10, wrap="word", bg=PANEL,
                       fg=METIN if metin else SOLUK, relief="flat", padx=14,
                       pady=12, font=("Consolas", 10), highlightthickness=1,
                       highlightbackground=KENAR, insertbackground=METIN)
        kutu.pack(fill="both", expand=True)
        kutu.insert("1.0", metin or t("capture.nothing"))
        kutu.configure(state="disabled")

        if metin:
            alt = tk.Frame(s, bg=BG)
            alt.pack(fill="x", pady=(10, 0))
            dugme(alt, t("capture.copy_again"),
                  lambda: (self.app.panoya(metin),
                           self.bilgi(t("hist.copied"), "iyi"))).pack(side="left")
            tk.Label(alt, text=t("common.chars_lines", n=len(metin),
                                 l=metin.count("\n") + 1),
                     bg=BG, fg=SOLUK, font=(F, 9)).pack(side="left", padx=12)

    def _yakala_tikla(self):
        self.win.withdraw()
        self.app.root.after(220, lambda: self.app.yakala(False))

    # -- sekme: diller ----------------------------------------------------
    def _sekme_diller(self):
        s = self._sayfa()
        baslik(s, t("lang.title"), t("lang.subtitle"))
        self.dil_satirlari.clear()

        kurulu = self.app.diller
        secili = self.cfg["dil"]

        oto = tk.Frame(s, bg=PANEL, highlightthickness=1,
                       highlightbackground=VURGU if secili == "oto" else KENAR)
        oto.pack(fill="x", pady=(0, 14))
        ici = tk.Frame(oto, bg=PANEL)
        ici.pack(fill="x", padx=18, pady=14)
        tk.Label(ici, text=t("lang.auto"), bg=PANEL, fg=METIN,
                 font=(F, 11, "bold"), anchor="w").pack(side="left")
        tk.Label(ici, text=t("lang.auto_desc"), bg=PANEL, fg=SOLUK, font=(F, 9),
                 justify="left").pack(side="left")
        if secili == "oto":
            tk.Label(ici, text=t("btn.selected"), bg=PANEL, fg=VURGU,
                     font=(F, 9, "bold")).pack(side="right", padx=6)
        else:
            dugme(ici, t("btn.select"),
                  lambda: self._dil_sec("oto"), "sessiz").pack(side="right")

        bolum(s, t("lang.installed"), 4)
        kurulu_cerceve = tk.Frame(s, bg=BG)
        kurulu_cerceve.pack(fill="x")
        bolum(s, t("lang.available"), 18)
        indir_cerceve = tk.Frame(s, bg=BG)
        indir_cerceve.pack(fill="x")

        var, yok = [], []
        for satir in dl.OCR_DILLERI:
            etiket = satir[0]
            (var if dl.kurulu_mu(etiket, kurulu) else yok).append(
                (etiket, dl.gorunen_ad(etiket)))
        bilinen = {s_[0].split("-")[0].lower() for s_ in dl.OCR_DILLERI}
        for k in kurulu:                       # listede olmayan kurulu diller
            if k.split("-")[0].lower() not in bilinen:
                var.append((k, dl.gorunen_ad(k)))

        for etiket, ad in sorted(var, key=lambda x: x[1].lower()):
            self._dil_satiri(kurulu_cerceve, etiket, ad, True, kurulu, secili)
        if not var:
            tk.Label(kurulu_cerceve, text=t("lang.none"), bg=BG, fg=KIRMIZI,
                     font=(F, 10), anchor="w").pack(fill="x")
        for etiket, ad in sorted(yok, key=lambda x: x[1].lower()):
            self._dil_satiri(indir_cerceve, etiket, ad, False, kurulu, secili)

    def _dil_satiri(self, ust, etiket, ad, kurulu_mu, kurulu, secili):
        bu_secili = (kurulu_mu and secili != "oto"
                     and dl.kurulu_mu(etiket, [secili]))
        satir = tk.Frame(ust, bg=PANEL, highlightthickness=1,
                         highlightbackground=VURGU if bu_secili else KENAR)
        satir.pack(fill="x", pady=2)
        ic = tk.Frame(satir, bg=PANEL)
        ic.pack(fill="x", padx=16, pady=9)

        tk.Label(ic, text=ad, bg=PANEL, fg=METIN, font=(F, 10, "bold"),
                 anchor="w", width=26).pack(side="left")
        tk.Label(ic, text=etiket, bg=PANEL, fg=SOLUK, font=("Consolas", 9),
                 anchor="w", width=12).pack(side="left")

        sag = tk.Frame(ic, bg=PANEL)
        sag.pack(side="right")
        self.dil_satirlari[etiket] = sag

        if not kurulu_mu:
            dugme(sag, t("btn.download"),
                  lambda e=etiket, a=ad: self._dil_indir(e, a)).pack(side="right")
        elif bu_secili:
            tk.Label(sag, text=t("btn.selected"), bg=PANEL, fg=VURGU,
                     font=(F, 9, "bold")).pack(side="right", padx=6)
        else:
            # kurulu listedeki gerçek etiket kısa olabilir (tr-TR yerine tr)
            gercek = next((k for k in kurulu if dl.kurulu_mu(etiket, [k])), etiket)
            dugme(sag, t("btn.select"),
                  lambda g=gercek: self._dil_sec(g), "sessiz").pack(side="right")

    def _dil_sec(self, etiket):
        self.cfg["dil"] = etiket
        self.app.ayar_yaz()
        self.sekme_goster("diller")
        self.bilgi(t("lang.selected_toast",
                     ad=t("lang.auto") if etiket == "oto"
                     else dl.gorunen_ad(etiket)), "iyi")

    def _dil_indir(self, etiket, ad):
        if self.mesgul:
            return self.bilgi(t("lang.busy"), "kotu")
        self.mesgul = True
        sag = self.dil_satirlari.get(etiket)
        if sag is not None:
            try:
                for c in sag.winfo_children():
                    c.destroy()
                tk.Label(sag, text=t("btn.downloading"), bg=PANEL, fg=SARI,
                         font=(F, 9, "bold")).pack(side="right", padx=6)
            except tk.TclError:
                pass
        self.bilgi(t("lang.downloading", ad=ad), "normal", 9000)

        def calis():
            # root.after() thread guvenli DEGIL (createcommand ana thread ister);
            # arka plandan cagrilinca RuntimeError atiyor ve sonuc hic islenmiyordu.
            # Uygulamanin kuyrugu ana thread tarafindan bosaltiliyor, oradan gec.
            try:
                ok, mesaj = dl.dil_kur(etiket)
            except Exception as e:
                ok, mesaj = False, f"{type(e).__name__}: {e}"
            finally:
                self.mesgul = False        # ne olursa olsun kilit acik kalmasin
            self.app._tk_de_calistir(lambda: bitti(ok, mesaj))

        def bitti(ok, mesaj):
            self.mesgul = False
            if not self.win.winfo_exists():
                return
            self.app.ocr.unut()
            self.app.dilleri_tazele(ekstra=etiket)
            if self.aktif == "diller":
                self.sekme_goster("diller")
            if not ok:
                return self.bilgi(t("lang.failed", ad=ad, m=mesaj), "kotu", 12000)
            if dl.kurulu_mu(etiket, self.app.diller):
                return self.bilgi(t("lang.installed_toast", ad=ad), "iyi", 4000)
            # Paket kuruldu ama Windows'un dil listesi bu süreçte eskimiş:
            # yeniden başlatmadan görünmüyor.
            self.bilgi(t("lang.need_restart", ad=ad), "iyi", eylem=(
                t("btn.restart"), self.app.yeniden_baslat))

        threading.Thread(target=calis, daemon=True).start()

    # -- sekme: ayarlar ---------------------------------------------------
    def _sekme_ayarlar(self):
        s = self._sayfa()
        baslik(s, t("set.title"))

        bolum(s, t("set.iface_lang"))
        satir = tk.Frame(s, bg=BG)
        satir.pack(fill="x")
        for kod, ad in ceviri.DESTEKLENEN:
            secili = ceviri.aktif() == kod
            dugme(satir, ad, (lambda k=kod: self._arayuz_dili(k)),
                  "normal" if secili else "sessiz").pack(side="left", padx=(0, 8))

        ayirici(s)
        bolum(s, t("set.shortcuts"))
        tk.Label(s, text=t("set.altgr_warning"), bg=BG, fg=SARI, font=(F, 9),
                 anchor="w", justify="left",
                 wraplength=ol(560)).pack(fill="x", pady=(0, 12))

        for anahtar, etiket in (("kisayol", "set.hk_capture"),
                                ("kisayol_duzelt", "set.hk_edit"),
                                ("kisayol_tekrar", "set.hk_repeat"),
                                ("kisayol_biriktir", "set.hk_stack")):
            sat = tk.Frame(s, bg=BG)
            sat.pack(fill="x", pady=4)
            tk.Label(sat, text=t(etiket), bg=BG, fg=METIN, font=(F, 10),
                     anchor="w", width=26).pack(side="left")
            KisayolSecici(sat, self, self.cfg[anahtar],
                          lambda v, a=anahtar: self._kisayol_degisti(a, v)
                          ).pack(side="left")

        tk.Label(s, text=t("set.presets"), bg=BG, fg=SOLUK, font=(F, 9),
                 anchor="w", justify="left",
                 wraplength=ol(560)).pack(fill="x", pady=(14, 6))
        oner = tk.Frame(s, bg=BG)
        oner.pack(fill="x")
        for k in ONERILEN_KISAYOLLAR:
            dugme(oner, gosterim(k),
                  lambda kk=k: self._kisayol_degisti("kisayol", kk),
                  "sessiz").pack(side="left", padx=(0, 6))

        ayirici(s)
        bolum(s, t("set.format"))
        self.mod_var = tk.StringVar(value=self.cfg["satir_modu"])
        for mod, ad, aciklama in (
                ("satir", "set.mode_lines", "set.mode_lines_d"),
                ("akilli", "set.mode_smart", "set.mode_smart_d"),
                ("paragraf", "set.mode_para", "set.mode_para_d"),
                ("girinti", "set.mode_indent", "set.mode_indent_d"),
                ("tablo", "set.mode_table", "set.mode_table_d")):
            self._radyo(s, self.mod_var, mod, t(ad), t(aciklama),
                        lambda: self._ayar("satir_modu", self.mod_var.get()))

        ayirici(s)
        bolum(s, t("set.recognition"))
        self._onay(s, "buyutme", t("set.upscale"), t("set.upscale_d"))
        self._onay(s, "bant_birlestir", t("set.bandmerge"), t("set.bandmerge_d"))

        ayirici(s)
        bolum(s, t("set.behaviour"))
        self._onay(s, "bildirim", t("set.toast"))
        self._onay(s, "geri_yapistir", t("set.paste_back"),
                   t("set.paste_back_d"))
        self._onay(s, "gecmis_kaydet", t("set.history_file"),
                   t("set.history_file_d"))

        sat = tk.Frame(s, bg=BG)
        sat.pack(fill="x", pady=(10, 0))
        tk.Label(sat, text=t("set.dim"), bg=BG, fg=METIN, font=(F, 10),
                 anchor="w", width=30).pack(side="left")
        kaydirak = tk.Scale(sat, from_=0, to=80, orient="horizontal", length=ol(240),
                            bg=BG, fg=METIN, troughcolor=PANEL2,
                            highlightthickness=0, bd=0, sliderrelief="flat",
                            activebackground=VURGU, font=(F, 8))
        kaydirak.set(int(self.cfg["karartma"] * 100))
        kaydirak.configure(command=self._karartma_degisti)
        kaydirak.pack(side="left")

        ayirici(s)
        self.oto_var = tk.BooleanVar(value=dl.baslangica_ekli_mi())
        self._onay_ham(s, self.oto_var, t("set.autostart"), None,
                       self._otomatik_degisti)

    def _radyo(self, ust, var, deger, ad, aciklama, komut):
        c = tk.Frame(ust, bg=BG)
        c.pack(fill="x", pady=2)
        tk.Radiobutton(c, variable=var, value=deger, text=ad, command=komut,
                       bg=BG, fg=METIN, selectcolor=PANEL2, activebackground=BG,
                       activeforeground=METIN, font=(F, 10), anchor="w",
                       highlightthickness=0, bd=0, cursor="hand2").pack(anchor="w")
        if aciklama:
            tk.Label(c, text=aciklama, bg=BG, fg=SOLUK, font=(F, 9), anchor="w",
                     justify="left", wraplength=ol(520)).pack(fill="x",
                                                              padx=(24, 0))

    def _onay(self, ust, anahtar, ad, aciklama=None):
        var = tk.BooleanVar(value=bool(self.cfg[anahtar]))
        self._onay_ham(ust, var, ad, aciklama,
                       lambda: self._ayar(anahtar, var.get()))

    def _onay_ham(self, ust, var, ad, aciklama, komut):
        c = tk.Frame(ust, bg=BG)
        c.pack(fill="x", pady=2)
        tk.Checkbutton(c, variable=var, text=ad, command=komut, bg=BG, fg=METIN,
                       selectcolor=PANEL2, activebackground=BG,
                       activeforeground=METIN, font=(F, 10), anchor="w",
                       highlightthickness=0, bd=0, cursor="hand2").pack(anchor="w")
        if aciklama:
            tk.Label(c, text=aciklama, bg=BG, fg=SOLUK, font=(F, 9), anchor="w",
                     justify="left", wraplength=ol(520)).pack(fill="x",
                                                              padx=(24, 0))

    def _ayar(self, anahtar, deger):
        self.cfg[anahtar] = deger
        self.app.ayar_yaz()

    def _arayuz_dili(self, kod):
        if ceviri.aktif() == kod:
            return
        self.app.arayuz_dilini_ayarla(kod)
        self._serit_ciz()
        self.sekme_goster("ayarlar")

    def _karartma_degisti(self, v):
        """Kaydırak her pikselde tetikleniyor; diske yazmayı geciktiriyoruz."""
        self.cfg["karartma"] = int(v) / 100
        if self._karartma_is:
            self.win.after_cancel(self._karartma_is)
        self._karartma_is = self.win.after(400, self.app.ayar_yaz)

    def _kisayol_degisti(self, anahtar, yeni):
        if yeni == self.cfg[anahtar]:
            return
        digerleri = [a for a in ("kisayol", "kisayol_duzelt", "kisayol_tekrar",
                                 "kisayol_biriktir") if a != anahtar]
        if any(self.cfg[a] == yeni for a in digerleri):
            self.sekme_goster("ayarlar")
            return self.bilgi(t("set.hk_taken"), "kotu")

        eski = self.cfg[anahtar]
        self.cfg[anahtar] = yeni
        # Yalnizca DEGISTIRILEN islev kaydedilemediyse geri al: baska bir
        # kisayol baska uygulamada tutuluysa da hatalar dolu doner ve eskiden
        # hicbir kisayol degistirilemiyordu.
        if anahtar in self.app.kisayollari_yenile():
            self.cfg[anahtar] = eski
            self.app.kisayollari_yenile()
            self.sekme_goster("ayarlar")
            return self.bilgi(t("set.hk_failed"), "kotu", 6000)
        self.app.ayar_yaz()
        self.sekme_goster("ayarlar")
        self.bilgi(t("set.hk_set", k=gosterim(yeni)), "iyi")

    def _otomatik_degisti(self):
        ok, mesaj = dl.baslangici_ayarla(
            self.oto_var.get(), self.app.pythonw_yolu(), self.app.betik_yolu())
        if ok:
            self.bilgi(t("hist.saved"), "iyi", 1500)
        else:
            self.bilgi(mesaj, "kotu")
            self.oto_var.set(dl.baslangica_ekli_mi())

    # -- sekme: geçmiş ----------------------------------------------------
    def _sekme_gecmis(self):
        s = self._sayfa(kaydir=False)
        baslik(s, t("hist.title"),
               t("hist.subtitle", n=self.cfg["gecmis_boyut"]))
        self._gecmis_kirli = False

        if not self.app.gecmis:
            tk.Label(s, text=t("hist.empty"), bg=BG, fg=SOLUK, font=(F, 11),
                     anchor="w").pack(fill="x")
            return

        bolme = tk.Frame(s, bg=BG)
        bolme.pack(fill="both", expand=True)

        solk = Kaydirilabilir(bolme, width=ol(290))
        solk.pack(side="left", fill="y", padx=(0, ol(14)))
        solk.pack_propagate(False)
        self.kaydirilabilir = solk

        sag = tk.Frame(bolme, bg=BG)
        sag.pack(side="left", fill="both", expand=True)
        tk.Label(sag, text=t("hist.edit_hint"), bg=BG, fg=SOLUK, font=(F, 8),
                 anchor="w").pack(fill="x", pady=(0, 4))
        self.gecmis_kutu = tk.Text(sag, wrap="word", bg=PANEL, fg=METIN,
                                   relief="flat", padx=14, pady=12,
                                   font=("Consolas", 10), highlightthickness=1,
                                   highlightbackground=KENAR, undo=True,
                                   insertbackground=METIN)
        self.gecmis_kutu.pack(fill="both", expand=True)
        self.gecmis_kutu.bind("<<Modified>>", self._gecmis_yazildi)
        self.gecmis_kutu.bind("<Control-s>", lambda e: (self._gecmis_kaydet(),
                                                        "break")[1])
        self.gecmis_kutu.bind("<Control-Return>", lambda e: (self._gecmis_kopyala(),
                                                             "break")[1])

        self._gecmis_kartlar = []
        for i, kayit in enumerate(self.app.gecmis):
            ozet = " ".join(kayit["metin"].split())
            ozet = (ozet[:32] + "…") if len(ozet) > 32 else ozet
            kart = tk.Frame(solk.govde, bg=PANEL, highlightthickness=1,
                            highlightbackground=KENAR, cursor="hand2")
            kart.pack(fill="x", pady=2, padx=(0, ol(4)))
            e1 = tk.Label(kart, text=ozet or t("common.empty"), bg=PANEL,
                          fg=METIN, font=(F, 10), anchor="w", padx=12)
            e1.pack(fill="x", pady=(8, 0))
            e2 = tk.Label(kart, text=(kayit["zaman"] + "  ·  " if kayit["zaman"]
                                      else "") + t("common.chars",
                                                   n=len(kayit["metin"])),
                          bg=PANEL, fg=SOLUK, font=(F, 8), anchor="w", padx=12)
            e2.pack(fill="x", pady=(0, 8))
            for wdg in (kart, e1, e2):
                wdg.bind("<Button-1>", lambda e, k=i: self._gecmis_sec(k))
            self._gecmis_kartlar.append(kart)

        alt = tk.Frame(s, bg=BG)
        alt.pack(fill="x", pady=(12, 0))
        self.kaydet_dugmesi = dugme(alt, t("btn.save"), self._gecmis_kaydet,
                                    "sessiz")
        self.kaydet_dugmesi.pack(side="left")
        dugme(alt, t("btn.copy"), self._gecmis_kopyala).pack(side="left", padx=8)
        dugme(alt, t("btn.delete"), self._gecmis_sil, "tehlike").pack(side="left")
        dugme(alt, t("hist.clear_all"), self._gecmis_temizle,
              "tehlike").pack(side="right")

        i = self.app.gecmis_bul(self._gecmis_id)
        self._gecmis_goster(i if i >= 0 else 0)

    def _gecmis_goster(self, i):
        i = max(0, min(i, len(self.app.gecmis) - 1))
        self._gecmis_id = self.app.gecmis[i]["id"]
        for j, k in enumerate(self._gecmis_kartlar):
            k.configure(highlightbackground=VURGU if j == i else KENAR)
        self.gecmis_kutu.delete("1.0", "end")
        self.gecmis_kutu.insert("1.0", self.app.gecmis[i]["metin"])
        self.gecmis_kutu.edit_modified(False)
        self.gecmis_kutu.edit_reset()
        self._gecmis_kirli = False
        self._kaydet_dugmesini_tazele()

    def _gecmis_sec(self, i):
        if 0 <= i < len(self.app.gecmis) and                 self.app.gecmis[i]["id"] == self._gecmis_id:
            return
        self._gecmis_kaydet_sessiz()       # düzenleme kaybolmasın
        self._gecmis_goster(i)

    def _gecmis_yazildi(self, _e):
        """<<Modified>> programla yapilan insert'te de tetiklendigi icin bayraga
        guvenilmiyor; metin gercekten kayittan farkli mi diye bakiliyor. Yan
        faydasi: kullanici degisikligi geri alirsa Kaydet sonuyor."""
        try:
            self.gecmis_kutu.edit_modified(False)
            kirli = self._gecmis_metni() != self._secili_kayit()
        except (tk.TclError, IndexError):
            return
        if kirli != self._gecmis_kirli:
            self._gecmis_kirli = kirli
            self._kaydet_dugmesini_tazele()

    def _secili_kayit(self):
        i = self.app.gecmis_bul(self._gecmis_id)
        if i < 0:
            raise IndexError("kayit artik yok")
        return self.app.gecmis[i]["metin"]

    def _kaydet_dugmesini_tazele(self):
        try:
            self.kaydet_dugmesi.configure(
                bg=VURGU if self._gecmis_kirli else PANEL2,
                fg="white" if self._gecmis_kirli else METIN)
        except (tk.TclError, AttributeError):
            pass

    def _gecmis_metni(self):
        return self.gecmis_kutu.get("1.0", "end-1c")

    def _gecmis_kaydet(self):
        if not self.app.gecmis:
            return
        self.app.gecmis_guncelle(self._gecmis_id, self._gecmis_metni())
        self._gecmis_kirli = False
        self._kaydet_dugmesini_tazele()
        self.sekme_goster("gecmis")
        self.bilgi(t("hist.saved"), "iyi", 1800)

    def _gecmis_kaydet_sessiz(self):
        """Sekme/kayıt değişiminde kaydedilmemiş düzenlemeyi sessizce korur."""
        if not self._gecmis_kirli:
            return
        try:
            metin = self._gecmis_metni()
            farkli = metin != self._secili_kayit()
        except (tk.TclError, AttributeError, IndexError):
            self._gecmis_kirli = False
            return
        if farkli:
            self.app.gecmis_guncelle(self._gecmis_id, metin)
        self._gecmis_kirli = False

    def _gecmis_kopyala(self):
        self._gecmis_kaydet_sessiz()
        self.app.panoya(self._gecmis_metni())
        self.bilgi(t("hist.copied"), "iyi", 1800)

    def _gecmis_sil(self):
        self._gecmis_kirli = False
        i = self.app.gecmis_bul(self._gecmis_id)
        self.app.gecmis_sil(self._gecmis_id)
        kalan = self.app.gecmis
        self._gecmis_id = kalan[min(max(i, 0), len(kalan) - 1)]["id"] if kalan else None
        self.sekme_goster("gecmis")
        self.bilgi(t("hist.deleted"), "iyi", 1800)

    def _gecmis_temizle(self):
        self._gecmis_kirli = False
        self._gecmis_id = None
        self.app.gecmis_temizle()
        self.sekme_goster("gecmis")
        self.bilgi(t("hist.cleared"), "iyi", 1800)

    # -- sekme: hakkında --------------------------------------------------
    def _sekme_hakkinda(self):
        s = self._sayfa()
        baslik(s, t("about.title"))

        import metinkap as mkmod
        tk.Label(s, text=f"MetinKap {mkmod.__version__}", bg=BG, fg=METIN,
                 font=(F, 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(s, text=t("about.desc"), bg=BG, fg=SOLUK, font=(F, 10),
                 anchor="w", justify="left",
                 wraplength=ol(540)).pack(fill="x", pady=(4, 16))

        bolum(s, t("about.accuracy"))
        tablo = tk.Frame(s, bg=PANEL, highlightthickness=1, highlightbackground=KENAR)
        tablo.pack(fill="x")
        satirlar = [(t("about.col_size"), t("about.col_raw"), "×2", t("about.col_x3")),
                    ("11pt", "94.0%", "97.4%", "99.6%"),
                    ("14pt", "96.6%", "95.8%", "98.5%"),
                    ("18pt", "99.6%", "100%", "100%")]
        for i, sat in enumerate(satirlar):
            c = tk.Frame(tablo, bg=PANEL)
            c.pack(fill="x", padx=16,
                   pady=(10 if i == 0 else 3, 10 if i == len(satirlar) - 1 else 3))
            for h in sat:
                tk.Label(c, text=h, bg=PANEL, fg=SOLUK if i == 0 else METIN,
                         font=(F, 9, "bold") if i == 0 else (F, 10),
                         anchor="w", width=16).pack(side="left")
        tk.Label(s, text=t("about.accuracy_note"), bg=BG, fg=SOLUK, font=(F, 9),
                 anchor="w", justify="left",
                 wraplength=ol(540)).pack(fill="x", pady=(8, 16))

        bolum(s, t("about.files"))
        for anahtar, yol in self.app.yollar():
            c = tk.Frame(s, bg=BG)
            c.pack(fill="x", pady=1)
            tk.Label(c, text=t(anahtar), bg=BG, fg=SOLUK, font=(F, 9), anchor="w",
                     width=20).pack(side="left")
            tk.Label(c, text=yol, bg=BG, fg=METIN, font=("Consolas", 8), anchor="w",
                     justify="left", wraplength=ol(430)).pack(side="left")

        c = tk.Frame(s, bg=BG)
        c.pack(fill="x", pady=(16, 0))
        dugme(c, t("about.open_folder"),
              lambda: os.startfile(self.app.veri_klasoru()), "sessiz").pack(side="left")
        dugme(c, t("about.quit"), self.app.cikis, "tehlike").pack(side="left", padx=8)
