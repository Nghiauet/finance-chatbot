# main.py
"""
Main entry point for the finance chatbot application.
This file sets up the FastAPI application, initializes the database,
and starts the web server.
"""

import os
import asyncio
import logging
import argparse
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapter.database.connection import init_db, get_session_factory
from adapter.database.models import Base
from api.v1.deps import init_dependencies
from api.v1.routes import company, financial_statements, company_extras, financial_analysis, chat
from core.app_factory import create_app, init_app  # Import from core

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


async def create_sample_data(app: FastAPI) -> None:
    """Create sample data for demo purposes."""
    # This would create sample companies, financial statements, etc.
    # Implementation would depend on how you want to structure your demo data
    logger.info("Creating sample data")
    # Implement sample data creation here
    pass


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Finance Chatbot API")
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind the server to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to bind the server to"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Create sample data for demo purposes"
    )
    return parser.parse_args()


async def main():
    """Main entry point for the application."""
    args = parse_args()

    # Create the FastAPI application
    app = create_app()  # Use function from core

    # Initialize the application
    await init_app(app) # Use function from core

    # Create sample data if requested
    if args.sample_data:
        await create_sample_data(app)

    # Start the server
    logger.info(f"Starting server on {args.host}:{args.port}")
    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())