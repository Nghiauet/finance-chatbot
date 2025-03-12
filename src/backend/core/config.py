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
BASE_DIR = Path(__file__).parent.parent  # src/backend -> src
DATA_DIR = BASE_DIR.parent / "data"
LOGS_DIR = BASE_DIR.parent / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# LLM Configuration
LLM_CONFIG = {
    "api_key": os.getenv("GOOGLE_API_KEY"),
    "default_model": os.getenv("DEFAULT_MODEL", "gemini-2.0-flash"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
    "top_p": float(os.getenv("LLM_TOP_P", "0.95")),
    "top_k": int(os.getenv("LLM_TOP_K", "40")),
}

# S3 Configuration
S3_CONFIG = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "region_name": os.getenv("AWS_REGION", "us-east-1"),
    "bucket_name": os.getenv("S3_BUCKET_NAME"),
}

# Database Configuration - Example (adjust as needed for your database)
DATABASE_CONFIG = {
    "db_url": os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost/finance_chatbot"
    )
}

# CORS Configuration
CORS_CONFIG = {
    "origins": os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:3000").split(",")
}
CORS_ORIGINS = CORS_CONFIG["origins"]


class LogConfig:
    """Centralized logging configuration for the application."""
    
    def __init__(self, app_name: str = "finance_chatbot"):
        """
        Initialize logging configuration.
        
        Args:
            app_name: Name of the application for log identification
        """
        self.app_name = app_name
        self.log_file = LOGS_DIR / f"{app_name}.log"
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Set up loguru logger with file and console outputs."""
        # Remove default logger
        logger.remove()
        
        # Add console logger (INFO level and above)
        logger.add(
            sink=lambda msg: print(msg),
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        # Add file logger (DEBUG level and above with rotation)
        logger.add(
            sink=str(self.log_file),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week",
            compression="zip"
        )
    
    def get_logger(self, module_name: str):
        """
        Get a logger instance for a specific module.
        
        Args:
            module_name: Name of the module for log identification
            
        Returns:
            Configured logger instance
        """
        return logger.bind(name=f"{self.app_name}.{module_name}")


# Create default logging configuration
log_config = LogConfig()


def get_logger(module_name: str):
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        Configured logger instance
    """
    return log_config.get_logger(module_name)