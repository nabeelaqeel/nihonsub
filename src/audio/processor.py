from pathlib import Path

import torch
import numpy as np
import soundfile as sf
import silero_vad


def load_vad_model():
    return silero_vad.load_silero_vad()


def _load_audio(path: str | Path, target_sr: int = 16000) -> torch.Tensor:
    wav, sr = sf.read(str(path))
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    wav = wav.astype(np.float32)
    if sr != target_sr:
        ratio = target_sr / sr
        new_len = int(len(wav) * ratio)
        indices = np.linspace(0, len(wav) - 1, new_len)
        wav = np.interp(indices, np.arange(len(wav)), wav).astype(np.float32)
    return torch.from_numpy(wav).unsqueeze(0)


def get_speech_timestamps(
    audio_path: str | Path,
    vad_model,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 500,
) -> list[dict]:
    wav = _load_audio(audio_path)

    speech_segments = silero_vad.get_speech_timestamps(
        wav,
        vad_model,
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
        return_seconds=True,
    )

    return speech_segments


def split_audio_on_speech_segments(
    audio_path: str | Path,
    speech_segments: list[dict],
) -> list[dict]:
    segments = []
    for seg in speech_segments:
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "audio_path": str(audio_path),
        })
    return segments
