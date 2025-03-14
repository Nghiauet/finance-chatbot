"""
Main FastAPI application for the finance chatbot backend.
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1 import chat_api

# Create FastAPI app
app = FastAPI(
    title="Finance Chatbot API",
    description="API for interacting with the finance chatbot",
    version="1.0.0"
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
app.include_router(
    chat_api.router,
    prefix="/api/v1",
    tags=["chat"]
)

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {
        "status": "online",
        "message": "Finance Chatbot API is running",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    try:
        config = uvicorn.Config(app, host="0.0.0.0", port=8123, reload=True)
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"An error occurred: {e}")