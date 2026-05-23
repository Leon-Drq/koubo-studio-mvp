from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Koubo Studio"
    data_dir: Path = Path("data")
    default_asr_provider: str = "auto"
    default_llm_provider: str = "auto"
    default_tts_provider: str = "auto"
    default_lipsync_provider: str = "auto"
    default_tts_model: str = "f5"
    asr_command: str = ""
    llm_command: str = ""
    tts_command: str = ""
    f5_tts_command: str = ""
    indextts_command: str = ""
    lipsync_command: str = ""
    latentsync_command: str = ""
    musetalk_batch_size: int = 8
    musetalk_bbox_shift: int = 0
    auto_unload_ollama_before_media: bool = True
    ollama_bin: str = ""
    ollama_model: str = "qwen2.5:7b"
    asr_api_url: str = ""
    asr_api_key: str = ""
    asr_api_model: str = "whisper-1"
    asr_api_file_field: str = "file"
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_api_model: str = "gpt-4o-mini"
    llm_api_temperature: float = 0.7
    tts_api_url: str = ""
    tts_api_key: str = ""
    tts_api_model: str = "tts-1"
    tts_api_voice: str = "alloy"
    tts_api_mode: str = "json"
    tts_api_text_field: str = "input"
    tts_api_voice_field: str = "voice"
    tts_api_file_field: str = "voice_sample"
    lipsync_api_url: str = ""
    lipsync_api_key: str = ""
    lipsync_api_video_field: str = "video"
    lipsync_api_audio_field: str = "audio"
    burn_subtitles: bool = False
    enable_browser_publish: bool = False
    ytdlp_cookies_file: str = ""
    ytdlp_cookies_from_browser: str = ""
    ytdlp_proxy: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    return settings
