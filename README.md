# 🛡️ Aegis Security | Defense Matrix

<p align="center">
  <img src="[https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge](https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge)" alt="Version">
  <img src="[https://img.shields.io/badge/platform-Windows-lightgrey?style=for-the-badge](https://img.shields.io/badge/platform-Windows-lightgrey?style=for-the-badge)" alt="Platform">
  <img src="[https://img.shields.io/badge/python-3.12-green?style=for-the-badge](https://img.shields.io/badge/python-3.12-green?style=for-the-badge)" alt="Python">
  <img src="[https://img.shields.io/badge/license-MIT-orange?style=for-the-badge](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)" alt="License">
</p>

> **A powerful, lightweight antivirus and system protection tool for Windows — built with Python and PyQt5.**

---

## ✨ Features

- 🔴 **Real-Time File Protection** — Monitors your entire system for threats as they appear.
- 🧠 **RAM Scanner** — Scans all running processes for injected malware.
- 🌐 **Network Radar** — Monitors live internet connections and kills suspicious traffic.
- ☁️ **Cloud Intel (VirusTotal)** — Scan any file against 70+ antivirus engines instantly.
- 🍯 **Ransomware Honeypot** — Traps ransomware before it can encrypt your files.
- 🔬 **Heuristic Engine** — Detects unknown threats by behavioral pattern analysis.
- 🛠️ **System Repair** — Restores registry keys broken or locked by viruses.
- 🔒 **Quarantine Center** — Safely isolates and manages detected threats.
- 🛡️ **Aegis Guardian** — A Vanguard-style watchdog that keeps protection alive 24/7.
- 🌍 **Multi-Language** — Available in English, Turkish, and French.

---

## 🚀 Getting Started

### Download & Installation
Go to the [Releases](../../releases) page and download the latest `.rar` or `.zip` archive.

> [!WARNING]  
> **CRITICAL DIRECTORY RULE:** After extracting the downloaded archive, **DO NOT** separate the files. `Aegis_Security.exe` and `Aegis_Guardian.exe` (along with any other generated folders) **MUST remain in the exact same folder**. If you move the main executable to your Desktop alone, the GUI will not open and the Guardian architecture will fail.

**Run Instructions:**
1. Extract the archive to a folder of your choice.
2. Ensure both `.exe` files are side-by-side.
3. Run `Aegis_Guardian.exe` first (it will initialize silently).
4. Run `Aegis_Security.exe` to open the Defense Matrix interface.

### Requirements
- Windows 10 / 11 (64-bit)
- Administrator privileges (Required for Vanguard-style system-level protection)

---

## ⚠️ Antivirus False Positive Notice

Some antivirus engines or browsers may flag this application as suspicious.  
**This is a false positive.**

Aegis Security is compiled using [Nuitka](https://nuitka.net/), a Python-to-C compiler. Nuitka's packaging method is sometimes misidentified by antivirus heuristics — even for completely clean, open-source applications.

The full source code is available in this repository for anyone to inspect. You can safely build it yourself using the instructions below.

---

## 🔧 Build From Source

To avoid False Positives and build the project from scratch, follow these steps:

```bash
# 1. Install dependencies
py -3.12 -m pip install pyqt5 psutil requests watchdog nuitka zstandard

# 2. Compile Guardian Core
py -3.12 -m nuitka --standalone --windows-console-mode=disable --windows-company-name="Aegis Cyber Security" --windows-product-name="Aegis Guardian Core" --windows-file-version="1.0.0.0" --windows-icon-from-ico=guardian.ico --mingw64 Aegis_Guardian.py

# 3. Compile Security Matrix (GUI)
py -3.12 -m nuitka --standalone --windows-console-mode=disable --windows-company-name="Aegis Cyber Security" --windows-product-name="Aegis Defense Matrix" --windows-file-version="1.0.0.0" --windows-icon-from-ico=aegis.ico --enable-plugin=pyqt5 --mingw64 aegis_security.py
[!IMPORTANT]
After compiling: Nuitka will create two .dist folders. You must create a new folder (e.g., Aegis_Final), move everything from aegis_security.dist into it, and then copy Aegis_Guardian.exe from its .dist folder into that same Aegis_Final folder.

🛡️ How Aegis Guardian Works
Aegis Guardian is a Vanguard-style watchdog process that runs silently in the background to ensure absolute persistence.

Starts automatically with Windows (via Task Scheduler at SYSTEM level).

Aegis Security cannot launch without Guardian running first.

If Security is killed by a virus or manually via Task Manager, Guardian revives it within 1 second.

If Guardian itself is killed, Security revives it within 3 seconds.

Both processes protect each other — Mutual Resurrection.

📸 Screenshots
Soon...

📄 License
This project is licensed under the MIT License — see the LICENSE file for details.

🤝 Contributing
Pull requests are welcome! If you find a bug or want to suggest a feature, please open an issue.

<p align="center">
Made with 🛡️ by <strong>Myronexx</strong>
</p>
