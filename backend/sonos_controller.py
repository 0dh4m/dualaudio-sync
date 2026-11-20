import logging
import socket
import threading
import time
import concurrent.futures
import soco

logger = logging.getLogger("SonosController")

class SonosController:
    def __init__(self, target_ip=None, auto_stream_url=None):
        self.device = None
        self.target_ip = target_ip
        self.is_connected = False
        self.device_name = "Sonos Play:1"
        self.current_volume = 45
        self.auto_stream_url = auto_stream_url
        self._lock = threading.Lock()
        
        # Start background auto-discovery loop if not connected
        self._running = True
        self._discovery_thread = threading.Thread(target=self._auto_discovery_worker, daemon=True)
        self._discovery_thread.start()

        if target_ip:
            self.connect(target_ip)

    def connect(self, ip):
        """Connects to Sonos device by IP."""
        with self._lock:
            try:
                self.target_ip = ip
                device = soco.SoCo(ip)
                info = device.get_speaker_info(timeout=3)
                self.device = device
                self.device_name = info.get("zone_name", "Sonos Play:1")
                self.current_volume = device.volume
                self.is_connected = True
                logger.info(f"Connected to Sonos: {self.device_name} ({ip})")
                
                # Auto-start stream if URL is provided
                if self.auto_stream_url:
                    self._start_stream_internal(self.auto_stream_url)
                    
                return True, f"Connected to {self.device_name} ({ip})"
            except Exception as e:
                self.device = None
                self.is_connected = False
                logger.warning(f"Could not connect to Sonos at {ip}: {e}")
                return False, str(e)

    def _auto_discovery_worker(self):
        """Runs in background to find Sonos automatically if not connected."""
        while self._running:
            if not self.is_connected:
                devices = self.discover_devices()
                if devices and len(devices) > 0:
                    found_ip = devices[0]["ip"]
                    logger.info(f"Auto-discovery found Sonos at {found_ip}. Connecting...")
                    self.connect(found_ip)
            time.sleep(6)

    def discover_devices(self, local_interface_ip=None):
        """Scans for Sonos using SSDP and subnet probing."""
        discovered = []

        # 1. SSDP
        try:
            kwargs = {"timeout": 3}
            if local_interface_ip:
                kwargs["interface_addr"] = local_interface_ip
            devices = soco.discover(**kwargs)
            if devices:
                for d in devices:
                    try:
                        info = d.get_speaker_info(timeout=2)
                        name = info.get("zone_name", "Sonos Speaker")
                    except Exception:
                        name = "Sonos Speaker"
                    discovered.append({"ip": d.ip_address, "name": name, "model": "Play:1"})
        except Exception:
            pass

        if discovered:
            return discovered

        # 2. Subnet port 1400 scan
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
            s.close()
            prefix = ".".join(my_ip.split(".")[:3])

            def check_host(ip):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                try:
                    if sock.connect_ex((ip, 1400)) == 0:
                        try:
                            d = soco.SoCo(ip)
                            info = d.get_speaker_info(timeout=2)
                            return {"ip": ip, "name": info.get("zone_name", "Sonos Speaker"), "model": "Play:1"}
                        except Exception:
                            return {"ip": ip, "name": f"Sonos ({ip})", "model": "Play:1"}
                except Exception:
                    pass
                finally:
                    sock.close()
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
                ips = [f"{prefix}.{i}" for i in range(1, 255)]
                results = list(executor.map(check_host, ips))
                for res in results:
                    if res:
                        discovered.append(res)
        except Exception:
            pass

        return discovered

    def _start_stream_internal(self, stream_url):
        if self.device:
            try:
                self.device.play_uri(stream_url, title="DualAudio Sync Live")
                logger.info(f"Sonos stream dispatched to {stream_url}")
            except Exception as e:
                logger.warning(f"Sonos play_uri warning: {e}")

    def play_stream(self, stream_url, title="DualAudio Sync Live"):
        self.auto_stream_url = stream_url
        if not self.is_connected or not self.device:
            return False, "Sonos not connected"
        try:
            self.device.play_uri(stream_url, title=title)
            return True, "Streaming started"
        except Exception as e:
            logger.error(f"Error starting Sonos stream: {e}")
            return False, str(e)

    def stop(self):
        if not self.is_connected or not self.device:
            return False, "Sonos not connected"
        try:
            self.device.stop()
            return True, "Sonos stopped"
        except Exception as e:
            logger.warning(f"Error stopping Sonos: {e}")
            return False, str(e)

    def set_volume(self, volume):
        vol = max(0, min(100, int(volume)))
        self.current_volume = vol
        if not self.is_connected or not self.device:
            return False
        try:
            self.device.volume = vol
            return True
        except Exception as e:
            logger.warning(f"Error setting Sonos volume: {e}")
            return False

    def get_status(self):
        return {
            "connected": self.is_connected,
            "ip": self.target_ip,
            "name": self.device_name,
            "volume": self.current_volume
        }

    def close(self):
        self._running = False
