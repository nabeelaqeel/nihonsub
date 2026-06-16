import os
import platform
import subprocess
import threading
import numpy as np


def _os_name() -> str:
    return platform.system()


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


def _find_wasapi_loopback() -> str | None:
    devices = _list_wasapi_devices()
    for d in devices:
        if "cable" in d.lower():
            return d
    if devices:
        return devices[0]
    return None


def _list_avfoundation_devices() -> list[dict]:
    proc = subprocess.run(
        ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True, text=True, stderr=subprocess.PIPE,
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


def _capture_device() -> tuple[str, list[str]]:
    os_name = _os_name()
    if os_name == "Linux":
        monitor = _find_pulse_monitor()
        if monitor is None:
            raise RuntimeError(
                "No PulseAudio monitor source found.\n"
                "  Ensure audio is playing so the monitor is active.\n"
                "  Run: pactl list sources short | grep monitor"
            )
        return "pulse", ["-f", "pulse", "-i", monitor]

    elif os_name == "Windows":
        device = _find_wasapi_loopback()
        if device is None:
            raise RuntimeError(
                "No WASAPI loopback device found.\n"
                "  Install VB-Cable (https://vb-audio.com/Cable/)\n"
                "  Set your system audio output to 'CABLE Input'.\n"
                "  Then restart nihonsub."
            )
        return "wasapi", ["-f", "wasapi", "-i", device]

    elif os_name == "Darwin":
        idx = _find_avfoundation_device()
        if idx is None:
            raise RuntimeError(
                "No AVFoundation audio capture device found.\n"
                "  Install BlackHole (https://github.com/ExistentialAudio/BlackHole)\n"
                "  Set your system audio output to BlackHole.\n"
                "  Then restart nihonsub."
            )
        return "avfoundation", ["-f", "avfoundation", "-i", f"{idx}:none"]

    else:
        raise RuntimeError(f"Unsupported platform: {os_name}")


class AudioCapture:
    def __init__(self, target_sr: int = 16000):
        self.target_sr = target_sr
        self._callback = None
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        self._backend_name, self._ffmpeg_input_args = _capture_device()

    def start(self, callback):
        self._callback = callback
        self._running = True

        self._process = subprocess.Popen(
            [
                "ffmpeg",
                *self._ffmpeg_input_args,
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

    def stop(self):
        self._running = False
        if self._process:
            self._process.stdout.close()
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None
        self._thread = None

    def _read_loop(self):
        BYTES_PER_FRAME = 4
        CHUNK_FRAMES = self.target_sr // 10
        CHUNK_SIZE = CHUNK_FRAMES * BYTES_PER_FRAME

        assert self._process is not None
        assert self._process.stdout is not None

        leftover = b""
        while self._running:
            try:
                raw = self._process.stdout.read(CHUNK_SIZE)
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
