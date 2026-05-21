from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Koubo Studio"
    data_dir: Path = Path("data")
    asr_command: str = ""
    llm_command: str = ""
    tts_command: str = ""
    lipsync_command: str = ""
    ollama_model: str = "qwen2.5:7b"
    burn_subtitles: bool = False
    enable_browser_publish: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    return settings
