"""
Configuration management for the Finance Chatbot application.
Handles environment variables, service credentials, and logging setup.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Base project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR.parent / "data"
LOGS_DIR = BASE_DIR.parent / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
import sys

class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # MongoDB settings
        self.MONGO_CONN_STR = os.getenv("MONGO_CONN_STR", "")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "finance_chatbot")
        
        # API settings
        self.API_VERSION = os.getenv("API_VERSION", "v1")
        self.API_PREFIX = f"/api/{self.API_VERSION}"
        
        # Application settings
        self.APP_NAME = os.getenv("APP_NAME", "Finance Chatbot")
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        
        # File storage settings
        self.UPLOAD_DIR = DATA_DIR / "uploads"
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.RAW_PDF_DIR = DATA_DIR / "raw_pdf"
        self.RAW_PDF_DIR.mkdir(exist_ok=True)
        self.CONVERTED_FILE_DIR = DATA_DIR / "converted_file"
        self.CONVERTED_FILE_DIR.mkdir(exist_ok=True)
        
        # CORS settings
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        self.BACKEND_CORS_ORIGINS = os.getenv("BACKEND_CORS_ORIGINS", "*").split(",")
        self.SEARCH_ENGINE_API_KEY = os.getenv("SEARCH_ENGINE_API_KEY")
        self.SEARCH_ENGINE_CSE_ID = os.getenv("SEARCH_ENGINE_CSE_ID")

# Create a global settings instance
settings = Settings()

class LLMConfig:
    """LLM configuration for the application."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL")
        self.url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.top_p = float(os.getenv("LLM_TOP_P", "0.95"))
        self.top_k = int(os.getenv("LLM_TOP_K", "40"))


# Create a global LLMConfig instance
llm_config = LLMConfig()
