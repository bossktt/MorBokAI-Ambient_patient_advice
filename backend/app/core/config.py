# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional

# Path to workspace root directory containing .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ROOT_ENV = os.path.join(BASE_DIR, ".env")

# Set PyThaiNLP data directory within the project workspace to avoid permission errors
os.environ["PYTHAINLP_DATA_DIR"] = os.path.join(BASE_DIR, "backend", "pythainlp_data")

class Settings(BaseSettings):
    APP_NAME: str = "Ambient PVS Platform"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-this-super-secret-key-32bytes-min"

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://pvs_admin:SecretPassword123@localhost:5432/pvs_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ASR Multi-Tier Pipeline Configuration
    PRIMARY_ASR_ENGINE: str = "google-speech"      # Step 1 Primary: Google Speech-to-Text (via gcp-key.json)
    GCP_KEY_PATH: str = "gcp-key.json"             # Path to GCP credentials file

    SECONDARY_ASR_ENGINE: str = "typhoon-asr"       # Step 2 Secondary: Local Typhoon ASR Realtime
    TYPHOON_ASR_MODEL: str = "bossktt/typhoon-asr-realtime-bucket"
    TYPHOON_ASR_API_KEY: Optional[str] = None
    TYPHOON_API_KEY: Optional[str] = None
    ASR_TYPHOON_HOST: str = "http://localhost:8000"
    TYPHOON_ASR_WEBSOCKET_URL: str = "wss://api.opn.ai/v1/audio/transcriptions/realtime"

    WHISPER_MODEL: str = "Systran/faster-whisper-small"
    ASR_WHISPER_HOST: str = "http://localhost:8001"
    HF_TOKEN: Optional[str] = None

    ASSEMBLYAI_API_KEY: Optional[str] = None

    # Clinical LLM Adapter Configuration
    DEFAULT_LLM_PROVIDER: str = "openrouter"      # Primary: OpenRouter (Gemini via API)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"
    OPENROUTER_PROVIDER: Optional[str] = "Google"

    # Gemini AI Studio (direct fallback)
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_API_KEY: Optional[str] = None           # AI Studio API key (AIzaSy...)

    # Azure OpenAI (enterprise HIPAA fallback)
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None

    # LINE OA & LIFF
    LINE_CHANNEL_SECRET: Optional[str] = None
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_LIFF_ID: Optional[str] = None
    LINE_BASIC_ID: Optional[str] = None

    class Config:
        env_file = (ROOT_ENV, ".env")
        extra = "ignore"

settings = Settings()
