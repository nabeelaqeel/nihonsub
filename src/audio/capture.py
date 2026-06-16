import os
import platform
import subprocess
import threading
import numpy as np


def _os_name() -> str:
    return platform.system()


# ── Linux: PulseAudio monitor ──────────────────────────

def _find_pulse_monitor() -> str | None:
    result = subprocess.run(
        ["pactl", "list", "sources", "short"],
        capture_output=True, text=True,
    )
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and ".monitor" in parts[1]:
            return parts[1]
    return None


# ── Windows: ffmpeg WASAPI ─────────────────────────────

def _list_wasapi_devices() -> list[str]:
    proc = subprocess.run(
        ["ffmpeg", "-f", "wasapi", "-list_devices", "true", "-i", "dummy"],
        capture_output=True, text=True, stderr=subprocess.PIPE,
    )
    devices = []
    in_wasapi = False
    for line in proc.stderr.split("\n"):
        if "WASAPI audio devices" in line:
            in_wasapi = True
            continue
        if in_wasapi and '"' in line:
            import re
            m = re.search(r'"([^"]+)"', line)
            if m and "(loopback)" in line.lower():
                devices.append(m.group(1))
    return devices


def _find_wasapi_ffmpeg() -> str | None:
    try:
        devices = _list_wasapi_devices()
        return devices[0] if devices else None
    except Exception:
        return None


# ── Windows/macOS: sounddevice fallback ────────────────

def _find_sounddevice_device() -> tuple[int, str] | None:
    try:
        import sounddevice as sd
    except ImportError:
        return None

    priority_keywords = ["voicemeeter", "voice meeter", "vaio", "cable", "loopback", "stereo mix"]

    candidates: list[tuple[int, str, bool]] = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            name = dev["name"].lower()
            is_priority = any(kw in name for kw in priority_keywords)
            candidates.append((i, dev["name"], is_priority))

    if not candidates:
        return None

    priority = [c for c in candidates if c[2]]
    chosen = priority[0] if priority else candidates[0]
    return chosen[0], chosen[1]


# ── macOS: AVFoundation ────────────────────────────────

def _list_avfoundation_devices() -> list[dict]:
    proc = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True,
    )
    devices = []
    current_section = None
    for line in proc.stderr.split("\n"):
        if "[AVFoundation input device @ " not in line:
            continue
        line = line.split("] ", 1)[-1] if "] " in line else line
        line = line.strip()
        if "audio devices" in line:
            current_section = "audio"
            continue
        if "video devices" in line:
            current_section = None
            continue
        if current_section == "audio" and "[" in line and "]" in line:
            idx = line.split("[")[1].split("]")[0].strip()
            name = line.split("]", 1)[-1].strip()
            devices.append({"index": int(idx), "name": name})
    return devices


def _find_avfoundation_device() -> int | None:
    devices = _list_avfoundation_devices()
    for d in devices:
        if "blackhole" in d["name"].lower() or "soundflower" in d["name"].lower():
            return d["index"]
    if devices:
        return devices[0]["index"]
    return None


# ── Platform detection ─────────────────────────────────

def _detect_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def _capture_config() -> dict:
    os_name = _os_name()

    if os_name == "Linux":
        if not _detect_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found. Install it:\n"
                "  sudo apt install ffmpeg"
            )
        monitor = _find_pulse_monitor()
        if monitor is None:
            raise RuntimeError(
                "No PulseAudio monitor source found.\n"
                "  Ensure audio is playing so the monitor is active.\n"
                "  Run: pactl list sources short | grep monitor"
            )
        return {"engine": "ffmpeg", "args": ["-f", "pulse", "-i", monitor]}

    elif os_name == "Windows":
        if _detect_ffmpeg():
            device = _find_wasapi_ffmpeg()
            if device:
                return {"engine": "ffmpeg", "args": ["-f", "wasapi", "-i", device]}

        sd_dev = _find_sounddevice_device()
        if sd_dev is not None:
            idx, name = sd_dev
            print(f"Using sounddevice capture device: {name} (index {idx})")
            return {"engine": "sounddevice", "device_index": idx, "device_name": name}

        raise RuntimeError(
            "No audio capture device found.\n"
            "  Ensure ffmpeg is installed and on PATH, OR\n"
            "  Install VB-Cable (https://vb-audio.com/Cable/)\n"
            "  Set CABLE Input as your default playback device."
        )

    elif os_name == "Darwin":
        if not _detect_ffmpeg():
            raise RuntimeError(
                "ffmpeg not found. Install it:\n"
                "  brew install ffmpeg"
            )
        idx = _find_avfoundation_device()
        if idx is None:
            raise RuntimeError(
                "No AVFoundation audio capture device found.\n"
                "  Install BlackHole: brew install blackhole-2ch\n"
                "  Then create a Multi-Output Device in Audio MIDI Setup."
            )
        return {"engine": "ffmpeg", "args": ["-f", "avfoundation", "-i", f"{idx}:none"]}

    else:
        raise RuntimeError(f"Unsupported platform: {os_name}")


