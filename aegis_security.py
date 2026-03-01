"""
AEGIS SECURITY - VANGUARD MANTIĞI
===================================
- Guardian çalışmadan AÇILMAZ (Valorant'ın Vanguard'sız açılmaması gibi)
- Her açılışta Yönetici izni ister
- Guardian kill edilirse kullanıcıyı uyarır ve kapanır
- Sadece Guardian'ın yasal çıkışıyla kapanabilir
"""

import sys
import os
import hashlib
import threading
import ctypes
import shutil
import time
import subprocess
import winreg as reg
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLabel, QMenu, QAction, QMessageBox, QSystemTrayIcon,
                             QStyle, QTabWidget, QCheckBox, QListWidget, QFileDialog,
                             QLineEdit, QGroupBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QBrush, QColor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import psutil
    import requests
except ImportError:
    ctypes.windll.user32.MessageBoxW(0,
        "Lutfen terminalden 'pip install psutil requests' komutunu calistirin.",
        "Eksik Kutuphane", 16)
    sys.exit()

# --- SABITLER ---
APP_DIR = os.path.join(os.environ['APPDATA'], "AegisSecurity")
os.makedirs(APP_DIR, exist_ok=True)
EXIT_FLAG = os.path.join(APP_DIR, "exit.flag")
READY_FLAG = os.path.join(APP_DIR, "guardian_ready.flag")  # Guardian hazır mı?
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
GUARDIAN_EXE = "Aegis_Guardian.exe"
GUARDIAN_PATH = os.path.join(BASE_DIR, GUARDIAN_EXE)

# --- YÖNETİCİ KONTROLÜ (Her açılışta) ---
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas",
        sys.executable if sys.argv[0].endswith('.py') else sys.argv[0],
        " ".join(f'"{a}"' for a in sys.argv), None, 1
    )
    sys.exit()

# --- VANGUARD KONTROLÜ: Guardian olmadan açılma ---
def check_guardian_running():
    """Guardian çalışıyor mu ve ready flag var mı?"""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == GUARDIAN_EXE.lower():
                return True
        except: pass
    return False

def wait_for_guardian():
    """
    Guardian'ı başlat ve hazır olmasını bekle.
    Vanguard mantığı: Vanguard yoksa Valorant açılmaz.
    """
    if check_guardian_running():
        return True  # Zaten çalışıyor

    # Guardian'ı başlat
    if os.path.exists(GUARDIAN_PATH):
        try:
            subprocess.Popen(
                [GUARDIAN_PATH, "--watcher"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Aegis Guardian baslatılamadı!\nHata: {e}\n\n"
                f"Lutfen '{GUARDIAN_EXE}' dosyasinin ayni klasorde oldugunu kontrol edin.",
                "Guardian Hatası", 0x10
            )
            sys.exit()
    else:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Aegis Guardian bulunamadı!\n\n"
            f"'{GUARDIAN_EXE}' dosyası Security ile aynı klasörde olmalıdır.\n"
            f"Aranan konum: {GUARDIAN_PATH}",
            "Guardian Bulunamadı", 0x10
        )
        sys.exit()

    # Guardian'ın ready flag yazmasını bekle (max 10 saniye)
    for _ in range(100):
        if os.path.exists(READY_FLAG) or check_guardian_running():
            return True
        time.sleep(0.1)

    # Timeout - Guardian başlamadı
    ctypes.windll.user32.MessageBoxW(
        0,
        "Aegis Guardian zaman aşımına uğradı!\n\n"
        "Guardian başlatılamadı. Uygulama kapanıyor.",
        "Zaman Aşımı", 0x10
    )
    sys.exit()

# Guardian kontrolü - uygulama başlamadan önce
wait_for_guardian()

# --- HONEYPOT ---
def deploy_honeypot():
    documents_path = os.path.join(os.environ['USERPROFILE'], "Documents")
    trap_path = os.path.join(documents_path, "Bank_Account_Passwords.txt")
    if not os.path.exists(trap_path):
        try:
            with open(trap_path, "w", encoding="utf-8") as f:
                f.write("THIS IS A HONEYPOT DEPLOYED BY AEGIS SECURITY TO TRAP RANSOMWARE.")
            ctypes.windll.kernel32.SetFileAttributesW(trap_path, 2)
        except: pass
    return trap_path

HONEYPOT_PATH = deploy_honeypot()

# --- VİRÜS DB ---
VIRUS_DB = {
    "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f": "EICAR-Test-File",
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": "Trojan:VBS/InfoStealer.A"
}

HEURISTIC_RULES = {
    b"DisableTaskMgr": ("Gorev Yoneticisini kapatma", 50),
    b"DisableRegistryTools": ("Kayit Defterini kilitleme", 50),
    b"schtasks /create": ("Gizli gorev ekleme", 30),
    b"WScript.Shell": ("Kayit defterine mudahale", 30),
    b"vssadmin delete shadows": ("Fidye Yazilimi Yedek Silme", 90),
    b"CreateRemoteThread": ("Bellege sizma", 40),
    b"powershell -ExecutionPolicy Bypass": ("Guvenlik duvari asma", 50),
    b"stratum+tcp://": ("Kripto para kazima", 80)
}

EXCLUDED_DIRS = [".gradle", "System32", "SysWOW64", "Windows\\Temp", "Prefetch"]
RISKY_EXTENSIONS = ['.exe', '.vbs', '.bat', '.cmd', '.ps1', '.jar', '.txt']


class ScanEngine:
    @staticmethod
    def analyze_file(filepath):
        if not filepath or not os.path.exists(filepath): return False, "Not Found", ""
        if os.path.abspath(filepath) == os.path.abspath(sys.argv[0]): return False, "Clean", ""
        for excluded in EXCLUDED_DIRS:
            if excluded.lower() in filepath.lower(): return False, "Excluded", ""
        try:
            size = os.path.getsize(filepath)
            if size == 0 or size > 50 * 1024 * 1024: return False, "Clean / Too Large", ""
            with open(filepath, "rb") as f:
                content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()
            if file_hash in VIRUS_DB: return True, VIRUS_DB[file_hash], "Signature Detected."
            file_ext = os.path.splitext(filepath)[1].lower()
            if file_ext in RISKY_EXTENSIONS:
                total_score = 0
                detected_crimes = []
                for rule, (desc, points) in HEURISTIC_RULES.items():
                    if rule in content:
                        total_score += points
                        detected_crimes.append(desc)
                if total_score >= 70:
                    return True, f"Heur.Suspicious (Score: {total_score})", f"Threats: {', '.join(detected_crimes)}"
            return False, "Clean", ""
        except Exception:
            return False, "Unreadable", ""


