from functools import lru_cache
from typing import Literal

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
    api_version: str = "0.6.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://veriflow:veriflow_dev_password@localhost:55432/veriflow"
    )
    redis_url: str = "redis://localhost:6379/0"
    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    session_cookie_name: str = "veriflow_session"
    csrf_cookie_name: str = "veriflow_csrf"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_domain: str | None = None

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "veriflow_minio"
    minio_secret_key: str = "veriflow_minio_password"
    minio_secure: bool = False
    minio_bucket: str = "veriflow-documents"
    max_upload_size_bytes: int = 25 * 1024 * 1024

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_queue_name: str = "document-processing"
    processing_max_retries: int = 3
    processing_retry_base_seconds: int = 5
    worker_heartbeat_key: str = "veriflow:workers:document-processing"
    worker_heartbeat_ttl_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
