# Architecture

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| ASR Engine | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (local, CTranslate2) |
| Voice Activity Detection | [`silero-vad`](https://github.com/snakers4/silero-vad) v6 |
| Audio Extraction (file mode) | `ffmpeg` via subprocess |
| Live Capture (live mode) | ffmpeg / sounddevice (platform-dependent) |
| CLI Framework | [`fire`](https://github.com/google/python-fire) |
| Terminal UI | [`rich`](https://github.com/Textualize/rich) |
| Config | `pydantic-settings` + `.env` |

## Data Flows

### File Transcribe

```
Input File (mp4/mkv/mp3/wav/m4a)
  │
  ▼
ffmpeg ──► 16 kHz mono WAV (temp)
  │
  ▼
silero-vad ──► speech segments with timestamps
  │
  ▼
faster-whisper ──► transcribed text
  │
  ▼
Subtitle Generator ──► .srt / .vtt
```

See [features/file-transcribe.md](features/file-transcribe.md) for details.

### Live Listen

```
System Audio (any app playing sound)
  │
  ▼
[Platform Capture Backend]
  ├── Linux:   ffmpeg + PulseAudio monitor
  ├── Windows: ffmpeg WASAPI → fallback sounddevice (PortAudio)
  └── macOS:   ffmpeg + AVFoundation
  │
  ▼
16 kHz mono f32le audio chunks
  │
  ▼
VAD Thread (silero-vad, 512-sample frames)
  │  detect speech onset/offset
  ▼
Worker Thread (faster-whisper)
  │  transcribe speech segments
  ▼
Main Thread (rich Live display + SRT append)
```

See [features/live-listen.md](features/live-listen.md) for details.

## Threading Model (Live Mode)

```
┌──────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Capture Thread  │────►│   VAD Thread     │────►│  Worker Thread     │────► display_queue
│  (platform dep)  │     │  (silero-vad)    │     │ (faster-whisper)   │
│                  │     │                  │     │                    │
│  ffmpeg stdout   │     │  512-sample      │     │  Transcribes       │
│  or sounddevice  │     │  frames, tracks  │     │  speech segment    │
│  callback        │     │  speech state    │     │  in bg thread      │
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

## Capture Engine Selection

### `src/audio/capture.py`

The `AudioCapture` class selects an engine based on platform:

```
_capture_config()
  │
  ├── Linux
  │     └── ffmpeg + PulseAudio monitor (auto-detected)
  │
  ├── Windows
  │     ├── ffmpeg + WASAPI loopback (primary)
  │     └── sounddevice PortAudio   (fallback)
  │
  ├── macOS
  │     └── ffmpeg + AVFoundation (BlackHole auto-detected)
  │
  └── Unsupported → RuntimeError
```

Each engine delivers 16 kHz mono float32 audio chunks to the VAD pipeline.

## Project Structure

```
nihonsub/
├── AGENTS.md                 # AI agent reference
├── opencode.json             # Opencode permissions config
├── pyproject.toml            # Python project & dependencies
├── .env.example              # Configuration template
├── docs/
│   ├── index.md              # Documentation hub
│   ├── architecture.md       # This file
│   ├── usage.md              # CLI quick-reference
│   ├── configuration.md      # .env config reference
│   ├── development.md        # Dev setup & conventions
│   ├── voicemeeter.md        # VoiceMeeter setup guide
│   ├── releases/             # Per-version changelogs
│   │   ├── v0.1.md
│   │   └── v0.2.md
│   └── features/             # Feature reference docs
│       ├── file-transcribe.md
│       ├── live-listen.md
│       └── windows-support.md
├── src/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry: transcribe + listen
│   ├── config.py             # pydantic-settings config
│   ├── audio/
│   │   ├── capture.py        # Live: multi-platform capture (ffmpeg / sounddevice)
│   │   ├── extractor.py      # File: ffmpeg audio extraction
│   │   └── processor.py      # File: VAD + resampling
│   ├── transcription/
│   │   ├── engine.py         # faster-whisper wrapper
│   │   ├── stream.py         # Live: streaming VAD + threaded pipeline
│   │   └── display.py        # Live: rich terminal + SRT output
│   ├── subtitle/
│   │   └── generator.py      # .srt / .vtt generation
│   └── models/
│       └── schemas.py        # Pydantic models
├── tests/
└── data/
    ├── input/
    └── output/
```

## Model Sizes

| Model | VRAM | Speed | Japanese Quality |
|-------|------|-------|-----------------|
| `tiny` | ~1 GB | Very fast | Poor |
| `base` | ~1 GB | Fast | OK |
| `small` | ~2 GB | Moderate | Good |
| `medium` | ~5 GB | Slow | Very good |
| `large-v3` | ~10 GB | Very slow | Best |

Default: `medium`. For live mode, `small` recommended for lower latency.

## Latency Budget (Live Mode)

| Step | Time |
|------|------|
| Audio buffer accumulation | ~0.5–1 s |
| VAD detection | ~0.2 s |
| Speech segment (natural pause) | ~0.5–2 s |
| faster-whisper transcribe (small) | ~1–3 s |
| **Total delay** | **~3–6 s** |
