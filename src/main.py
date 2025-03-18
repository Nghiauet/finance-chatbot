"""
Main FastAPI application for the finance chatbot backend.
"""
import argparse

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import chat_api


# Create FastAPI app
app = FastAPI(
    title="Finance Chatbot API",
    description="API for interacting with the finance chatbot",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_api.router, prefix="/api/v1", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {
        "status": "online",
        "message": "Finance Chatbot API is running",
        "docs_url": "/docs",
    }


def main():
    """Main function to run the FastAPI application with Uvicorn."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host IP to bind to"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()