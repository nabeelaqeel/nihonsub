# NihonSub — Japanese Audio Transcription Project

## Goal
Transcribe Japanese audio (anime episodes, class recordings) into Japanese text subtitles (.srt/.vtt).

## Modes
1. **File transcribe** — Batch transcribe a video/audio file → subtitle file
2. **Live listen** — Capture system audio in real-time, transcribe continuously

## Architecture

### Tech Stack
- **Language**: Python 3.11+
- **ASR Engine**: `faster-whisper` (local, no cloud APIs)
- **Audio Processing**: `ffmpeg` + `silero-vad`
- **Live Capture**: `ffmpeg` subprocess (PipeWire monitor source via PulseAudio)
- **API Layer**: FastAPI + uvicorn (Phase 2)
- **Subtitle Output**: SRT, VTT

### Data Flows

#### File Transcribe
```
Input Video/Audio (mp4, mkv, mp3, wav, m4a)
  → ffmpeg → 16kHz mono WAV
  → silero-vad → speech segments with timestamps
  → faster-whisper → transcribed text with word-level timestamps
  → subtitle generator → .srt / .vtt
```

#### Live Listen
```
System Audio (YouTube, VLC, anime player, Zoom class)
  → PipeWire monitor source (loopback)
  → ffmpeg subprocess (pulse input → f32le stdout pipe)
  → silero-vad (speech onset/offset detection on streaming buffer)
  → speech segment buffer
  → faster-whisper (transcribe segment in worker thread)
  → rich terminal output + append to .srt file
```

### Threading Model (Live Listen)
```
[Capture Thread]  ffmpeg stdout read → audio chunks → VAD queue
[VAD Thread]      consume chunks → detect speech start/end → push segments to transcribe queue
[Worker Thread]   faster-whisper transcription → push results to display queue
[Main Thread]     consume results → print (rich) + write .srt
```

### Project Structure
```
nihonsub/
├── opencode.json
├── AGENTS.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── __main__.py             # CLI entry point (transcribe + listen)
│   ├── config.py               # Configuration
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── extractor.py        # ffmpeg audio extraction (file mode)
│   │   ├── processor.py        # VAD, resampling (file mode)
│   │   └── capture.py          # System audio loopback capture (live mode)
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── engine.py           # faster-whisper wrapper
│   │   ├── stream.py           # Live VAD + streaming pipeline
│   │   └── display.py          # Terminal + SRT output
│   └── subtitle/
│       ├── __init__.py
│       └── generator.py        # SRT/VTT generation
├── tests/
│   └── ...
└── data/
    ├── input/
    └── output/
```

### Key Design Decisions
- **faster-whisper** over OpenAI Whisper: 4x faster, lower memory, same accuracy
- **No diarization**: Speaker identification not needed for initial version
- **silero-vad**: Best-in-class voice activity detection, lightweight
- **CLI-first**: Develop and test via CLI before adding REST API
- **ffmpeg subprocess for live capture**: more reliable on PipeWire than `sounddevice` + PULSE_SOURCE (see Lessons Learned)
- **Threaded pipeline**: Separate threads for capture, VAD, transcription, display to avoid blocking
- **SRT append mode**: Write segments as they complete so media players can load live-updating files

### Models (faster-whisper)
| Model | VRAM | Speed | Quality |
|---|---|---|---|
| tiny | ~1GB | Very fast | Poor |
| base | ~1GB | Fast | OK |
| small | ~2GB | Moderate | Good |
| medium | ~5GB | Slow | Very Good |
| large-v3 | ~10GB | Very slow | Best |

Default: `medium` — good balance for Japanese.
For live mode, `small` or `base` recommended for lower latency.

### Live Listen Latency Budget
| Step | Time |
|---|---|
| Audio buffer accumulation | ~0.5-1s |
| VAD detection | ~0.2s |
| Speech segment (natural pause) | ~0.5-2s |
| faster-whisper transcribe | ~1-3s (small model) |
| **Total delay** | **~3-6s** |

### CLI Usage
```bash
# File mode
python -m src transcribe data/input/episode1.mp4 -o data/output/episode1.srt

# Live mode
python -m src listen                              # terminal + auto-named SRT
python -m src listen --output live_subtitles.srt  # specify SRT path
python -m src listen --model_size small            # faster model for lower latency
```

