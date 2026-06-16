from pathlib import Path


def format_timestamp(seconds: float, fmt: str = "srt") -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    if fmt == "srt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    elif fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def generate_srt(segments: list[dict]) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg["start"], "srt")
        end = format_timestamp(seg["end"], "srt")
        text = seg.get("text", "").strip()

        if not text:
            continue

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def generate_vtt(segments: list[dict]) -> str:
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg["start"], "vtt")
        end = format_timestamp(seg["end"], "vtt")
        text = seg.get("text", "").strip()

        if not text:
            continue

        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def write_subtitles(
    segments: list[dict],
    output_path: str | Path,
    fmt: str = "srt",
) -> Path:
    output_path = Path(output_path)

    if fmt == "srt":
        content = generate_srt(segments)
    elif fmt == "vtt":
        content = generate_vtt(segments)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    if output_path.suffix.lstrip(".") != fmt:
        output_path = output_path.with_suffix(f".{fmt}")

    output_path.write_text(content, encoding="utf-8")
    return output_path
