import time
import queue
import threading
import numpy as np
import torch
import silero_vad

from src.transcription.engine import load_model, transcribe


FRAME_SIZE = 512
FRAME_SEC = FRAME_SIZE / 16000
PRE_BUFFER_FRAMES = 17


class SpeechBuffer:
    def __init__(self, vad_model, threshold=0.5):
        self.vad = vad_model
        self.threshold = threshold

        self.state = "silence"
        self.speech_consecutive = 0
        self.silence_consecutive = 0
        self.audio_buffer = np.array([], dtype=np.float32)
        self.pre_buffer = np.array([], dtype=np.float32)
        self.speech_start_time = 0.0

        self.min_speech_frames = 10
        self.min_silence_frames = 20

    def reset(self):
        self.state = "silence"
        self.speech_consecutive = 0
        self.silence_consecutive = 0
        self.audio_buffer = np.array([], dtype=np.float32)
        self.pre_buffer = np.array([], dtype=np.float32)

    def process_chunk(self, chunk: np.ndarray) -> dict | None:
        tensor = torch.from_numpy(chunk).unsqueeze(0).float()
        prob = self.vad(tensor, 16000).item()

        self.pre_buffer = np.concatenate([self.pre_buffer, chunk])
        if len(self.pre_buffer) > PRE_BUFFER_FRAMES * FRAME_SIZE:
            self.pre_buffer = self.pre_buffer[-PRE_BUFFER_FRAMES * FRAME_SIZE:]

        if prob > self.threshold:
            self.speech_consecutive += 1
            self.silence_consecutive = 0

            if self.state == "silence" and self.speech_consecutive >= self.min_speech_frames:
                self.state = "speaking"
                self.speech_start_time = time.time()
                self.audio_buffer = self.pre_buffer.copy()

            if self.state == "speaking":
                self.audio_buffer = np.concatenate([self.audio_buffer, chunk])
        else:
            self.silence_consecutive += 1

            if self.state == "speaking":
                self.audio_buffer = np.concatenate([self.audio_buffer, chunk])
                if self.silence_consecutive >= self.min_silence_frames:
                    self.state = "silence"
                    seg = {
                        "audio": self.audio_buffer.copy(),
                        "start": self.speech_start_time,
                        "end": time.time(),
                    }
                    self.audio_buffer = np.array([], dtype=np.float32)
                    self.speech_consecutive = 0
                    self.silence_consecutive = 0
                    return seg

            if self.state == "silence":
                self.speech_consecutive = 0

        return None


class LiveStream:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size
        self.vad_model = silero_vad.load_silero_vad()
        self.whisper_model = None

        self.vad_queue: queue.Queue[np.ndarray] = queue.Queue()
        self.transcribe_queue: queue.Queue[dict] = queue.Queue()
        self.display_queue: queue.Queue[dict] = queue.Queue()

        self.running = False
        self.segment_id = 0
        self.current_rms: float = 0.0

        self._vad_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None

    def start(self):
        self.running = True
        self.whisper_model = load_model(self.model_size)

        self._vad_thread = threading.Thread(target=self._vad_loop, daemon=True)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._vad_thread.start()
        self._worker_thread.start()

    def stop(self):
        self.running = False

    def push_audio(self, chunk: np.ndarray):
        self.current_rms = np.sqrt(np.mean(chunk ** 2))
        self.vad_queue.put(chunk)

    def _vad_loop(self):
        frame_buffer = np.array([], dtype=np.float32)
        speech_buf = SpeechBuffer(self.vad_model)

        while self.running:
            try:
                chunk = self.vad_queue.get(timeout=0.1)
                frame_buffer = np.concatenate([frame_buffer, chunk])

                while len(frame_buffer) >= FRAME_SIZE:
                    frame = frame_buffer[:FRAME_SIZE].copy()
                    frame_buffer = frame_buffer[FRAME_SIZE:]

                    seg = speech_buf.process_chunk(frame)
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
                    "text": f"[VAD error: {e}]",
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
