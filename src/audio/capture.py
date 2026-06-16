import subprocess
import signal
import threading
import numpy as np


def find_monitor_source() -> str | None:
    try:
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
    except FileNotFoundError:
        pass
    return None


class AudioCapture:
    def __init__(self, target_sr: int = 16000):
        self.target_sr = target_sr
        self._callback = None
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        monitor_name = find_monitor_source()
        if monitor_name is None:
            raise RuntimeError(
                "No PulseAudio/PipeWire monitor source found.\n"
                "Ensure audio is playing (monitor appears when something plays).\n"
                "Or run: pactl list sources short | grep monitor"
            )
        self.monitor_name = monitor_name

    def start(self, callback):
        self._callback = callback
        self._running = True

        self._process = subprocess.Popen(
            [
                "ffmpeg",
                "-f", "pulse",
                "-i", self.monitor_name,
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
