import time
from pathlib import Path
from datetime import datetime

from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.layout import Layout
from rich.text import Text


class LiveDisplay:
    def __init__(self, srt_path: str | Path | None = None):
        self.console = Console()
        self.srt_path = Path(srt_path) if srt_path else None
        self.segments: list[dict] = []
        self.session_start = time.time()

        if self.srt_path:
            self.srt_path.parent.mkdir(parents=True, exist_ok=True)
            self.srt_path.write_text("", encoding="utf-8")

    def _format_srt_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _duration_since_start(self) -> float:
        return time.time() - self.session_start

    def add_segment(self, seg: dict):
        self.segments.append(seg)

        if self.srt_path:
            self._append_srt(seg)

    def _append_srt(self, seg: dict):
        idx = len(self.segments)
        start_ts = self._format_srt_timestamp(seg["start"] - self.session_start)
        end_ts = self._format_srt_timestamp(seg["end"] - self.session_start)
        text = seg.get("text", "").strip()
        if not text:
            return

        block = f"{idx}\n{start_ts} --> {end_ts}\n{text}\n\n"
        with open(self.srt_path, "a", encoding="utf-8") as f:
            f.write(block)

    def render(self) -> Layout:
        elapsed = self._duration_since_start()
        elapsed_str = self._format_srt_timestamp(elapsed)

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        header_text = Text(
            f"NihonSub — Listening  •  {elapsed_str}",
            style="bold cyan",
        )
        layout["header"].update(
            Panel(header_text, style="bold white on dark_blue")
        )

        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 2),
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Time", style="dim", width=28)
        table.add_column("Text", style="white")

        recent = self.segments[-20:] if self.segments else []
        for seg in recent:
            start = seg["start"] - self.session_start
            end = seg["end"] - self.session_start
            time_str = (
                f"{self._format_srt_timestamp(start)} → {self._format_srt_timestamp(end)}"
            )
            text = seg.get("text", "").strip()
            table.add_row(str(seg.get("id", "?")), time_str, text)

        layout["body"].update(table)

        if self.srt_path:
            footer_text = Text(
                f"Output: {self.srt_path.resolve()}  •  "
                f"{len(self.segments)} segments",
                style="dim",
            )
        else:
            footer_text = Text(
                f"{len(self.segments)} segments  •  Ctrl+C to stop",
                style="dim",
            )
        layout["footer"].update(
            Panel(footer_text, style="bold black on grey93")
        )

        return layout

    def final_summary(self):
        total_segments = len(self.segments)
        total_chars = sum(len(s.get("text", "")) for s in self.segments)
        elapsed = self._duration_since_start()

        self.console.print()
        self.console.print(Panel(
            "[bold]Session Summary[/bold]\n"
            f"  Duration: {self._format_srt_timestamp(elapsed)}\n"
            f"  Segments: {total_segments}\n"
            f"  Characters: {total_chars}\n"
            + (f"  SRT file: {self.srt_path.resolve()}" if self.srt_path else ""),
            style="bold green",
        ))
