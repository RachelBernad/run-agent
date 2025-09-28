"""Application settings and environment configuration."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

"""Constants for the running coach application."""

# API Messages
MSG_GOAL_CREATED = "Running program created successfully"
MSG_INVALID_GOAL = "Invalid goal parameters"
MSG_INVALID_TIME = "Invalid time frame"
MSG_SERVER_ERROR = "Internal server error occurred"
MSG_PROGRAM_NOT_FOUND = "Program not found"

# Validation Messages
MSG_GOAL_TOO_SMALL = "Goal must be at least 1 km"
MSG_GOAL_TOO_LARGE = "Goal must be less than 1000 km"
MSG_TIME_TOO_SHORT = "Time frame must be at least 1 week"
MSG_TIME_TOO_LONG = "Time frame must be less than 52 weeks"

# Logging Messages
LOG_STARTUP = "Running coach API starting up"
LOG_SHUTDOWN = "Running coach API shutting down"
LOG_REQUEST_RECEIVED = "Received request for running program"
LOG_PROGRAM_GENERATED = "Running program generated successfully"
LOG_PROGRAM_SAVED = "Program saved to memory"
LOG_HISTORY_REQUESTED = "History requested"
LOG_ERROR_OCCURRED = "Error occurred during request processing"

# Default Values
DEFAULT_GOAL_KM = 5.0
DEFAULT_TIME_WEEKS = 8
MIN_GOAL_KM = 1.0
MAX_GOAL_KM = 1000.0
MIN_TIME_WEEKS = 1
MAX_TIME_WEEKS = 52

# API Configuration
API_TAGS_METADATA = [
    {
        "name": "programs",
        "description": "Generate and manage running programs",
    },
    {
        "name": "history",
        "description": "View previously generated programs",
    },
]

# Memory Storage
MEMORY_KEY_PREFIX = "program_"
MEMORY_MAX_ENTRIES = 1000
load_dotenv()
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Ollama Configuration
    ollama_base_url: str = Field("http://localhost:11434", description="Ollama server base URL")
    ollama_model: str = Field("hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M", description="Ollama model name")
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(True, env="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field("running-coach-analysis", env="LANGCHAIN_PROJECT")
    langchain_api_key: str = Field("", env="LANGCHAIN_API_KEY")

    # FastAPI Configuration
    app_title: str = Field("Running Coach API", description="Application title")
    app_description: str = Field("AI-powered running coach with plan analysis", description="Application description")
    app_version: str = Field("1.0.0", description="Application version")
    debug: bool = Field(False, description="Debug mode")
    
    # Server Configuration
    host: str = Field("127.0.0.1", description="Server host")
    port: int = Field(8000, description="Server port")
    reload: bool = Field(False, description="Auto-reload on changes")
    
    # LLM Configuration
    llm_temperature: float = Field(0.1, description="LLM temperature setting")
    
    # CORS Configuration
    cors_origins: list[str] = Field(["*"], description="Allowed CORS origins")
    cors_credentials: bool = Field(True, description="Allow CORS credentials")
    cors_methods: list[str] = Field(["*"], description="Allowed CORS methods")
    cors_headers: list[str] = Field(["*"], description="Allowed CORS headers")
    
    # Logging Configuration
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

    # garmin credentials
    garmin_username: str = Field(..., description="Garmin user name")
    garmin_password: str = Field(..., description="Garmin password")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings
