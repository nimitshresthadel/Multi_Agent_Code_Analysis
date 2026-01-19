from typing import List
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Code Analysis System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str="postgresql+psycopg2://sampleuser:samplepass@localhost:5430/sample_db"
    SECRET_KEY: str="dev-secret-change-me"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # # OpenAI Configuration
    # OPENAI_API_KEY = your - openai - api - key - here
    #
    # # Tavily Search (Optional - for better web search)
    # TAVILY_API_KEY = your - tavily - api - key - here  # Optional
    #
    # # LangGraph Configuration
    # LANGCHAIN_TRACING_V2 = true
    # LANGCHAIN_ENDPOINT = https: // api.smith.langchain.com
    # LANGCHAIN_API_KEY = your - langchain - api - key - here  # Optional for tracing
    #
    # # Langfuse (Optional - for observability)
    # LANGFUSE_PUBLIC_KEY = your - langfuse - public - key
    # LANGFUSE_SECRET_KEY = your - langfuse - secret - key
    # LANGFUSE_HOST = https: // cloud.langfuse.com

    # File Storage
    UPLOAD_DIR: str = "backend/app/storage/uploads"  # Where ZIPs are saved
    PROJECT_DIR: str = "backend/app/storage/projects"  # Where ZIPs are extracted
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB

    # Allowed file extensions
    ALLOWED_EXTENSIONS: List[str] = [".zip"]

    # GitHub
    GITHUB_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8501"]

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure storage directories exist
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.PROJECT_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
