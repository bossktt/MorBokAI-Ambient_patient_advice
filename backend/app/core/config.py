# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional

# Path to workspace root directory containing .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ROOT_ENV = os.path.join(BASE_DIR, ".env")

# Set PyThaiNLP data directory
os.environ["PYTHAINLP_DATA_DIR"] = os.path.join(BASE_DIR, "backend", "pythainlp_data")

class Settings(BaseSettings):
    APP_NAME: str = "Ambient PVS Platform"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-this-super-secret-key-32bytes-min"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://pvs_admin:SecretPassword123@localhost:5432/pvs_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Clinical LLM Adapter
    DEFAULT_LLM_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"
    OPENROUTER_PROVIDER: Optional[str] = "google-vertex"

    # Gemini AI Studio (fallback)
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_API_KEY: Optional[str] = None

    # AssemblyAI (ASR fallback for audio pipeline)
    ASSEMBLYAI_API_KEY: Optional[str] = None

    # Logging Configuration
    ENABLE_ENCOUNTER_LOGGING: bool = True
    LOGS_DIR: str = os.path.join(BASE_DIR, "backend", "logs")
    LOG_FILE_NAME: str = "encounter_logs.jsonl"

    class Config:
        env_file = (ROOT_ENV, ".env")
        extra = "ignore"

settings = Settings()
