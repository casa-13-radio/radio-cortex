# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://cortex:cortex_dev_password@localhost:5432/radiocortex")
    
    # Hunter Agent
    hunter_download_dir: str = os.getenv("HUNTER_DOWNLOAD_DIR", "/tmp/hunter_downloads")
    hunter_timeout_seconds: int = int(os.getenv("HUNTER_TIMEOUT_SECONDS", "30"))
    hunter_max_concurrent_downloads: int = int(os.getenv("HUNTER_MAX_CONCURRENT_DOWNLOADS", "3"))
    
    # Librarian Agent
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    librarian_embedding_model: str = os.getenv("LIBRARIAN_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    librarian_llm_model: str = os.getenv("LIBRARIAN_LLM_MODEL", "llama3-70b-8192")
    
    # App
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"

settings = Settings()