class RealTimeMonitor(QObject, FileSystemEventHandler):
    threat_found_signal = pyqtSignal(str, str, str, str)

    def __init__(self):
        super().__init__()

    def on_created(self, event):
        if not event.is_directory: self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory: self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory: self.process_file(event.dest_path)

    def process_file(self, filepath):
        if filepath == HONEYPOT_PATH:
            self.threat_found_signal.emit("Bank_Passwords.txt", "Ransomware.Trap", filepath, "Ransomware trapped!")
            return
        for excluded in EXCLUDED_DIRS:
            if excluded.lower() in filepath.lower(): return
        file_ready = False
        for _ in range(15):
            try:
                with open(filepath, "rb"): pass
                file_ready = True; break
            except: time.sleep(0.05)
        if not file_ready: return
        is_infected, threat_name, desc = ScanEngine.analyze_file(filepath)
        if is_infected:
            quarantine_dir = os.path.join(APP_DIR, "Quarantine")
            os.makedirs(quarantine_dir, exist_ok=True)
            safe_name = os.path.basename(filepath) + ".locked"
            safe_path = os.path.join(quarantine_dir, safe_name)
            try:
                shutil.move(filepath, safe_path)
                self.threat_found_signal.emit(safe_name, threat_name, filepath, desc)
            except: pass


