# 🎵 DualAudio Sync — Millisecond-Accurate Multi-Device Audio Synchronizer

<div align="center">

[![Author](https://img.shields.io/badge/Author-0dh4m-00E5FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0dh4m)
[![Technology](https://img.shields.io/badge/Audio-WASAPI%20%7C%20UPnP%20%7C%20DLNA-7928CA?style=for-the-badge)](https://github.com/0dh4m/dualaudio-sync)
[![Python](https://img.shields.io/badge/Backend-Python%20Flask-FF0080?style=for-the-badge&logo=python&logoColor=white)](https://github.com/0dh4m/dualaudio-sync)
[![Hardware](https://img.shields.io/badge/Hardware-Sonos%20Play:1%20%2B%20Citytek-success?style=for-the-badge)](https://github.com/0dh4m/dualaudio-sync)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

**An echo-minimizing audio broadcasting engine bridging two fundamentally different sound systems:**
1. **Sonos Play:1**: Network Wi-Fi speaker communicating via UPnP/DLNA HTTP audio streams.
2. **Citytek MF109099**: Local speaker paired via Windows Bluetooth audio or 3.5mm AUX.

[Features](#-key-features) • [How It Works](#-problem--engineering-solution) • [Repository](#-repository-structure) • [Quickstart](#-installation--usage)

</div>

---

## ⚡ Problem & Engineering Solution

Wirelessly pairing a network Wi-Fi speaker (Sonos Play:1) with a direct Bluetooth/AUX speaker produces a noticeable acoustic delay (typically between 200ms to 900ms), resulting in severe echo and phase distortion.

**DualAudio Sync solves this through:**
- **WASAPI Loopback Capture**: Low-overhead real-time capture of the Windows Master Audio mix.
- **Precision Delay Line Engine**: High-resolution buffer calibration down to the millisecond (0ms – 3000ms).
- **Synchronous Metronome Calibration**: Integrated rhythmic beat calibration pulse enabling manual, ear-tuned echo alignment.
- **UPnP / DLNA Local HTTP Streamer**: Transmits chunked lossless PCM/WAV streams over the local subnet directly into the Sonos UPnP media renderer.

---

## 🌟 Key Features

- 🖥️ **Master System Audio Broadcast (WASAPI)**: Stream any audio played on your PC (YouTube, Spotify, Netflix, games, DAW, Zoom) simultaneously to both speakers.
- 🎵 **Drag-and-Drop Local Audio Player**: Upload and play MP3, WAV, and FLAC files with interactive seek bar, volume balance, and loop control.
- ⏱️ **Millisecond Calibration Slider**: Smooth, real-time latency calibration slider (0–3000 ms) with instant preset storage.
- 🥁 **Acoustic Sync Metronome**: One-click sync calibration tone emitting an audio pulse every 1,000 ms to dial in phase alignment.
- 🌐 **Modern Glassmorphic UI**: Ultra-responsive dark control deck with live playback telemetry, speaker connection indicators, and master volume control.
- 🔌 **Guided Audio Routing Setup**: Helper script that opens the official VB-Audio Virtual Cable download page when extra routing is needed.

---

## 📂 Repository Structure

```text
dualaudio-sync/
├── app.py                          # Root launcher (adds backend/ to sys.path)
├── backend/
│   ├── app.py                      # Flask HTTP server & 350 ms status polling API
│   ├── audio_engine.py             # WASAPI loopback capture & delay calibration
│   ├── sonos_controller.py         # UPnP / DLNA discovery and AVTransport engine
│   └── presets.json                # Saved speaker delay profiles
├── web/
│   ├── index.html                  # Glassmorphic control dashboard
│   ├── app.js                      # State polling, sliders & transport handlers
│   └── style.css                   # Custom theme & responsive styling
├── scripts/
│   ├── install_requirements.bat    # Installs requirements.txt
│   ├── install_vbcable.bat         # Opens the VB-Audio Virtual Cable page
│   └── start.bat                   # One-click launcher
├── docs/README_AR.md               # Detailed documentation in Arabic
└── requirements.txt
```

---

## 🚀 Installation & Usage

### 1. Requirements
- Windows 10 or 11 (64-bit).
- **Python 3.10 – 3.12** (the code uses the `audioop` module, removed in Python 3.13).
- Sonos Play:1 connected to your local Wi-Fi subnet.
- Citytek speaker paired via Bluetooth or plugged into AUX.

### 2. Setup (One-Click)
Run the automated installation script as Administrator:
```cmd
scripts\install_requirements.bat
```
If your routing setup needs a virtual cable, run `scripts\install_vbcable.bat` — it opens the official VB-Audio download page; the driver itself must be installed manually.

### 3. Start DualAudio Sync
Double-click `scripts\start.bat` or run:
```bash
python app.py
```
Open your browser at `http://localhost:5000` to access the Control Deck.

---

## 👤 Author & Copyright

**Adham Cherkaoui Eddeqaqi (0dh4m)**  
- 🌐 Portfolio: [0dh4m.github.io](https://0dh4m.github.io/)
- 🐙 GitHub: [@0dh4m](https://github.com/0dh4m)
- 📧 Email: 0dh4mm@gmail.com

---

## 📄 License

Proprietary and confidential — see [LICENSE](LICENSE). Unauthorized copying or distribution is prohibited.

*Copyright © 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.*
