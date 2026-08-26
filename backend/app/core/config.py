import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RuralBiz AI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = "ruralbiz-ai-super-secret-key-development-change-in-prod-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database Settings (Supports SQLite for lightweight testing & PostgreSQL AsyncPG for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./ruralbiz.db"
    
    # Gemini API Key
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    # Vernacular Language Support
    DEFAULT_LANGUAGE: str = "te"  # te: Telugu, hi: Hindi, en: English
    SUPPORTED_LANGUAGES: List[str] = ["en", "te", "hi"]
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

