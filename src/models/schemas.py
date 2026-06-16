from pydantic import BaseModel, Field
from enum import Enum


class SubtitleFormat(str, Enum):
    srt = "srt"
    vtt = "vtt"


class TranscriptionSegment(BaseModel):
    start: float = Field(description="Start time in seconds")
    end: float = Field(description="End time in seconds")
    text: str = Field(description="Transcribed text")


class TranscriptionResult(BaseModel):
    segments: list[TranscriptionSegment]
    language: str
    duration_seconds: float


class TranscribeRequest(BaseModel):
    file_path: str
    model_size: str = "medium"
    subtitle_format: SubtitleFormat = SubtitleFormat.srt


class TranscribeResponse(BaseModel):
    status: str
    subtitle_path: str | None = None
    segments: list[TranscriptionSegment] | None = None
    error: str | None = None
