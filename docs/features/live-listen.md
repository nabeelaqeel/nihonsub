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
2. **Segmenter Thread** — in VAD mode, runs silero-vad on 32ms frames to detect speech boundaries; in time mode, accumulates audio into fixed-interval chunks
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

## Segmentation Modes

### Time Mode (Default)

Audio is segmented into fixed-length chunks. No VAD model needed.

```bash
# Default: 15-second intervals
python -m src listen

# Custom interval for faster feedback
python -m src listen --interval 5
```

The `TimeSegmenter` accumulates audio until the interval elapses, then emits the segment. Simple and predictable — regardless of whether someone is speaking.

**Latency Budget (time mode, `--interval 5`)**

| Step | Time |
|------|------|
| Audio accumulation | ~5 s (configurable) |
| faster-whisper transcribe (small) | ~1–3 s |
| **Total delay** | **~6–8 s** |

### VAD Mode

Audio is segmented by speech activity using silero-vad. Better for dialog — captures natural utterance boundaries.

```bash
python -m src listen --mode vad

# Adjust silence threshold
python -m src listen --mode vad --silence_duration 1.0
```

The `VadSegmenter` runs silero-vad on each 32ms frame, tracks speech/silence state, and emits a segment when silence exceeds the threshold.

**Latency Budget (VAD mode)**

| Step | Time |
|------|------|
| Audio buffer accumulation | ~0.5–1 s |
| VAD detection | ~0.2 s |
| Speech segment (natural pause) | ~0.5–2 s |
| faster-whisper transcribe (small) | ~1–3 s |
| **Total delay** | **~3–6 s** |

## Usage

```bash
# Time mode (default, 15s intervals)
python -m src listen

# Custom interval
python -m src listen --interval 5

# VAD mode
python -m src listen --mode vad

# Custom silence threshold (VAD mode)
python -m src listen --mode vad --silence_duration 1.0

# Specify output file
python -m src listen -o live_subtitles.srt

# Faster model for lower latency
python -m src listen --model_size small

# GTK live captions window (Linux only, opens in background)
python -m src captions

# Custom interval for captions
python -m src captions --interval 5

# VAD mode for captions
python -m src captions --mode vad
```

### GTK Live Captions Window (Linux Only)

The `captions` command opens a transparent, always-on-top overlay window that displays live subtitles as they're transcribed. Perfect for watching anime or streams while seeing live Japanese transcription.

**Features:**
- Transparent overlay with semi-opaque background (doesn't block video)
- Auto-scroll to latest caption
- Always-on-top (stays above any window)
- Draggable and resizable from any edge
- Default size: 2/3 of screen width, 20% of screen height (wide subtitle band)
- Opens at the **bottom center of the screen** by default
- Transparent overlay with semi-opaque background (doesn't block video)
- Auto-scroll to latest caption
- Always-on-top (stays above any window)
- Draggable and resizable from any edge
- Invisible scrollbar (scrollbar hidden but still functional for manual scrolling)
- Undecorated window (no title bar)

**Default Size and Position:**
```python
# Dynamically calculated on launch
width = screen_width * 2 / 3        # 2/3 of screen width
height = 30                         # single thin line
x = (screen_width - width) / 2      # centered horizontally
y = screen_height - height          # flush with bottom (y = screen_height - 30)
```

For a typical 1920×1080 screen, this is approximately **1280×30** pixels, positioned at the bottom center (x=320, y=1080).

Note: The 30px height is very compact. For better readability, adjust font size and padding in the CSS at `src/ui/gtk_window.py`.

**Controls:**
- **Drag anywhere on the window** to move it
- **Click and drag from any edge** to resize:
  - Top/bottom edges: resize vertically
  - Left/right edges: resize horizontally
  - Corners: resize in both directions
- **Manual scroll** if content exceeds visible area (scrollbar hidden but functional)
- **Close**: Alt+F4 or click window close button (when decorated)

**Platform Support:**
- **Linux (GTK3)**: Fully supported
- **Windows/macOS**: Not yet implemented (use `listen` command instead for CLI output)

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--output, -o` | auto | Output SRT file path |
| `--model_size` | `small` | Whisper model (small recommended for live) |
| `--mode` | `time` | Segmentation mode: `time` (fixed-interval) or `vad` (speech-bounded) |
| `--interval` | `15.0` | Seconds per segment in time mode |
| `--silence_duration` | `0.64` | Seconds of silence to end a segment in VAD mode |

### VAD Parameters (VAD Mode Only)

| Parameter | Value | Description |
|-----------|-------|-------------|
| Frame size | 512 samples (32 ms at 16 kHz) | silero-vad v6 minimum |
| Threshold | 0.5 | Speech probability threshold |
| Min speech frames | 10 (320 ms) | Consecutive speech frames to trigger |
| Min silence frames | 20 (640 ms) | Consecutive silence to end segment |

The VAD accumulates audio during speech + a pre-buffer (17 frames, ~544 ms) to capture speech onset.

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
| v0.3 | GTK live captions window (Linux), time-based segmenter mode (default), `--interval`/`--mode`/`--silence_duration` flags, pluggable segmenter architecture |
