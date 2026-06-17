# NihonSub 🇯🇵

Transcribe Japanese audio (anime, class recordings, YouTube) into Japanese text subtitles — **fully local, no cloud APIs**.

## Features

- **File transcribe** — batch audio/video → `.srt` / `.vtt` subtitles
- **Live listen** — capture system audio in real-time, transcribe as it plays
- **Live captions** — always-on-top GTK3 captions window (Linux)
- **Fully offline** — faster-whisper runs locally, no internet needed
- **Japanese-optimized** — default model tuned for Japanese speech
- **CLI-first** — simple commands, composable with other tools

## Prerequisites

- **Python 3.11+**
- **ffmpeg** — [install guide](https://ffmpeg.org/download.html)

## Installation

```bash
git clone https://github.com/nabeelaqeel/nihonsub.git
cd nihonsub
python3 -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -e .
```

## Quick Start

### Transcribe a file

```bash
python -m src transcribe episode.mp4 -o subtitles.srt
```

### Live listen (capture system audio)

```bash
# Default: 15-second intervals
python -m src listen

# Faster feedback: 5-second intervals
python -m src listen --interval 5

# Speech-bounded mode (VAD)
python -m src listen --mode vad
```

Press **Ctrl+C** to stop. Output saves automatically to `data/output/`.

### Live captions (Linux only)

```bash
# Always-on-top GTK captions window
python -m src captions

# Custom interval
python -m src captions --interval 5
```

## Platform Support

| Feature | Linux | macOS | Windows |
|---|---|---|---|---|
| File transcribe | ✅ | ✅ | ✅ |
| Live listen | ✅ | ✅* | ✅* |
| Live captions (GTK) | ✅ | ❌ | ❌ |

*\* macOS requires [BlackHole](https://github.com/ExistentialAudio/BlackHole). Windows and Linux work out of the box. See [docs/usage.md](docs/usage.md).*

## Documentation

| Doc | Contents |
|---|---|
| [docs/index.md](docs/index.md) | Project overview |
| [docs/architecture.md](docs/architecture.md) | System design, data flows, threading |
| [docs/usage.md](docs/usage.md) | CLI reference, examples |
| [docs/configuration.md](docs/configuration.md) | Model sizes, VAD settings |
| [docs/development.md](docs/development.md) | Setup, conventions, contributing |
| [docs/lessons-learned.md](docs/lessons-learned.md) | Bugs encountered & fixes |

## License

MIT
