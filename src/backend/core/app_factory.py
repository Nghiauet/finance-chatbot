import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapter.database.connection import init_db, get_session_factory
from api.v1.deps import init_dependencies
from api.v1.routes import company, financial_statements, company_extras, financial_analysis, chat
from core.config import CORS_ORIGINS

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Finance Chatbot API",
        description="REST API for finance chatbot application",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    origins = CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(company.router)
    app.include_router(financial_statements.router)
    app.include_router(company_extras.router)
    app.include_router(financial_analysis.router)
    app.include_router(chat.router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Welcome to Finance Chatbot API",
            "documentation": "/docs",
            "redoc": "/redoc"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


async def init_app(app: FastAPI) -> None:
    """Initialize the application, database, and dependencies."""
    # Get database URL from environment or use default
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost/finance_chatbot"
    )

    logger.info(f"Initializing database connection to {db_url}")

    try:
        # Initialize database
        engine = await init_db(db_url)
        session_factory = get_session_factory(engine)

        # Initialize dependencies
        init_dependencies(session_factory)

        logger.info("Application initialized successfully")

        # Add startup and shutdown events to the app
        @app.on_event("startup")
        async def startup_event():
            logger.info("Application starting up")

        @app.on_event("shutdown")
        async def shutdown_event():
            logger.info("Application shutting down")
            # Cleanup resources here if needed
            pass

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise 