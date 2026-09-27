"""Application configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/deepresearch"
    sync_database_url: str = "postgresql://postgres:postgres@localhost:5432/deepresearch"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    tavily_api_key: str = ""
    cors_origins: str = "*"
    environment: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def resolved_gemini_api_key(self) -> str:
        return self.gemini_api_key or self.google_api_key

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins or self.cors_origins.strip() == "*":
            return ["*"]
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins if origins else ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
