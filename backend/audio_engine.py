# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <0dh4mm@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import os
import time
import math
import queue
import logging
import threading
import subprocess
import audioop
import numpy as np
import pyaudiowpatch as pyaudio
from collections import deque

logger = logging.getLogger("AudioEngine")

SAMPLE_RATE = 44100
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit
BYTES_PER_FRAME = CHANNELS * SAMPLE_WIDTH
CHUNK_FRAMES = 1024  # Lower chunk size (~23.2ms) for ultra-low latency & smoother jitter
CHUNK_BYTES = CHUNK_FRAMES * BYTES_PER_FRAME

def create_wav_header(sample_rate=SAMPLE_RATE, channels=CHANNELS, bits_per_sample=16):
    """Creates a standard 44-byte WAV header for continuous streaming."""
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = 0x7FFFFFFF
    file_size = data_size + 36

    header = bytearray()
    header.extend(b'RIFF')
    header.extend(file_size.to_bytes(4, 'little'))
    header.extend(b'WAVE')
    header.extend(b'fmt ')
    header.extend((16).to_bytes(4, 'little'))
    header.extend((1).to_bytes(2, 'little'))
    header.extend(channels.to_bytes(2, 'little'))
    header.extend(sample_rate.to_bytes(4, 'little'))
    header.extend(byte_rate.to_bytes(4, 'little'))
    header.extend(block_align.to_bytes(2, 'little'))
    header.extend(bits_per_sample.to_bytes(2, 'little'))
    header.extend(b'data')
    header.extend(data_size.to_bytes(4, 'little'))
    return bytes(header)


# Helper to ensure Windows endpoint volume is at 100%
def maximize_windows_device_volume(name_substr="MF109099"):
    try:
        from pycaw.pycaw import AudioUtilities
        for d in AudioUtilities.GetAllDevices():
            if name_substr.lower() in d.FriendlyName.lower():
                vol = d.EndpointVolume
                if vol:
                    vol.SetMasterVolumeLevelScalar(1.0, None)
                    vol.SetMute(0, None)
                    logger.info(f"Maximized Windows endpoint volume for {d.FriendlyName} to 100%")
                    return True
    except Exception as e:
        logger.debug(f"Volume check: {e}")
    return False

import winreg

