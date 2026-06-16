import queue
import time
import signal
from pathlib import Path
from datetime import datetime

import fire
from rich.live import Live

from src.config import settings
from src.audio.extractor import extract_audio, get_audio_duration
from src.audio.processor import load_vad_model, get_speech_timestamps
from src.audio.capture import AudioCapture
from src.transcription.engine import load_model, transcribe
from src.transcription.stream import LiveStream
from src.transcription.display import LiveDisplay
from src.subtitle.generator import write_subtitles


def transcribe_command(
    input_path: str,
    output: str | None = None,
    model_size: str | None = None,
    subtitle_format: str | None = None,
):
    model_size = model_size or settings.whisper_model_size
    subtitle_format = subtitle_format or settings.subtitle_format

    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: {input_path} not found")
        return

    if output:
        output_path = Path(output)
    else:
        output_path = input_file.with_suffix(f".{subtitle_format}")

    temp_wav = input_file.with_suffix(".temp.wav")

    try:
        print(f"Extracting audio from {input_path}...")
        audio_path = extract_audio(input_file, temp_wav)

        duration = get_audio_duration(audio_path)
        print(f"Audio duration: {duration:.1f}s")

        print(f"Loading VAD model...")
        vad_model = load_vad_model()

        print(f"Detecting speech segments...")
        speech_segments = get_speech_timestamps(
            audio_path, vad_model,
            threshold=settings.vad_threshold,
            min_speech_duration_ms=settings.vad_min_speech_duration_ms,
            min_silence_duration_ms=settings.vad_min_silence_duration_ms,
        )
        print(f"Found {len(speech_segments)} speech segments")

        print(f"Loading faster-whisper model ({model_size})...")
        model = load_model(model_size, settings.whisper_device)

        print(f"Transcribing...")
        segments, detected_lang = transcribe(model, audio_path)
        print(f"Detected language: {detected_lang}")
        print(f"Transcribed {len(segments)} segments")

        print(f"Writing {subtitle_format.upper()} file...")
        result_path = write_subtitles(segments, output_path, subtitle_format)
        print(f"Done! Subtitles saved to: {result_path}")

    finally:
        if temp_wav.exists():
            temp_wav.unlink()


def listen_command(
    output: str | None = None,
    model_size: str = "small",
):
    if output:
        srt_path = Path(output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        srt_path = Path(f"data/output/live_{timestamp}.srt")

    print(f"Initializing live listening (model: {model_size})...")
    print(f"Output SRT: {srt_path.resolve()}")

    stream = LiveStream(model_size=model_size)
    stream.start()

    display = LiveDisplay(srt_path)

    capture = AudioCapture()
    capture.start(callback=lambda chunk: stream.push_audio(chunk))

    print(f"Listening... (Ctrl+C to stop)")

    try:
        with Live(
            display.render(),
            refresh_per_second=4,
            screen=True,
        ) as live:
            while True:
                while True:
                    try:
                        seg = stream.display_queue.get_nowait()
                        display.add_segment(seg)
                    except queue.Empty:
                        break
                live.update(display.render())
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()
        stream.stop()
        display.final_summary()
        print(f"Session ended. SRT saved to: {srt_path.resolve()}")


def main():
    fire.Fire({
        "transcribe": transcribe_command,
        "listen": listen_command,
    })


if __name__ == "__main__":
    main()
