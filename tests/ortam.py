"""Testleri kullanıcının gerçek verisinden izole eder.

Testler doğrudan `%APPDATA%\\MetinKap` altına yazıyordu. İki sorun vardı:
kullanıcının gerçek ayarları/geçmişi test sırasında değişiyordu, ve MetinKap
o sırada çalışıyorsa aynı dosyalara iki taraf birden yazdığı için testler
rastgele başarısız oluyordu.

Her test dosyası ilk iş olarak `ortam.izole_et()` çağırır.
"""

import atexit
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def izole_et():
    """Veri yollarını geçici bir klasöre yönlendirir, çıkışta siler."""
    import metinkap as mk

    klasor = tempfile.mkdtemp(prefix="mktest_")   # diller.py "metinkap_" kullaniyor, karismasin
    mk.DATA_DIR = klasor
    mk.CONFIG_PATH = os.path.join(klasor, "config.json")
    mk.HISTORY_JSON = os.path.join(klasor, "gecmis.json")
    mk.HISTORY_TXT = os.path.join(klasor, "gecmis.txt")
    mk.LAST_CROP_PATH = os.path.join(klasor, "son_kirpim.png")
    mk.LOG_PATH = os.path.join(klasor, "hata.log")
    mk.SHOW_FLAG = os.path.join(klasor, ".goster")
    atexit.register(shutil.rmtree, klasor, ignore_errors=True)
    return klasor
