# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <0dh4mm@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import os
import json
import socket
import logging
from flask import Flask, request, jsonify, Response, send_from_directory

from sonos_controller import SonosController
from audio_engine import AudioEngine, create_wav_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DualAudioSyncApp")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(os.path.dirname(BASE_DIR), "web")
PRESETS_FILE = os.path.join(BASE_DIR, "presets.json")

app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")

def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_presets(data):
    try:
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

presets = load_presets()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
SERVER_PORT = 5050
STREAM_URL = f"http://{LOCAL_IP}:{SERVER_PORT}/stream.wav"

# Initialize Controllers with auto-stream URL
sonos_ctrl = SonosController(target_ip=presets.get("sonos_ip") or None, auto_stream_url=STREAM_URL)
audio_engine = AudioEngine(sonos_controller=sonos_ctrl)

# Apply saved presets
if "delay_ms" in presets:
    audio_engine.set_delay_ms(presets["delay_ms"])
if "citytek_volume" in presets:
    audio_engine.set_volume("citytek", presets["citytek_volume"])
if "sonos_volume" in presets:
    audio_engine.set_volume("sonos", presets["sonos_volume"])
if "master_volume" in presets:
    audio_engine.set_volume("master", presets["master_volume"])
if "preamp_gain" in presets:
    audio_engine.set_preamp_gain(presets["preamp_gain"])
if "mute_system_notifications" in presets:
    audio_engine.mute_system_notifications = bool(presets["mute_system_notifications"])
    from audio_engine import mute_windows_system_sounds
    mute_windows_system_sounds(audio_engine.mute_system_notifications)


# ==================== STATIC / WEB UI ====================

@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


# ==================== SONOS HTTP AUDIO STREAM ====================

@app.route("/stream.wav")
def stream_wav():
    """Continuous PCM WAV stream for Sonos Play:1."""
    logger.info("Sonos client connected to /stream.wav")
    subscriber_queue = audio_engine.register_sonos_subscriber()

    def generate_audio():
        try:
            yield create_wav_header()
            while True:
                chunk = subscriber_queue.get()
                if chunk is None:
                    break
                yield chunk
        except GeneratorExit:
            logger.info("Sonos client disconnected from /stream.wav")
        finally:
            audio_engine.unregister_sonos_subscriber(subscriber_queue)

    return Response(
        generate_audio(),
        mimetype="audio/wav",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )


# ==================== REST API ENDPOINTS ====================

@app.route("/api/status", methods=["GET"])
def get_status():
    global LOCAL_IP, STREAM_URL
    LOCAL_IP = get_local_ip()
    STREAM_URL = f"http://{LOCAL_IP}:{SERVER_PORT}/stream.wav"
    sonos_ctrl.auto_stream_url = STREAM_URL
    
    return jsonify({
        "server": {
            "local_ip": LOCAL_IP,
            "port": SERVER_PORT,
            "stream_url": STREAM_URL
        },
        "sonos": sonos_ctrl.get_status(),
        "engine": audio_engine.get_status()
    })

# --- SONOS CONTROLS ---

@app.route("/api/sonos/connect", methods=["POST"])
def sonos_connect():
    data = request.json or {}
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"success": False, "message": "IP address required"}), 400
    
    success, msg = sonos_ctrl.connect(ip)
    if success:
        presets["sonos_ip"] = ip
        save_presets(presets)
        sonos_ctrl.play_stream(STREAM_URL)
    return jsonify({"success": success, "message": msg, "status": sonos_ctrl.get_status()})

@app.route("/api/sonos/volume", methods=["POST"])
def set_sonos_volume():
    data = request.json or {}
    vol = data.get("volume", 45)
    audio_engine.set_volume("sonos", vol)
    presets["sonos_volume"] = vol
    save_presets(presets)
    return jsonify({"success": True, "volume": vol})

# --- CITYTEK CONTROLS ---

@app.route("/api/devices", methods=["GET"])
def get_devices():
    return jsonify({"devices": audio_engine.list_output_devices()})

@app.route("/api/citytek/device", methods=["POST"])
def set_citytek_device():
    data = request.json or {}
    idx = data.get("index")
    if idx is None:
        return jsonify({"success": False, "message": "Index required"}), 400
    
    success, dev_name = audio_engine.set_citytek_device(idx)
    if success:
        presets["citytek_device_index"] = idx
        presets["citytek_device_name"] = dev_name
        save_presets(presets)
    return jsonify({"success": success, "device_name": dev_name})

@app.route("/api/citytek/volume", methods=["POST"])
def set_citytek_volume():
    data = request.json or {}
    vol = data.get("volume", 80)
    audio_engine.set_volume("citytek", vol)
    presets["citytek_volume"] = vol
    save_presets(presets)
    return jsonify({"success": True, "volume": vol})

# --- SYNC & CALIBRATION ---

@app.route("/api/sync/delay", methods=["POST"])
def set_sync_delay():
    data = request.json or {}
    delay = data.get("delay_ms", 1150)
    new_delay = audio_engine.set_delay_ms(delay)
    presets["delay_ms"] = new_delay
    save_presets(presets)
    return jsonify({"success": True, "delay_ms": new_delay})

@app.route("/api/sync/calibrate", methods=["POST"])
def toggle_calibration():
    is_cal = audio_engine.toggle_calibration()
    if is_cal and sonos_ctrl.is_connected:
        sonos_ctrl.play_stream(STREAM_URL, title="Calibration Click")
    return jsonify({"success": True, "calibrating": is_cal})

# --- VOLUMES ---

@app.route("/api/volume/master", methods=["POST"])
def set_master_volume():
    data = request.json or {}
    vol = data.get("volume", 85)
    audio_engine.set_volume("master", vol)
    presets["master_volume"] = vol
    save_presets(presets)
    return jsonify({"success": True, "volume": vol})

@app.route("/api/volume/mute", methods=["POST"])
def toggle_mute():
    audio_engine.is_muted = not audio_engine.is_muted
    return jsonify({"success": True, "is_muted": audio_engine.is_muted})

@app.route("/api/volume/boost", methods=["POST"])
def set_preamp_boost():
    data = request.json or {}
    boost = data.get("boost", 1.6)
    new_boost = audio_engine.set_preamp_gain(boost)
    presets["preamp_gain"] = new_boost
    save_presets(presets)
    return jsonify({"success": True, "preamp_gain": new_boost})

@app.route("/api/system_sounds/toggle", methods=["POST"])
def toggle_system_sounds():
    is_muted = audio_engine.toggle_system_sounds_mute()
    presets["mute_system_notifications"] = is_muted
    save_presets(presets)
    return jsonify({"success": True, "mute_system_notifications": is_muted})

# --- RECONNECT ALL ---

@app.route("/api/sync/restart", methods=["POST"])
def restart_audio_sync():
    """Restarts system loopback and tells Sonos to reconnect."""
    audio_engine.stop_capture()
    audio_engine.start_system_capture()
    if sonos_ctrl.is_connected:
        sonos_ctrl.play_stream(STREAM_URL)
    return jsonify({"success": True, "message": "Audio sync stream re-initialized."})


if __name__ == "__main__":
    logger.info("==================================================")
    logger.info("   DualAudio Sync Auto-Pilot Active")
    logger.info(f"   Dashboard: http://localhost:{SERVER_PORT}")
    logger.info(f"   Sonos Stream: {STREAM_URL}")
    logger.info("==================================================")
    app.run(host="0.0.0.0", port=SERVER_PORT, threaded=True, debug=False)
