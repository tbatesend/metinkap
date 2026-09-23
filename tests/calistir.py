"""Tum test takimlarini sirayla calistirir.

    python tests/calistir.py           # hepsi
    python tests/calistir.py --hizli   # yalnizca pencere acmayanlar

Bazi takimlar gercek bir pencere acip ekran yakaladigi icin calisirken
bilgisayari kullanma; --hizli bunlari atlar.
"""
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.abspath(__file__))

# (dosya, pencere_aciyor_mu)
TAKIMLAR = [
    ("test_veri_ve_ayarlar.py", False),
    ("test_ceviri_ve_kurtarma.py", False),
    ("test_metin_bicimleri.py", False),
    ("test_biriktirme.py", False),
    ("test_geri_yapistir.py", False),
    ("test_arayuz.py", True),
    ("test_dil_kurulumu.py", True),
]


def main():
    hizli = "--hizli" in sys.argv
    basarisiz = []
    for dosya, pencereli in TAKIMLAR:
        if hizli and pencereli:
            print(f"{dosya:28s} ATLANDI (--hizli)")
            continue
        r = subprocess.run([sys.executable, os.path.join(KOK, dosya)],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        son = [s for s in (r.stdout or "").strip().splitlines() if s.strip()]
        durum = son[-1] if son else f"cikis {r.returncode}"
        print(f"{dosya:28s} {durum}")
        if r.returncode != 0:
            basarisiz.append(dosya)
            print((r.stdout or "")[-1500:])
            print((r.stderr or "")[-800:])
    print()
    if basarisiz:
        print("BASARISIZ:", ", ".join(basarisiz))
        return 1
    print("Tum takimlar gecti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
