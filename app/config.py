from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, PositiveInt, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


Visibility = Literal["public", "unlisted", "private"]


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    youtube_channel_id: str = Field(..., alias="YOUTUBE_CHANNEL_ID")
    web_sub_callback_base: HttpUrl = Field(..., alias="WEB_SUB_CALLBACK_BASE")
    web_sub_secret: str = Field(..., alias="WEB_SUB_SECRET")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    work_dir: Path = Field(Path("./data"), alias="WORK_DIR")
    database_path: Path = Field(Path("./data/app.db"), alias="DATABASE_PATH")
    enable_transcode: bool = Field(False, alias="ENABLE_TRANSCODE")
    rutube_visibility: Visibility = Field("public", alias="RUTUBE_VISIBILITY")
    tags_from_yt: bool = Field(True, alias="TAGS_FROM_YT")
    title_prefix: str = Field("", alias="TITLE_PREFIX")
    title_suffix: str = Field("", alias="TITLE_SUFFIX")
    max_title_len: PositiveInt = Field(100, alias="MAX_TITLE_LEN")
    max_desc_len: PositiveInt = Field(5000, alias="MAX_DESC_LEN")
    poll_interval_seconds: PositiveInt = Field(300, alias="POLL_INTERVAL_SECONDS")
    max_concurrency: PositiveInt = Field(1, alias="MAX_CONCURRENCY")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    application_version: str = Field("0.1.0", alias="APPLICATION_VERSION")
    cookies_path: Path = Field(Path("auth/rutube_cookies.json"), alias="COOKIES_PATH")

    @validator("work_dir", "cookies_path", "database_path", pre=True)
    def _expand_path(cls, value: str | Path) -> Path:
        path = Path(value).expanduser().resolve()
        return path

    @property
    def database_url(self) -> str:
        if self.database_path.suffix != ".db":
            return f"sqlite:///{self.database_path.as_posix()}"
        return f"sqlite:///{self.database_path}"


class RetryPolicy(BaseModel):
    max_attempts: PositiveInt = 5
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 300.0
    jitter_factor: float = 0.3


@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    cfg = AppConfig()
    cfg.work_dir.mkdir(parents=True, exist_ok=True)
    cfg.cookies_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.database_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg


@lru_cache(maxsize=1)
def get_retry_policy() -> RetryPolicy:
    return RetryPolicy()