# ── AudioCapture class ─────────────────────────────────

class AudioCapture:
    def __init__(self, target_sr: int = 16000):
        self.target_sr = target_sr
        self._callback = None

        self._engine: str | None = None
        self._ffmpeg_process: subprocess.Popen | None = None
        self._sd_stream = None
        self._thread: threading.Thread | None = None
        self._running = False

        cfg = _capture_config()
        self._engine = cfg["engine"]
        if self._engine == "ffmpeg":
            self._ffmpeg_args = cfg["args"]
        else:
            self._sd_device_index = cfg["device_index"]
            dev_info = self._get_sd_device_info()
            self._sd_device_sr = int(dev_info["default_samplerate"])

    def _get_sd_device_info(self):
        import sounddevice as sd
        return sd.query_devices(self._sd_device_index)

    def start(self, callback):
        self._callback = callback
        self._running = True

        if self._engine == "ffmpeg":
            print(f"Capture engine: ffmpeg ({' '.join(self._ffmpeg_args)})")
            self._start_ffmpeg()
        else:
            print(f"Capture engine: sounddevice (device {self._sd_device_index})")
            self._start_sounddevice()

    def _start_ffmpeg(self):
        self._ffmpeg_process = subprocess.Popen(
            [
                "ffmpeg",
                *self._ffmpeg_args,
                "-ac", "1",
                "-ar", str(self.target_sr),
                "-f", "f32le",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=4096,
        )
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _start_sounddevice(self):
        import sounddevice as sd
        self._sd_stream = sd.InputStream(
            device=self._sd_device_index,
            channels=2,
            samplerate=self._sd_device_sr,
            callback=self._sd_callback,
        )
        self._sd_stream.start()

    def stop(self):
        self._running = False
        if self._engine == "ffmpeg":
            self._stop_ffmpeg()
        else:
            self._stop_sounddevice()

    def _stop_ffmpeg(self):
        if self._ffmpeg_process:
            self._ffmpeg_process.stdout.close()
            self._ffmpeg_process.terminate()
            try:
                self._ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._ffmpeg_process.kill()
                self._ffmpeg_process.wait()
            self._ffmpeg_process = None
        self._thread = None

    def _stop_sounddevice(self):
        if self._sd_stream:
            self._sd_stream.stop()
            self._sd_stream.close()
            self._sd_stream = None

    def _read_loop(self):
        BYTES_PER_FRAME = 4
        CHUNK_FRAMES = self.target_sr // 10
        CHUNK_SIZE = CHUNK_FRAMES * BYTES_PER_FRAME

        assert self._ffmpeg_process is not None
        assert self._ffmpeg_process.stdout is not None

        leftover = b""
        while self._running:
            try:
                raw = self._ffmpeg_process.stdout.read(CHUNK_SIZE)
                if not raw:
                    break
                data = leftover + raw
                n = len(data) // BYTES_PER_FRAME
                usable = n * BYTES_PER_FRAME
                leftover = data[usable:]
                if usable > 0:
                    chunk = np.frombuffer(data[:usable], dtype=np.float32)
                    if self._callback:
                        self._callback(chunk)
            except (BrokenPipeError, OSError, ValueError):
                break

    def _sd_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        if not self._running:
            return
        mono = indata.mean(axis=1).astype(np.float32)
        if self._sd_device_sr != self.target_sr:
            ratio = self.target_sr / self._sd_device_sr
            new_len = int(len(mono) * ratio)
            indices = np.linspace(0, len(mono) - 1, new_len)
            mono = np.interp(indices, np.arange(len(mono)), mono).astype(np.float32)
        if self._callback:
            self._callback(mono)
