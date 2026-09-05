"""
Lenny Growth Assistant — Core Configuration Module

Uses Pydantic Settings to load and validate environment variables with safe defaults.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application Metadata ---
    PROJECT_NAME: str = "Lenny Growth Assistant"
    APP_ENV: str = Field(default="development", description="Runtime environment (development, staging, production)")
    DEBUG: bool = Field(default=True, description="Enable debug logging and SQL echo")
    API_PORT: int = Field(default=8000, description="FastAPI server port")

    # --- Database Configuration ---
    # Default to localhost for host development; docker-compose overrides to db:5432
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_growth_db",
        description="Async PostgreSQL connection string using asyncpg driver",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/lenny_growth_db",
        description="Sync PostgreSQL connection string for Alembic migrations",
    )
    DB_POOL_SIZE: int = Field(default=10, description="Maximum persistent connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=5, description="Maximum temporary connections above pool size")
    DB_POOL_TIMEOUT: float = Field(default=30.0, description="Connection acquisition timeout in seconds")

    # --- Provider & Model Defaults ---
    DEFAULT_LLM_PROVIDER: str = Field(default="openai", description="Default model provider: openai or ollama")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key (required for OpenAI provider)")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="Default cloud model")
    OPENAI_BUDGET_USD: float = Field(default=4.00, description="Hard ceiling for OpenAI API expenditure")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Model for vector embeddings")
    EMBEDDING_DIMENSION: int = Field(default=1536, description="Vector dimension size for pgvector")

    # --- Ollama Local Model Configuration ---
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama local HTTP endpoint")
    OLLAMA_MODEL: str = Field(default="qwen2.5:1.5b", description="Target model for local demo")

    # --- RAG & Retrieval Parameters ---
    RETRIEVAL_TOP_K: int = Field(default=5, description="Number of candidate chunks to retrieve")
    RETRIEVAL_SIMILARITY_THRESHOLD: float = Field(
        default=0.45, description="Minimum cosine similarity cutoff for grounded retrieval"
    )

    # --- Security & CORS ---
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed web origins for CORS headers",
    )


settings = Settings()
