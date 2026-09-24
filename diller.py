"""Windows OCR dil paketlerini listeler ve kurar.

Windows OCR dilleri pip ile değil, Windows'un kendi "capability" sistemiyle
gelir: Language.OCR~~~<etiket>~0.0.1.0. Kurmak yönetici yetkisi ister, bu
yüzden kurulum UAC onayıyla ayrı bir işlemde çalıştırılır.
"""

import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import tempfile

from ceviri import aktif as _dil

# (capability etiketi, İngilizce ad, Türkçe ad). Etiketler capability
# adlarındaki biçimdedir; kurulu diller listesi bunların kısa halini dönebilir
# (tr-TR -> tr), bu yüzden eşleştirme kurulu_mu() içinde önek toleranslıdır.
OCR_DILLERI = [
    ("en-US", "English (US)", "İngilizce (ABD)"),
    ("en-GB", "English (UK)", "İngilizce (Birleşik Krallık)"),
    ("tr-TR", "Turkish", "Türkçe"),
    ("de-DE", "German", "Almanca"),
    ("fr-FR", "French", "Fransızca"),
    ("fr-CA", "French (Canada)", "Fransızca (Kanada)"),
    ("es-ES", "Spanish", "İspanyolca"),
    ("es-MX", "Spanish (Mexico)", "İspanyolca (Meksika)"),
    ("it-IT", "Italian", "İtalyanca"),
    ("pt-PT", "Portuguese", "Portekizce"),
    ("pt-BR", "Portuguese (Brazil)", "Portekizce (Brezilya)"),
    ("ru-RU", "Russian", "Rusça"),
    ("ar-SA", "Arabic", "Arapça"),
    ("ja-JP", "Japanese", "Japonca"),
    ("ko-KR", "Korean", "Korece"),
    ("zh-CN", "Chinese (Simplified)", "Çince (Basitleştirilmiş)"),
    ("zh-TW", "Chinese (Traditional)", "Çince (Geleneksel)"),
    ("nl-NL", "Dutch", "Felemenkçe"),
    ("pl-PL", "Polish", "Lehçe"),
    ("sv-SE", "Swedish", "İsveççe"),
    ("nb-NO", "Norwegian", "Norveççe"),
    ("da-DK", "Danish", "Danca"),
    ("fi-FI", "Finnish", "Fince"),
    ("el-GR", "Greek", "Yunanca"),
    ("cs-CZ", "Czech", "Çekçe"),
    ("sk-SK", "Slovak", "Slovakça"),
    ("sl-SI", "Slovenian", "Slovence"),
    ("hu-HU", "Hungarian", "Macarca"),
    ("ro-RO", "Romanian", "Romence"),
    ("hr-HR", "Croatian", "Hırvatça"),
    ("bs-Latn-BA", "Bosnian", "Boşnakça"),
    ("sr-Latn-RS", "Serbian (Latin)", "Sırpça (Latin)"),
    ("sr-Cyrl-RS", "Serbian (Cyrillic)", "Sırpça (Kiril)"),
    ("hi-IN", "Hindi", "Hintçe"),
    ("af-ZA", "Afrikaans", "Afrikaans"),
]


def gorunen_ad(etiket):
    """'tr' veya 'tr-TR' için, arayüz diline göre okunur ad döndürür."""
    i = 2 if _dil() == "tr" else 1
    e = etiket.lower()
    for satir in OCR_DILLERI:
        if satir[0].lower() == e:
            return satir[i]
    kok = e.split("-")[0]
    for satir in OCR_DILLERI:
        if satir[0].split("-")[0].lower() == kok:
            return satir[i]
    return etiket


def kurulu_mu(etiket, kurulu_etiketler):
    """Capability etiketi (tr-TR), kurulu liste (tr) ile eşleşiyor mu?"""
    k = {e.lower() for e in kurulu_etiketler}
    e = etiket.lower()
    return e in k or e.split("-")[0] in k


def capability_adi(etiket):
    return f"Language.OCR~~~{etiket}~0.0.1.0"


# --------------------------------------------------------------------------
# UAC ile yükseltilmiş çalıştırma
# --------------------------------------------------------------------------
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NO_CONSOLE = 0x00008000
UAC_REDDEDILDI = 1223
WAIT_TIMEOUT = 0x102


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wt.HWND),
        ("lpVerb", wt.LPCWSTR),
        ("lpFile", wt.LPCWSTR),
        ("lpParameters", wt.LPCWSTR),
        ("lpDirectory", wt.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wt.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wt.LPCWSTR),
        ("hkeyClass", wt.HKEY),
        ("dwHotKey", wt.DWORD),
        ("hIcon", wt.HANDLE),
        ("hProcess", wt.HANDLE),
    ]


