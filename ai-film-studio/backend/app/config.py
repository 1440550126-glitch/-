from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./ai_film_studio.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./storage"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    runway_api_key: str = ""
    kling_api_key: str = ""
    veo_api_key: str = ""
    luma_api_key: str = ""
    pika_api_key: str = ""
    elevenlabs_api_key: str = ""
    default_llm_provider: str = "mock"
    default_image_provider: str = "mock"
    default_video_provider: str = "mock"
    default_vision_provider: str = "mock"
    default_embedding_provider: str = "mock"
    max_shot_retry: int = 3
    continuity_pass_score: int = 85
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_root).resolve()

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for folder in ["projects","characters","locations","props","shots","videos","frames","exports","mock"]:
        (settings.storage_path / folder).mkdir(parents=True, exist_ok=True)
    return settings
