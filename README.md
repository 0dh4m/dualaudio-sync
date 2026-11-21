# 🎵 DualAudio Sync — Sub-Millisecond Multi-Device Audio Synchronizer

<div align="center">

[![Author](https://img.shields.io/badge/Author-0dh4m-00E5FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0dh4m)
[![Technology](https://img.shields.io/badge/Audio-WASAPI%20%7C%20UPnP%20%7C%20DLNA-7928CA?style=for-the-badge)](https://github.com/0dh4m/dualaudio-sync)
[![Python](https://img.shields.io/badge/Backend-Python%20Flask-FF0080?style=for-the-badge&logo=python&logoColor=white)](https://github.com/0dh4m/dualaudio-sync)
[![Hardware](https://img.shields.io/badge/Hardware-Sonos%20Play:1%20%2B%20Citytek-success?style=for-the-badge)](https://github.com/0dh4m/dualaudio-sync)

**An advanced zero-echo audio broadcasting engine bridging two fundamentally incompatible sound systems into synchronized harmony:**
1. **Sonos Play:1**: Network Wi-Fi speaker communicating via UPnP/DLNA HTTP Audio Streams.
2. **Citytek MF109099**: Local speaker paired via Windows Bluetooth audio or 3.5mm AUX.

[Features](#-key-features) • [How It Works](#-how-it-works) • [Web Control Deck](#-interactive-web-controller) • [Quickstart](#-installation--usage)

</div>

---

## ⚡ Problem & Engineering Solution

Wirelessly pairing a network Wi-Fi speaker (Sonos Play:1) with a direct Bluetooth/AUX speaker produces a noticeable acoustic delay (typically between 200ms to 900ms), resulting in severe echo and phase distortion.

**DualAudio Sync solves this through:**
- **WASAPI Loopback Capture**: Low-overhead real-time capture of the Windows Master Audio mix.
- **Precision Delay Line Engine**: High-resolution buffer calibration down to the millisecond (0ms – 3000ms).
- **Synchronous Metronome Calibration**: Integrated rhythmic beat calibration pulse enabling zero-echo alignment purely by ear.
- **UPnP / DLNA Local HTTP Streamer**: Transmits chunked lossless PCM/WAV streams over the local subnet directly into the Sonos UPnP media renderer.

---

## 🌟 Key Features

- 🖥️ **Master System Audio Broadcast (WASAPI)**: Stream any audio played on your PC (YouTube, Spotify, Netflix, games, DAW, Zoom) simultaneously to both speakers.
- 🎵 **Drag-and-Drop Local Audio Player**: Upload and play MP3, WAV, and FLAC files with interactive seek bar, volume balance, and loop control.
- ⏱️ **Sub-Millisecond Calibration Slider**: Smooth, real-time latency calibration slider with instant preset storage.
- 🥁 **Acoustic Sync Metronome**: One-click sync calibration tone emitting an audio pulse every 1,000ms to dial in exact phase alignment.
- 🌐 **Modern Glassmorphic UI**: Ultra-responsive dark control deck with live playback telemetry, speaker connection indicators, and volume master control.
- 🚀 **Silent One-Click Setup**: Automated background Windows launchers and silent VB-Audio Virtual Cable installer.

---

## 📂 Repository Structure

```text
dualaudio-sync/
├── backend/
│   ├── app.py                      # Flask HTTP server & WebSocket event bus
│   ├── audio_engine.py             # WASAPI Loopback buffer & delay calibration
│   ├── sonos_controller.py         # UPnP / DLNA discovery and AVTransport engine
│   └── presets.json                # Saved speaker delay profiles
├── web/
│   ├── index.html                  # Cyberpunk glassmorphic control dashboard
│   ├── app.js                      # Real-time state management & slider handlers
│   └── style.css                   # Custom glowing theme & responsive styling
├── vbcable/                        # Bundled virtual audio driver binaries
├── scripts/install_requirements.bat        # Automated Python environment dependency setup
├── Install_Virtual_Cable_Silent_PC.bat # Automated silent driver installer
├── scripts/start.bat              # One-click background launcher
└── docs/README_AR.md                    # Detailed documentation in Arabic
```

---

## 🚀 Installation & Usage

### 1. Requirements
- Windows 10 or 11 (64-bit).
- Python 3.10+ installed and added to PATH.
- Sonos Play:1 connected to your local Wi-Fi subnet.
- Citytek speaker paired via Bluetooth or plugged into AUX.

### 2. Setup (One-Click)
Run the automated installation scripts as Administrator:
```cmd
scripts/install_requirements.bat
Install_Virtual_Cable_Silent_PC.bat
```

### 3. Start DualAudio Sync
Double-click `scripts/start.bat` or run:
```bash
python app.py
```
Open your browser at `http://localhost:5000` to access the Control Deck.

---

## 👤 Author & Copyright

**Adham Cherkaoui Eddeqaqi (0dh4m)**  
- 🌐 Portfolio: [0dh4m.github.io/portfolio](https://0dh4m.github.io/portfolio)
- 🐙 GitHub: [@0dh4m](https://github.com/0dh4m)
- 📧 Email: 0dh4mm@gmail.com

*Copyright © 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.*
