import subprocess
from pathlib import Path


def extract_audio(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".wav")

    output_path = Path(output_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed: {result.stderr.strip()}"
        )

    return output_path


def get_audio_duration(audio_path: str | Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed: {result.stderr.strip()}"
        )

    return float(result.stdout.strip())
