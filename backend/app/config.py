import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./local.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_UPLOAD_MB: int = 4
    LLM_PROVIDER_ORDER: str = "gemini,groq,openrouter"
    LLM_CACHE: bool = True
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b,qwen/qwen3.8-27b"  # text only; comma-separated, tried in order
    OPENROUTER_API_KEY: str = ""
    # Backup when Gemini has no quota; must accept images. Several models: comma-separated, tried in order.
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free,nvidia/nemotron-3.5-super-vl:free"
    ADMIN_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def writable_sqlite_on_vercel(self) -> "Settings":
        """Vercel's disk is read-only except /tmp. Without Neon the API still starts, with a throwaway DB."""
        if os.environ.get("VERCEL") and self.DATABASE_URL == "sqlite:///./local.db":
            self.DATABASE_URL = "sqlite:////tmp/local.db"
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
