"""Arayüz dili. Varsayılan İngilizce; eksik anahtar İngilizceye düşer.

Kullanım:  from ceviri import t  ->  t("tab.capture")
           t("toast.copied", n=12) ile alan doldurulur.
"""

DESTEKLENEN = [("en", "English"), ("tr", "Türkçe")]

_AKTIF = "en"


def dili_ayarla(kod):
    global _AKTIF
    _AKTIF = kod if kod in dict(DESTEKLENEN) else "en"
    return _AKTIF


def aktif():
    return _AKTIF


def t(anahtar, **kw):
    tablo = TR if _AKTIF == "tr" else EN
    s = tablo.get(anahtar) or EN.get(anahtar) or anahtar
    if kw:
        try:
            return s.format(**kw)
        except (KeyError, IndexError, ValueError):
            return s
    return s


EN = {
    # --- genel ---
    "app.tagline": "Grab text from anywhere on screen",
    "btn.change": "Change",
    "btn.copy": "Copy",
    "btn.close": "Close",
    "btn.save": "Save",
    "btn.delete": "Delete",
    "btn.select": "Select",
    "btn.selected": "selected",
    "btn.download": "Download",
    "btn.hide": "Hide",
    "btn.downloading": "downloading…",
    "btn.restart": "Restart now",
    "common.chars": "{n} characters",
    "common.chars_lines": "{n} characters · {l} lines",
    "common.empty": "(empty)",

    # --- sekmeler ---
    "tab.capture": "Capture",
    "tab.languages": "Languages",
    "tab.settings": "Settings",
    "tab.history": "History",
    "tab.about": "About",
    "side.status": "{k}\n{n} OCR languages",
    "side.keeps_running": "Keeps running\nin the tray",

    # --- yakala sekmesi ---
    "capture.title": "Grab text from the screen",
    "capture.subtitle": "Press the shortcut, drag over the area, paste anywhere.",
    "capture.now": "  Capture now  ",
    "capture.or": "or {k}",
    "capture.edit_hint": "Edit before copying: {k}   ·   Holding Shift while releasing "
                         "the selection does the same",
    "capture.repeat_hint": "Re-grab the last area without selecting again: {k}",
    "capture.last": "Last capture",
    "capture.nothing": "Nothing captured yet.",
    "capture.copy_again": "Copy again",

    # --- diller sekmesi ---
    "lang.title": "OCR languages",
    "lang.subtitle": "The language pack must be installed in Windows. Installing asks "
                     "for administrator permission and downloads through Windows Update.",
    "lang.auto": "Automatic",
    "lang.auto_desc": "  tries the installed languages and keeps\n  the one that reads "
                      "the most (slightly slower)",
    "lang.installed": "Installed",
    "lang.available": "Available to download",
    "lang.none": "No OCR language is installed.",
    "lang.selected_toast": "OCR language: {ad}",
    "lang.busy": "An installation is already running.",
    "lang.downloading": "Downloading {ad}. Windows will ask for administrator "
                        "permission; this can take a few minutes.",
    "lang.installed_toast": "{ad} installed.",
    "lang.failed": "Could not install {ad}: {m}",
    "lang.need_restart": "{ad} was installed. Windows only reveals a new OCR "
                         "language to a freshly started program, so MetinKap "
                         "needs a restart to list it.",

    # --- ayarlar sekmesi ---
    "set.title": "Settings",
    "set.iface_lang": "Interface language",
    "set.shortcuts": "Shortcuts",
    "set.altgr_warning": "Avoid Ctrl+Alt: on a Turkish keyboard it is the same as AltGr, "
                         "so a Ctrl+Alt shortcut breaks typing characters like ₺. "
                         "Ctrl+Shift combinations are safe.",
    "set.hk_capture": "Capture and copy",
    "set.hk_edit": "Capture, edit, copy",
    "set.hk_repeat": "Re-grab last area",
    "set.hk_stack": "Stacking mode on/off",
    "set.presets": "Ready-made options for the capture shortcut — each can be pressed "
                   "with one hand and none clash with AltGr:",
    "set.format": "Text layout",
    "set.mode_lines": "Keep lines",
    "set.mode_lines_d": "Leaves the text as it looks on screen.",
    "set.mode_smart": "Join wrapped lines",
    "set.mode_smart_d": "Rejoins lines broken by wrapping and by hyphens, while "
                        "keeping separate sentences apart.",
    "set.mode_para": "Single paragraph",
    "set.mode_para_d": "Puts everything on one line.",
    "set.mode_indent": "Keep indentation (code)",
    "set.mode_indent_d": "Rebuilds leading indentation from where each line "
                         "starts on screen. Windows OCR drops leading spaces, "
                         "so pasted code loses its shape without this.",
    "set.mode_table": "Table (Markdown)",
    "set.mode_table_d": "Finds columns from word positions and writes a Markdown "
                        "table, so a pasted table keeps its rows and columns.",
    "set.recognition": "Recognition",
    "set.upscale": "Upscale small selections",
    "set.upscale_d": "Measured effect is large: small text is often not read at all "
                     "without it. Leave this on.",
    "set.bandmerge": "Rejoin split lines",
    "set.bandmerge_d": "Collects pieces that a wide gap split into separate lines. "
                       "Columns in two-column text stay apart.",
    "set.behaviour": "Behaviour",
    "set.toast": "Show the copied notification",
    "set.paste_back": "Paste back into the window you came from",
    "set.paste_back_d": "After copying, brings the window that was in front "
                        "before the capture back and sends Ctrl+V. It waits for "
                        "you to let go of the shortcut keys first, and does "
                        "nothing if focus did not return to that window.",
    "set.history_file": "Keep history between restarts",
    "set.history_file_d": "Captures are stored in history.json so they survive a "
                          "restart, and appended to history.txt with a timestamp.",
    "set.dim": "Selection screen dimming",
    "set.autostart": "Start with Windows",
    "set.hk_taken": "That shortcut is already used by another MetinKap action.",
    "set.hk_failed": "Could not register — another app may be using it. Try a "
                     "different combination.",
    "set.hk_set": "Shortcut: {k}",
    "set.press_keys": "Press the key combination…",
    "set.key_unusable": "That key cannot be used as a shortcut.",
    "set.need_modifier": "Add at least one modifier (Ctrl / Alt / Shift / Win).",
    "set.save_failed": "Could not save — config.json could not be written. "
                       "See error.log.",

    # --- geçmiş sekmesi ---
    "hist.title": "History",
    "hist.subtitle": "Last {n} captures. Click one, edit it on the right, copy it back.",
    "hist.empty": "Nothing captured yet.",
    "hist.copied": "Copied to clipboard.",
    "hist.saved": "Saved.",
    "hist.deleted": "Entry deleted.",
    "hist.cleared": "History cleared.",
    "hist.clear_failed": "History was cleared here, but the file on disk could not be removed. See error.log.",
    "hist.clear_all": "Clear all",
    "hist.unsaved": "Unsaved changes — press Save or they are lost when you switch.",
    "hist.edit_hint": "Editable · Ctrl+S saves, Ctrl+Enter copies",

    # --- hakkında sekmesi ---
    "about.title": "About",
    "about.desc": "Grabs text from anywhere on screen and puts it on the clipboard. "
                  "Uses the OCR engine built into Windows: no install, no internet. "
                  "Reading takes about 15 ms for a line, 100 ms for a paragraph and "
                  "250 ms for a screenful.",
    "about.accuracy": "Measured accuracy",
    "about.col_scale": "Upscale",
    "about.col_acc": "Accuracy",
    "about.used": "(used)",
    "about.accuracy_note": "Measured over 6 fonts × 6 sizes, on text containing numbers "
                           "and punctuation. ×3 reads clean prose slightly better but "
                           "corrupts figures, so ×2.5 is used. Contrast stretching and "
                           "greyscale conversion were tried and dropped — both lowered "
                           "accuracy.",
    "about.files": "Files",
    "about.open_folder": "Open data folder",
    "about.quit": "Quit MetinKap",
    "about.f_settings": "Settings",
    "about.f_history": "History",
    "about.f_crop": "Last crop",
    "about.f_log": "Error log",
    "about.f_source": "Source",

    # --- tepsi menüsü ---
    "tray.settings": "Settings…",
    "tray.capture": "Capture  ({k})",
    "tray.capture_edit": "Capture + edit  ({k})",
    "tray.repeat": "Re-grab last area  ({k})",
    "tray.stack_start": "Start stacking  ({k})",
    "tray.stack_finish": "Finish stacking — copy {n} piece(s)",
    "tray.language": "Language",
    "tray.download_lang": "Download a language…",
    "tray.line_mode": "Text layout",
    "tray.copy_last": "Copy last text again",
    "tray.history": "History",
    "tray.quit": "Quit",

    # --- seçim ekranı / baloncuklar ---
    "sel.hint": "Drag to select   ·   hold Shift on release: edit before copying"
                "   ·   Enter: last area   ·   Esc: cancel",
    "toast.ready": "MetinKap ready  ·  {k}\nLanguage: {d}",
    "toast.copied": "Copied · {bilgi}\n{onizleme}",
    "toast.pasted": "Pasted · {bilgi}\n{onizleme}",
    "toast.info": "{n} characters · {l} lines",
    "toast.info_ms": "{n} characters · {l} lines · {ms} ms",
    "toast.no_text": "No text found.\nSelect a wider area, or change the language "
                     "in Settings.",
    "toast.no_clipboard": "Could not write to the clipboard.",
    "toast.ocr_fail": "OCR error: {e}",
    "toast.no_ocr": "OCR is not ready.",
    "toast.no_grab": "Could not capture the screen.",
    "toast.no_last_area": "No previous area yet — capture something first.",
    "toast.stack_on": "Stacking on. Captures are collected instead of copied. "
                      "Press {k} again to copy them all.",
    "toast.stack_added": "Stacked: {n} piece(s). {k} finishes.",
    "toast.stack_done": "{n} pieces copied as one ({c} characters).",
    "toast.stack_empty": "Stacking off — nothing was collected.",
    "toast.hk_failed": "Could not register shortcut:\n{h}\nPick another key in Settings.",
    "toast.no_winrt": "OCR modules failed to load.\nSee error.log.",
    "toast.ui_failed": "Could not open the settings window.\nSee error.log.",

    # --- düzeltme penceresi ---
    "edit.title": "MetinKap — edit text",
    "edit.hint": "Ctrl+Enter copies, Esc closes",

    # --- mesaj kutuları ---
    "msg.running": "MetinKap is already running.\nOpening its settings window.",
    "msg.start_failed": "Could not start. Details:\n{p}",
}

