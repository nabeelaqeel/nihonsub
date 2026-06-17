from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    whisper_model_size: str = "medium"
    whisper_device: str = "auto"
    subtitle_format: str = "srt"
    vad_threshold: float = 0.5
    vad_min_speech_duration_ms: int = 250
    vad_min_silence_duration_ms: int = 500
    mode: str = "time"
    interval_sec: float = 15.0
    silence_duration_sec: float = 0.64

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