# Helper to completely silence Windows notification sound banners and sound scheme clicks
def set_windows_sounds_silenced(silence=True):
    root = winreg.HKEY_CURRENT_USER
    # 1. Global notification sound toggle (Windows 10/11)
    try:
        notif_key_path = r'Software\Microsoft\Windows\CurrentVersion\Notifications\Settings'
        with winreg.OpenKey(root, notif_key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND', 0, winreg.REG_DWORD, 0 if silence else 1)
    except Exception as e:
        logger.debug(f"Notification registry setting: {e}")

    # 2. Scheme events under AppEvents\\Schemes\\Apps (Navigating clicks, notification dings, error chimes)
    base_path = r'AppEvents\Schemes\Apps'
    try:
        with winreg.OpenKey(root, base_path) as apps_key:
            app_idx = 0
            while True:
                try:
                    app_name = winreg.EnumKey(apps_key, app_idx)
                    app_idx += 1
                    with winreg.OpenKey(apps_key, app_name) as ev_parent_key:
                        ev_idx = 0
                        while True:
                            try:
                                ev_name = winreg.EnumKey(ev_parent_key, ev_idx)
                                ev_idx += 1
                                try:
                                    val_to_set = ''
                                    if not silence:
                                        try:
                                            with winreg.OpenKey(ev_parent_key, f'{ev_name}\\.Default') as def_key:
                                                val_to_set, _ = winreg.QueryValueEx(def_key, '')
                                        except Exception:
                                            val_to_set = ''
                                    with winreg.OpenKey(ev_parent_key, f'{ev_name}\\.Current', 0, winreg.KEY_SET_VALUE) as cur_key:
                                        winreg.SetValueEx(cur_key, '', 0, winreg.REG_SZ, val_to_set)
                                except FileNotFoundError:
                                    pass
                            except OSError:
                                break
                except OSError:
                    break
    except Exception as e:
        logger.debug(f"Scheme registry setting: {e}")


# Helper to completely mute Windows notification, alert, and click sounds
def mute_windows_system_sounds(mute=True):
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            proc = s.Process
            disp = (s.DisplayName or "").lower()
            if proc is None or "audiosrv.dll" in disp or "system" in disp:
                vol = s.SimpleAudioVolume
                vol.SetMute(1 if mute else 0, None)
                vol.SetMasterVolume(0.0 if mute else 1.0, None)
    except Exception as e:
        logger.debug(f"System sound session mute: {e}")

    try:
        set_windows_sounds_silenced(mute)
    except Exception as e:
        logger.debug(f"System sound scheme silence: {e}")
    return True


class AudioEngine:
    def __init__(self, sonos_controller=None):
        self.sonos = sonos_controller
        self.pyaudio_instance = pyaudio.PyAudio()
        
        # Audio routing settings
        self.citytek_device_index = None
        self.citytek_device_name = "MF109099"
        self.delay_ms = 1150  # Default delay (optimal Sonos Wi-Fi buffer compensation)
        
        # Volumes (0 to 100) - Maximum power by default
        self.master_volume = 100
        self.citytek_volume = 100
        self.sonos_volume = 100
        self.preamp_gain = 1.6  # 160% Pre-Amp Boost with soft limiter for rich, loud audio
        self.is_muted = False
        self.mute_system_notifications = True  # Block annoying Windows clicks and notification dings
        
        # Source & Playback state
        self.current_source = "system"
        self.is_playing = False
        self.is_calibrating = False
        
        # Audio distribution
        self._sonos_subscribers = []
        self._citytek_buffer = bytearray()
        self._buffer_lock = threading.Lock()
        
        # Real-time Visualizer levels
        self.level_l = 0.0
        self.level_r = 0.0
        
        # Workers & Threading
        self._running = True
        self._capture_thread = None
        self._citytek_thread = None
        self._stop_capture_event = threading.Event()
        
        # Mute Windows system sounds immediately and launch keeper thread
        mute_windows_system_sounds(True)
        self._sys_sounds_thread = threading.Thread(target=self._system_sounds_keeper_worker, daemon=True)
        self._sys_sounds_thread.start()
        
        # 1. Initialize output device (Citytek)
        self._init_citytek_device()
        
        # 2. Start Citytek playback consumer
        self._citytek_thread = threading.Thread(target=self._citytek_playback_worker, daemon=True)
        self._citytek_thread.start()
        
        # 3. Automatically start System Audio capture loop immediately!
        self.start_system_capture()

    def _system_sounds_keeper_worker(self):
        """Continuously guards and keeps Windows notification sounds muted."""
        while self._running:
            if getattr(self, "mute_system_notifications", True):
                try:
                    from pycaw.pycaw import AudioUtilities
                    for s in AudioUtilities.GetAllSessions():
                        proc = s.Process
                        disp = (s.DisplayName or "").lower()
                        if proc is None or "audiosrv.dll" in disp or "system" in disp:
                            vol = s.SimpleAudioVolume
                            if not vol.GetMute() or vol.GetMasterVolume() > 0.01:
                                vol.SetMute(1, None)
                                vol.SetMasterVolume(0.0, None)
                except Exception:
                    pass
            time.sleep(5)

    def toggle_system_sounds_mute(self):
        """Toggles muting of Windows system sounds."""
        self.mute_system_notifications = not self.mute_system_notifications
        mute_windows_system_sounds(self.mute_system_notifications)
        return self.mute_system_notifications

    def _init_citytek_device(self):
        """Auto-detects Citytek MF109099 or selects default output device."""
        found = False
        try:
            for i in range(self.pyaudio_instance.get_device_count()):
                dev = self.pyaudio_instance.get_device_info_by_index(i)
                if dev['maxOutputChannels'] > 0:
                    if "MF109099" in dev['name']:
                        self.citytek_device_index = i
                        self.citytek_device_name = dev['name']
                        found = True
                        logger.info(f"Auto-selected Citytek speaker: [{i}] {dev['name']}")
                        maximize_windows_device_volume("MF109099")
                        break
            
            if not found:
                default_dev = self.pyaudio_instance.get_default_output_device_info()
                self.citytek_device_index = default_dev['index']
                self.citytek_device_name = default_dev['name']
                logger.info(f"Citytek not found by name, using default output: [{self.citytek_device_index}] {self.citytek_device_name}")
        except Exception as e:
            logger.error(f"Error initializing audio devices: {e}")

    def list_output_devices(self):
        """Lists all Windows audio output devices."""
        devices = []
        try:
            for i in range(self.pyaudio_instance.get_device_count()):
                dev = self.pyaudio_instance.get_device_info_by_index(i)
                if dev['maxOutputChannels'] > 0:
                    devices.append({
                        "index": i,
                        "name": dev['name'],
                        "sample_rate": int(dev['defaultSampleRate']),
                        "is_citytek": "MF109099" in dev['name'],
                        "is_selected": (i == self.citytek_device_index)
                    })
        except Exception as e:
            logger.error(f"Error querying output devices: {e}")
        return devices

    def set_citytek_device(self, device_index):
        """Changes the audio device for Citytek/Bluetooth."""
        try:
            dev = self.pyaudio_instance.get_device_info_by_index(int(device_index))
            if dev['maxOutputChannels'] > 0:
                self.citytek_device_index = int(device_index)
                self.citytek_device_name = dev['name']
                logger.info(f"Citytek device switched to [{self.citytek_device_index}] {self.citytek_device_name}")
                maximize_windows_device_volume(self.citytek_device_name)
                return True, self.citytek_device_name
        except Exception as e:
            logger.error(f"Error setting Citytek device: {e}")
        return False, "Failed to set device"

    def set_delay_ms(self, delay_ms):
        """Sets the sync delay in milliseconds (0 - 4000ms)."""
        d = int(delay_ms) if delay_ms is not None else 1150
        if d <= 50:
            d = 1150
        self.delay_ms = max(50, min(4000, d))
        return self.delay_ms

    def set_preamp_gain(self, gain):
        """Sets digital pre-amp boost multiplier (1.0 to 3.0)."""
        self.preamp_gain = max(1.0, min(3.0, float(gain)))
        logger.info(f"Pre-amp gain set to: {self.preamp_gain}x")
        return self.preamp_gain

    def set_volume(self, target, volume):
        """Sets volume for master, citytek or sonos."""
        vol = max(0, min(100, int(volume)))
        if target == "master":
            self.master_volume = vol
        elif target == "citytek":
            self.citytek_volume = vol
            maximize_windows_device_volume("MF109099")
        elif target == "sonos":
            self.sonos_volume = vol
            if self.sonos:
                self.sonos.set_volume(vol)
        return vol

    # ==================== SONOS STREAM CLIENTS ====================

    def register_sonos_subscriber(self):
        """Registers a new HTTP client queue for streaming to Sonos."""
        q = queue.Queue(maxsize=150)
        self._sonos_subscribers.append(q)
        return q

    def unregister_sonos_subscriber(self, q):
        """Removes a disconnected Sonos HTTP streaming client."""
        if q in self._sonos_subscribers:
            self._sonos_subscribers.remove(q)

    # ==================== CORE AUDIO DISPATCH ====================

    def _broadcast_audio(self, raw_pcm_bytes):
        """
        Dispatches audio:
        1. Applies pre-amp gain boost with soft limiter.
        2. Immediately to Sonos HTTP queue (zero lag).
        3. To Citytek byte buffer for delay compensation.
        4. Updates real-time visualizer stereo VU meters.
        """
        # Apply Pre-Amp Gain Booster to make sound rich, loud and powerful
        if getattr(self, "preamp_gain", 1.0) > 1.01:
            try:
                samples = np.frombuffer(raw_pcm_bytes, dtype=np.int16).astype(np.float32)
                scaled = samples * self.preamp_gain
                np.clip(scaled, -32767.0, 32767.0, out=scaled)
                raw_pcm_bytes = scaled.astype(np.int16).tobytes()
            except Exception:
                pass

        # Calculate VU level meters
        try:
            samples = np.frombuffer(raw_pcm_bytes, dtype=np.int16)
            if len(samples) >= 2:
                left = samples[0::2].astype(np.float32)
                right = samples[1::2].astype(np.float32)
                rms_l = np.sqrt(np.mean(left**2) + 1e-6) / 32768.0
                rms_r = np.sqrt(np.mean(right**2) + 1e-6) / 32768.0
                self.level_l = min(1.0, float(rms_l * 2.8))
                self.level_r = min(1.0, float(rms_r * 2.8))
        except Exception:
            pass

        # 1. Dispatch to Sonos subscribers
        for q in list(self._sonos_subscribers):
            try:
                q.put_nowait(raw_pcm_bytes)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(raw_pcm_bytes)
                except Exception:
                    pass

        # 2. Append to Citytek delay ring buffer
        with self._buffer_lock:
            self._citytek_buffer.extend(raw_pcm_bytes)
            # Prevent runaway buffer if playback is paused (max 4 seconds buffer)
            max_allowed = int(4.5 * SAMPLE_RATE * BYTES_PER_FRAME)
            if len(self._citytek_buffer) > max_allowed:
                del self._citytek_buffer[:len(self._citytek_buffer) - max_allowed]

    # ==================== JITTER-FREE CITYTEK PLAYBACK ====================

    def _citytek_playback_worker(self):
        """
        Continuous, hardware-clocked playback worker for Citytek (Bluetooth/AUX).
        Maintains an exact delay buffer without underflows or stuttering.
        """
        current_stream = None
        current_device = None

        while self._running:
            target_device = self.citytek_device_index
            if target_device is None:
                time.sleep(0.05)
                continue

            # Ensure PyAudio output stream is open on target device
            if current_stream is None or current_device != target_device:
                if current_stream:
                    try:
                        current_stream.stop_stream()
                        current_stream.close()
                    except Exception:
                        pass
                    current_stream = None

                try:
                    current_stream = self.pyaudio_instance.open(
                        format=pyaudio.paInt16,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        output=True,
                        output_device_index=target_device,
                        frames_per_buffer=CHUNK_FRAMES
                    )
                    current_device = target_device
                    logger.info(f"Opened Citytek PyAudio output on device {target_device}")
                except Exception as e:
                    logger.error(f"Failed opening Citytek output on device {target_device}: {e}")
                    time.sleep(1.0)
                    continue

            # Target delay in bytes
            target_delay_bytes = int((self.delay_ms / 1000.0) * SAMPLE_RATE * BYTES_PER_FRAME)
            
            chunk_to_play = None
            with self._buffer_lock:
                buffer_len = len(self._citytek_buffer)
                if buffer_len >= target_delay_bytes + CHUNK_BYTES:
                    # We have sufficient delay buffer! Pop one chunk
                    chunk_to_play = bytes(self._citytek_buffer[:CHUNK_BYTES])
                    del self._citytek_buffer[:CHUNK_BYTES]
                    
                    # If buffer accumulated excess delay (e.g. user lowered delay slider), trim slightly
                    excess = len(self._citytek_buffer) - target_delay_bytes
                    if excess > (CHUNK_BYTES * 4):
                        del self._citytek_buffer[:excess]

            if chunk_to_play:
                try:
                    # Apply software volume scaling
                    gain = (self.citytek_volume / 100.0) * (self.master_volume / 100.0)
                    if self.is_muted:
                        gain = 0.0

                    if gain < 0.99 or gain > 1.01:
                        samples = np.frombuffer(chunk_to_play, dtype=np.int16).astype(np.float32)
                        samples = np.clip(samples * gain, -32768, 32767).astype(np.int16)
                        chunk_to_play = samples.tobytes()

                    # stream.write is hardware rate-paced, so it automatically provides perfectly smooth playback!
                    current_stream.write(chunk_to_play)
                except Exception as e:
                    logger.warning(f"Citytek playback write error: {e}")
                    try:
                        current_stream.close()
                    except Exception:
                        pass
                    current_stream = None
            else:
                # Buffer is still building up to delay_ms, sleep briefly
                time.sleep(0.01)

        if current_stream:
            try:
                current_stream.stop_stream()
                current_stream.close()
            except Exception:
                pass

    # ==================== AUTOMATIC SYSTEM AUDIO LOOPBACK ====================

    def _loopback_worker(self):
        """Continuously captures Windows system audio (WASAPI Loopback)."""
        logger.info("Starting automatic Windows audio capture...")
        p = pyaudio.PyAudio()
        stream = None
        ratecv_state = None

        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
            
            loopback_device = None
            # Priority 1: If VB-CABLE loopback exists, prioritize it for 100% silent laptop playback
            for lb in p.get_loopback_device_info_generator():
                if "CABLE" in lb['name']:
                    loopback_device = lb
                    logger.info(f"Using VB-CABLE silent loopback: {lb['name']}")
                    break

            # Priority 2: Use default speaker loopback
            if not loopback_device:
                if default_speakers.get('isLoopbackDevice', False):
                    loopback_device = default_speakers
                else:
                    for lb in p.get_loopback_device_info_generator():
                        if default_speakers['name'] in lb['name']:
                            loopback_device = lb
                            break
            
            # Priority 3: Any available loopback
            if not loopback_device:
                for lb in p.get_loopback_device_info_generator():
                    loopback_device = lb
                    break

            if not loopback_device:
                logger.error("No WASAPI Loopback device found!")
                self.is_playing = False
                p.terminate()
                return

            device_rate = int(loopback_device['defaultSampleRate'])
            device_channels = loopback_device['maxInputChannels']
            frames_to_read = int(CHUNK_FRAMES * (device_rate / SAMPLE_RATE))

            logger.info(f"Loopback active on: {loopback_device['name']} ({device_rate} Hz, {device_channels} ch)")

            stream = p.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                input=True,
                input_device_index=loopback_device['index'],
                frames_per_buffer=frames_to_read
            )

            self.is_playing = True

            while not self._stop_capture_event.is_set():
                if self.is_calibrating:
                    time.sleep(0.05)
                    continue

                raw_data = stream.read(frames_to_read, exception_on_overflow=False)

                # Convert to Stereo if needed
                if device_channels == 1:
                    raw_data = audioop.tostereo(raw_data, 2, 1, 1)
                elif device_channels > 2:
                    raw_data = audioop.tomono(raw_data, 2, 0.5, 0.5)
                    raw_data = audioop.tostereo(raw_data, 2, 1, 1)

                # Resample to 44.1 kHz if Windows is set to 48 kHz
                if device_rate != SAMPLE_RATE:
                    raw_data, ratecv_state = audioop.ratecv(
                        raw_data, 2, CHANNELS, device_rate, SAMPLE_RATE, ratecv_state
                    )

                self._broadcast_audio(raw_data)

        except Exception as e:
            logger.error(f"WASAPI Loopback capture error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()
            self.is_playing = False
            logger.info("WASAPI Loopback capture stopped.")

    def start_system_capture(self):
        """Starts automatic system loopback capture thread."""
        self.stop_capture()
        self._stop_capture_event.clear()
        self.current_source = "system"
        self._capture_thread = threading.Thread(target=self._loopback_worker, daemon=True)
        self._capture_thread.start()

    def stop_capture(self):
        """Stops active capture thread."""
        self._stop_capture_event.set()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=0.8)
        self.is_playing = False
        with self._buffer_lock:
            self._citytek_buffer.clear()
        self.level_l = 0.0
        self.level_r = 0.0

    # ==================== SYNC CALIBRATION METRONOME ====================

    def _calibration_worker(self):
        """Emits a clean 1000Hz click every second to calibrate sync."""
        logger.info("Metronome sync beat active...")
        self.is_calibrating = True

        # Generate 50ms 1kHz beep
        beep_len = int(SAMPLE_RATE * 0.05)
        t = np.linspace(0, 0.05, beep_len, endpoint=False)
        window = np.hanning(beep_len)
        beep_data = (np.sin(2 * np.pi * 1000 * t) * 0.8 * window * 32767).astype(np.int16)
        beep_stereo = np.column_stack((beep_data, beep_data)).ravel().tobytes()

        # Generate 950ms silence
        silence_len = int(SAMPLE_RATE * 0.95)
        silence_stereo = b'\x00' * (silence_len * BYTES_PER_FRAME)

        cycle = beep_stereo + silence_stereo
        chunks = [cycle[i:i+CHUNK_BYTES] for i in range(0, len(cycle), CHUNK_BYTES)]

        while not self._stop_capture_event.is_set():
            for c in chunks:
                if self._stop_capture_event.is_set():
                    break
                self._broadcast_audio(c)
                time.sleep(CHUNK_FRAMES / SAMPLE_RATE)

        self.is_calibrating = False

    def toggle_calibration(self):
        """Toggles between calibration metronome and live system audio."""
        if self.is_calibrating:
            self.stop_capture()
            self.start_system_capture()
            return False
        else:
            self.stop_capture()
            self._stop_capture_event.clear()
            self._capture_thread = threading.Thread(target=self._calibration_worker, daemon=True)
            self._capture_thread.start()
            return True

    def get_status(self):
        """Returns engine status."""
        return {
            "source": self.current_source,
            "is_playing": self.is_playing,
            "is_calibrating": self.is_calibrating,
            "delay_ms": self.delay_ms,
            "master_volume": self.master_volume,
            "citytek_volume": self.citytek_volume,
            "sonos_volume": self.sonos_volume,
            "is_muted": self.is_muted,
            "citytek_device": {
                "index": self.citytek_device_index,
                "name": self.citytek_device_name
            },
            "preamp_gain": round(getattr(self, "preamp_gain", 1.6), 1),
            "mute_system_notifications": getattr(self, "mute_system_notifications", True),
            "levels": {
                "left": round(self.level_l, 2),
                "right": round(self.level_r, 2)
            }
        }

    def close(self):
        self._running = False
        self.stop_capture()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
