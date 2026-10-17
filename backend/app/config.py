from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./local.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_UPLOAD_MB: int = 4
    LLM_PROVIDER_ORDER: str = "gemini,groq,openrouter"
    LLM_CACHE: bool = True
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
