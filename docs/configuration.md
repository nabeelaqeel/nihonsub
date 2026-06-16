# Configuration

Settings are loaded from `.env` (optional) or use defaults.

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL_SIZE` | `medium` | Model size: tiny / base / small / medium / large-v3 |
| `WHISPER_DEVICE` | `auto` | Device: `auto` (auto-detect CUDA/CPU), `cuda`, `cpu` |
| `SUBTITLE_FORMAT` | `srt` | Output format: `srt` or `vtt` |
| `VAD_THRESHOLD` | `0.5` | Speech probability threshold (0.0–1.0) |
| `VAD_MIN_SPEECH_DURATION_MS` | `250` | Minimum speech duration to trigger (ms) |
| `VAD_MIN_SILENCE_DURATION_MS` | `500` | Silence duration to end a speech segment (ms) |

## Model Selection Guide

| Use Case | Recommended Model | Why |
|---|---|---|
| Batch file transcription | `medium` or `large-v3` | Best accuracy, time doesn't matter |
| Live listening (fast) | `small` or `base` | Lower latency (~2–4s per segment) |
| Live listening (accurate) | `medium` | Good accuracy if you have a GPU |
| Low-end laptop (CPU only) | `tiny` or `base` | Minimal memory/CPU usage |
