# NihonSub

Transcribe Japanese audio (anime episodes, class recordings) into Japanese text subtitles — fully local, no cloud APIs.

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# File mode
python -m src transcribe episode.mp4 -o subtitles.srt

# Live mode (captures audio playing on your laptop)
python -m src listen

# Live captions window (Linux only)
python -m src captions
```

Requires: Python 3.11+, ffmpeg on PATH.

## Features

| Feature | Description | Docs |
|---------|-------------|------|
| **File Transcribe** | Batch convert video/audio → .srt / .vtt | [docs](features/file-transcribe.md) |
| **Live Listen** | Real-time system audio capture + transcription | [docs](features/live-listen.md) |
| **Live Captions** | Always-on-top GTK3 captions window (Linux) | [docs](features/live-listen.md) |
| **Windows Support** | WASAPI + sounddevice, VoiceMeeter | [docs](features/windows-support.md) |

## Platform Support

| Platform | Live Capture | Live Captions (GTK) | Notes |
|----------|-------------|---------------------|-------|
| Linux | ✅ PulseAudio monitor | ✅ | Auto-detected |
| Windows | ✅ WASAPI / sounddevice | ❌ | VoiceMeeter for Bluetooth speakers |
| macOS | ✅ AVFoundation | ❌ | Requires BlackHole |

## Releases

| Version | Branch | Highlights |
|---------|--------|------------|
| [v0.1](releases/v0.1.md) | `main` | File transcribe + Linux live listen (MVP) |
| [v0.2](releases/v0.2.md) | `feat/windows-support` | Windows/macOS support, VoiceMeeter, audio meter |
| [v0.3](releases/v0.3.md) | `feat/live-captions-ui` | GTK live captions, time-based segmentation, `--interval`/`--mode` flags |

## Documentation

- [Usage](usage.md) — CLI commands and arguments
- [Architecture](architecture.md) — system design and data flows
- [Configuration](configuration.md) — `.env` reference
- [VoiceMeeter Guide](voicemeeter.md) — Windows Bluetooth speaker setup
- [Development](development.md) — contributing and conventions
- [Lessons Learned](lessons-learned.md) — engineering notes

## License

MIT
