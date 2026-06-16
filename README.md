# NihonSub 🇯🇵

Transcribe Japanese audio (anime, class recordings, YouTube) into Japanese text subtitles — **fully local, no cloud APIs**.

## Features

- **File transcribe** — batch audio/video → `.srt` / `.vtt` subtitles
- **Live listen** — capture system audio in real-time, transcribe as it plays
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
python -m src listen
```

Press **Ctrl+C** to stop. Output saves automatically to `data/output/`.

## Platform Support

| Feature | Linux | macOS | Windows |
|---|---|---|---|
| File transcribe | ✅ | ✅ | ✅ |
| Live listen | ✅ | ✅* | ✅* |

*\* Requires a virtual audio cable: [VB-Cable](https://vb-audio.com/Cable/) on Windows, [BlackHole](https://github.com/ExistentialAudio/BlackHole) on macOS. See [docs/usage.md](docs/usage.md).*

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
