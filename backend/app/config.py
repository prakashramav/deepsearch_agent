"""Application configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/deepresearch"
    sync_database_url: str = "postgresql://postgres:postgres@localhost:5432/deepresearch"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    cors_origins: str = "http://localhost:3000"
    environment: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
