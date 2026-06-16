from pathlib import Path
from typing import BinaryIO

import numpy as np
from faster_whisper import WhisperModel


def load_model(model_size: str = "medium", device: str = "auto"):
    if device == "auto":
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(
    model,
    audio: str | Path | BinaryIO | np.ndarray,
    language: str = "ja",
    beam_size: int = 5,
    word_timestamps: bool = True,
) -> tuple[list[dict], str]:
    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=beam_size,
        word_timestamps=word_timestamps,
        vad_filter=False,
    )

    results = []
    for seg in segments:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    return results, info.language


def transcribe_segments(
    model,
    segments: list[dict],
    language: str = "ja",
    beam_size: int = 5,
) -> list[dict]:
    for seg in segments:
        seg_texts, _ = transcribe(
            model, seg["audio_path"], language=language,
            beam_size=beam_size, word_timestamps=False,
        )
        seg["text"] = " ".join(s["text"] for s in seg_texts) if seg_texts else ""
    return segments
