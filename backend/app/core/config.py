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

    # Repeatable clinical extraction. Temperature reduces variation, while the
    # server-side content-addressed cache is the hard consistency guarantee.
    SUMMARY_GENERATION_TEMPERATURE: float = 0.05
    SUMMARY_GENERATION_SEED: int = 42
    SUMMARY_PROMPT_VERSION: str = "grounded-clinical-summary-v1"

    # ASR quality gate before any clinical LLM call.
    ASR_QUALITY_MIN_SCORE: float = 0.65
    ASR_QUALITY_MIN_CONFIDENCE: float = 0.55
    ASR_QUALITY_MIN_CHARS: int = 10
    OPENROUTER_ASR_MODEL: str = "x-ai/grok-stt-1.0"
    OPENROUTER_ASR_VERIFIER_MODEL: str = "openai/whisper-large-v3-turbo"
    ASR_MIN_MODEL_AGREEMENT: float = 0.85
    ASR_MIN_DICTIONARY_COVERAGE: float = 0.4
    OPENROUTER_ASR_TEMPERATURE: float = 0.0
    ASR_DOMAIN_PROMPT: str = (
        "คำแนะนำทางการแพทย์ ห้องฉุกเฉิน ประเทศไทย "
        "Metformin Amlodipine Paracetamol Cetirizine Loratadine "
        "มิลลิกรัม เม็ด รับประทาน ก่อนนอน หลังอาหาร เช้า เย็น นัดติดตามอาการ"
    )

    # AssemblyAI (ASR fallback for audio pipeline)
    ASSEMBLYAI_API_KEY: Optional[str] = None
    GCP_KEY_PATH: Optional[str] = "gcp-key.json"

    # Logging & Google Drive Auto-Sync Configuration
    ENABLE_ENCOUNTER_LOGGING: bool = True
    LOGS_DIR: str = os.path.join(BASE_DIR, "backend", "logs")
    LOG_FILE_NAME: str = "encounter_logs.jsonl"
    GDRIVE_WEBHOOK_URL: Optional[str] = None

    class Config:
        env_file = (ROOT_ENV, ".env")
        extra = "ignore"

settings = Settings()
