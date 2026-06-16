# Usage

## Prerequisites

- Python 3.11+
- `ffmpeg` installed and on PATH

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## File Transcribe

Convert a video or audio file to Japanese subtitles.

```bash
# Basic usage
python -m src transcribe data/input/episode1.mp4 -o data/output/episode1.srt

# Specify a different model
python -m src transcribe episode.mp4 --model_size small

# Specify subtitle format
python -m src transcribe episode.mp4 --subtitle_format vtt

# All options
python -m src transcribe --help
```

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `input_path` | str | (required) | Path to audio/video file |
| `--output` / `-o` | str | auto | Output subtitle path (.srt/.vtt) |
| `--model_size` | str | `medium` | Whisper model: tiny/base/small/medium/large-v3 |
| `--subtitle_format` | str | `srt` | Output format: `srt` or `vtt` |

## Live Listen

Capture system audio in real-time and transcribe as it plays.

```bash
# Start listening (auto-named SRT file in data/output/)
python -m src listen

# Specify output SRT path
python -m src listen -o live_subtitles.srt

# Use a faster model for lower latency
python -m src listen --model_size small

# All options
python -m src listen --help
```

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--output` / `-o` | str | auto | Output SRT file path |
| `--model_size` | str | `small` | Whisper model for live mode |

### How it works

1. **Detects** your system's audio loopback device (platform-specific)
2. **Captures** 16kHz mono f32le audio (ffmpeg or sounddevice depending on platform)
3. **Runs** `silero-vad` on the stream to detect speech segments
4. **Transcribes** each segment with `faster-whisper` in a background thread
5. **Displays** results in a live rich terminal window with audio level meter
6. **Appends** completed segments to the `.srt` file in real-time

Press **Ctrl+C** to stop. A session summary is printed on exit.

See [features/live-listen.md](features/live-listen.md) for detailed architecture and platform notes.

### Platform Setup

#### Linux
No setup needed. Uses PulseAudio monitor source, auto-detected.

#### Windows
Auto-detects your capture device. First tries ffmpeg WASAPI loopback, then falls back to sounddevice (PortAudio). Works out of the box with most setups.

If you use **Bluetooth speakers** or other hardware without loopback support, use **VoiceMeeter** (virtual audio mixer) to route audio to both your speakers and a virtual capture device. See the [VoiceMeeter guide](voicemeeter.md) for detailed setup.

**Troubleshooting**: If `ffmpeg -f wasapi` fails with `Unknown input format: 'wasapi'`, your ffmpeg binary was compiled without WASAPI input support. The tool automatically falls back to sounddevice. To check available input devices:
```bash
python -c "import sounddevice as sd; [print(f'{i}: {d[\"name\"]}') for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]"
```
Loopback-capable devices (like CABLE Output, VoiceMeeter Output, Stereo Mix) should appear. If none show up, install [VB-Cable](https://vb-audio.com/Cable/) or [VoiceMeeter](https://vb-audio.com/Voicemeeter/) to create a virtual loopback.

#### macOS
Requires [BlackHole](https://github.com/ExistentialAudio/BlackHole) (free virtual audio driver):
1. Download and install BlackHole (e.g. `brew install blackhole-2ch`)
2. Open **Audio MIDI Setup** → create a Multi-Output Device
3. Add both your speakers and BlackHole to the Multi-Output Device
4. Set the Multi-Output Device as your system output
5. Run nihonsub — it will auto-detect BlackHole as the capture source

## .env Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

See [configuration.md](configuration.md) for all options.
