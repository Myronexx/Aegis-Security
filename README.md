# 🛡️ Aegis Security | Defense Matrix

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Python](https://img.shields.io/badge/python-3.12-green)
![License](https://img.shields.io/badge/license-MIT-orange)

> A powerful, lightweight antivirus and system protection tool for Windows — built with Python and PyQt5.

---

## ✨ Features

- 🔴 **Real-Time File Protection** — Monitors your entire system for threats as they appear
- 🧠 **RAM Scanner** — Scans all running processes for injected malware
- 🌐 **Network Radar** — Monitors live internet connections and kills suspicious traffic
- ☁️ **Cloud Intel (VirusTotal)** — Scan any file against 70+ antivirus engines instantly
- 🍯 **Ransomware Honeypot** — Traps ransomware before it can encrypt your files
- 🔬 **Heuristic Engine** — Detects unknown threats by behavioral pattern analysis
- 🛠️ **System Repair** — Restores registry keys broken or locked by viruses
- 🔒 **Quarantine Center** — Safely isolates and manages detected threats
- 🛡️ **Aegis Guardian** — A Vanguard-style watchdog that keeps protection alive 24/7
- 🌍 **Multi-Language** — English, Turkish, French

---

## 🚀 Getting Started

### Download
Go to the [Releases](../../releases) page and download the latest version:
- `Aegis_Security.exe` — Main application
- `Aegis_Guardian.exe` — Background protection watchdog

Place **both files in the same folder** and run first `Aegis_Guardian.exe` and second `Aegis_Security.exe`.

### Requirements
- Windows 10 / 11 (64-bit)
- Administrator privileges (required for system-level protection)

---

## ⚠️ Antivirus False Positive Notice

Some antivirus engines may flag this application as suspicious.  
**This is a false positive.**

Aegis Security is compiled using [Nuitka](https://nuitka.net/), a Python-to-C compiler.  
Nuitka's packaging method is sometimes misidentified by antivirus heuristics — even for completely clean applications.

The full source code is available in this repository for anyone to inspect.  
You can build it yourself using the instructions below.

---

## 🔧 Build From Source

```bash
# Install dependencies
py -3.12 -m pip install pyqt5 psutil requests watchdog nuitka zstandard

# Compile Guardian
py -3.12 -m nuitka --onefile --windows-disable-console --windows-icon-from-ico=guardian.ico --enable-plugin=pyqt5 --mingw64 --output-filename=Aegis_Guardian.exe Aegis_Guardian.py

# Compile Security
py -3.12 -m nuitka --onefile --windows-disable-console --windows-icon-from-ico=aegis.ico --enable-plugin=pyqt5 --mingw64 --output-filename=Aegis_Security.exe aegis_security.py
```

---

## 🛡️ How Aegis Guardian Works

Aegis Guardian is a Vanguard-style watchdog process that runs silently in the background.

- Starts automatically with Windows (via Task Scheduler at SYSTEM level)
- Aegis Security **cannot launch** without Guardian running first
- If Security is killed by a virus or manually, Guardian revives it within 1 second
- If Guardian itself is killed, Security revives it within 3 seconds
- Both processes protect each other — mutual resurrection

---

## 📸 Screenshots

> <img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/3959966a-7128-43aa-8682-cd338c55a2e6" />
  <img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/f454ced0-b5d7-4cfd-a6d3-0874b249e3fe" />
  <img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/bd13eb30-82da-41e3-aa56-901a1115b11d" />
  <img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/b6c04c39-2f43-4baf-b9d0-7f82c69d6db2" />



---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Pull requests are welcome! If you find a bug or want to suggest a feature, please open an issue.

---

<p align="center">
  Made by <strong>Myronexx</strong>
</p>
