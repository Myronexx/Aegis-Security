"""
AEGIS GUARDIAN - VANGUARD MANTIĞI
==================================
- Çift tıkla veya --watcher ile açılabilir
- Windows başlangıcında SİSTEM seviyesinde otomatik başlar
- Security kill edilirse 1 saniyede diriltir
- Security, Guardian olmadan açılamaz
"""

import os
import sys
import time
import ctypes
import psutil
import subprocess
import winreg as reg

# --- SABITLER ---
TARGET_EXE = "Aegis_Security.exe"
GUARDIAN_EXE = "Aegis_Guardian.exe"
APP_DIR = os.path.join(os.environ['APPDATA'], "AegisSecurity")
EXIT_FLAG = os.path.join(APP_DIR, "exit.flag")
READY_FLAG = os.path.join(APP_DIR, "guardian_ready.flag")
LOG_FILE = os.path.join(APP_DIR, "guardian.log")
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
TARGET_PATH = os.path.join(BASE_DIR, TARGET_EXE)
GUARDIAN_PATH = os.path.join(BASE_DIR, GUARDIAN_EXE)

os.makedirs(APP_DIR, exist_ok=True)

# --- FONKSİYONLAR ---
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def request_admin():
    """Yönetici izni iste, yoksa yeniden başlat"""
    if not is_admin():
        args = "--watcher"
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas",
            sys.executable if sys.argv[0].endswith('.py') else sys.argv[0],
            args, None, 1
        )
        sys.exit()

def log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except: pass

def install_to_startup():
    """Guardian'ı Windows başlangıcına SYSTEM seviyesinde ekle."""
    try:
        task_cmd = (
            f'schtasks /create /tn "AegisGuardian" /tr "{GUARDIAN_PATH} --watcher" '
            f'/sc onstart /ru SYSTEM /rl HIGHEST /f'
        )
        result = subprocess.run(task_cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            log("Task Scheduler'a eklendi (SYSTEM yetkisi).")
        else:
            key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0, reg.KEY_SET_VALUE)
            reg.SetValueEx(key, 'AegisGuardian', 0, reg.REG_SZ,
                f'"{GUARDIAN_PATH}" --watcher')
            reg.CloseKey(key)
            log("Registry HKLM\\Run'a eklendi.")
    except Exception as e:
        log(f"Başlangıca ekleme hatası: {e}")

def is_guardian_in_startup():
    """Guardian zaten başlangıçta kayıtlı mı?"""
    result = subprocess.run(
        'schtasks /query /tn "AegisGuardian"',
        shell=True, capture_output=True
    )
    if result.returncode == 0:
        return True
    try:
        key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0, reg.KEY_READ)
        reg.QueryValueEx(key, 'AegisGuardian')
        reg.CloseKey(key)
        return True
    except:
        return False

def is_process_running(exe_name):
    """Belirtilen exe çalışıyor mu?"""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def is_guardian_already_running():
    """Başka bir Guardian instance'ı zaten çalışıyor mu?"""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == GUARDIAN_EXE.lower():
                if proc.info['pid'] != current_pid:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def write_ready_flag():
    """Security'ye 'Guardian hazır, açılabilirsin' sinyali"""
    try:
        with open(READY_FLAG, "w") as f:
            f.write(f"ready:{time.time()}")
    except: pass

def clear_ready_flag():
    """Guardian kapanırken ready flag'i sil"""
    try:
        if os.path.exists(READY_FLAG):
            os.remove(READY_FLAG)
    except: pass

def revive_loop():
    """Ana döngü: Her saniye Security'yi kontrol et, kill edildiyse dirilt."""
    log("Guardian koruma döngüsü başladı.")
    write_ready_flag()

    while True:
        if os.path.exists(EXIT_FLAG):
            log("Exit flag algılandı. Guardian kapanıyor.")
            clear_ready_flag()
            try: os.remove(EXIT_FLAG)
            except: pass
            sys.exit(0)

        if not is_process_running(TARGET_EXE):
            if os.path.exists(TARGET_PATH):
                try:
                    subprocess.Popen(
                        [TARGET_PATH, "--startup"],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    log("Security yeniden canlandırıldı.")
                except Exception as e:
                    log(f"Canlandırma hatası: {e}")
            else:
                log(f"HATA: {TARGET_PATH} bulunamadı!")

        time.sleep(1)


# ==================== MAIN ====================
if __name__ == "__main__":

    # DÜZELTME: Çift tıkla açılınca da çalışır, --watcher otomatik eklenir
    if "--watcher" not in sys.argv:
        sys.argv.append("--watcher")

    # Yönetici izni şart
    request_admin()

    # Zaten çalışan bir Guardian varsa ikinci instance açılmasın
    if is_guardian_already_running():
        log("Guardian zaten çalışıyor, ikinci instance kapatılıyor.")
        sys.exit(0)

    log("=" * 50)
    log("Aegis Guardian başlatılıyor...")

    # İlk kurulumda başlangıca ekle
    if not is_guardian_in_startup():
        log("İlk kurulum: Başlangıca ekleniyor...")
        install_to_startup()

    # Exit flag varsa temizle
    if os.path.exists(EXIT_FLAG):
        os.remove(EXIT_FLAG)

    # Koruma döngüsünü başlat
    revive_loop()
