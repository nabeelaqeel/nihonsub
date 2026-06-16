# Live Listen

Capture system audio in real-time and transcribe it as it plays.

## How It Works

### Threading Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Capture Thread  │────►│   VAD Thread     │────►│  Worker Thread     │────► display_queue
│  (audio source)  │     │  (silero-vad)    │     │ (faster-whisper)   │
│                  │     │                  │     │                    │
│  Reads audio     │     │  512-sample      │     │  Transcribes       │
│  chunks from     │     │  frames, tracks  │     │  speech segment    │
│  system loopback │     │  speech state    │     │  in bg thread      │
└──────────────────┘     └──────────────────┘     └────────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
  vad_queue               transcribe_queue          display_queue
                                                          │
                                                          ▼
                                                  ┌──────────────────┐
                                                  │  Main Thread     │
                                                  │  (rich + SRT)    │
                                                  │                  │
                                                  │  Live terminal   │
                                                  │  + SRT append    │
                                                  └──────────────────┘
```

Four threads coordinate via `queue.Queue`:

1. **Capture Thread** — reads audio from the platform's loopback device
2. **VAD Thread** — runs silero-vad on 32ms frames, detects speech segments
3. **Worker Thread** — transcribes each speech segment with faster-whisper
4. **Main Thread** — renders the rich display and writes .srt output

### Capture Backend Selection

The capture engine is selected automatically based on platform:

| Platform | Primary Engine | Fallback |
|----------|---------------|----------|
| Linux | ffmpeg + PulseAudio monitor | — |
| Windows | ffmpeg + WASAPI loopback | sounddevice (PortAudio) |
| macOS | ffmpeg + AVFoundation | — |

See [windows-support.md](windows-support.md) for Windows-specific details.

### VAD Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Frame size | 512 samples (32 ms at 16 kHz) | silero-vad v6 minimum |
| Threshold | 0.5 | Speech probability threshold |
| Min speech frames | 10 (320 ms) | Consecutive speech frames to trigger |
| Min silence frames | 20 (640 ms) | Consecutive silence to end segment |

The VAD accumulates audio during speech + a pre-buffer (17 frames, ~544 ms) to capture speech onset.

### Audio Level Meter

The live display header shows a real-time RMS audio level bar:

```
NihonSub — Listening  •  00:03:45,200  •  Audio: [██████░░░░] 50%
```

This indicates audio is flowing through the capture pipeline, even before VAD triggers transcription. If the bar is at 0%, audio is not reaching the capture device.

## Usage

```bash
# Default (auto-named SRT in data/output/)
python -m src listen

# Specify output file
python -m src listen -o live_subtitles.srt

# Faster model for lower latency
python -m src listen --model_size small
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--output, -o` | auto | Output SRT file path |
| `--model_size` | `small` | Whisper model (small recommended for live) |

### Latency Budget

| Step | Time |
|------|------|
| Audio buffer accumulation | ~0.5–1 s |
| VAD detection | ~0.2 s |
| Speech segment (natural pause) | ~0.5–2 s |
| faster-whisper transcribe (small) | ~1–3 s |
| **Total delay** | **~3–6 s** |

## Key Files

- `src/audio/capture.py` — platform-specific audio capture
- `src/transcription/stream.py` — VAD pipeline + threading
- `src/transcription/display.py` — rich terminal + SRT output
- `src/__main__.py` — CLI entry point

## Version History

| Version | Changes |
|---------|---------|
| v0.1 | Linux-only PulseAudio capture, 4-thread pipeline, rich display |
| v0.2 | Windows (WASAPI + sounddevice) + macOS (AVFoundation) capture backends, audio level meter |