def yonetici_calistir(govde, zaman_asimi_sn=900):
    """PowerShell gövdesini UAC onayıyla çalıştırır, (cikis_kodu, çıktı) döner.

    Çıktıyı betiğin kendisi dosyaya yazar: powershell.exe -File modunda komut
    satırındaki `*>` yönlendirmesi işlenmez, argüman olarak betiğe geçer — yani
    dışarıdan yönlendirme sessizce kaybolur.
    """
    kls = tempfile.mkdtemp(prefix="metinkap_")
    betik = os.path.join(kls, "islem.ps1")
    cikti_dosyasi = os.path.join(kls, "cikti.txt")

    tam = (
        "$ErrorActionPreference = 'Stop'\n"
        "$kod = 0\n"
        "$satirlar = New-Object System.Collections.ArrayList\n"
        "function Yaz($m) { [void]$satirlar.Add([string]$m) }\n"
        "try {\n"
        + govde +
        "\n} catch {\n"
        "  Yaz ('ERROR: ' + $_.Exception.Message)\n"
        "  $kod = 1\n"
        "}\n"
        f"$satirlar | Set-Content -LiteralPath '{cikti_dosyasi}' -Encoding UTF8\n"
        "exit $kod\n"
    )
    with open(betik, "w", encoding="utf-8-sig") as f:
        f.write(tam)

    sei = _SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE
    sei.lpVerb = "runas"
    sei.lpFile = "powershell.exe"
    sei.lpParameters = f'-NoProfile -ExecutionPolicy Bypass -File "{betik}"'
    sei.nShow = 0                                  # SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        _temizle(kls, betik, cikti_dosyasi)
        return UAC_REDDEDILDI, ""

    k32 = ctypes.windll.kernel32
    bekleme = k32.WaitForSingleObject(sei.hProcess, int(zaman_asimi_sn * 1000))
    if bekleme == WAIT_TIMEOUT:
        k32.CloseHandle(sei.hProcess)
        _temizle(kls, betik, cikti_dosyasi)        # yoksa %TEMP%'te birikiyor
        return 1460, "Timed out."                  # ERROR_TIMEOUT
    kod = wt.DWORD()
    k32.GetExitCodeProcess(sei.hProcess, ctypes.byref(kod))
    k32.CloseHandle(sei.hProcess)

    cikti = ""
    try:
        with open(cikti_dosyasi, encoding="utf-8-sig", errors="replace") as f:
            cikti = f.read().strip()
    except OSError:
        pass
    _temizle(kls, betik, cikti_dosyasi)
    return kod.value, cikti


def _temizle(kls, *dosyalar):
    for d in dosyalar:
        try:
            os.remove(d)
        except OSError:
            pass
    try:
        os.rmdir(kls)
    except OSError:
        pass


def dil_kur(etiket):
    """OCR dil paketini indirir/kurar. (basarili, mesaj) döndürür."""
    ad = capability_adi(etiket)
    kod, cikti = yonetici_calistir(
        f"  $c = Get-WindowsCapability -Online -Name '{ad}'\n"
        f"  if (-not $c) {{ Yaz 'Not offered on this Windows build.'; $kod = 1 }}\n"
        f"  elseif ($c.State -eq 'Installed') {{ Yaz 'Already installed.' }}\n"
        f"  else {{\n"
        f"    Add-WindowsCapability -Online -Name '{ad}' | Out-Null\n"
        f"    $s = (Get-WindowsCapability -Online -Name '{ad}').State\n"
        f"    Yaz \"State: $s\"\n"
        f"    if ($s -ne 'Installed') {{ $kod = 1 }}\n"
        f"  }}\n"
    )
    if kod == UAC_REDDEDILDI:
        return False, "Administrator permission was not granted."
    return kod == 0, cikti or (f"Failed (exit {kod})." if kod else "Installed.")


# --------------------------------------------------------------------------
# Windows açılışında başlatma (yönetici gerekmez)
# --------------------------------------------------------------------------
def _baslangic_yolu():
    return os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup", "MetinKap.lnk")


def baslangica_ekli_mi():
    return os.path.exists(_baslangic_yolu())


def baslangici_ayarla(acik, pythonw, betik):
    yol = _baslangic_yolu()
    if not acik:
        try:
            os.remove(yol)
        except FileNotFoundError:
            pass
        except OSError as e:                       # salt okunur / kilitli dosya
            return False, str(e)
        return not os.path.exists(yol), ""
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='\"%s\"';"
        "$s.WorkingDirectory='%s';$s.Description='MetinKap';$s.Save()"
        % (yol, pythonw, betik, os.path.dirname(betik))
    )
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True,
                       creationflags=0x08000000)   # CREATE_NO_WINDOW
    if r.returncode == 0 and os.path.exists(yol):
        return True, ""
    return False, (r.stderr or "Could not create the shortcut.").strip()
