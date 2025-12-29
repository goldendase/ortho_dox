"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API configuration settings."""

    mongo_uri: str = "mongodb://localhost:27017"
    db_name_dox: str = "ortho_dox"
    db_name_raw: str = "ortho_raw"

    # API settings
    api_title: str = "Orthodox Study Bible API"
    api_version: str = "0.1.0"

    # CORS settings (comma-separated origins, or "*" for all)
    cors_origins: str = "*"

    # LLM settings
    openrouter_api_key: str = ""

    # Auth settings
    hmog_secret: str = ""

    # Vector search settings (Pinecone + Voyage AI)
    pinecone_api_key: str = ""
    pinecone_index_name: str = "ortho-docs"
    voyage_api_key: str = ""
    embedding_model_name: str = "voyage-3-large"
    vector_search_min_score: float = 0.35  # Minimum similarity score (dotproduct, 0-1 range)
    vector_search_judge_enabled: bool = False  # Enable Gemini Flash relevance judge for search results

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