class AegisSecurityAV(QMainWindow):
    scan_progress_signal = pyqtSignal(str)
    scan_finished_signal = pyqtSignal(bool)
    update_proc_table_signal = pyqtSignal(int, str, str)
    update_vt_result_signal = pyqtSignal(str, str)

    def __init__(self, start_hidden=False):
        super().__init__()

        if os.path.exists(EXIT_FLAG): os.remove(EXIT_FLAG)

        self.langs = {
            "EN": {
                "win_title": "🛡️ AEGIS SECURITY | DEFENSE MATRIX",
                "t_dash": "Dashboard", "t_ram": "🧠 RAM Scanner", "t_net": "🌐 Net Radar",
                "t_cld": "☁️ Cloud Intel", "t_qua": "Quarantine", "t_rep": "🛠️ Repair",
                "t_set": "Settings", "t_lng": "🌍 Language",
                "d_ok": "🟢 System Protected", "d_off": "🔴 Protection DISABLED",
                "d_scan": "🔄 Scanning...", "d_stop": "🟠 Scan Stopped",
                "btn_q": "⚡ Quick Scan", "btn_f": "🔍 Full Scan", "btn_s": "🛑 Stop Scan",
                "btn_auto": "🚀 Auto-Start", "btn_hide": "⬇️ Hide to Tray",
                "r_info": "Scan RAM processes in real-time for injected threats.",
                "r_h1": "PID", "r_h2": "Process Name", "r_h3": "RAM Usage", "r_h4": "Status",
                "btn_r_ref": "🔄 List Processes", "btn_r_scan": "🧠 Scan RAM & Kill Viruses",
                "n_info": "Monitor internet connections. Terminate suspicious traffic!",
                "n_h1": "PID", "n_h2": "Process", "n_h3": "Remote IP", "n_h4": "Status", "n_h5": "Action",
                "btn_n_ref": "📡 Radar Scan", "n_conn": "CONNECTED 🟢", "n_kill": "✂️ Kill Connection",
                "c_grp": "VirusTotal API Settings", "c_ph": "Paste your API Key here...",
                "c_save": "💾 Save", "c_wait": "Waiting for API Key... (virustotal.com)",
                "c_ready": "🟢 API Key Active. Ready to scan.",
                "btn_c_scan": "☁️ Scan File (70 Engines)", "btn_c_quick": "⚡ Smart Quick Scan (Latest Download)",
                "q_h1": "File", "q_h2": "Threat", "q_h3": "Date", "q_h4": "Path",
                "btn_q_res": "♻️ Restore All", "btn_q_del": "🗑️ Delete All",
                "rp_info": "Repair system tools locked by viruses (Registry fixes).",
                "rp_h1": "System Tool", "rp_h2": "Status", "rp_h3": "Action",
                "btn_rp_scan": "🔍 Scan Damage", "btn_rp_fix1": "🔧 Fix Selected",
                "btn_rp_fix2": "🩺 Fix All", "rp_ok": "Healthy ✅", "rp_bad": "Broken ❌",
                "rp_act": "Restore Default",
                "rp_k1": "Task Manager", "rp_k2": "Registry Editor", "rp_k3": "Command Prompt",
                "rp_k4": "Control Panel", "rp_k5": "Folder Options",
                "rp_k6": "Win. Defender (Engine)", "rp_k7": "Win. Defender (Scan)",
                "s_lbl1": "🛡️ Protection Settings", "s_cb1": "Real-Time File Protection",
                "s_cb2": "Cloud-Based Telemetry", "s_cb3": "Auto Sample Submission",
                "s_cb4": "Tamper Protection", "s_lbl2": "📂 Exclusions (Do Not Scan)",
                "btn_s_add": "➕ Add Folder", "btn_s_rem": "➖ Remove Selected",
                "l_info": "🌍 Select Interface Language:",
                "tray_title": "🚨 THREAT BLOCKED!", "tray_msg": "caught and quarantined in background!",
                "msg_startup": "Aegis Security and Guardian successfully added to Windows Startup!",
                "guardian_lost": "⚠️ Guardian connection lost! Attempting to reconnect...",
                "guardian_ok": "🛡️ Guardian reconnected."
            },
            "TR": {
                "win_title": "🛡️ AEGIS SECURITY | SAVUNMA MATRİSİ",
                "t_dash": "Ana Panel", "t_ram": "🧠 RAM Tarayıcı", "t_net": "🌐 Ağ Radarı",
                "t_cld": "☁️ Bulut Zekası", "t_qua": "Karantina Merkezi", "t_rep": "🛠️ Onarım",
                "t_set": "Ayarlar", "t_lng": "🌍 Dil / Lang",
                "d_ok": "🟢 Sistem Korunuyor", "d_off": "🔴 Koruma KAPALI",
                "d_scan": "🔄 Taranıyor...", "d_stop": "🟠 Tarama Durduruldu",
                "btn_q": "⚡ Hızlı Tarama", "btn_f": "🔍 Tam Tarama", "btn_s": "🛑 Taramayı Durdur",
                "btn_auto": "🚀 Başlangıca Ekle", "btn_hide": "⬇️ Tepsiye Küçült",
                "r_info": "Arka planda çalışan işlemleri anlık DNA taramasından geçirin.",
                "r_h1": "PID", "r_h2": "Program Adı", "r_h3": "RAM", "r_h4": "Durum",
                "btn_r_ref": "🔄 İşlemleri Listele", "btn_r_scan": "🧠 Tüm Belleği Tara & Virüsleri Öldür",
                "n_info": "İnternete bağlanan programları izle. Şüpheli bağlantıları anında kes!",
                "n_h1": "PID", "n_h2": "Program", "n_h3": "Bağlandığı IP", "n_h4": "Durum", "n_h5": "İşlem",
                "btn_n_ref": "📡 Ağı Tara (Radar)", "n_conn": "BAĞLI 🟢", "n_kill": "✂️ Bağlantıyı Kes",
                "c_grp": "VirusTotal API Ayarları", "c_ph": "API Anahtarınızı Buraya Girin...",
                "c_save": "💾 Kaydet", "c_wait": "API Anahtarı bekleniyor... (virustotal.com)",
                "c_ready": "🟢 API Anahtarı Aktif. Tarama yapabilirsiniz.",
                "btn_c_scan": "☁️ Dosya Seç ve 70 Antivirüse Sor",
                "btn_c_quick": "⚡ Akıllı Hızlı Tarama (Son İndirilen Dosya)",
                "q_h1": "Dosya", "q_h2": "Tehdit Türü", "q_h3": "Tarih", "q_h4": "Orijinal Konum",
                "btn_q_res": "♻️ Hepsini Geri Yükle", "btn_q_del": "🗑️ Hepsini Kalıcı Sil",
                "rp_info": "Virüslerin bozduğu ve kilitlediği sistem ayarlarını buradan onarabilirsiniz.",
                "rp_h1": "Sistem Aracı / Ayar", "rp_h2": "Mevcut Durum", "rp_h3": "Onarım",
                "btn_rp_scan": "🔍 Hasar Taraması Yap", "btn_rp_fix1": "🔧 Seçilenleri Onar",
                "btn_rp_fix2": "🩺 Hepsini Tek Tuşla Onar", "rp_ok": "Sağlıklı ✅", "rp_bad": "Bozulmuş ❌",
                "rp_act": "Fabrika Ayarına Dön",
                "rp_k1": "Görev Yöneticisi", "rp_k2": "Kayıt Defteri (Regedit)",
                "rp_k3": "Komut İstemi (CMD)", "rp_k4": "Denetim Masası",
                "rp_k5": "Gizli Dosyaları Göster", "rp_k6": "Win. Defender (Motor)",
                "rp_k7": "Win. Defender (Tarama)",
                "s_lbl1": "🛡️ Koruma Ayarları", "s_cb1": "Gerçek Zamanlı Koruma (Tüm Sistemi İzler)",
                "s_cb2": "Bulut Tabanlı Koruma", "s_cb3": "Otomatik Örnek Gönderimi",
                "s_cb4": "Kurcalamaya Karşı Koruma",
                "s_lbl2": "📂 Dışlamalar (Taranmayacak Klasörler)",
                "btn_s_add": "➕ Klasör Ekle", "btn_s_rem": "➖ Seçileni Kaldır",
                "l_info": "🌍 Arayüz Dilini Seçin:",
                "tray_title": "🚨 TEHDİT ENGELLENDİ!", "tray_msg": "arka planda yakalandı ve hapsedildi!",
                "msg_startup": "Aegis Kalkanı ve Muhafız Windows başlangıcına başarıyla eklendi!",
                "guardian_lost": "⚠️ Guardian bağlantısı kesildi! Yeniden bağlanılıyor...",
                "guardian_ok": "🛡️ Guardian yeniden bağlandı."
            },
            "FR": {
                "win_title": "🛡️ AEGIS SECURITY | MATRICE DE DÉFENSE",
                "t_dash": "Accueil", "t_ram": "🧠 Analyse RAM", "t_net": "🌐 Radar Réseau",
                "t_cld": "☁️ Intel Cloud", "t_qua": "Quarantaine", "t_rep": "🛠️ Réparation",
                "t_set": "Paramètres", "t_lng": "🌍 Langue",
                "d_ok": "🟢 Système Protégé", "d_off": "🔴 Protection DÉSACTIVÉE",
                "d_scan": "🔄 Analyse...", "d_stop": "🟠 Arrêté",
                "btn_q": "⚡ Analyse Rapide", "btn_f": "🔍 Complète", "btn_s": "🛑 Arrêter",
                "btn_auto": "🚀 Démarrage Auto", "btn_hide": "⬇️ Réduire",
                "r_info": "Scannez la mémoire RAM en temps réel.",
                "r_h1": "PID", "r_h2": "Processus", "r_h3": "RAM", "r_h4": "Statut",
                "btn_r_ref": "🔄 Liste", "btn_r_scan": "🧠 Analyser RAM & Tuer",
                "n_info": "Surveiller les connexions. Coupez le trafic suspect!",
                "n_h1": "PID", "n_h2": "Processus", "n_h3": "IP Distante", "n_h4": "Statut", "n_h5": "Action",
                "btn_n_ref": "📡 Radar", "n_conn": "CONNECTÉ 🟢", "n_kill": "✂️ Couper",
                "c_grp": "API VirusTotal", "c_ph": "Clé API ici...",
                "c_save": "💾 Enregistrer", "c_wait": "En attente de l'API... (virustotal.com)",
                "c_ready": "🟢 Clé API Active. Prêt à scanner.",
                "btn_c_scan": "☁️ Analyser Fichier (70 Moteurs)",
                "btn_c_quick": "⚡ Analyse Intelligente (Dernier Fichier)",
                "q_h1": "Fichier", "q_h2": "Menace", "q_h3": "Date", "q_h4": "Chemin",
                "btn_q_res": "♻️ Tout Restaurer", "btn_q_del": "🗑️ Tout Supprimer",
                "rp_info": "Réparez les outils système verrouillés par des virus.",
                "rp_h1": "Outil Système", "rp_h2": "Statut", "rp_h3": "Action",
                "btn_rp_scan": "🔍 Scanner", "btn_rp_fix1": "🔧 Réparer Sélection",
                "btn_rp_fix2": "🩺 Tout Réparer", "rp_ok": "Sain ✅", "rp_bad": "Cassé ❌",
                "rp_act": "Restaurer",
                "rp_k1": "Gestionnaire des tâches", "rp_k2": "Éditeur du Registre",
                "rp_k3": "Invite de commandes", "rp_k4": "Panneau de conf.",
                "rp_k5": "Options des dossiers", "rp_k6": "Win. Defender (Moteur)",
                "rp_k7": "Win. Defender (Analyse)",
                "s_lbl1": "🛡️ Paramètres de Protection", "s_cb1": "Protection en Temps Réel",
                "s_cb2": "Télémétrie Cloud", "s_cb3": "Envoi Automatique",
                "s_cb4": "Protection Falsification", "s_lbl2": "📂 Exclusions",
                "btn_s_add": "➕ Ajouter", "btn_s_rem": "➖ Retirer",
                "l_info": "🌍 Choisissez la langue de l'interface:",
                "tray_title": "🚨 MENACE BLOQUÉE!", "tray_msg": "attrapé et mis en quarantaine!",
                "msg_startup": "Aegis Security et Guardian ajoutés avec succès au démarrage!",
                "guardian_lost": "⚠️ Guardian déconnecté! Reconnexion en cours...",
                "guardian_ok": "🛡️ Guardian reconnecté."
            }
        }

        self.cur_lang = "EN"
        self.setWindowTitle(self.t("win_title"))
        self.setGeometry(100, 100, 1250, 750)
        self.setStyleSheet("background-color: #0f0f14; color: #e0e0e0; font-family: 'Segoe UI';")

        self.quarantine_data = {}
        self.stop_scan_flag = False
        self.vt_api_key = ""
        self.quarantine_dir = os.path.join(APP_DIR, "Quarantine")
        os.makedirs(self.quarantine_dir, exist_ok=True)
        self.observer = None
        self.monitor = None
        self._guardian_was_alive = True  # Guardian durumu takibi

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.header_lbl = QLabel(self.t("win_title"))
        self.header_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #00ff88; padding: 10px;")
        layout.addWidget(self.header_lbl)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { background: #1a1a24; color: white; padding: 12px 18px;}"
            "QTabBar::tab:selected { background: #00ff88; color: black; font-weight: bold;}")

        self.tab_dashboard = QWidget(); self.tab_processes = QWidget()
        self.tab_network = QWidget(); self.tab_cloud = QWidget()
        self.tab_quarantine = QWidget(); self.tab_repair = QWidget()
        self.tab_settings = QWidget(); self.tab_language = QWidget()

        for tab, key in [(self.tab_dashboard, "t_dash"), (self.tab_processes, "t_ram"),
                         (self.tab_network, "t_net"), (self.tab_cloud, "t_cld"),
                         (self.tab_quarantine, "t_qua"), (self.tab_repair, "t_rep"),
                         (self.tab_settings, "t_set"), (self.tab_language, "t_lng")]:
            self.tabs.addTab(tab, self.t(key))
        layout.addWidget(self.tabs)

        self.update_proc_table_signal.connect(self.safe_update_proc_table)
        self.update_vt_result_signal.connect(self.safe_update_vt_result)

        self.setup_dashboard(); self.setup_processes(); self.setup_network()
        self.setup_cloud(); self.setup_quarantine(); self.setup_repair()
        self.setup_settings(); self.setup_language_tab(); self.setup_system_tray()

        self.load_api_key()
        self.scan_progress_signal.connect(self.update_scan_status)
        self.scan_finished_signal.connect(self.scan_complete)
        self.tabs.currentChanged.connect(self.clear_quarantine_alert)

        self.start_realtime_protection()

        # Guardian watchdog - 3 saniyede bir Guardian'ı kontrol et
        self.guardian_timer = QTimer()
        self.guardian_timer.timeout.connect(self.check_guardian_alive)
        self.guardian_timer.start(3000)

        # Security da Guardian'ı izler (karşılıklı koruma)
        threading.Thread(target=self.watch_guardian_thread, daemon=True).start()

        if start_hidden: self.hide_to_tray()
        else: self.show()

    def watch_guardian_thread(self):
        """Guardian ölürse Security yeniden başlatır"""
        while True:
            time.sleep(3)
            if os.path.exists(EXIT_FLAG):
                break
            guardian_alive = any(
                p.info['name'] and p.info['name'].lower() == GUARDIAN_EXE.lower()
                for p in psutil.process_iter(['name'])
            )
            if not guardian_alive and os.path.exists(GUARDIAN_PATH):
                try:
                    subprocess.Popen(
                        [GUARDIAN_PATH, "--watcher"],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except: pass

    def check_guardian_alive(self):
        """GUI thread'de Guardian durumunu status bar'a yansıt"""
        guardian_alive = any(
            p.info['name'] and p.info['name'].lower() == GUARDIAN_EXE.lower()
            for p in psutil.process_iter(['name'])
        )
        if not guardian_alive and self._guardian_was_alive:
            self._guardian_was_alive = False
            if hasattr(self, 'status_label') and self.cb1.isChecked():
                self.status_label.setText(self.t("guardian_lost"))
                self.status_label.setStyleSheet("font-size: 16px; color: #ff9900; margin-bottom: 20px;")
        elif guardian_alive and not self._guardian_was_alive:
            self._guardian_was_alive = True
            if hasattr(self, 'status_label') and self.cb1.isChecked():
                self.status_label.setText(self.t("d_ok"))
                self.status_label.setStyleSheet("font-size: 16px; color: #00ff88; margin-bottom: 20px;")

    def t(self, key): return self.langs.get(self.cur_lang, self.langs["EN"]).get(key, key)

    def create_button(self, text, border_color):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: #20202a; border: 2px solid {border_color}; "
            f"border-radius: 8px; padding: 15px; font-size: 14px; font-weight: bold; color: white;}}"
            f"QPushButton:hover {{ background-color: {border_color}; color: black; }}")
        return btn

    def setup_language_tab(self):
        layout = QVBoxLayout(self.tab_language)
        self.lbl_l_info = QLabel(self.t("l_info"))
        self.lbl_l_info.setStyleSheet("font-size: 18px; font-weight: bold; color: #8888ff; margin-bottom: 20px;")
        layout.addWidget(self.lbl_l_info)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English (EN)", "Türkçe (TR)", "Français (FR)"])
        self.lang_combo.setStyleSheet("background-color: #1a1a24; color: white; padding: 15px; font-size: 16px; border: 2px solid #00ff88;")
        self.lang_combo.currentIndexChanged.connect(self.apply_language_change)
        layout.addWidget(self.lang_combo)
        layout.addStretch()

    def apply_language_change(self, index):
        langs = ["EN", "TR", "FR"]
        if index < len(langs): self.cur_lang = langs[index]
        self.update_all_texts()

    def update_all_texts(self):
        self.setWindowTitle(self.t("win_title"))
        self.header_lbl.setText(self.t("win_title"))
        keys = ['dash', 'ram', 'net', 'cld', 'qua', 'rep', 'set', 'lng']
        for i, k in enumerate(keys): self.tabs.setTabText(i, self.t(f"t_{k}"))
        if self.cb1.isChecked():
            self.status_label.setText(self.t("d_ok"))
            self.status_label.setStyleSheet("font-size: 16px; color: #00ff88; margin-bottom: 20px;")
        else:
            self.status_label.setText(self.t("d_off"))
            self.status_label.setStyleSheet("font-size: 16px; color: #ff4444; margin-bottom: 20px;")
        self.btn_quick.setText(self.t("btn_q")); self.btn_full.setText(self.t("btn_f"))
        self.btn_stop.setText(self.t("btn_s")); self.btn_startup.setText(self.t("btn_auto"))
        self.btn_hide.setText(self.t("btn_hide")); self.lbl_r_info.setText(self.t("r_info"))
        self.proc_table.setHorizontalHeaderLabels([self.t(f"r_h{i}") for i in range(1, 5)])
        self.btn_refresh_proc.setText(self.t("btn_r_ref")); self.btn_scan_proc.setText(self.t("btn_r_scan"))
        self.lbl_n_info.setText(self.t("n_info"))
        self.net_table.setHorizontalHeaderLabels([self.t(f"n_h{i}") for i in range(1, 6)])
        self.btn_refresh_net.setText(self.t("btn_n_ref"))
        self.api_group.setTitle(self.t("c_grp")); self.api_input.setPlaceholderText(self.t("c_ph"))
        self.btn_save_api.setText(self.t("c_save"))
        self.vt_status.setText(self.t("c_ready") if self.vt_api_key else self.t("c_wait"))
        self.btn_vt_scan.setText(self.t("btn_c_scan")); self.btn_vt_quick.setText(self.t("btn_c_quick"))
        self.table.setHorizontalHeaderLabels([self.t(f"q_h{i}") for i in range(1, 5)])
        self.btn_res_all.setText(self.t("btn_q_res")); self.btn_del_all.setText(self.t("btn_q_del"))
        self.lbl_rp_info.setText(self.t("rp_info"))
        self.repair_table.setHorizontalHeaderLabels([self.t(f"rp_h{i}") for i in range(1, 4)])
        self.btn_rp_scan.setText(self.t("btn_rp_scan")); self.btn_rp_fix1.setText(self.t("btn_rp_fix1"))
        self.btn_rp_fix2.setText(self.t("btn_rp_fix2")); self.lbl_s_lbl1.setText(self.t("s_lbl1"))
        self.cb1.setText(self.t("s_cb1")); self.cb2.setText(self.t("s_cb2"))
        self.cb3.setText(self.t("s_cb3")); self.cb4.setText(self.t("s_cb4"))
        self.lbl_s_lbl2.setText(self.t("s_lbl2")); self.btn_s_add.setText(self.t("btn_s_add"))
        self.btn_s_rem.setText(self.t("btn_s_rem")); self.lbl_l_info.setText(self.t("l_info"))
        self.refresh_process_list(); self.refresh_network_list(); self.check_system_health()

    def setup_dashboard(self):
        layout = QVBoxLayout(self.tab_dashboard)
        self.status_label = QLabel(self.t("d_ok"))
        self.status_label.setStyleSheet("font-size: 16px; color: #00ff88; margin-bottom: 20px;")
        layout.addWidget(self.status_label)
        scan_layout = QHBoxLayout()
        self.btn_quick = self.create_button(self.t("btn_q"), "#00ff88")
        self.btn_full = self.create_button(self.t("btn_f"), "#ff9900")
        self.btn_stop = self.create_button(self.t("btn_s"), "#ff4444")
        self.btn_stop.setEnabled(False)
        self.btn_quick.clicked.connect(lambda: self.start_manual_scan("quick"))
        self.btn_full.clicked.connect(lambda: self.start_manual_scan("full"))
        self.btn_stop.clicked.connect(self.stop_manual_scan)
        for b in [self.btn_quick, self.btn_full, self.btn_stop]: scan_layout.addWidget(b)
        layout.addLayout(scan_layout)
        sys_layout = QHBoxLayout()
        self.btn_startup = self.create_button(self.t("btn_auto"), "#8888ff")
        self.btn_hide = self.create_button(self.t("btn_hide"), "#8888ff")
        self.btn_startup.clicked.connect(self.add_to_startup_via_button)
        self.btn_hide.clicked.connect(self.hide_to_tray)
        sys_layout.addWidget(self.btn_startup); sys_layout.addWidget(self.btn_hide)
        layout.addLayout(sys_layout)
        layout.addStretch()

    def setup_processes(self):
        layout = QVBoxLayout(self.tab_processes)
        self.lbl_r_info = QLabel(self.t("r_info"))
        self.lbl_r_info.setStyleSheet("color: #a0a0a0; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(self.lbl_r_info)
        self.proc_table = QTableWidget(0, 4)
        self.proc_table.setHorizontalHeaderLabels([self.t(f"r_h{i}") for i in range(1, 5)])
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.setStyleSheet("background-color: #15151e; color: white;")
        layout.addWidget(self.proc_table)
        btn_layout = QHBoxLayout()
        self.btn_refresh_proc = self.create_button(self.t("btn_r_ref"), "#8888ff")
        self.btn_scan_proc = self.create_button(self.t("btn_r_scan"), "#ff4444")
        self.btn_refresh_proc.clicked.connect(self.refresh_process_list)
        self.btn_scan_proc.clicked.connect(self.scan_all_processes)
        btn_layout.addWidget(self.btn_refresh_proc); btn_layout.addWidget(self.btn_scan_proc)
        layout.addLayout(btn_layout)

    def refresh_process_list(self):
        self.proc_table.setRowCount(0)
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                row = self.proc_table.rowCount(); self.proc_table.insertRow(row)
                mem_mb = f"{proc.info['memory_info'].rss / (1024*1024):.1f} MB"
                self.proc_table.setItem(row, 0, QTableWidgetItem(str(proc.info['pid'])))
                self.proc_table.setItem(row, 1, QTableWidgetItem(proc.info['name']))
                self.proc_table.setItem(row, 2, QTableWidgetItem(mem_mb))
                self.proc_table.setItem(row, 3, QTableWidgetItem("..."))
            except: pass

    def scan_all_processes(self):
        threading.Thread(target=self.run_process_scan_thread, daemon=True).start()

    def run_process_scan_thread(self):
        for row in range(self.proc_table.rowCount()):
            pid_item = self.proc_table.item(row, 0)
            if not pid_item: continue
            try:
                proc = psutil.Process(int(pid_item.text())); exe_path = proc.exe()
                if exe_path:
                    is_infected, threat_name, _ = ScanEngine.analyze_file(exe_path)
                    if is_infected:
                        proc.terminate(); self.update_proc_table_signal.emit(row, "KILLED ☠️", "#ff4444")
                    else: self.update_proc_table_signal.emit(row, "Clean ✅", "#00ff88")
            except: self.update_proc_table_signal.emit(row, "System", "#8888ff")

    def safe_update_proc_table(self, row, text, color):
        item = QTableWidgetItem(text); item.setForeground(QBrush(QColor(color)))
        self.proc_table.setItem(row, 3, item)

    def setup_network(self):
        layout = QVBoxLayout(self.tab_network)
        self.lbl_n_info = QLabel(self.t("n_info"))
        self.lbl_n_info.setStyleSheet("color: #a0a0a0; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(self.lbl_n_info)
        self.net_table = QTableWidget(0, 5)
        self.net_table.setHorizontalHeaderLabels([self.t(f"n_h{i}") for i in range(1, 6)])
        self.net_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.net_table.setStyleSheet("background-color: #15151e; color: white;")
        layout.addWidget(self.net_table)
        self.btn_refresh_net = self.create_button(self.t("btn_n_ref"), "#00ffff")
        self.btn_refresh_net.clicked.connect(self.refresh_network_list)
        layout.addWidget(self.btn_refresh_net)

    def refresh_network_list(self):
        self.net_table.setRowCount(0)
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED' and conn.raddr:
                try:
                    proc = psutil.Process(conn.pid)
                    row = self.net_table.rowCount(); self.net_table.insertRow(row)
                    self.net_table.setItem(row, 0, QTableWidgetItem(str(conn.pid)))
                    self.net_table.setItem(row, 1, QTableWidgetItem(proc.name()))
                    self.net_table.setItem(row, 2, QTableWidgetItem(f"{conn.raddr.ip}:{conn.raddr.port}"))
                    si = QTableWidgetItem(self.t("n_conn")); si.setForeground(QBrush(QColor("#00ff88")))
                    self.net_table.setItem(row, 3, si)
                    kb = QPushButton(self.t("n_kill"))
                    kb.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
                    kb.clicked.connect(lambda _, p=conn.pid: self.kill_process(p))
                    self.net_table.setCellWidget(row, 4, kb)
                except: pass

    def kill_process(self, pid):
        try: psutil.Process(pid).terminate(); self.refresh_network_list()
        except: pass

    def setup_cloud(self):
        layout = QVBoxLayout(self.tab_cloud)
        self.api_group = QGroupBox(self.t("c_grp"))
        self.api_group.setStyleSheet("color: #8888ff; font-weight: bold; font-size: 14px;")
        api_layout = QHBoxLayout()
        self.api_input = QLineEdit(); self.api_input.setPlaceholderText(self.t("c_ph"))
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setStyleSheet("background-color: #1a1a24; color: white; padding: 8px; border: 1px solid #8888ff;")
        self.btn_save_api = QPushButton(self.t("c_save"))
        self.btn_save_api.setStyleSheet("background-color: #20202a; border: 1px solid #00ff88; color: white; padding: 8px;")
        self.btn_save_api.clicked.connect(self.save_api_key)
        api_layout.addWidget(self.api_input); api_layout.addWidget(self.btn_save_api)
        self.api_group.setLayout(api_layout); layout.addWidget(self.api_group)
        self.vt_status = QLabel(self.t("c_wait")); self.vt_status.setWordWrap(True)
        self.vt_status.setStyleSheet("color: #ff9900; margin-top: 15px; font-size: 14px;")
        layout.addWidget(self.vt_status)
        vt_btn_layout = QHBoxLayout()
        self.btn_vt_scan = self.create_button(self.t("btn_c_scan"), "#8888ff")
        self.btn_vt_quick = self.create_button(self.t("btn_c_quick"), "#00ff88")
        self.btn_vt_scan.clicked.connect(self.start_vt_scan)
        self.btn_vt_quick.clicked.connect(self.start_vt_quick_scan)
        vt_btn_layout.addWidget(self.btn_vt_scan); vt_btn_layout.addWidget(self.btn_vt_quick)
        layout.addLayout(vt_btn_layout); layout.addStretch()

    def load_api_key(self):
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\AegisSecurity", 0, reg.KEY_READ)
            val, _ = reg.QueryValueEx(key, "VT_API_KEY"); reg.CloseKey(key)
            if val:
                self.vt_api_key = val; self.api_input.setText(val)
                self.vt_status.setText(self.t("c_ready"))
                self.vt_status.setStyleSheet("color: #00ff88; font-size: 14px;")
        except: pass

    def save_api_key(self):
        self.vt_api_key = self.api_input.text().strip()
        if len(self.vt_api_key) > 20:
            try:
                key = reg.CreateKey(reg.HKEY_CURRENT_USER, r"Software\AegisSecurity")
                reg.SetValueEx(key, "VT_API_KEY", 0, reg.REG_SZ, self.vt_api_key); reg.CloseKey(key)
            except: pass
            self.vt_status.setText(self.t("c_ready"))
            self.vt_status.setStyleSheet("color: #00ff88; font-size: 14px;")

    def start_vt_quick_scan(self):
        if not self.vt_api_key: return
        downloads = os.path.join(os.environ['USERPROFILE'], "Downloads")
        newest_file, max_time = None, 0
        if os.path.exists(downloads):
            for root, _, files in os.walk(downloads):
                for f in files:
                    if f.lower().endswith(('.exe', '.bat', '.vbs', '.msi', '.jar', '.ps1')):
                        fp = os.path.join(root, f); mt = os.path.getmtime(fp)
                        if mt > max_time: max_time = mt; newest_file = fp
        if newest_file:
            self.vt_status.setText(f"⚡ Cloud Scan: '{os.path.basename(newest_file)}' ...")
            self.vt_status.setStyleSheet("color: #00ffff; font-size: 14px;")
            threading.Thread(target=self.vt_scan_thread, args=(newest_file,), daemon=True).start()

    def start_vt_scan(self):
        if not self.vt_api_key: return
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File")
        if not filepath: return
        self.vt_status.setText(f"🔄 Scanning '{os.path.basename(filepath)}' ...")
        self.vt_status.setStyleSheet("color: #00ffff; font-size: 14px;")
        threading.Thread(target=self.vt_scan_thread, args=(filepath,), daemon=True).start()

    def vt_scan_thread(self, filepath):
        try:
            with open(filepath, "rb") as f: data = f.read()
            file_hash = hashlib.sha256(data).hexdigest()
            headers = {"accept": "application/json", "x-apikey": self.vt_api_key}
            response = requests.get(f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers)
            if response.status_code == 200:
                stats = response.json()['data']['attributes']['last_analysis_stats']
                mal = stats.get('malicious', 0); har = stats.get('harmless', 0)
                if mal > 0: self.update_vt_result_signal.emit(f"🚨 THREAT: {mal} engines detected!", "#ff4444")
                else: self.update_vt_result_signal.emit(f"✅ SAFE: {har} engines found clean.", "#00ff88")
            elif response.status_code == 401: self.update_vt_result_signal.emit("❌ Invalid API Key!", "#ff4444")
            elif response.status_code == 404: self.update_vt_result_signal.emit("❓ Unknown file (not in DB).", "#ff9900")
            elif response.status_code == 429: self.update_vt_result_signal.emit("❌ Quota exceeded (max 4/min).", "#ff4444")
            else: self.update_vt_result_signal.emit(f"❌ HTTP Error: {response.status_code}", "#ff4444")
        except Exception as e:
            self.update_vt_result_signal.emit(f"Connection error: {e}", "#ff4444")

    def safe_update_vt_result(self, text, color):
        self.vt_status.setText(text)
        self.vt_status.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")

    def setup_quarantine(self):
        layout = QVBoxLayout(self.tab_quarantine)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([self.t(f"q_h{i}") for i in range(1, 5)])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background-color: #15151e; color: white;")
        layout.addWidget(self.table)
        btn_layout = QHBoxLayout()
        self.btn_res_all = QPushButton(self.t("btn_q_res"))
        self.btn_del_all = QPushButton(self.t("btn_q_del"))
        self.btn_res_all.setStyleSheet("background-color: #20202a; border: 1px solid #ff9900; padding: 10px; font-weight:bold; color:white;")
        self.btn_del_all.setStyleSheet("background-color: #20202a; border: 1px solid #ff4444; padding: 10px; font-weight:bold; color:white;")
        self.btn_res_all.clicked.connect(self.restore_all_quarantine)
        self.btn_del_all.clicked.connect(self.delete_all_quarantine)
        btn_layout.addWidget(self.btn_res_all); btn_layout.addWidget(self.btn_del_all)
        layout.addLayout(btn_layout)

    def restore_all_quarantine(self):
        for name, data in list(self.quarantine_data.items()):
            try: shutil.move(data['locked_path'], data['original_path']); del self.quarantine_data[name]
            except: pass
        self.table.setRowCount(0)

    def delete_all_quarantine(self):
        for name, data in list(self.quarantine_data.items()):
            try: os.remove(data['locked_path']); del self.quarantine_data[name]
            except: pass
        self.table.setRowCount(0)

    def add_threat_to_gui(self, safe_name, threat_name, original_path, desc):
        row = self.table.rowCount(); self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(safe_name))
        self.table.setItem(row, 1, QTableWidgetItem(threat_name))
        self.table.setItem(row, 2, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.table.setItem(row, 3, QTableWidgetItem(original_path))
        self.quarantine_data[safe_name] = {
            "original_path": original_path, "desc": desc,
            "locked_path": os.path.join(self.quarantine_dir, safe_name)
        }
        if self.isHidden() or self.isMinimized():
            self.tray_icon.showMessage(self.t("tray_title"),
                f"{threat_name} {self.t('tray_msg')}", QSystemTrayIcon.Warning, 5000)

    def clear_quarantine_alert(self, index):
        if index == 4: self.tabs.setTabText(4, self.t("t_qua"))

    def setup_repair(self):
        layout = QVBoxLayout(self.tab_repair)
        self.lbl_rp_info = QLabel(self.t("rp_info"))
        self.lbl_rp_info.setStyleSheet("color: #a0a0a0; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(self.lbl_rp_info)
        self.repair_table = QTableWidget(0, 3)
        self.repair_table.setHorizontalHeaderLabels([self.t(f"rp_h{i}") for i in range(1, 4)])
        self.repair_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.repair_table.setStyleSheet("background-color: #15151e; color: white;")
        layout.addWidget(self.repair_table)
        btn_layout = QHBoxLayout()
        self.btn_rp_scan = self.create_button(self.t("btn_rp_scan"), "#00ff88")
        self.btn_rp_fix1 = self.create_button(self.t("btn_rp_fix1"), "#ff9900")
        self.btn_rp_fix2 = self.create_button(self.t("btn_rp_fix2"), "#ff4444")
        self.btn_rp_scan.clicked.connect(self.check_system_health)
        self.btn_rp_fix1.clicked.connect(self.fix_selected_issues)
        self.btn_rp_fix2.clicked.connect(self.fix_all_issues)
        for b in [self.btn_rp_scan, self.btn_rp_fix1, self.btn_rp_fix2]: btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

    def check_system_health(self):
        self.repair_table.setRowCount(0)
        self.active_sys_keys = [
            (self.t("rp_k1"), reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "DisableTaskMgr", 1),
            (self.t("rp_k2"), reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\System", "DisableRegistryTools", 1),
            (self.t("rp_k3"), reg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\System", "DisableCMD", 1),
            (self.t("rp_k4"), reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoControlPanel", 1),
            (self.t("rp_k5"), reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "NoFolderOptions", 1),
            (self.t("rp_k6"), reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows Defender", "DisableAntiSpyware", 1),
            (self.t("rp_k7"), reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "DisableRealtimeMonitoring", 1)
        ]
        for item in self.active_sys_keys:
            name, hkey, path, value_name, broken_val = item; is_broken = False
            try:
                k = reg.OpenKey(hkey, path, 0, reg.KEY_READ)
                val, _ = reg.QueryValueEx(k, value_name)
                if val == broken_val: is_broken = True
                reg.CloseKey(k)
            except: pass
            row = self.repair_table.rowCount(); self.repair_table.insertRow(row)
            chk = QTableWidgetItem(name)
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if is_broken else Qt.Unchecked)
            self.repair_table.setItem(row, 0, chk)
            it = QTableWidgetItem(self.t("rp_bad") if is_broken else self.t("rp_ok"))
            it.setForeground(QBrush(QColor("#ff4444" if is_broken else "#00ff88")))
            self.repair_table.setItem(row, 1, it)
            self.repair_table.setItem(row, 2, QTableWidgetItem(self.t("rp_act")))

    def repair_registry_key(self, tool_name):
        for item in getattr(self, "active_sys_keys", []):
            if item[0] == tool_name:
                try:
                    k = reg.OpenKey(item[1], item[2], 0, reg.KEY_SET_VALUE)
                    reg.DeleteValue(k, item[3]); reg.CloseKey(k); return True
                except: return False
        return False

    def fix_selected_issues(self):
        for row in range(self.repair_table.rowCount()):
            chk = self.repair_table.item(row, 0)
            if chk and chk.checkState() == Qt.Checked: self.repair_registry_key(chk.text())
        self.check_system_health()

    def fix_all_issues(self):
        for item in getattr(self, "active_sys_keys", []): self.repair_registry_key(item[0])
        self.check_system_health()

    def setup_settings(self):
        layout = QVBoxLayout(self.tab_settings)
        self.lbl_s_lbl1 = QLabel(self.t("s_lbl1"))
        self.lbl_s_lbl1.setStyleSheet("font-size: 18px; font-weight:bold; color:#8888ff; margin-bottom:10px;")
        layout.addWidget(self.lbl_s_lbl1)
        self.cb1 = QCheckBox(self.t("s_cb1")); self.cb2 = QCheckBox(self.t("s_cb2"))
        self.cb3 = QCheckBox(self.t("s_cb3")); self.cb4 = QCheckBox(self.t("s_cb4"))
        cb_style = "QCheckBox { font-size: 14px; padding: 5px; color: white;} QCheckBox::indicator { width: 20px; height: 20px; }"
        for cb in [self.cb1, self.cb2, self.cb3, self.cb4]:
            cb.setChecked(True); cb.setStyleSheet(cb_style); layout.addWidget(cb)
        self.cb1.stateChanged.connect(self.toggle_realtime_protection)
        layout.addSpacing(20)
        self.lbl_s_lbl2 = QLabel(self.t("s_lbl2"))
        self.lbl_s_lbl2.setStyleSheet("font-size: 18px; font-weight:bold; color:#ff9900; margin-bottom:5px;")
        layout.addWidget(self.lbl_s_lbl2)
        self.exclusion_list = QListWidget()
        self.exclusion_list.setStyleSheet("background-color: #15151e; border: 1px solid #333; padding: 5px; font-size: 13px; color: white;")
        for item in EXCLUDED_DIRS: self.exclusion_list.addItem(item)
        layout.addWidget(self.exclusion_list)
        exc_btn_layout = QHBoxLayout()
        self.btn_s_add = QPushButton(self.t("btn_s_add"))
        self.btn_s_rem = QPushButton(self.t("btn_s_rem"))
        self.btn_s_add.setStyleSheet("background-color: #20202a; border: 1px solid #00ff88; padding: 10px; color: white;")
        self.btn_s_rem.setStyleSheet("background-color: #20202a; border: 1px solid #ff4444; padding: 10px; color: white;")
        self.btn_s_add.clicked.connect(self.add_exclusion)
        self.btn_s_rem.clicked.connect(self.remove_exclusion)
        exc_btn_layout.addWidget(self.btn_s_add); exc_btn_layout.addWidget(self.btn_s_rem)
        layout.addLayout(exc_btn_layout)

    def toggle_realtime_protection(self, state):
        if state == Qt.Checked or state == 2:
            self.start_realtime_protection()
            self.status_label.setText(self.t("d_ok"))
            self.status_label.setStyleSheet("font-size: 16px; color: #00ff88; margin-bottom: 20px;")
        else:
            if self.observer is not None and self.observer.is_alive():
                self.observer.stop(); self.observer.join(); self.observer = None
            self.status_label.setText(self.t("d_off"))
            self.status_label.setStyleSheet("font-size: 16px; color: #ff4444; margin-bottom: 20px;")

    def add_exclusion(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder: EXCLUDED_DIRS.append(folder); self.exclusion_list.addItem(folder)

    def remove_exclusion(self):
        selected = self.exclusion_list.currentItem()
        if selected:
            folder = selected.text()
            if folder in EXCLUDED_DIRS: EXCLUDED_DIRS.remove(folder)
            self.exclusion_list.takeItem(self.exclusion_list.row(selected))

    def start_manual_scan(self, scan_type):
        paths = ["C:\\"] if scan_type == "full" else [os.environ['USERPROFILE']]
        self.btn_stop.setEnabled(True); self.stop_scan_flag = False
        threading.Thread(target=self.run_scan_thread, args=(paths,), daemon=True).start()

    def stop_manual_scan(self):
        self.stop_scan_flag = True; self.status_label.setText(self.t("d_stop"))

    def run_scan_thread(self, paths):
        for b_path in paths:
            if self.stop_scan_flag: break
            for root, _, files in os.walk(b_path):
                if self.stop_scan_flag: break
                for file in files:
                    if self.stop_scan_flag: break
                    filepath = os.path.join(root, file)
                    self.scan_progress_signal.emit(f"{self.t('d_scan')} {filepath[-40:]}")
                    is_infected, t_name, desc = ScanEngine.analyze_file(filepath)
                    if is_infected:
                        safe_name = file + ".locked"
                        try:
                            shutil.move(filepath, os.path.join(self.quarantine_dir, safe_name))
                            if self.monitor:
                                self.monitor.threat_found_signal.emit(safe_name, t_name, filepath, desc)
                        except: pass
        self.scan_finished_signal.emit(not self.stop_scan_flag)

    def update_scan_status(self, text): self.status_label.setText(text)

    def scan_complete(self, completed):
        self.btn_stop.setEnabled(False)
        if completed: self.status_label.setText(self.t("d_ok"))

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        m = QMenu()
        a1 = QAction("Open Aegis", self); a2 = QAction("Quit (Shutdown Shield)", self)
        a1.triggered.connect(self.showNormal); a2.triggered.connect(self.real_quit)
        m.addAction(a1); m.addAction(a2)
        self.tray_icon.setContextMenu(m); self.tray_icon.show()

    def hide_to_tray(self):
        self.hide()
        self.tray_icon.showMessage("Aegis Security", "Protection Active in Background",
            QSystemTrayIcon.Information, 2000)

    def closeEvent(self, e): e.ignore(); self.hide_to_tray()

    def real_quit(self):
        self.guardian_timer.stop()
        if self.observer is not None and self.observer.is_alive():
            self.observer.stop(); self.observer.join()
        with open(EXIT_FLAG, "w") as f: f.write("quit")
        QApplication.instance().quit()

    def add_to_startup_via_button(self):
        try:
            # Guardian Task Scheduler ile zaten başlıyor
            # Security'yi sadece kullanıcı başlatır - Guardian açar
            task_cmd = (
                f'schtasks /create /tn "AegisGuardian" /tr "{GUARDIAN_PATH} --watcher" '
                f'/sc onstart /ru SYSTEM /rl HIGHEST /f'
            )
            subprocess.run(task_cmd, shell=True, capture_output=True)
            QMessageBox.information(self, "Auto-Start", self.t("msg_startup"))
        except Exception as e:
            pass

    def start_realtime_protection(self):
        if self.observer is not None and self.observer.is_alive():
            return
        self.monitor = RealTimeMonitor()
        self.monitor.threat_found_signal.connect(self.add_threat_to_gui)
        self.observer = Observer()
        try:
            self.observer.schedule(self.monitor, "C:\\", recursive=True)
            self.observer.start()
        except:
            self.observer = Observer()
            self.observer.schedule(self.monitor, os.environ['USERPROFILE'], recursive=True)
            self.observer.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    start_hidden = "--startup" in sys.argv
    window = AegisSecurityAV(start_hidden=start_hidden)
    sys.exit(app.exec_())