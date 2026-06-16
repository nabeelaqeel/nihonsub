# NihonSub

Transcribe Japanese audio (anime episodes, class recordings) into Japanese text subtitles — fully local, no cloud APIs.

## Features

- **File transcribe** — Batch convert MP4/MKV/MP3/WAV → .srt or .vtt
- **Live listen** — Capture system audio in real-time and transcribe as it plays (YouTube, VLC, anime player, Zoom classes)

## Quick Start

```bash
# Prerequisites: Python 3.11+, ffmpeg
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# File mode
python -m src transcribe episode.mp4 -o subtitles.srt

# Live mode (captures audio playing on your laptop)
python -m src listen
```

## Project Status

**v0.1** — MVP. File transcription and live listening both functional. See [docs/usage.md](usage.md) for detailed usage.

## License

MIT
