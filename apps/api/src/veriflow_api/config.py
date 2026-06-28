from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "VeriFlow AI API"
    app_env: str = "development"
    debug: bool = True
    api_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://veriflow:veriflow_dev_password@localhost:5432/veriflow"
    )
    redis_url: str = "redis://localhost:6379/0"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