### Python Dependencies
- `faster-whisper` — ASR engine
- `silero-vad` — Voice activity detection
- `ffmpeg-python` — Audio extraction wrapper
- `soundfile` — Audio file I/O
- `torch` — ML backend
- `pydantic` — Data validation
- `pydantic-settings` — Config management
- `fire` — CLI framework (lightweight, no boilerplate)
- `rich` — Terminal formatting (live display)

### Conventions
- Type hints everywhere
- Threading for live pipeline (capture/VAD/transcribe/display)
- Pydantic models for data schemas
- Absolute imports within package
- Tests in `tests/` mirroring `src/` structure

### Git Workflow
- **Branching**: GitHub Flow — `main` is stable, feature branches (`feat/*`, `fix/*`) PR into `main`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **Releases**: Tagged versions (`v0.1`, `v0.2`, etc.)
- User-facing documentation lives in `docs/` — update whenever behavior changes

---

## Lessons Learned

### 1. `PULSE_SOURCE` env var is ignored by `sounddevice` on PipeWire

**Symptom**: Live capture produced all-zero audio chunks.
**Root cause**: Setting `os.environ["PULSE_SOURCE"]` before creating a `sounddevice.InputStream(device="pulse")` does NOT route audio through the monitor source. The PulseAudio backend in PortAudio/sounddevice uses PulseAudio's internal default source override mechanism, which doesn't work reliably with PipeWire's PulseAudio compatibility layer.

**Fix**: Spawn an `ffmpeg` subprocess that captures directly from the monitor source:
```python
subprocess.Popen([
    "ffmpeg",
    "-f", "pulse",
    "-i", monitor_name,       # e.g. alsa_output...sink.monitor
    "-ac", "1",               # mono
    "-ar", "16000",           # 16kHz
    "-f", "f32le",
    "pipe:1",                 # stdout
])
```
This is more reliable because ffmpeg handles PulseAudio directly, and we just read the raw float32 samples from its stdout.

Note: `-sample_fmt f32le` is NOT a valid ffmpeg option — use `-f f32le` instead.

### 2. silero-vad v6 rejects 480-sample chunks

**Symptom**: VAD thread crashed silently with `ValueError: Input audio chunk is too short`. No transcription appeared.
**Root cause**: silero-vad v6 requires `sample_rate / chunk_length > 31.25`. At 16kHz:
- 480 samples → 16000/480 = 33.33 > 31.25 → too short → **crash**
- 512 samples → 16000/512 = 31.25 == 31.25 → **OK**

**Fix**: Changed `FRAME_SIZE` from 480 (30ms) to 512 (32ms).

### 3. silero-vad v6 has no `process_chunk()` method

**Symptom**: `AttributeError: 'RecursiveScriptModule' object has no attribute 'process_chunk'` — but only in the daemon thread, so it silently killed the VAD pipeline.
**Root cause**: silero-vad v6 returns a TorchScript `RecursiveScriptModule`. The correct API is to call it directly:
- Wrong: `vad.process_chunk(tensor, sr)` → AttributeError
- Correct: `vad(tensor, sr).item()` → returns float probability

**Fix**: Replaced `vad.process_chunk(tensor, 16000)` with `vad(tensor, 16000).item()`.

### 4. Daemon threads swallow exceptions silently

**Symptom**: No error output when VAD or worker threads crash.
**Root cause**: Python daemon threads (`threading.Thread(daemon=True)`) exit silently on unhandled exceptions. The main thread never sees the error.
**Fix**: Added `try/except` around the worker loop. The VAD loop should also have error handling in future iterations.

### 5. ffmpeg `-sample_fmt` doesn't exist

**Symptom**: ffmpeg exits with code 234, `Invalid sample format 'f32le'`.
**Root cause**: `-sample_fmt` is not a valid ffmpeg option. Use `-f f32le` which sets both container and sample format.
**Fix**: Remove `-sample_fmt f32le` — only use `-f f32le`.

### 6. torch.Tensor dtype mismatch with silero-vad

**Symptom**: `RuntimeError: expected scalar type Double but found Float` on VAD forward call.
**Root cause**: silero-vad v6 weights are float32. If input tensor is float64 (e.g. from numpy float64), the internal conv1d fails.
**Fix**: Always convert: `torch.from_numpy(chunk).unsqueeze(0).float()` before calling the VAD model.
