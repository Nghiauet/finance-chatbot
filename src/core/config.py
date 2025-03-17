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


# Create a global settings instance
settings = Settings()


class LLMConfig:
    """LLM configuration for the application."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self.top_p = float(os.getenv("LLM_TOP_P", "0.95"))
        self.top_k = int(os.getenv("LLM_TOP_K", "40"))


# Create a global LLMConfig instance
llm_config = LLMConfig()

# Logging configuration
def get_logger(name, request_id=None):
    """
    Get a configured logger instance.
    
    Args:
        name: Name of the logger (typically __name__)
        request_id: Optional request ID for tracking requests across logs
        
    Returns:
        Configured logger instance
    """
    from loguru import logger
    
    # Configure logger format
    format_string = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    format_string += "<level>{level: <8}</level> | "
    format_string += "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    
    if request_id:
        format_string += f"<yellow>request_id={request_id}</yellow> | "
    
    format_string += "<level>{message}</level>"
    
    # Remove default logger and add custom configuration
    logger.remove()
    logger.add(sys.stderr, format=format_string, level="DEBUG" if settings.DEBUG else "INFO")
    logger.add(
        LOGS_DIR / "app.log",
        rotation="10 MB",
        retention="1 week",
        format=format_string,
        level="DEBUG",
        enqueue=True
    )
    
    return logger.bind(name=name)
