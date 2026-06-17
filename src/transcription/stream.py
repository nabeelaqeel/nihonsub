import queue
import threading
import numpy as np

from src.transcription.engine import load_model, transcribe
from src.transcription.segmenter import TimeSegmenter, VadSegmenter, FRAME_SIZE


class LiveStream:
    def __init__(self, model_size: str = "small", mode: str = "time", interval_sec: float = 15.0, silence_duration_sec: float = 0.64):
        self.model_size = model_size
        self.mode = mode
        self.interval_sec = interval_sec
        self.silence_duration_sec = silence_duration_sec
        self.segmenter = None
        self.whisper_model = None

        self.vad_queue: queue.Queue[np.ndarray] = queue.Queue()
        self.transcribe_queue: queue.Queue[dict] = queue.Queue()
        self.display_queue: queue.Queue[dict] = queue.Queue()

        self.running = False
        self.segment_id = 0
        self.current_rms: float = 0.0
        self._rms_lock = threading.Lock()

        self._segment_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None

    def start(self):
        self.running = True
        self.whisper_model = load_model(self.model_size)

        if self.mode == "vad":
            import silero_vad
            vad_model = silero_vad.load_silero_vad()
            self.segmenter = VadSegmenter(vad_model, silence_duration_sec=self.silence_duration_sec)
        else:
            self.segmenter = TimeSegmenter(interval_sec=self.interval_sec)

        self._segment_thread = threading.Thread(target=self._segment_loop, daemon=True)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._segment_thread.start()
        self._worker_thread.start()

    def stop(self):
        self.running = False

    def push_audio(self, chunk: np.ndarray):
        with self._rms_lock:
            self.current_rms = np.sqrt(np.mean(chunk ** 2))
        self.vad_queue.put(chunk)

    def _segment_loop(self):
        frame_buffer = np.array([], dtype=np.float32)

        while self.running:
            try:
                chunk = self.vad_queue.get(timeout=0.1)

                if self.mode == "vad":
                    frame_buffer = np.concatenate([frame_buffer, chunk])
                    while len(frame_buffer) >= FRAME_SIZE:
                        frame = frame_buffer[:FRAME_SIZE].copy()
                        frame_buffer = frame_buffer[FRAME_SIZE:]
                        seg = self.segmenter.add_audio(frame)
                        if seg is not None:
                            self.transcribe_queue.put(seg)
                else:
                    seg = self.segmenter.add_audio(chunk)
                    if seg is not None:
                        self.transcribe_queue.put(seg)
            except queue.Empty:
                continue
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.display_queue.put({
                    "id": -1,
                    "start": 0,
                    "end": 0,
                    "text": f"[segmenter error: {e}]",
                    "language": "",
                })

    def _worker_loop(self):
        while self.running:
            try:
                seg = self.transcribe_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if not self.running:
                break

            try:
                audio = seg["audio"]

                segments, lang = transcribe(
                    self.whisper_model,
                    audio,
                    language="ja",
                    beam_size=5,
                    word_timestamps=False,
                )

                if segments:
                    combined = "".join(s["text"] for s in segments)
                    self.segment_id += 1
                    result = {
                        "id": self.segment_id,
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": combined,
                        "language": lang,
                    }
                    self.display_queue.put(result)
            except Exception as e:
                import traceback
                self.display_queue.put({
                    "id": -1,
                    "start": 0,
                    "end": 0,
                    "text": f"[transcribe error: {e}]",
                    "language": "",
                    "error": traceback.format_exc(),
                })
