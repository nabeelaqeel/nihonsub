# File Transcribe

Batch transcribe a video or audio file into Japanese subtitles (.srt / .vtt).

## How It Works

```
Input File (mp4/mkv/mp3/wav/m4a)
  │
  ▼
ffmpeg ──► 16 kHz mono WAV (temporary)
  │
  ▼
silero-vad ──► speech segments with start/end timestamps
  │
  ▼
faster-whisper ──► transcribed text segments
  │
  ▼
Subtitle Generator ──► .srt or .vtt file
```

1. **Audio Extraction** — ffmpeg converts the input to a 16 kHz mono WAV file
2. **Voice Activity Detection** — silero-vad splits the audio into speech segments (pauses = segment boundaries)
3. **Transcription** — faster-whisper transcribes each segment (word-level timestamps)
4. **Subtitle Generation** — segments are written to .srt or .vtt format
5. **Cleanup** — temporary WAV file is deleted

## Usage

```bash
python -m src transcribe data/input/episode1.mp4 -o data/output/subtitles.srt
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `input_path` | (required) | Path to audio/video file |
| `--output, -o` | auto | Output subtitle path |
| `--model_size` | `medium` | See model table below |
| `--subtitle_format` | `srt` | `srt` or `vtt` |

### Model Selection

| Model | VRAM | Speed | Japanese Quality |
|-------|------|-------|-----------------|
| `tiny` | ~1 GB | Very fast | Poor |
| `base` | ~1 GB | Fast | OK |
| `small` | ~2 GB | Moderate | Good |
| `medium` | ~5 GB | Slow | Very good |
| `large-v3` | ~10 GB | Very slow | Best |

`medium` is the default — good balance of quality and speed for file mode.

### VAD Configuration (via `.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VAD_THRESHOLD` | `0.5` | Speech probability threshold (0-1) |
| `VAD_MIN_SPEECH_DURATION_MS` | `250` | Minimum speech segment (ms) |
| `VAD_MIN_SILENCE_DURATION_MS` | `500` | Silence to end segment (ms) |

## Key Files

- `src/audio/extractor.py` — ffmpeg audio extraction
- `src/audio/processor.py` — VAD + resampling
- `src/transcription/engine.py` — faster-whisper wrapper
- `src/subtitle/generator.py` — .srt / .vtt generation

## Version History

| Version | Changes |
|---------|---------|
| v0.1 | Initial implementation |
