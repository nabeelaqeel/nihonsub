# Architecture

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| ASR Engine | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (local, CTranslate2) |
| Voice Activity Detection | [`silero-vad`](https://github.com/snakers4/silero-vad) v6 |
| Audio Extraction (file mode) | `ffmpeg` via subprocess |
| Live Capture (live mode) | `ffmpeg` subprocess (PulseAudio monitor source) |
| CLI Framework | [`fire`](https://github.com/google/python-fire) |
| Terminal UI | [`rich`](https://github.com/Textualize/rich) |
| Config | `pydantic-settings` + `.env` |

## Data Flows

### File Transcribe

```
Input File (mp4/mkv/mp3/wav/m4a)
  │
  ▼
ffmpeg ──► 16kHz mono WAV
  │
  ▼
silero-vad ──► speech segments with timestamps
  │
  ▼
faster-whisper ──► transcribed text (word-level timestamps)
  │
  ▼
Subtitle Generator ──► .srt / .vtt
```

### Live Listen

```
System Audio (any app playing sound)
  │
  ▼
PipeWire PulseAudio monitor source
  │
  ▼
ffmpeg subprocess (pulse input → f32le stdout)
  │
  ▼
VAD Thread (silero-vad, 32ms frames)
  │  detect speech onset/offset
  ▼
Worker Thread (faster-whisper)
  │  transcribe speech segments
  ▼
Main Thread (rich Live display + SRT append)
```

## Threading Model (Live Mode)

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Capture Thread │────►│   VAD Thread    │────►│  Worker Thread   │────► display_queue
│  (ffmpeg read)  │     │  (silero-vad)   │     │ (faster-whisper) │
│                 │     │                 │     │                  │
│  Reads f32le    │     │  512-sample     │     │  Transcribes     │
│  chunks from    │     │  frames, tracks │     │  speech segment  │
│  ffmpeg stdout  │     │  speech state   │     │  in bg thread    │
└─────────────────┘     └─────────────────┘     └──────────────────┘
                               │                        │
                               ▼                        ▼
                         transcribe_queue         display_queue
                                                      │
                                                      ▼
                                              ┌─────────────────┐
                                              │  Main Thread    │
                                              │  (rich + SRT)   │
                                              │                 │
                                              │  Live terminal  │
                                              │  + SRT append   │
                                              └─────────────────┘
```

## Project Structure

```
nihonsub/
├── AGENTS.md                 # AI agent reference (architecture, conventions, lessons)
├── opencode.json             # Opencode permissions config
├── pyproject.toml            # Python project & dependencies
├── .env.example              # Configuration template
├── .gitignore
├── docs/                     # User-facing documentation
│   ├── index.md
│   ├── architecture.md
│   ├── usage.md
│   ├── configuration.md
│   ├── development.md
│   └── lessons-learned.md
├── src/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry: transcribe + listen
│   ├── config.py             # pydantic-settings config
│   ├── audio/
│   │   ├── capture.py        # Live: ffmpeg PulseAudio monitor capture
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
|---|---|---|---|
| `tiny` | ~1GB | Very fast | Poor |
| `base` | ~1GB | Fast | OK |
| `small` | ~2GB | Moderate | Good |
| `medium` | ~5GB | Slow | Very good |
| `large-v3` | ~10GB | Very slow | Best |

Default: `medium`. For live mode, `small` or `base` recommended for lower latency.

## Latency Budget (Live Mode)

| Step | Time |
|---|---|
| Audio buffer accumulation | ~0.5–1s |
| VAD detection | ~0.2s |
| Speech segment (natural pause) | ~0.5–2s |
| faster-whisper transcribe | ~1–3s (small model) |
| **Total delay** | **~3–6s** |
