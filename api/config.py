"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API configuration settings."""

    mongodb_uri: str = "mongodb://localhost:27017"
    db_name_dox: str = "ortho_dox"
    db_name_raw: str = "ortho_raw"

    # API settings
    api_title: str = "Orthodox Study Bible API"
    api_version: str = "0.1.0"

    # CORS settings (comma-separated origins, or "*" for all)
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_prefix="OSB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