TR = {
    "app.tagline": "Ekranın herhangi bir yerinden metin yakala",
    "btn.change": "Değiştir",
    "btn.copy": "Kopyala",
    "btn.close": "Kapat",
    "btn.save": "Kaydet",
    "btn.delete": "Sil",
    "btn.select": "Seç",
    "btn.selected": "seçili",
    "btn.download": "İndir",
    "btn.hide": "Gizle",
    "btn.downloading": "indiriliyor…",
    "btn.restart": "Şimdi yeniden başlat",
    "common.chars": "{n} karakter",
    "common.chars_lines": "{n} karakter · {l} satır",
    "common.empty": "(boş)",

    "tab.capture": "Yakala",
    "tab.languages": "Diller",
    "tab.settings": "Ayarlar",
    "tab.history": "Geçmiş",
    "tab.about": "Hakkında",
    "side.status": "{k}\n{n} OCR dili kurulu",
    "side.keeps_running": "Tepside çalışmaya\ndevam eder",

    "capture.title": "Ekrandan metin yakala",
    "capture.subtitle": "Kısayola bas, alanı sürükle, istediğin yere yapıştır.",
    "capture.now": "  Şimdi yakala  ",
    "capture.or": "veya {k}",
    "capture.edit_hint": "Kopyalamadan önce düzelt: {k}   ·   Seçimi bırakırken Shift'e "
                         "basılı tutmak da aynısını yapar",
    "capture.repeat_hint": "Son alanı tekrar seçmeden yakala: {k}",
    "capture.last": "Son yakalanan",
    "capture.nothing": "Henüz bir şey yakalamadın.",
    "capture.copy_again": "Tekrar kopyala",

    "lang.title": "OCR dilleri",
    "lang.subtitle": "Okunacak dilin paketi Windows'ta kurulu olmalı. Kurulum yönetici "
                     "izni ister ve Windows Update üzerinden indirilir.",
    "lang.auto": "Otomatik",
    "lang.auto_desc": "  kurulu dilleri dener, en çok metin\n  çıkaranı seçer "
                      "(biraz daha yavaş)",
    "lang.installed": "Kurulu diller",
    "lang.available": "İndirilebilir diller",
    "lang.none": "Kurulu OCR dili yok.",
    "lang.selected_toast": "OCR dili: {ad}",
    "lang.busy": "Zaten bir kurulum sürüyor.",
    "lang.downloading": "{ad} indiriliyor. Windows yönetici izni isteyecek, "
                        "indirme birkaç dakika sürebilir.",
    "lang.installed_toast": "{ad} kuruldu.",
    "lang.failed": "{ad} kurulamadı: {m}",
    "lang.need_restart": "{ad} kuruldu. Windows yeni bir OCR dilini ancak yeni "
                         "başlatılan bir programa gösteriyor, bu yüzden listede "
                         "görünmesi için MetinKap'ın yeniden başlaması gerekiyor.",

    "set.title": "Ayarlar",
    "set.iface_lang": "Arayüz dili",
    "set.shortcuts": "Kısayollar",
    "set.altgr_warning": "Ctrl+Alt kullanma: Türkçe klavyede AltGr ile aynı şey, o yüzden "
                         "Ctrl+Alt'lı bir kısayol ₺ gibi karakterleri yazamaz hale "
                         "getirir. Ctrl+Shift'li kombinasyonlar güvenli.",
    "set.hk_capture": "Yakala ve kopyala",
    "set.hk_edit": "Yakala, düzelt, kopyala",
    "set.hk_repeat": "Son alanı tekrar yakala",
    "set.hk_stack": "Biriktirme modu aç/kapa",
    "set.presets": "Yakala kısayolu için hazır seçenekler — hepsi tek elle basılabilir "
                   "ve AltGr ile çakışmaz:",
    "set.format": "Metin biçimi",
    "set.mode_lines": "Satırları koru",
    "set.mode_lines_d": "Ekranda göründüğü gibi bırakır.",
    "set.mode_smart": "Akıllı birleştir",
    "set.mode_smart_d": "Satır sonu bölünmelerini ve kelime- tirelerini birleştirir, "
                        "ayrı cümleleri ayrı tutar.",
    "set.mode_para": "Tek paragraf",
    "set.mode_para_d": "Her şeyi tek satır yapar.",
    "set.mode_indent": "Girintiyi koru (kod)",
    "set.mode_indent_d": "Her satırın ekranda nereden başladığına bakıp baştaki "
                         "girintiyi geri kurar. Windows OCR baştaki boşlukları "
                         "yuttuğu için kod bu olmadan şeklini kaybediyor.",
    "set.mode_table": "Tablo (Markdown)",
    "set.mode_table_d": "Kelime konumlarından sütunları bulup Markdown tablosu "
                        "yazar; yapıştırılan tablo satır ve sütunlarını korur.",
    "set.recognition": "Tanıma",
    "set.upscale": "Küçük seçimleri büyüt",
    "set.upscale_d": "Ölçülen etkisi büyük: küçük yazılar bu olmadan çoğu zaman hiç "
                     "okunmuyor. Açık kalsın.",
    "set.bandmerge": "Bölünmüş satırları birleştir",
    "set.bandmerge_d": "Geniş boşluk yüzünden ayrı satırlara bölünmüş parçaları toparlar. "
                       "İki sütunlu metinde sütunlar ayrı kalır.",
    "set.behaviour": "Davranış",
    "set.toast": "Kopyalandı bildirimini göster",
    "set.paste_back": "Geldiğin pencereye geri yapıştır",
    "set.paste_back_d": "Kopyaladıktan sonra, yakalamadan önce önde olan "
                        "pencereyi geri getirip Ctrl+V gönderir. Önce kısayol "
                        "tuşlarını bırakmanı bekler; odak o pencereye dönmediyse "
                        "hiçbir şey yapmaz.",
    "set.history_file": "Geçmişi kapanışlar arasında sakla",
    "set.history_file_d": "Yakalamalar gecmis.json içinde tutulur, uygulama kapanınca "
                          "kaybolmaz; ayrıca gecmis.txt'ye zaman damgasıyla eklenir.",
    "set.dim": "Seçim ekranı karartması",
    "set.autostart": "Windows ile başlat",
    "set.hk_taken": "Bu kısayol MetinKap'ın başka bir işlevinde kullanılıyor.",
    "set.hk_failed": "Kaydedilemedi — başka bir uygulama kullanıyor olabilir. "
                     "Başka bir kombinasyon dene.",
    "set.hk_set": "Kısayol: {k}",
    "set.press_keys": "Tuş kombinasyonuna bas…",
    "set.key_unusable": "Bu tuş kısayol olarak kullanılamıyor.",
    "set.need_modifier": "En az bir yardımcı tuş gerekli (Ctrl / Alt / Shift / Win).",
    "set.save_failed": "Kaydedilemedi — config.json yazılamadı. "
                       "hata.log dosyasına bak.",

    "hist.title": "Geçmiş",
    "hist.subtitle": "Son {n} yakalama. Birine tıkla, sağda düzenle, geri kopyala.",
    "hist.empty": "Henüz bir şey yakalamadın.",
    "hist.copied": "Panoya kopyalandı.",
    "hist.saved": "Kaydedildi.",
    "hist.deleted": "Kayıt silindi.",
    "hist.cleared": "Geçmiş temizlendi.",
    "hist.clear_failed": "Geçmiş burada temizlendi ama diskteki dosya silinemedi. hata.log dosyasına bak.",
    "hist.clear_all": "Hepsini temizle",
    "hist.unsaved": "Kaydedilmemiş değişiklik var — Kaydet'e bas, yoksa geçince kaybolur.",
    "hist.edit_hint": "Düzenlenebilir · Ctrl+S kaydeder, Ctrl+Enter kopyalar",

    "about.title": "Hakkında",
    "about.desc": "Ekranın herhangi bir yerinden metni alıp panoya koyar. Windows'un "
                  "kendi OCR motorunu kullanır: kurulum yok, internet yok. Okuma "
                  "bir satır için ~15 ms, bir paragraf için ~100 ms, ekran dolusu "
                  "için ~250 ms sürüyor.",
    "about.accuracy": "Ölçülen doğruluk",
    "about.col_scale": "Büyütme",
    "about.col_acc": "Doğruluk",
    "about.used": "(kullanılan)",
    "about.accuracy_note": "6 font × 6 punto üzerinde, sayı ve noktalama içeren metinle "
                           "ölçüldü. ×3 temiz metni biraz daha iyi okuyor ama sayıları "
                           "bozuyor, o yüzden ×2.5 kullanılıyor. Kontrast artırma ve gri "
                           "dönüşümü denendi, ikisi de doğruluğu düşürdüğü için elendi.",
    "about.files": "Dosyalar",
    "about.open_folder": "Veri klasörünü aç",
    "about.quit": "MetinKap'tan çık",
    "about.f_settings": "Ayarlar",
    "about.f_history": "Geçmiş",
    "about.f_crop": "Son kırpım",
    "about.f_log": "Hata kaydı",
    "about.f_source": "Kaynak",

    "tray.settings": "Ayarlar…",
    "tray.capture": "Yakala  ({k})",
    "tray.capture_edit": "Yakala + düzelt  ({k})",
    "tray.repeat": "Son alanı tekrar yakala  ({k})",
    "tray.stack_start": "Biriktirmeye başla  ({k})",
    "tray.stack_finish": "Biriktirmeyi bitir — {n} parçayı kopyala",
    "tray.language": "Dil",
    "tray.download_lang": "Dil indir…",
    "tray.line_mode": "Metin biçimi",
    "tray.copy_last": "Son metni tekrar kopyala",
    "tray.history": "Geçmiş",
    "tray.quit": "Çıkış",

    "sel.hint": "Sürükleyerek seç   ·   bırakırken Shift: kopyalamadan önce düzelt"
                "   ·   Enter: son alan   ·   Esc: iptal",
    "toast.ready": "MetinKap hazır  ·  {k}\nDil: {d}",
    "toast.copied": "Kopyalandı · {bilgi}\n{onizleme}",
    "toast.pasted": "Yapıştırıldı · {bilgi}\n{onizleme}",
    "toast.info": "{n} karakter · {l} satır",
    "toast.info_ms": "{n} karakter · {l} satır · {ms} ms",
    "toast.no_text": "Metin bulunamadı.\nDaha geniş bir alan seç ya da Ayarlar'dan "
                     "dili değiştir.",
    "toast.no_clipboard": "Panoya yazılamadı.",
    "toast.ocr_fail": "OCR hatası: {e}",
    "toast.no_ocr": "OCR hazır değil.",
    "toast.no_grab": "Ekran yakalanamadı.",
    "toast.no_last_area": "Henüz bir alan yok — önce bir şey yakala.",
    "toast.stack_on": "Biriktirme açık. Yakaladıkların kopyalanmak yerine "
                      "toplanıyor. Hepsini kopyalamak için tekrar {k}.",
    "toast.stack_added": "Biriktirildi: {n} parça. {k} bitirir.",
    "toast.stack_done": "{n} parça tek seferde kopyalandı ({c} karakter).",
    "toast.stack_empty": "Biriktirme kapandı — hiçbir şey toplanmamıştı.",
    "toast.hk_failed": "Kısayol kaydedilemedi:\n{h}\nAyarlardan başka bir tuş seç.",
    "toast.no_winrt": "OCR modülleri yüklenemedi.\nhata.log dosyasına bak.",
    "toast.ui_failed": "Ayar penceresi açılamadı.\nhata.log dosyasına bak.",

    "edit.title": "MetinKap — metni düzelt",
    "edit.hint": "Ctrl+Enter kopyalar, Esc kapatır",

    "msg.running": "MetinKap zaten çalışıyor.\nAyar penceresi açılıyor.",
    "msg.start_failed": "Başlatılamadı. Ayrıntı:\n{p}",
}
