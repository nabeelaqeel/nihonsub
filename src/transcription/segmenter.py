import time
import numpy as np
import torch


FRAME_SIZE = 512
PRE_BUFFER_FRAMES = 17


class TimeSegmenter:
    def __init__(self, interval_sec: float = 15.0, sample_rate: int = 16000):
        self.target_samples = int(interval_sec * sample_rate)
        self.sample_rate = sample_rate
        self.buffer = np.array([], dtype=np.float32)
        self._start_time = time.time()

    def add_audio(self, chunk: np.ndarray) -> dict | None:
        self.buffer = np.concatenate([self.buffer, chunk])
        if len(self.buffer) >= self.target_samples:
            audio = self.buffer[:self.target_samples].copy()
            self.buffer = self.buffer[self.target_samples:]
            now = time.time()
            seg = {
                "audio": audio,
                "start": self._start_time,
                "end": now,
            }
            self._start_time = now
            return seg
        return None

    def reset(self):
        self.buffer = np.array([], dtype=np.float32)
        self._start_time = time.time()


class VadSegmenter:
    def __init__(self, vad_model, threshold: float = 0.5, silence_duration_sec: float = 0.64):
        self.vad = vad_model
        self.threshold = threshold

        self.state = "silence"
        self.speech_consecutive = 0
        self.silence_consecutive = 0
        self.audio_buffer = np.array([], dtype=np.float32)
        self.pre_buffer = np.array([], dtype=np.float32)
        self.speech_start_time = 0.0

        self.min_speech_frames = 10
        self.min_silence_frames = max(1, int(silence_duration_sec * 16000 / FRAME_SIZE))

    def add_audio(self, chunk: np.ndarray) -> dict | None:
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

    def reset(self):
        self.state = "silence"
        self.speech_consecutive = 0
        self.silence_consecutive = 0
        self.audio_buffer = np.array([], dtype=np.float32)
        self.pre_buffer = np.array([], dtype=np.float32)
